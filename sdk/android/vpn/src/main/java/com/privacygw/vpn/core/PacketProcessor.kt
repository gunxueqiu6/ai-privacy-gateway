package com.privacygw.vpn.core

import android.util.Log
import com.privacygw.vpn.protocol.*
import kotlinx.coroutines.*
import java.io.FileDescriptor
import java.io.FileInputStream
import java.io.FileOutputStream
import java.net.InetSocketAddress
import java.net.Socket
import java.nio.ByteBuffer
import java.nio.channels.FileChannel
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Main packet processing loop.
 *
 * Reads raw IP packets from the TUN interface, parses headers, and classifies
 * traffic. For HTTP connections to AI service domains, it intercepts the TCP
 * stream, buffers the HTTP request, calls the PrivacyGateway to mask PII,
 * forwards to the real server via a raw socket, and returns the response
 * through the TUN interface.
 *
 * Passthrough traffic is written back to the TUN output channel unmodified.
 * HTTPS traffic to AI domains is detected via SNI and tracked for stats.
 *
 * TCP handshake for intercepted connections:
 *   1. Client SYN        -> Open real socket to server, send fake SYN-ACK to client
 *   2. Client ACK         -> Handshake complete locally (client thinks it connected)
 *   3. Client data        -> Buffer HTTP request
 *   4. Complete request   -> Mask body, send via real socket to server
 *   5. Server response    -> Build IP/TCP response packets, write to TUN
 *   6. Client ACK/cleanup -> Release connection
 */
