package com.privacygw.vpn.protocol

import android.util.Log

/**
 * TLS ClientHello parser for extracting the SNI (Server Name Indication)
 * from the initial TLS handshake packet.
 *
 * This allows the VPN to identify which domain an HTTPS connection targets
 * without decrypting the traffic.
 */
object TlsParser {

    private const val TAG = "TlsParser"

    // TLS record content types
    private const val TLS_CHANGE_CIPHER_SPEC = 20
    private const val TLS_ALERT = 21
    private const val TLS_HANDSHAKE = 22
    private const val TLS_APPLICATION_DATA = 23

    // TLS handshake types
    private const val HS_CLIENT_HELLO = 1
    private const val HS_SERVER_HELLO = 2

    // Extension type for SNI
    private const val EXT_SERVER_NAME = 0x0000

    /**
     * Result of parsing a TLS record.
     */
    data class TlsSniResult(
        val sni: String,
        val tlsVersion: Int       // e.g., 0x0303 = TLS 1.2, 0x0304 = TLS 1.3
    )

    /**
     * Extract the SNI (server name) from a TLS ClientHello record.
     *
     * @param data raw bytes starting from the TLS record layer header
     * @return the extracted SNI, or null if parsing fails / no SNI extension
     */
    fun extractSni(data: ByteArray): TlsSniResult? {
        if (data.size < 5) {
            Log.v(TAG, "Data too short for TLS record header: ${data.size} bytes")
            return null
        }

        val contentType = data[0].toInt() and 0xFF

        // Must be a Handshake record
        if (contentType != TLS_HANDSHAKE) {
            return null
        }

        if (data.size < 11) return null
        // TLS record: type(1) + version(2) + length(2)
        val version = ((data[1].toInt() and 0xFF) shl 8) or (data[2].toInt() and 0xFF)
        val recordLength = ((data[3].toInt() and 0xFF) shl 8) or (data[4].toInt() and 0xFF)

        if (data.size < 5 + recordLength) return null

        var offset = 5

        // Handshake header: type(1) + length(3)
        if (offset + 4 > data.size) return null
        val handshakeType = data[offset].toInt() and 0xFF
        if (handshakeType != HS_CLIENT_HELLO) return null
        offset += 1

        val handshakeLength = ((data[offset].toInt() and 0xFF) shl 16) or
                ((data[offset + 1].toInt() and 0xFF) shl 8) or
                (data[offset + 2].toInt() and 0xFF)
        offset += 3

        // ClientHello: version(2) + random(32)
        if (offset + 34 > data.size) return null
        val clientVersion = ((data[offset].toInt() and 0xFF) shl 8) or (data[offset + 1].toInt() and 0xFF)
        offset += 34  // version(2) + random(32)

        // Session ID: length(1) + data(var)
        if (offset >= data.size) return null
        val sessionIdLength = data[offset].toInt() and 0xFF
        offset += 1 + sessionIdLength

        // Cipher Suites: length(2) + data(var)
        if (offset + 2 > data.size) return null
        val cipherSuitesLength = ((data[offset].toInt() and 0xFF) shl 8) or (data[offset + 1].toInt() and 0xFF)
        offset += 2 + cipherSuitesLength

        // Compression Methods: length(1) + data(var)
        if (offset >= data.size) return null
        val compressionLength = data[offset].toInt() and 0xFF
        offset += 1 + compressionLength

        // Extensions: length(2) + data(var)
        if (offset + 2 > data.size) return null
        val extensionsLength = ((data[offset].toInt() and 0xFF) shl 8) or (data[offset + 1].toInt() and 0xFF)
        offset += 2

        // Parse extensions
        val extensionsEnd = offset + extensionsLength
        while (offset + 4 <= extensionsEnd && offset <= data.size - 4) {
            val extType = ((data[offset].toInt() and 0xFF) shl 8) or (data[offset + 1].toInt() and 0xFF)
            val extLength = ((data[offset + 2].toInt() and 0xFF) shl 8) or (data[offset + 3].toInt() and 0xFF)
            offset += 4

            if (extType == EXT_SERVER_NAME) {
                // Server Name Indication extension
                // SNI list: length(2) + server name list
                if (offset + 2 > data.size) return null
                val sniListLength = ((data[offset].toInt() and 0xFF) shl 8) or (data[offset + 1].toInt() and 0xFF)
                offset += 2

                if (offset + 1 > data.size) return null
                val nameType = data[offset].toInt() and 0xFF
                offset += 1

                // 0x00 = host_name (the only defined value)
                if (nameType == 0x00) {
                    if (offset + 2 > data.size) return null
                    val nameLength = ((data[offset].toInt() and 0xFF) shl 8) or (data[offset + 1].toInt() and 0xFF)
                    offset += 2

                    if (offset + nameLength > data.size) return null
                    val sni = data.decodeToString(offset, offset + nameLength)

                    Log.d(TAG, "Extracted SNI: $sni (TLS version: 0x${clientVersion.toString(16)})")

                    // SNI hostnames should be ASCII, strip trailing dot if present
                    return TlsSniResult(
                        sni = sni.trimEnd('.'),
                        tlsVersion = clientVersion
                    )
                }
            }

            offset += extLength
        }

        return null
    }

    /**
     * Check if a hostname (from SNI or Host header) matches an AI service domain.
     */
    fun isAiServiceHost(host: String): Boolean {
        val lower = host.lowercase().trim()
        return AI_HOST_PATTERNS.any { pattern ->
            lower == pattern || lower.endsWith(".$pattern")
        }
    }

    /**
     * AI service hosts we know about.
     */
    val AI_HOST_PATTERNS = listOf(
        "openai.com",
        "anthropic.com",
        "deepseek.com",
        "moonshot.cn",
        "x.ai",
        "doubao.com",
        "yuanbao.com",
        "coze.cn",
        "coze.com",
        "mistral.ai",
        "perplexity.ai",
        "groq.com",
        "together.xyz",
        "ai.google.dev",
        "generativelanguage.googleapis.com",
        "gemini.google.com",
        "cerebras.ai",
        "fireworks.ai",
        "github.com",
        "models.github.ai"
    )
}
