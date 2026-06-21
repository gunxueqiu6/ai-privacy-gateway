package com.privacygw.vpn.protocol

import android.util.Log

/**
 * Represents a parsed HTTP/1.x request extracted from TCP payload data.
 */
data class HttpRequest(
    val method: String,
    val path: String,
    val version: String,
    val headers: Map<String, String>,     // lowercase keys
    val host: String,
    val body: ByteArray?,
    val bodyStartOffset: Int,              // offset in originalData where body begins
    val totalHeaderLength: Int,            // length of request line + headers + CRLF
    val originalData: ByteArray
)

/**
 * Represents a parsed HTTP/1.x response.
 */
data class HttpResponse(
    val version: String,
    val statusCode: Int,
    val statusMessage: String,
    val headers: Map<String, String>,
    val body: ByteArray?,
    val bodyStartOffset: Int,
    val totalHeaderLength: Int
)

/**
 * HTTP/1.x request and response parser for intercepted traffic.
 *
 * Handles Content-Length based bodies (chunked encoding is detected but
 * full chunked reassembly is delegated to the proxy layer).
 */
object HttpParser {

    private const val TAG = "HttpParser"

    private val VALID_METHODS = setOf("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "CONNECT")

    /**
     * Try to parse an HTTP/1.x request from raw bytes.
     * Returns null if the data doesn't contain a complete HTTP request.
     */
    fun tryParseRequest(data: ByteArray): HttpRequest? {
        if (data.size < 8) return null

        val text: String
        try {
            text = data.decodeToString()
        } catch (e: Exception) {
            return null
        }

        // Find the end of the request line
        val firstLineEnd = text.indexOf("\r\n")
        if (firstLineEnd < 0) return null

        val firstLine = text.substring(0, firstLineEnd)
        val parts = firstLine.split(" ")
        if (parts.size < 3) return null
        if (parts[0] !in VALID_METHODS) return null

        val method = parts[0]
        val path = parts[1]
        val version = parts[2]

        // Find end of headers (double CRLF)
        val headersEnd = text.indexOf("\r\n\r\n")
        if (headersEnd < 0) return null

        val headerSection = text.substring(firstLineEnd + 2, headersEnd)
        val headers = mutableMapOf<String, String>()
        var host = ""

        for (line in headerSection.lines()) {
            val colonIdx = line.indexOf(':')
            if (colonIdx > 0) {
                val key = line.substring(0, colonIdx).trim().lowercase()
                val value = line.substring(colonIdx + 1).trim()
                headers[key] = value
                if (key == "host") {
                    host = value
                }
            }
        }

        val headerLength = headersEnd + 4  // include the trailing \r\n\r\n

        // Determine body
        val body: ByteArray?
        val contentLength = headers["content-length"]?.toIntOrNull()
        val transferEncoding = headers["transfer-encoding"]
        val isChunked = transferEncoding.equals("chunked", ignoreCase = true)

        if (contentLength != null && contentLength > 0) {
            // Content-Length based
            if (data.size < headerLength + contentLength) {
                // Don't have the full body yet — incomplete
                return null
            }
            body = data.copyOfRange(headerLength, headerLength + contentLength)
        } else if (isChunked) {
            // Chunked transfer encoding — try to reassemble
            val parsedBody = parseChunkedBody(data, headerLength)
            if (parsedBody == null) {
                // Incomplete chunked body
                return null
            }
            body = parsedBody
        } else {
            // No body (GET, DELETE, etc.)
            body = null
        }

        return HttpRequest(
            method = method,
            path = path,
            version = version,
            headers = headers.toMap(),
            host = host,
            body = body,
            bodyStartOffset = headerLength,
            totalHeaderLength = headerLength,
            originalData = data
        )
    }

    /**
     * Try to parse an HTTP/1.x response.
     */
    fun tryParseResponse(data: ByteArray): HttpResponse? {
        if (data.size < 8) return null

        val text: String
        try {
            text = data.decodeToString()
        } catch (e: Exception) {
            return null
        }

        // Find end of status line
        val firstLineEnd = text.indexOf("\r\n")
        if (firstLineEnd < 0) return null

        val firstLine = text.substring(0, firstLineEnd)
        if (!firstLine.startsWith("HTTP/")) return null

        val parts = firstLine.split(" ", limit = 3)
        if (parts.size < 2) return null

        val version = parts[0]
        val statusCode = parts[1].toIntOrNull() ?: return null
        val statusMessage = if (parts.size >= 3) parts[2] else ""

        // Find end of headers
        val headersEnd = text.indexOf("\r\n\r\n")
        if (headersEnd < 0) return null

        val headerSection = text.substring(firstLineEnd + 2, headersEnd)
        val headers = mutableMapOf<String, String>()

        for (line in headerSection.lines()) {
            val colonIdx = line.indexOf(':')
            if (colonIdx > 0) {
                val key = line.substring(0, colonIdx).trim().lowercase()
                val value = line.substring(colonIdx + 1).trim()
                headers[key] = value
            }
        }

        val headerLength = headersEnd + 4
        val contentLength = headers["content-length"]?.toIntOrNull()

        val body = if (contentLength != null && contentLength > 0) {
            if (data.size < headerLength + contentLength) return null
            data.copyOfRange(headerLength, headerLength + contentLength)
        } else {
            null
        }

        return HttpResponse(
            version = version,
            statusCode = statusCode,
            statusMessage = statusMessage,
            headers = headers.toMap(),
            body = body,
            bodyStartOffset = headerLength,
            totalHeaderLength = headerLength
        )
    }

    /**
     * Determine if a given port is likely HTTP traffic.
     */
    fun isHttpPort(port: Int): Boolean = port == 80 || port == 8080 || port == 8000

    /**
     * Check if headers indicate this is a streaming SSE response (e.g., Server-Sent Events
     * used by AI chat APIs).
     */
    fun isSseResponse(headers: Map<String, String>): Boolean {
        val contentType = headers["content-type"] ?: ""
        return contentType.contains("text/event-stream", ignoreCase = true)
    }

    /**
     * Rebuild an HTTP request byte array with a modified body.
     * The original headers are preserved except Content-Length is updated.
     */
    fun buildModifiedRequest(original: HttpRequest, newBody: ByteArray?): ByteArray {
        val sb = StringBuilder()
        sb.append("${original.method} ${original.path} ${original.version}\r\n")

        for ((key, value) in original.headers) {
            when (key.lowercase()) {
                "content-length" -> {
                    // Skip — we'll add it below if there's a body
                }
                "transfer-encoding" -> {
                    // Skip — we'll use Content-Length instead
                }
                "host" -> {
                    // Always include Host header
                    sb.append("Host: ${original.host}\r\n")
                }
                else -> {
                    sb.append("$key: $value\r\n")
                }
            }
        }

        if (newBody != null) {
            sb.append("Content-Length: ${newBody.size}\r\n")
        }

        sb.append("\r\n")

        val headerBytes = sb.toString().encodeToByteArray()
        val bodyBytes = newBody ?: original.body ?: byteArrayOf()

        return headerBytes + bodyBytes
    }

    /**
     * Rebuild an HTTP response with a modified body.
     */
    fun buildModifiedResponse(original: HttpResponse, newBody: ByteArray): ByteArray {
        val sb = StringBuilder()
        sb.append("${original.version} ${original.statusCode} ${original.statusMessage}\r\n")

        for ((key, value) in original.headers) {
            when (key.lowercase()) {
                "content-length" -> {
                    // Updated below
                }
                "transfer-encoding" -> {
                    // Use Content-Length instead
                }
                else -> {
                    sb.append("$key: $value\r\n")
                }
            }
        }

        sb.append("Content-Length: ${newBody.size}\r\n")
        sb.append("\r\n")

        return sb.toString().encodeToByteArray() + newBody
    }

    /**
     * Extract Host from headers or path.
     */
    fun extractHost(request: HttpRequest): String {
        if (request.host.isNotBlank()) return request.host
        // Try to extract from path (for proxy-style requests)
        val path = request.path
        if (path.startsWith("http://") || path.startsWith("https://")) {
            val afterScheme = path.substring(path.indexOf("://") + 3)
            val slashIdx = afterScheme.indexOf('/')
            val hostPort = if (slashIdx >= 0) afterScheme.substring(0, slashIdx) else afterScheme
            val colonIdx = hostPort.indexOf(':')
            return if (colonIdx >= 0) hostPort.substring(0, colonIdx) else hostPort
        }
        return ""
    }

    /**
     * Check if the domain is an AI service we should mask.
     */
    fun isAiServiceDomain(host: String): Boolean {
        val lower = host.lowercase().trim()
        return AI_DOMAINS.any { domain -> lower == domain || lower.endsWith(".$domain") }
    }

    /**
     * Simple chunked transfer encoding parser.
     * Attempts to reassemble the full body from chunked data.
     */
    fun parseChunkedBody(data: ByteArray, bodyStart: Int): ByteArray? {
        val output = java.io.ByteArrayOutputStream()
        var offset = bodyStart

        try {
            while (offset < data.size) {
                // Read chunk size line
                val chunkSizeEnd = findLineEnd(data, offset)
                    ?: return null  // Incomplete
                val chunkSizeStr = data.decodeToString(offset, chunkSizeEnd).trim()
                if (chunkSizeStr.isEmpty()) return null
                val semicolon = chunkSizeStr.indexOf(';')
                val sizeHex = if (semicolon >= 0) chunkSizeStr.substring(0, semicolon) else chunkSizeStr
                val chunkSize = sizeHex.toIntOrNull(16) ?: return null

                offset = chunkSizeEnd + 2  // skip \r\n after size line

                if (chunkSize == 0) {
                    // Final chunk — skip trailing CRLF + trailers
                    return output.toByteArray()
                }

                if (offset + chunkSize > data.size) return null  // Incomplete

                output.write(data, offset, chunkSize)
                offset += chunkSize + 2  // skip chunk data + trailing \r\n
            }
        } catch (e: Exception) {
            Log.w(TAG, "Chunked parse error", e)
            return null
        }

        return if (output.size() > 0) output.toByteArray() else null
    }

    private fun findLineEnd(data: ByteArray, start: Int): Int? {
        for (i in start until data.size - 1) {
            if (data[i] == '\r'.code.toByte() && data[i + 1] == '\n'.code.toByte()) {
                return i
            }
        }
        return null
    }

    /**
     * Known AI API service domains whose traffic should be intercepted and masked.
     */
    private val AI_DOMAINS = setOf(
        "openai.com",
        "api.openai.com",
        "chat.openai.com",
        "anthropic.com",
        "api.anthropic.com",
        "deepseek.com",
        "api.deepseek.com",
        "chat.deepseek.com",
        "moonshot.cn",
        "api.moonshot.cn",
        "kimi.moonshot.cn",
        "x.ai",
        "api.x.ai",
        "grok.x.ai",
        "doubao.com",
        "api.doubao.com",
        "yuanbao.com",
        "api.yuanbao.com",
        "coze.cn",
        "api.coze.cn",
        "coze.com",
        "api.coze.com",
        "mistral.ai",
        "api.mistral.ai",
        "perplexity.ai",
        "api.perplexity.ai",
        "groq.com",
        "api.groq.com",
        "together.xyz",
        "api.together.xyz",
        "ai.google.dev",
        "generativelanguage.googleapis.com",
        "gemini.google.com",
        "api.cerebras.ai",
        "fireworks.ai",
        "api.fireworks.ai",
        "github.com",
        "api.github.com",
        "models.github.ai"
    )
}