class PacketProcessor(
    private val vpnFd: FileDescriptor,
    private val gatewayUrl: String,
    private val gatewayApiKey: String,
    private val onStatsChanged: (() -> Unit)?,
    /** Port where the local MITM proxy is listening. 0 = HTTPS interception disabled. */
    private val proxyPort: Int = 0
) {

    companion object {
        private const val TAG = "PacketProcessor"
        private const val MAX_PACKET_SIZE = 65535

        // Ports we consider for HTTP interception
        private val HTTP_PORTS = setOf(80, 8080, 8000, 3000, 5000)
        private const val HTTPS_PORT = 443

        // Timeout for upstream server connections
        private const val UPSTREAM_CONNECT_TIMEOUT = 10_000
        private const val UPSTREAM_READ_TIMEOUT = 60_000
    }

    private lateinit var tunOutput: FileChannel

    private val isRunning = AtomicBoolean(true)
    private var processingThread: Thread? = null
    private var cleanupJob: Job? = null

    private val connectionManager = TcpConnectionManager()

    // Stats
    private var totalPackets = 0L
    private var maskedRequests = 0L
    private var interceptedConnections = 0L
    private var passthroughPackets = 0L
    private var httpPacketsSeen = 0L
    private var httpsConnectionsSeen = 0L

    // Our server-side sequence number base (random starting point for fake connections)
    private val ourSeqBase = (System.currentTimeMillis() and 0xFFFFFFFF).toLong()

    private val processorScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun start() {
        val input = FileInputStream(vpnFd)
        val output = FileOutputStream(vpnFd)
        tunOutput = output.channel

        val inputChannel = input.channel
        val buffer = ByteBuffer.allocate(MAX_PACKET_SIZE)

        Log.i(TAG, "Packet processor started, gateway=$gatewayUrl")

        processingThread = Thread {
            startCleanupTimer()
            try {
                while (isRunning.get()) {
                    buffer.clear()
                    val bytesRead = inputChannel.read(buffer)
                    if (bytesRead < 0) break
                    if (bytesRead == 0) continue

                    buffer.flip()
                    totalPackets++
                    processPacket(buffer)
                }
            } catch (e: Exception) {
                if (isRunning.get()) Log.e(TAG, "Packet processing error", e)
            } finally {
                cleanup()
                Log.i(TAG, "Processor stopped. Intercepted=$interceptedConnections Masked=$maskedRequests")
            }
        }.apply { name = "vpn-packet-processor"; start() }
    }

    fun stop() {
        isRunning.set(false)
        processingThread?.join(5000)
        cleanup()
    }

    private fun processPacket(buffer: ByteBuffer) {
        buffer.mark()

        val ipHeader = PacketParser.parseIpHeader(buffer) ?: run {
            buffer.reset(); writePassthrough(buffer); return
        }

        // Skip non-TCP and fragmented packets
        if (ipHeader.protocol != PacketParser.PROTOCOL_TCP ||
            ipHeader.fragmentOffset != 0
        ) {
            buffer.reset(); writePassthrough(buffer); return
        }

        val tcpHeader = PacketParser.parseTcpHeader(buffer) ?: run {
            buffer.reset(); writePassthrough(buffer); return
        }

        val srcIp = ipHeader.sourceIpString
        val dstIp = ipHeader.destIpString
        val srcPort = tcpHeader.sourcePort
        val dstPort = tcpHeader.destPort

        val clientKey = TcpConnectionKey(srcIp, dstIp, srcPort, dstPort)

        // Read TCP payload
        val payload = if (buffer.remaining() > 0) {
            val data = ByteArray(buffer.remaining())
            buffer.get(data); data
        } else byteArrayOf()

        // Decision tree
        if (tcpHeader.flags.rst) {
            handleRst(clientKey)
            buffer.reset(); writePassthrough(buffer); return
        }

        if (tcpHeader.flags.syn && !tcpHeader.flags.ack) {
            if (dstPort == HTTPS_PORT && proxyPort > 0) {
                // Intercept HTTPS — route through local MITM proxy
                handleHttpsSyn(clientKey, dstIp, dstPort, ipHeader, tcpHeader)
                if (connectionManager.get(clientKey) == null) {
                    buffer.reset(); writePassthrough(buffer)
                }
                return
            } else if (dstPort in HTTP_PORTS) {
                handleSyn(clientKey, dstIp, dstPort, ipHeader, tcpHeader)
                val wasIntercepted = connectionManager.get(clientKey) != null
                if (wasIntercepted) return
            }
            // Non-intercepted SYN -> passthrough
            buffer.reset(); writePassthrough(buffer)
            return
        }

        // Check for existing intercepted connection
        val conn = connectionManager.get(clientKey)
        if (conn != null) {
            if (conn.isHttps) {
                handleHttpsData(conn, payload, ipHeader, tcpHeader)
            } else {
                handleInterceptedData(conn, payload, ipHeader, tcpHeader)
            }
            return
        }

        // HTTPS SNI detection on non-intercepted data packets (stats only)
        if (dstPort == HTTPS_PORT && payload.isNotEmpty() &&
            payload[0].toInt() == 22 /* TLS handshake */
        ) {
            val sniResult = TlsParser.extractSni(payload)
            if (sniResult != null && TlsParser.isAiServiceHost(sniResult.sni)) {
                Log.i(TAG, "HTTPS AI connection (passthrough): ${sniResult.sni}")
                httpsConnectionsSeen++
            }
        }

        // Default: passthrough
        buffer.reset()
        writePassthrough(buffer)
        passthroughPackets++
    }

    /**
     * Handle a SYN packet for potential HTTP interception.
     *
     * For HTTP ports, we intercept the connection:
     * 1. Create connection tracking entry
     * 2. Open a real socket to the destination server
     * 3. Send fake SYN-ACK to the client through TUN
     */
    /**
     * Return true if the SYN was intercepted (consumed, caller should NOT passthrough).
     * Return false if the SYN should be passed through as normal traffic.
     */
    private fun handleSyn(
        clientKey: TcpConnectionKey,
        dstIp: String,
        dstPort: Int,
        ipHeader: IpHeader,
        tcpHeader: TcpHeader
    ) {
        if (dstPort !in HTTP_PORTS) {
            return
        }

        httpPacketsSeen++

        // Start interception
        val conn = connectionManager.getOrCreate(clientKey, "$dstIp:$dstPort", false)
        conn.clientSeq = tcpHeader.sequenceNumber
        conn.state = ConnectionState.ESTABLISHED

        Log.d(TAG, "Intercepting HTTP connection: ${clientKey.sourceIp}:${clientKey.sourcePort}" +
                " -> $dstIp:$dstPort")

        // Open real socket to the destination server in background
        processorScope.launch {
            try {
                val socket = Socket()
                socket.connect(InetSocketAddress(dstIp, dstPort), UPSTREAM_CONNECT_TIMEOUT)
                socket.soTimeout = UPSTREAM_READ_TIMEOUT
                conn.upstreamSocket = socket
                conn.upstreamOutput = socket.getOutputStream()
                conn.serverSeq = ourSeqBase

                Log.d(TAG, "Upstream connected to $dstIp:$dstPort")

                // Send fake SYN-ACK to the client
                val synAckPacket = buildSynAckPacket(ipHeader, tcpHeader, conn)
                tunOutput.write(ByteBuffer.wrap(synAckPacket))

                // Start reading upstream responses in background
                launch {
                    try {
                        val inputStream = socket.getInputStream()
                        val responseBuf = ByteArray(MAX_PACKET_SIZE)
                        val responseOutput = java.io.ByteArrayOutputStream()

                        while (isRunning.get() && conn.state != ConnectionState.CLOSED) {
                            val read = inputStream.read(responseBuf)
                            if (read < 0) break

                            responseOutput.reset()
                            responseOutput.write(responseBuf, 0, read)

                            val responseData = responseOutput.toByteArray()
                            Log.d(TAG, "Upstream response: ${responseData.size} bytes for ${conn.key}")

                            // Build response packets and write to TUN
                            val responsePackets = buildDataResponsePackets(conn, responseData)
                            for (pkt in responsePackets) {
                                tunOutput.write(ByteBuffer.wrap(pkt))
                            }

                            // Send FIN to client
                            val finPacket = buildFinPacket(conn, responseData.size)
                            tunOutput.write(ByteBuffer.wrap(finPacket))

                            conn.state = ConnectionState.CLOSED
                            connectionManager.remove(conn.key)
                        }
                    } catch (e: Exception) {
                        Log.w(TAG, "Upstream read error for ${conn.key}: ${e.message}")
                        conn.state = ConnectionState.CLOSED
                        connectionManager.remove(conn.key)
                    }
                }
            } catch (e: Exception) {
                Log.w(TAG, "Failed to connect upstream for ${conn.key}: ${e.message}")
                // Send RST to the client so it knows the connection failed
                val rstPacket = PacketParser.buildRstPacket(ipHeader, tcpHeader)
                try { tunOutput.write(ByteBuffer.wrap(rstPacket)) } catch (_: Exception) {}
                connectionManager.remove(conn.key)
            }
        }
    }

    /**
     * Build a SYN-ACK packet for intercepted connections.
     */
    private fun buildSynAckPacket(
        ipHeader: IpHeader,
        tcpHeader: TcpHeader,
        conn: InterceptedConnection
    ): ByteArray {
        val respIp = PacketParser.buildIpHeader(
            sourceIp = ipHeader.destIp,
            destIp = ipHeader.sourceIp,
            payloadLength = 20,
            identification = (ipHeader.identification + 1) and 0xFFFF,
            protocol = PacketParser.PROTOCOL_TCP
        )

        val respTcp = PacketParser.buildTcpHeader(
            sourcePort = tcpHeader.destPort,
            destPort = tcpHeader.sourcePort,
            sequenceNumber = conn.serverSeq,
            acknowledgmentNumber = (conn.clientSeq + 1) and 0xFFFFFFFFL,
            flags = TcpHeader.TcpFlags(
                fin = false, syn = true, rst = false,
                psh = false, ack = true, urg = false
            ),
            windowSize = 65535
        )

        val tcpChecksum = PacketParser.computeTcpChecksum(
            ipHeader.destIp, ipHeader.sourceIp, respTcp
        )
        respTcp[16] = ((tcpChecksum shr 8) and 0xFF).toByte()
        respTcp[17] = (tcpChecksum and 0xFF).toByte()

        return respIp + respTcp
    }

    /**
     * Handle a data packet on an intercepted connection.
     */
    private fun handleInterceptedData(
        conn: InterceptedConnection,
        payload: ByteArray,
        ipHeader: IpHeader,
        tcpHeader: TcpHeader
    ) {
        if (payload.isEmpty()) return

        conn.clientAck = tcpHeader.acknowledgmentNumber
        conn.clientWindow = tcpHeader.windowSize

        // Buffer the HTTP request payload
        val buffered = connectionManager.bufferClientData(conn, payload)
        if (!buffered) {
            Log.w(TAG, "Buffer overflow for ${conn.key}")
            connectionManager.remove(conn.key)
            return
        }

        // Try to extract complete HTTP request
        val httpRequest = connectionManager.tryExtractHttpRequest(conn)
        if (httpRequest != null) {
            interceptedConnections++
            val host = HttpParser.extractHost(httpRequest)

            val isAiService = HttpParser.isAiServiceDomain(host)
            val hasBody = httpRequest.body != null && httpRequest.body.isNotEmpty()

            if (!isAiService || !hasBody) {
                Log.d(TAG, if (!isAiService) "Non-AI request to $host"
                           else "No body to mask for $host, forwarding raw")
                forwardRequestToUpstream(conn, httpRequest.originalData)
                return
            }

            Log.i(TAG, "Masking HTTP request to $host: ${httpRequest.method} ${httpRequest.path}")

            processorScope.launch {
                try {
                    // Call PrivacyGateway SDK to mask PII in the body
                    val bodyText = httpRequest.body!!.decodeToString()
                    val maskResult = withContext(Dispatchers.IO) {
                        com.privacygw.sdk.PrivacyGateway.getInstance().mask(bodyText)
                    }

                    val maskedBody = maskResult.maskedText.encodeToByteArray()
                    val maskedRequest = HttpParser.buildModifiedRequest(httpRequest, maskedBody)

                    Log.i(TAG, "Masked ${maskResult.entities.size} items for $host")
                    maskedRequests++
                    onStatsChanged?.invoke()

                    // Send masked request via upstream socket
                    forwardRequestToUpstream(conn, maskedRequest)

                } catch (e: Exception) {
                    Log.w(TAG, "Masking failed for $host: ${e.message}")
                    // Fall back to original request
                    forwardRequestToUpstream(conn, httpRequest.originalData)
                }
            }
        }
    }

    /**
     * Forward raw HTTP request bytes via the upstream socket.
     */
    private fun forwardRequestToUpstream(conn: InterceptedConnection, requestBytes: ByteArray) {
        try {
            conn.upstreamOutput?.write(requestBytes)
            conn.upstreamOutput?.flush()
            Log.d(TAG, "Forwarded ${requestBytes.size} bytes upstream for ${conn.key}")
        } catch (e: Exception) {
            Log.w(TAG, "Upstream write error for ${conn.key}: ${e.message}")
        }
    }

    /**
     * Build IP/TCP response data packets for the client.
     *
     * Our response SEQ starts at (serverSeq + 1) because the SYN-ACK
     * consumed one SEQ number.  The ACK value acknowledges all the
     * data bytes received from the client (clientSeq + 1 for SYN
     * + total buffered payload).
     */
    private fun buildDataResponsePackets(
        conn: InterceptedConnection,
        responseData: ByteArray
    ): List<ByteArray> {
        val packets = mutableListOf<ByteArray>()
        val mss = 1460
        var offset = 0
        var packetId = 1

        // Correct ACK = client's initial SEQ + 1 (for SYN) + all data bytes received
        val ackNum = (conn.clientSeq + 1 + conn.clientBufferSize) and 0xFFFFFFFFL
        // First data byte starts 1 after our SYN-ACK seq
        val ourDataStart = (conn.serverSeq + 1) and 0xFFFFFFFFL

        while (offset < responseData.size) {
            val chunkSize = minOf(mss, responseData.size - offset)
            val chunk = responseData.copyOfRange(offset, offset + chunkSize)
            val isLast = (offset + chunkSize) >= responseData.size

            val dstIp = ipToInt(conn.key.sourceIp)
            val srcIp = ipToInt(conn.key.destIp)

            val ipHdr = IpHeader(
                version = 4, ihl = 5, totalLength = 0,
                identification = packetId++, flags = 2, fragmentOffset = 0,
                ttl = 64, protocol = 6, headerChecksum = 0,
                sourceIp = srcIp, destIp = dstIp
            )

            val tcpHdr = TcpHeader(
                sourcePort = conn.key.destPort,
                destPort = conn.key.sourcePort,
                sequenceNumber = (ourDataStart + offset) and 0xFFFFFFFFL,
                acknowledgmentNumber = ackNum,
                dataOffset = 5,
                flags = TcpHeader.TcpFlags(
                    fin = false, syn = false, rst = false,
                    psh = isLast, ack = true, urg = false
                ),
                windowSize = 65535, checksum = 0, urgentPointer = 0
            )

            packets.add(PacketParser.buildTcpResponsePacket(ipHdr, tcpHdr, chunk))
            offset += chunkSize
        }

        return packets
    }

    /**
     * Build a FIN packet to close the connection from our side.
     * The caller should provide the final seq/ack state after
     * response data has been sent.
     */
    private fun buildFinPacket(
        conn: InterceptedConnection,
        responseDataSize: Int
    ): ByteArray {
        val dstIp = ipToInt(conn.key.sourceIp)
        val srcIp = ipToInt(conn.key.destIp)
        val ackNum = (conn.clientSeq + 1 + conn.clientBufferSize) and 0xFFFFFFFFL
        val ourDataEnd = (conn.serverSeq + 1 + responseDataSize) and 0xFFFFFFFFL

        val ipHdr = IpHeader(
            version = 4, ihl = 5, totalLength = 0,
            identification = 9999, flags = 2, fragmentOffset = 0,
            ttl = 64, protocol = 6, headerChecksum = 0,
            sourceIp = srcIp, destIp = dstIp
        )

        val tcpHdr = TcpHeader(
            sourcePort = conn.key.destPort, destPort = conn.key.sourcePort,
            sequenceNumber = ourDataEnd,
            acknowledgmentNumber = ackNum,
            dataOffset = 5,
            flags = TcpHeader.TcpFlags(
                fin = true, syn = false, rst = false,
                psh = false, ack = true, urg = false
            ),
            windowSize = 65535, checksum = 0, urgentPointer = 0
        )

        return PacketParser.buildTcpResponsePacket(ipHdr, tcpHdr, byteArrayOf())
    }

    private fun handleRst(key: TcpConnectionKey) {
        connectionManager.remove(key)
    }

    private fun writePassthrough(buffer: ByteBuffer) {
        try {
            buffer.position(0)
            tunOutput.write(buffer)
        } catch (e: Exception) {
            Log.w(TAG, "Passthrough write error", e)
        }
    }

    private fun startCleanupTimer() {
        cleanupJob = processorScope.launch {
            while (isRunning.get()) {
                delay(TcpConnectionManager.CLEANUP_INTERVAL_MS)
                connectionManager.cleanupExpired()
            }
        }
    }

    private fun cleanup() {
        cleanupJob?.cancel()
        connectionManager.clear()
        processorScope.cancel()
    }

    private fun ipToInt(ip: String): Int {
        val parts = ip.split('.')
        if (parts.size != 4) return 0
        return ((parts[0].toInt() and 0xFF) shl 24) or
                ((parts[1].toInt() and 0xFF) shl 16) or
                ((parts[2].toInt() and 0xFF) shl 8) or
                (parts[3].toInt() and 0xFF)
    }

    // Stats accessors
    fun getTotalPackets() = totalPackets
    fun getMaskedRequests() = maskedRequests
    fun getInterceptedConnections() = interceptedConnections
    fun getActiveConnections() = connectionManager.activeCount
    fun getHttpsConnectionsSeen() = httpsConnectionsSeen
}
