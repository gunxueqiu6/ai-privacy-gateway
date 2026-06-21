package com.privacygw.vpn.protocol

import android.util.Log
import java.nio.ByteBuffer

/**
 * Low-level IP/TCP packet parser for raw TUN interface data.
 *
 * Parses the IP header and TCP header from a raw byte buffer read
 * from the TUN interface, returning structured header objects and
 * pointing at the payload region.
 */
object PacketParser {

    private const val TAG = "PacketParser"
    private const val IPV4 = 4
    const val PROTOCOL_TCP = 6
    const val PROTOCOL_UDP = 17

    /**
     * Parse the IPv4 header from a TUN packet.
     *
     * @param buffer positioned at the start of the packet
     * @return parsed header, or null if the packet is not IPv4 or is too short
     */
    fun parseIpHeader(buffer: ByteBuffer): IpHeader? {
        if (buffer.remaining() < 20) {
            Log.w(TAG, "Packet too short for IP header: ${buffer.remaining()} bytes")
            return null
        }

        val savedPosition = buffer.position()

        val versionIhl = buffer.get().toInt() and 0xFF
        val version = (versionIhl shr 4) and 0x0F
        val ihl = versionIhl and 0x0F

        if (version != IPV4) {
            // Not IPv4 — skip (future: handle IPv6 if needed)
            buffer.position(savedPosition)
            return null
        }

        if (ihl < 5) {
            Log.w(TAG, "Invalid IP header length: $ihl")
            buffer.position(savedPosition)
            return null
        }

        // DSCP + ECN
        buffer.get()
        val totalLength = buffer.short.toInt() and 0xFFFF
        val identification = buffer.short.toInt() and 0xFFFF
        val flagsFragment = buffer.short.toInt() and 0xFFFF
        val flags = (flagsFragment shr 13) and 0x07
        val fragmentOffset = flagsFragment and 0x1FFF
        val ttl = buffer.get().toInt() and 0xFF
        val protocol = buffer.get().toInt() and 0xFF
        val headerChecksum = buffer.short.toInt() and 0xFFFF
        val sourceIp = buffer.int
        val destIp = buffer.int

        // Skip IP options if any
        val optionLength = ihl * 4 - 20
        if (optionLength > 0) {
            buffer.position(buffer.position() + optionLength)
        }

        val header = IpHeader(
            version = version,
            ihl = ihl,
            totalLength = totalLength,
            identification = identification,
            flags = flags,
            fragmentOffset = fragmentOffset,
            ttl = ttl,
            protocol = protocol,
            headerChecksum = headerChecksum,
            sourceIp = sourceIp,
            destIp = destIp
        )

        // Verify we have enough data for the claimed total length
        if (buffer.remaining() < header.payloadLength) {
            Log.w(TAG, "Packet truncated: have ${buffer.remaining()}, need ${header.payloadLength}")
            buffer.position(savedPosition)
            return null
        }

        return header
    }

    /**
     * Parse the TCP header that follows the IP header.
     *
     * @param buffer positioned after the IP header (at start of TCP segment)
     * @return parsed TCP header
     */
    fun parseTcpHeader(buffer: ByteBuffer): TcpHeader? {
        if (buffer.remaining() < 20) {
            Log.w(TAG, "TCP data too short for header: ${buffer.remaining()} bytes")
            return null
        }

        val savedPosition = buffer.position()

        val srcPort = buffer.short.toInt() and 0xFFFF
        val dstPort = buffer.short.toInt() and 0xFFFF
        val seq = buffer.int.toLong() and 0xFFFFFFFFL
        val ack = buffer.int.toLong() and 0xFFFFFFFFL
        val dataOffsetReserved = buffer.get().toInt() and 0xFF
        val dataOffset = (dataOffsetReserved shr 4) and 0x0F
        val flagsByte = buffer.get().toInt() and 0xFF
        val window = buffer.short.toInt() and 0xFFFF
        val checksum = buffer.short.toInt() and 0xFFFF
        val urgent = buffer.short.toInt() and 0xFFFF

        // Skip TCP options
        val optionLength = dataOffset * 4 - 20
        if (optionLength > 0) {
            buffer.position(buffer.position() + optionLength)
        }

        if (dataOffset < 5) {
            Log.w(TAG, "Invalid TCP data offset: $dataOffset")
            buffer.position(savedPosition)
            return null
        }

        return TcpHeader(
            sourcePort = srcPort,
            destPort = dstPort,
            sequenceNumber = seq,
            acknowledgmentNumber = ack,
            dataOffset = dataOffset,
            flags = TcpHeader.TcpFlags(
                fin = (flagsByte and 0x01) != 0,
                syn = (flagsByte and 0x02) != 0,
                rst = (flagsByte and 0x04) != 0,
                psh = (flagsByte and 0x08) != 0,
                ack = (flagsByte and 0x10) != 0,
                urg = (flagsByte and 0x20) != 0
            ),
            windowSize = window,
            checksum = checksum,
            urgentPointer = urgent
        )
    }

