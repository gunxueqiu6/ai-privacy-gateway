package com.privacygw.vpn.protocol

/**
 * Parsed IPv4 header.
 */
data class IpHeader(
    val version: Int,
    val ihl: Int,                  // Internet Header Length (in 4-byte words)
    val totalLength: Int,          // Total IP packet length in bytes
    val identification: Int,
    val flags: Int,
    val fragmentOffset: Int,
    val ttl: Int,
    val protocol: Int,             // 6 = TCP, 17 = UDP
    val headerChecksum: Int,
    val sourceIp: Int,             // Raw 32-bit network-order integer
    val destIp: Int
) {
    /** Header length in bytes. */
    val headerLength: Int get() = ihl * 4

    /** Payload (L4 segment) length in bytes. */
    val payloadLength: Int get() = totalLength - headerLength

    /** Source IP as dotted-quad string. */
    val sourceIpString: String get() = ipToString(sourceIp)

    /** Destination IP as dotted-quad string. */
    val destIpString: String get() = ipToString(destIp)
}

/**
 * Parsed TCP header.
 */
data class TcpHeader(
    val sourcePort: Int,
    val destPort: Int,
    val sequenceNumber: Long,      // 32-bit, unsigned
    val acknowledgmentNumber: Long, // 32-bit, unsigned
    val dataOffset: Int,           // in 4-byte words
    val flags: TcpFlags,
    val windowSize: Int,
    val checksum: Int,
    val urgentPointer: Int
) {
    /** Header length in bytes. */
    val headerLength: Int get() = dataOffset * 4

    data class TcpFlags(
        val fin: Boolean,
        val syn: Boolean,
        val rst: Boolean,
        val psh: Boolean,
        val ack: Boolean,
        val urg: Boolean
    ) {
        val rawFlags: Int get() {
            var f = 0
            if (fin) f = f or 0x01
            if (syn) f = f or 0x02
            if (rst) f = f or 0x04
            if (psh) f = f or 0x08
            if (ack) f = f or 0x10
            if (urg) f = f or 0x20
            return f
        }
    }
}

/**
 * 5-tuple key for uniquely identifying a TCP connection.
 */
data class TcpConnectionKey(
    val sourceIp: String,
    val destIp: String,
    val sourcePort: Int,
    val destPort: Int
) {
    /** Reverse key (swap src <-> dst) for matching response packets. */
    val reversed: TcpConnectionKey
        get() = TcpConnectionKey(destIp, sourceIp, destPort, sourcePort)
}

/** Convert a 32-bit network-order integer to dotted-quad string. */
fun ipToString(ip: Int): String {
    return "${(ip shr 24) and 0xFF}.${(ip shr 16) and 0xFF}.${(ip shr 8) and 0xFF}.${ip and 0xFF}"
}

/** Convert dotted-quad string to 32-bit network-order integer. */
fun ipToInt(ip: String): Int {
    val parts = ip.split('.')
    if (parts.size != 4) return 0
    return ((parts[0].toInt() and 0xFF) shl 24) or
           ((parts[1].toInt() and 0xFF) shl 16) or
           ((parts[2].toInt() and 0xFF) shl 8) or
           (parts[3].toInt() and 0xFF)
}
