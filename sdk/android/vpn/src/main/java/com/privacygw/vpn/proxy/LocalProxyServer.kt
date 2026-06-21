package com.privacygw.vpn.proxy

import android.util.Log
import com.privacygw.sdk.PrivacyGateway
import com.privacygw.vpn.protocol.HttpParser
import com.privacygw.vpn.protocol.TlsParser
import kotlinx.coroutines.*
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.ByteBuffer
import java.security.SecureRandom
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicBoolean
import javax.net.ssl.*

/**
 * Local MITM proxy server for HTTPS interception.
 *
 * Listens on 127.0.0.1:PROXY_PORT and accepts connections forwarded by
 * PacketProcessor. For each connection it:
 *
 * 1. Reads TLS ClientHello from the client
 * 2. Extracts the SNI (Server Name Indication)
 * 3. If the domain is an AI service:
 *    - Terminates TLS with a dynamically-generated cert for the domain
 *    - Reads the decrypted HTTP request
 *    - Masks PII in the request body via PrivacyGateway SDK
 *    - Opens a new TLS connection to the real server
 *    - Forwards the masked request and streams the response back
 * 4. If the domain is NOT an AI service:
 *    - Opens a raw TCP connection to the real server
 *    - Bidirectional relay (encrypted bytes pass through untouched)
 *
 * The proxy communicates with PacketProcessor via a simple binary protocol:
 *   [dest_ip: 4B][dest_port: 2B][raw client data...]
 */