    /**
     * Compute the Internet Checksum (RFC 1071) for a byte range.
     */
    fun computeChecksum(data: ByteArray, offset: Int, length: Int): Int {
        var sum = 0L
        var i = 0
        while (i < length - 1) {
            sum += ((data[offset + i].toInt() and 0xFF) shl 8) or
                    (data[offset + i + 1].toInt() and 0xFF)
            i += 2
        }
        if (length % 2 != 0) {
            sum += (data[offset + i].toInt() and 0xFF) shl 8
        }
        while ((sum shr 16) != 0L) {
            sum = (sum and 0xFFFF) + (sum shr 16)
        }
        return (sum.inv().toInt()) and 0xFFFF
    }

    /**
     * Compute the TCP checksum including the TCP pseudo-header.
     *
     * @param sourceIp source IP (raw int)
     * @param destIp   destination IP (raw int)
     * @param segment  the full TCP segment (header + payload), with checksum
     *                 field set to 0 before calling
     */
    fun computeTcpChecksum(sourceIp: Int, destIp: Int, segment: ByteArray): Int {
        // Pseudo-header: src(4) + dst(4) + zeros(1) + protocol(1) + TCP length(2)
        val pseudoLen = 12 + segment.size
        val buf = ByteArray(pseudoLen)

        // Write pseudo-header
        var pos = 0
        // source IP
        buf[pos++] = ((sourceIp shr 24) and 0xFF).toByte()
        buf[pos++] = ((sourceIp shr 16) and 0xFF).toByte()
        buf[pos++] = ((sourceIp shr 8) and 0xFF).toByte()
        buf[pos++] = (sourceIp and 0xFF).toByte()
        // dest IP
        buf[pos++] = ((destIp shr 24) and 0xFF).toByte()
        buf[pos++] = ((destIp shr 16) and 0xFF).toByte()
        buf[pos++] = ((destIp shr 8) and 0xFF).toByte()
        buf[pos++] = (destIp and 0xFF).toByte()
        // reserved + protocol
        buf[pos++] = 0
        buf[pos++] = 6   // TCP protocol number
        // TCP segment length
        buf[pos++] = ((segment.size shr 8) and 0xFF).toByte()
        buf[pos++] = (segment.size and 0xFF).toByte()
        // TCP segment
        segment.copyInto(buf, pos)

        return computeChecksum(buf, 0, buf.size)
    }

    /**
     * Rebuild an IP header in a byte array with a correct checksum.
     * Used when we need to create response packets from scratch.
     */
    fun buildIpHeader(
        sourceIp: Int,
        destIp: Int,
        payloadLength: Int,
        identification: Int,
        ttl: Int = 64,
        protocol: Int = PROTOCOL_TCP
    ): ByteArray {
        val totalLength = 20 + payloadLength
        val buf = ByteBuffer.allocate(20)

        buf.put((0x45).toByte())                 // version=4, ihl=5
        buf.put(0x00.toByte())                   // DSCP + ECN
        buf.putShort(totalLength.toShort())      // total length
        buf.putShort((identification and 0xFFFF).toShort()) // identification
        buf.putShort(0x4000.toShort())           // flags=DF, offset=0
        buf.put(ttl.toByte())                    // TTL
        buf.put(protocol.toByte())               // protocol
        buf.putShort(0x00.toByte())              // checksum (placeholder)
        buf.putInt(sourceIp)                     // source IP
        buf.putInt(destIp)                       // dest IP

        val packet = buf.array()
        // Calculate and fill in checksum
        val checksum = computeChecksum(packet, 0, 20)
        packet[10] = ((checksum shr 8) and 0xFF).toByte()
        packet[11] = (checksum and 0xFF).toByte()

        return packet
    }

    /**
     * Build a TCP header byte array.
     */
    fun buildTcpHeader(
        sourcePort: Int,
        destPort: Int,
        sequenceNumber: Long,
        acknowledgmentNumber: Long,
        flags: TcpHeader.TcpFlags,
        windowSize: Int = 65535,
        payloadLength: Int = 0
    ): ByteArray {
        val headerLength = 20  // no options
        val buf = ByteBuffer.allocate(headerLength)

        buf.putShort(sourcePort.toShort())
        buf.putShort(destPort.toShort())
        buf.putInt((sequenceNumber and 0xFFFFFFFFL).toInt())
        buf.putInt((acknowledgmentNumber and 0xFFFFFFFFL).toInt())
        buf.put(((headerLength / 4) shl 4).toByte()) // data offset = 5 (20 bytes)
        buf.put(flags.rawFlags.toByte())
        buf.putShort(windowSize.toShort())
        buf.putShort(0x00.toByte())  // checksum placeholder
        buf.putShort(0x00.toByte())  // urgent pointer

        return buf.array()
    }