class LocalProxyServer(
    private val certManager: CertManager,
    private val gatewayUrl: String,
    private val gatewayApiKey: String,
    private val onStatsChanged: (() -> Unit)?
) {
    companion object {
        private const val TAG = "LocalProxyServer"
        const val DEFAULT_PORT = 8443
        private const val BUFFER_SIZE = 65536
        private const val CONNECT_TIMEOUT_MS = 10_000
        private const val UPSTREAM_READ_TIMEOUT_MS = 120_000
        private const val MAX_RECORDS_SIZE = 65536

        // Buffered TLS handshake bytes to try for SNI extraction
        private const val SNI_READ_SIZE = 4096
    }

    private val serverSocket: ServerSocket = ServerSocket()
    private val isRunning = AtomicBoolean(false)
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val activeConnections = ConcurrentHashMap<Socket, Boolean>()

    /** The port the proxy is listening on (assigned by OS if DEFAULT_PORT is busy). */
    @Volatile
    var port: Int = DEFAULT_PORT
        private set

    /**
     * Start the proxy server on localhost.
     */
    fun start(): Boolean {
        if (isRunning.getAndSet(true)) return true
        return try {
            serverSocket.reuseAddress = true
            serverSocket.bind(InetSocketAddress("127.0.0.1", DEFAULT_PORT), 50)
            port = serverSocket.localPort
            Log.i(TAG, "Proxy server listening on 127.0.0.1:$port")

            scope.launch {
                while (isRunning.get()) {
                    try {
                        val clientSocket = serverSocket.accept()
                        clientSocket.soTimeout = UPSTREAM_READ_TIMEOUT_MS
                        activeConnections[clientSocket] = true
                        scope.launch {
                            try {
                                handleConnection(clientSocket)
                            } catch (e: CancellationException) {
                                throw e
                            } catch (e: Exception) {
                                if (isRunning.get()) {
                                    Log.w(TAG, "Connection handler error: ${e.message}")
                                }
                            } finally {
                                safeClose(clientSocket)
                                activeConnections.remove(clientSocket)
                            }
                        }
                    } catch (e: Exception) {
                        if (isRunning.get()) {
                            Log.w(TAG, "Accept error: ${e.message}")
                        }
                    }
                }
            }
            true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start proxy server", e)
            isRunning.set(false)
            false
        }
    }

    /**
     * Stop the proxy server.
     */
    fun stop() {
        isRunning.set(false)
        // Close all active connections
        for (socket in activeConnections.keys) {
            safeClose(socket)
        }
        activeConnections.clear()
        safeClose(serverSocket)
        scope.cancel()
        Log.i(TAG, "Proxy server stopped")
    }

    // --- Connection handling ---

    private suspend fun handleConnection(clientSocket: Socket) = withContext(Dispatchers.IO) {
        val input = clientSocket.getInputStream()
        val output = clientSocket.getOutputStream()

        // 1. Read destination header: [4B IP][2B port]
        val header = readExactly(input, 6) ?: return@withContext
        val destIp = ((header[0].toInt() and 0xFF) shl 24) or
                ((header[1].toInt() and 0xFF) shl 16) or
                ((header[2].toInt() and 0xFF) shl 8) or
                (header[3].toInt() and 0xFF)
        val destPort = ((header[4].toInt() and 0xFF) shl 8) or (header[5].toInt() and 0xFF)
        val destIpStr = ipToString(destIp)

        // 2. Read TLS ClientHello (first few KB)
        val initialData = readAvailable(input, SNI_READ_SIZE)
        if (initialData.isEmpty()) return@withContext

        // 3. Extract SNI to determine if this is an AI domain
        val sniResult = TlsParser.extractSni(initialData)
        val hostname = sniResult?.sni
        val isAiDomain = hostname != null && TlsParser.isAiServiceHost(hostname)

        if (hostname != null) {
            Log.d(TAG, "SNI: $hostname -> ${if (isAiDomain) "MITM" else "PASSTHROUGH"}")
        } else {
            Log.d(TAG, "No SNI: $destIpStr:$destPort -> PASSTHROUGH")
        }

        if (isAiDomain) {
            handleMitm(clientSocket, input, output, hostname!!, initialData)
        } else {
            handlePassthrough(clientSocket, input, output, destIpStr, destPort, initialData)
        }
    }

    // --- MITM path (AI domains) ---

    private suspend fun handleMitm(
        clientSocket: Socket,
        input: InputStream,
        output: OutputStream,
        hostname: String,
        initialData: ByteArray
    ) = withContext(Dispatchers.IO) {
        try {
            Log.i(TAG, "MITM intercepting: $hostname")

            // 1. Get SSLContext for this domain
            val sslContext = certManager.getSSLContextForDomain(hostname)

            // 2. Create SSLEngine in server mode
            val engine = sslContext.createSSLEngine(hostname, 443)
            engine.useServerMode = true
            engine.enableSessionCreation = true

            // 3. TLS handshake
            val tlsProc = TlsProcessor(engine)
            if (!tlsProc.doHandshake(input, output, initialData)) {
                Log.w(TAG, "TLS handshake failed for $hostname")
                return@withContext
            }

            // 4. Read decrypted HTTP request from client
            val httpRequestBytes = tlsProc.readApplicationData(input)
            if (httpRequestBytes.isEmpty()) return@withContext

            val httpRequest = HttpParser.tryParseRequest(httpRequestBytes)
            if (httpRequest == null) {
                Log.w(TAG, "Failed to parse HTTP request for $hostname")
                // Forward raw data upstream anyway
                forwardRawUpstream(hostname, httpRequestBytes, tlsProc, output)
                return@withContext
            }

            // 5. Mask PII in request body
            val hasBody = httpRequest.body != null && httpRequest.body.isNotEmpty()
            val requestToSend: ByteArray = if (hasBody) {
                try {
                    val bodyText = httpRequest.body!!.decodeToString()
                    val maskResult = PrivacyGateway.getInstance().mask(bodyText)
                    val maskedBody = maskResult.maskedText.encodeToByteArray()
                    val maskedRequest = HttpParser.buildModifiedRequest(httpRequest, maskedBody)
                    Log.i(TAG, "Masked ${maskResult.entities.size} items for $hostname")
                    withContext(Dispatchers.Main) { onStatsChanged?.invoke() }
                    maskedRequest
                } catch (e: Exception) {
                    Log.w(TAG, "Masking failed for $hostname: ${e.message}")
                    httpRequest.originalData
                }
            } else {
                httpRequest.originalData
            }

            // 6. Forward to real server via TLS, stream response back
            val upContext = SSLContext.getInstance("TLS")
            upContext.init(null, null, null)
            val upstreamSocket = upContext.socketFactory.createSocket(hostname, 443)
            upstreamSocket.soTimeout = UPSTREAM_READ_TIMEOUT_MS

            try {
                upstreamSocket.outputStream.write(requestToSend)
                upstreamSocket.outputStream.flush()

                // Stream response back to client
                streamUpstreamResponse(upstreamSocket.inputStream, tlsProc, output)
            } finally {
                safeClose(upstreamSocket)
            }

            // 7. Send close_notify to client
            tlsProc.closeClientTls(output)

            Log.d(TAG, "MITM complete for $hostname")

        } catch (e: Exception) {
            Log.w(TAG, "MITM error for $hostname: ${e.message}")
        }
    }

    /**
     * Forward raw bytes upstream (fallback when HTTP parsing fails).
     */
    private suspend fun forwardRawUpstream(
        hostname: String,
        data: ByteArray,
        tlsProc: TlsProcessor,
        output: OutputStream
    ) {
        try {
            val upContext = SSLContext.getInstance("TLS")
            upContext.init(null, null, null)
            val upstreamSocket = upContext.socketFactory.createSocket(hostname, 443)
            upstreamSocket.soTimeout = UPSTREAM_READ_TIMEOUT_MS
            try {
                upstreamSocket.outputStream.write(data)
                upstreamSocket.outputStream.flush()
                streamUpstreamResponse(upstreamSocket.inputStream, tlsProc, output)
            } finally {
                safeClose(upstreamSocket)
            }
        } catch (e: Exception) {
            Log.w(TAG, "Raw upstream forward failed for $hostname: ${e.message}")
        }
    }

    /**
     * Stream response from upstream SSLSocket back to client via SSLEngine.
     */
    private fun streamUpstreamResponse(
        upstreamInput: InputStream,
        tlsProc: TlsProcessor,
        clientOutput: OutputStream
    ) {
        val responseBuf = ByteArray(BUFFER_SIZE)
        while (true) {
            val read = upstreamInput.read(responseBuf)
            if (read < 0) break
            if (read > 0) {
                tlsProc.wrapAndSend(responseBuf, 0, read, clientOutput)
            }
        }
    }

    // --- Passthrough path (non-AI domains) ---

    private suspend fun handlePassthrough(
        clientSocket: Socket,
        input: InputStream,
        output: OutputStream,
        destIp: String,
        destPort: Int,
        initialData: ByteArray
    ) = withContext(Dispatchers.IO) {
        var upstreamSocket: Socket? = null
        try {
            Log.d(TAG, "PASSTHROUGH tunnel: $destIp:$destPort")

            upstreamSocket = Socket()
            upstreamSocket.connect(InetSocketAddress(destIp, destPort), CONNECT_TIMEOUT_MS)
            upstreamSocket.soTimeout = UPSTREAM_READ_TIMEOUT_MS

            val upstreamOutput = upstreamSocket.getOutputStream()
            val upstreamInput = upstreamSocket.getInputStream()

            // Send initial data (ClientHello)
            upstreamOutput.write(initialData)
            upstreamOutput.flush()

            // Bidirectional relay using two coroutines
            // Client -> Upstream
            val clientToUpstream = scope.launch {
                try {
                    val buf = ByteArray(BUFFER_SIZE)
                    while (isRunning.get()) {
                        val read = input.read(buf)
                        if (read < 0) break
                        upstreamOutput.write(buf, 0, read)
                        upstreamOutput.flush()
                    }
                } catch (e: IOException) {
                    // Connection closed, expected
                }
            }

            // Upstream -> Client
            try {
                val buf = ByteArray(BUFFER_SIZE)
                while (isRunning.get()) {
                    val read = upstreamInput.read(buf)
                    if (read < 0) break
                    output.write(buf, 0, read)
                    output.flush()
                }
            } finally {
                clientToUpstream.cancel()
            }

            Log.d(TAG, "PASSTHROUGH complete: $destIp:$destPort")
        } catch (e: Exception) {
            Log.w(TAG, "PASSTHROUGH error to $destIp:$destPort: ${e.message}")
        } finally {
            safeClose(upstreamSocket)
        }
    }

    // --- TLS processor helper ---

    /**
     * Manages SSLEngine-based TLS termination for a single connection.
     */
    private class TlsProcessor(private val engine: SSLEngine) {
        private val netBuffer = ByteBuffer.allocate(MAX_RECORDS_SIZE)
        private val appBuffer = ByteBuffer.allocate(MAX_RECORDS_SIZE)

        /**
         * Complete TLS handshake with the client.
         *
         * @param initialData the ClientHello bytes already read from the socket
         * @return true if handshake completed successfully
         */
        fun doHandshake(
            input: InputStream,
            output: OutputStream,
            initialData: ByteArray
        ): Boolean {
            engine.beginHandshake()
            var pendingInitialData = initialData

            try {
                while (engine.handshakeStatus != HandshakeStatus.FINISHED &&
                    engine.handshakeStatus != HandshakeStatus.NOT_HANDSHAKING
                ) {
                    when (engine.handshakeStatus) {
                        HandshakeStatus.NEED_UNWRAP -> {
                            if (pendingInitialData.isNotEmpty()) {
                                netBuffer.clear()
                                netBuffer.put(pendingInitialData)
                                netBuffer.flip()
                                pendingInitialData = ByteArray(0)
                            } else {
                                netBuffer.clear()
                                val read = readAvailable(input, netBuffer)
                                if (read < 0) return false
                                netBuffer.flip()
                            }
                            val result = engine.unwrap(netBuffer, appBuffer)
                            appBuffer.clear()
                            when (result.status) {
                                Status.BUFFER_UNDERFLOW -> {
                                    // Need more data - compact and continue
                                    netBuffer.compact()
                                    continue
                                }
                                Status.CLOSED -> return false
                                else -> { /* OK or OVERFLOW handled below */ }
                            }
                            if (result.status == Status.BUFFER_OVERFLOW) {
                                appBuffer.clear()
                                engine.unwrap(netBuffer, appBuffer)
                                appBuffer.clear()
                            }
                        }
                        HandshakeStatus.NEED_WRAP -> {
                            netBuffer.clear()
                            val result = engine.wrap(ByteBuffer.allocate(0), netBuffer)
                            netBuffer.flip()
                            while (netBuffer.hasRemaining()) {
                                output.write(netBuffer.array(),
                                    netBuffer.arrayOffset() + netBuffer.position(),
                                    netBuffer.remaining())
                                netBuffer.position(netBuffer.limit())
                            }
                            if (result.status == Status.CLOSED) return false
                        }
                        HandshakeStatus.NEED_TASK -> {
                            runDelegatedTasks()
                        }
                        else -> {
                            Log.w(TAG, "Unexpected handshake status: ${engine.handshakeStatus}")
                            return false
                        }
                    }
                }
                return engine.handshakeStatus == HandshakeStatus.FINISHED ||
                        engine.handshakeStatus == HandshakeStatus.NOT_HANDSHAKING
            } catch (e: Exception) {
                Log.w(TAG, "TLS handshake error: ${e.message}")
                return false
            }
        }

        /**
         * Read and accumulate decrypted application data after handshake.
         * Returns complete bytes available from the TLS stream.
         */
        fun readApplicationData(input: InputStream): ByteArray {
            val outputBuf = java.io.ByteArrayOutputStream()

            try {
                // First check if there's already data in the app buffer from handshake
                if (appBuffer.position() > 0) {
                    appBuffer.flip()
                    outputBuf.write(appBuffer.array(), 0, appBuffer.remaining())
                    appBuffer.clear()
                }

                // Read TLS records and unwrap
                val tempNet = ByteBuffer.allocate(MAX_RECORDS_SIZE)
                var attempts = 0
                val maxAttempts = 100  // Safety limit

                while (attempts < maxAttempts) {
                    tempNet.clear()
                    val read = readAvailable(input, tempNet)
                    if (read < 0) break

                    tempNet.flip()
                    while (tempNet.hasRemaining()) {
                        val sourcePos = tempNet.position()
                        val result = engine.unwrap(tempNet, appBuffer)
                        if (result.status == Status.CLOSED || result.status == Status.BUFFER_UNDERFLOW) {
                            break
                        }
                        if (result.bytesProduced() > 0) {
                            appBuffer.flip()
                            outputBuf.write(appBuffer.array(), 0, appBuffer.remaining())
                            appBuffer.clear()
                        }
                        // Handle NEED_TASK
                        if (engine.handshakeStatus == HandshakeStatus.NEED_TASK) {
                            runDelegatedTasks()
                        }
                        // Handle renegotiation
                        if (engine.handshakeStatus == HandshakeStatus.NEED_UNWRAP ||
                            engine.handshakeStatus == HandshakeStatus.NEED_WRAP) {
                            // For simplicity, signal to the caller
                            Log.d(TAG, "TLS renegotiation detected, breaking read loop")
                            break
                        }
                        // Safety: prevent infinite loop if no progress
                        if (tempNet.position() == sourcePos && result.bytesProduced() == 0) break
                    }
                    attempts++
                }
            } catch (e: Exception) {
                Log.w(TAG, "Read application data error: ${e.message}")
            }

            return outputBuf.toByteArray()
        }

        /**
         * Encrypt application data and send to the client.
         */
        fun wrapAndSend(data: ByteArray, offset: Int, length: Int, output: OutputStream) {
            try {
                val appBuf = ByteBuffer.wrap(data, offset, length)
                val netBuf = ByteBuffer.allocate(MAX_RECORDS_SIZE)

                while (appBuf.hasRemaining()) {
                    netBuf.clear()
                    val result = engine.wrap(appBuf, netBuf)
                    netBuf.flip()
                    while (netBuf.hasRemaining()) {
                        output.write(netBuf.array(),
                            netBuf.arrayOffset() + netBuf.position(),
                            netBuf.remaining())
                        netBuf.position(netBuf.limit())
                    }

                    when (result.status) {
                        Status.CLOSED -> return
                        Status.BUFFER_OVERFLOW -> {
                            // Reallocate with larger buffer
                            netBuf.clear()
                            val biggerBuf = ByteBuffer.allocate(netBuf.capacity() * 2)
                            engine.wrap(appBuf, biggerBuf)
                            biggerBuf.flip()
                            while (biggerBuf.hasRemaining()) {
                                output.write(biggerBuf.array(),
                                    biggerBuf.arrayOffset() + biggerBuf.position(),
                                    biggerBuf.remaining())
                                biggerBuf.position(biggerBuf.limit())
                            }
                        }
                        else -> { /* OK */ }
                    }

                    if (result.status == Status.OK && result.bytesConsumed() == 0) break
                }
            } catch (e: Exception) {
                Log.w(TAG, "Wrap and send error: ${e.message}")
            }
        }

        /**
         * Send TLS close_notify to the client.
         */
        fun closeClientTls(output: OutputStream) {
            try {
                engine.closeOutbound()
                val netBuf = ByteBuffer.allocate(MAX_RECORDS_SIZE)
                engine.wrap(ByteBuffer.allocate(0), netBuf)
                netBuf.flip()
                if (netBuf.hasRemaining()) {
                    output.write(netBuf.array(), 0, netBuf.remaining())
                    output.flush()
                }
            } catch (e: Exception) {
                Log.w(TAG, "Close TLS error: ${e.message}")
            }
        }

        private fun runDelegatedTasks() {
            var task = engine.delegatedTask
            while (task != null) {
                task.run()
                task = engine.delegatedTask
            }
        }
    }

    // --- I/O helpers ---

    companion object {
        /**
         * Read exactly [len] bytes from the input stream.
         */
        private fun readExactly(input: InputStream, len: Int): ByteArray? {
            val buf = ByteArray(len)
            var offset = 0
            while (offset < len) {
                val read = input.read(buf, offset, len - offset)
                if (read < 0) return if (offset == 0) null else buf.copyOf(offset)
                offset += read
            }
            return buf
        }

        /**
         * Read available bytes from the input stream (up to maxLen).
         */
        private fun readAvailable(input: InputStream, maxLen: Int): ByteArray {
            val buf = ByteArray(maxLen)
            val read = input.read(buf, 0, maxLen)
            return if (read < 0) ByteArray(0) else buf.copyOf(read)
        }

        /**
         * Read from input stream into a ByteBuffer (non-blocking style).
         * Returns number of bytes read, or -1 on EOF.
         */
        private fun readAvailable(input: InputStream, buffer: ByteBuffer): Int {
            val read = input.read(buffer.array(),
                buffer.arrayOffset() + buffer.position(),
                buffer.remaining())
            if (read > 0) {
                buffer.position(buffer.position() + read)
            }
            return read
        }

        /**
         * Safely close a socket (ignore errors).
         */
        private fun safeClose(socket: Any?) {
            try {
                when (socket) {
                    is Socket -> if (!socket.isClosed) socket.close()
                    is ServerSocket -> if (!socket.isClosed) socket.close()
                }
            } catch (_: Exception) {
            }
        }

        private fun ipToString(ip: Int): String {
            return "${(ip shr 24) and 0xFF}.${(ip shr 16) and 0xFF}.${
                (ip shr 8) and 0xFF
            }.${ip and 0xFF}"
        }
    }
}