    /**
     * Build a complete IP + TCP response packet.
     *
     * The resulting packet can be written directly to the TUN output channel
     * as a response to an intercepted connection.
     */
    fun buildTcpResponsePacket(
        ipHeader: IpHeader,
        tcpHeader: TcpHeader,
        payload: ByteArray,
        identification: Int = ipHeader.identification
    ): ByteArray {
        // For the response, swap source and destination
        val responseIp = buildIpHeader(
            sourceIp = ipHeader.destIp,
            destIp = ipHeader.sourceIp,
            payloadLength = 20 + payload.size,  // TCP header + payload
            identification = identification,
            protocol = PROTOCOL_TCP
        )

        val responseTcp = buildTcpHeader(
            sourcePort = tcpHeader.destPort,
            destPort = tcpHeader.sourcePort,
            sequenceNumber = tcpHeader.acknowledgmentNumber,
            acknowledgmentNumber = tcpHeader.sequenceNumber + payload.size,
            flags = TcpHeader.TcpFlags(fin = false, syn = false, rst = false, psh = payload.isNotEmpty(), ack = true, urg = false),
            payloadLength = payload.size
        )

        // Full TCP segment (header + payload)
        val tcpSegment = responseTcp + payload

        // Calculate TCP checksum with pseudo-header
        val tcpChecksum = computeTcpChecksum(
            ipHeader.destIp, ipHeader.sourceIp, tcpSegment
        )
        // Patch checksum into the TCP header
        tcpSegment[16] = ((tcpChecksum shr 8) and 0xFF).toByte()
        tcpSegment[17] = (tcpChecksum and 0xFF).toByte()

        return responseIp + tcpSegment
    }

    /**
     * Build a TCP FIN packet to close a connection from our side.
     */
    fun buildFinPacket(
        ipHeader: IpHeader,
        tcpHeader: TcpHeader,
        identification: Int = ipHeader.identification + 1
    ): ByteArray {
        val responseIp = buildIpHeader(
            sourceIp = ipHeader.destIp,
            destIp = ipHeader.sourceIp,
            payloadLength = 20,
            identification = identification,
            protocol = PROTOCOL_TCP
        )

        val responseTcp = buildTcpHeader(
            sourcePort = tcpHeader.destPort,
            destPort = tcpHeader.sourcePort,
            sequenceNumber = tcpHeader.acknowledgmentNumber,
            acknowledgmentNumber = tcpHeader.sequenceNumber,
            flags = TcpHeader.TcpFlags(fin = true, syn = false, rst = false, psh = false, ack = true, urg = false)
        )

        val tcpChecksum = computeTcpChecksum(
            ipHeader.destIp, ipHeader.sourceIp, responseTcp
        )
        responseTcp[16] = ((tcpChecksum shr 8) and 0xFF).toByte()
        responseTcp[17] = (tcpChecksum and 0xFF).toByte()

        return responseIp + responseTcp
    }

    /**
     * Build a TCP RST packet to abort a connection.
     */
    fun buildRstPacket(
        ipHeader: IpHeader,
        tcpHeader: TcpHeader
    ): ByteArray {
        val responseIp = buildIpHeader(
            sourceIp = ipHeader.destIp,
            destIp = ipHeader.sourceIp,
            payloadLength = 20,
            identification = ipHeader.identification,
            protocol = PROTOCOL_TCP
        )

        val responseTcp = buildTcpHeader(
            sourcePort = tcpHeader.destPort,
            destPort = tcpHeader.sourcePort,
            sequenceNumber = tcpHeader.acknowledgmentNumber,
            acknowledgmentNumber = tcpHeader.sequenceNumber,
            flags = TcpHeader.TcpFlags(fin = false, syn = false, rst = true, psh = false, ack = true, urg = false)
        )

        val tcpChecksum = computeTcpChecksum(
            ipHeader.destIp, ipHeader.sourceIp, responseTcp
        )
        responseTcp[16] = ((tcpChecksum shr 8) and 0xFF).toByte()
        responseTcp[17] = (tcpChecksum and 0xFF).toByte()

        return responseIp + responseTcp
    }
}
