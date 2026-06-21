package com.privacygw.vpn.core

import android.util.Log
import com.privacygw.vpn.protocol.*
import java.io.OutputStream
import java.net.Socket
import java.util.concurrent.ConcurrentHashMap

/**
 * State of an intercepted TCP connection.
 */
enum class ConnectionState {
    /** TCP handshake in progress (SYN seen, waiting for SYN-ACK or data). */
    HANDSHAKING,

    /** Connection established, data flowing. */
    ESTABLISHED,

    /** Connection being closed (FIN seen). */
    CLOSING,

    /** Connection closed. */
    CLOSED
}

/**
 * Represents one intercepted TCP connection with its upstream proxy socket.
 */
class InterceptedConnection(
    val key: TcpConnectionKey,
    val destHost: String,
    val isHttps: Boolean
) {
    var state: ConnectionState = ConnectionState.ESTABLISHED

    /** Socket connected to the real destination server (for HTTP interception). */
    var upstreamSocket: Socket? = null

    /** Output stream to the upstream server. */
    var upstreamOutput: OutputStream? = null

    /** Buffered data from the client that hasn't been forwarded yet. */
    val clientBuffer = mutableListOf<ByteArray>()

    /** Total buffered bytes from the client. */
    var clientBufferSize = 0

    /** The client's initial sequence number. */
    var clientSeq: Long = 0

    /** Our acknowledgment number (matching client's sequence). */
    var clientAck: Long = 0

    /** Our sequence number (starting from server's SYN-ACK seq). */
    var serverSeq: Long = 0

    /** The client's advertised window size. */
    var clientWindow: Int = 65535

    /** Timestamp when this connection was created. */
    val createdAt = System.currentTimeMillis()

    /** Whether this connection is queued for masking. */
    var pendingMask = false
}

/**
 * Manages TCP connection state for intercepted and passthrough connections.
 *
 * Passthrough connections are simply forwarded (read from TUN, written back to TUN).
 * Intercepted connections are tracked so their TCP stream can be reassembled,
 * modified, and forwarded to the real destination via raw sockets.
 */
class TcpConnectionManager {

    companion object {
        private const val TAG = "TcpConnManager"
        const val MAX_BUFFER_SIZE = 256 * 1024    // 256KB max per connection buffer
        const val CONNECTION_TIMEOUT_MS = 300_000L  // 5 minutes idle timeout
        const val CLEANUP_INTERVAL_MS = 60_000L     // Cleanup every 60s
    }

    /** All active TCP connections tracked by the packet processor. */
    private val connections = ConcurrentHashMap<TcpConnectionKey, InterceptedConnection>()

    /** Sequence numbers for generating response packets. */
    private var responseIdCounter = 0

    /**
     * Get or create an intercepted connection entry.
     */
    fun getOrCreate(
        key: TcpConnectionKey,
        destHost: String,
        isHttps: Boolean
    ): InterceptedConnection {
        return connections.getOrPut(key) {
            Log.d(TAG, "New connection: $key -> $destHost (${if (isHttps) "HTTPS" else "HTTP"})")
            InterceptedConnection(key, destHost, isHttps)
        }
    }

    /**
     * Get an existing connection by key.
     */
    fun get(key: TcpConnectionKey): InterceptedConnection? {
        return connections[key]
    }

    /**
     * Get connection by the server-facing key.
     */
    fun getByServerKey(serverKey: TcpConnectionKey): InterceptedConnection? {
        return connections[serverKey.reversed]
    }

    /**
     * Remove and close a connection.
     */
    fun remove(key: TcpConnectionKey) {
        val conn = connections.remove(key)
        if (conn != null) {
            Log.d(TAG, "Removing connection: $key")
            try {
                conn.upstreamSocket?.close()
            } catch (e: Exception) {
                Log.w(TAG, "Error closing upstream socket", e)
            }
        }
    }

    /**
     * Remove a connection by the server-facing key.
     */
    fun removeByServerKey(serverKey: TcpConnectionKey) {
        remove(serverKey.reversed)
    }

    /**
     * Buffer a client data packet for later reassembly.
     * Returns true if the buffer is within limits.
     */
    fun bufferClientData(conn: InterceptedConnection, data: ByteArray): Boolean {
        if (conn.clientBufferSize + data.size > MAX_BUFFER_SIZE) {
            Log.w(TAG, "Buffer overflow for $conn, dropping data")
            return false
        }
        conn.clientBuffer.add(data)
        conn.clientBufferSize += data.size
        // Update ACK to reflect received data
        conn.clientAck = (conn.clientAck + data.size) and 0xFFFFFFFFL
        return true
    }

    /**
     * Reassemble all buffered HTTP request data into a single byte array.
     */
    fun reassembleBuffer(conn: InterceptedConnection): ByteArray {
        val totalSize = conn.clientBuffer.sumOf { it.size }
        val result = ByteArray(totalSize)
        var offset = 0
        for (chunk in conn.clientBuffer) {
            chunk.copyInto(result, offset)
            offset += chunk.size
        }
        return result
    }

    /**
     * Check if an intercepted HTTP connection has received a complete HTTP request.
     * If so, returns the parsed request.
     */
    fun tryExtractHttpRequest(conn: InterceptedConnection): HttpRequest? {
        val data = reassembleBuffer(conn)
        return HttpParser.tryParseRequest(data)
    }

    /**
     * Create a new response packet ID.
     */
    fun nextPacketId(): Int {
        return ++responseIdCounter
    }

    /**
     * Remove expired connections (idle > timeout).
     */
    fun cleanupExpired() {
        val now = System.currentTimeMillis()
        val toRemove = mutableListOf<TcpConnectionKey>()

        for ((key, conn) in connections) {
            if (conn.state == ConnectionState.CLOSED ||
                (now - conn.createdAt > CONNECTION_TIMEOUT_MS)
            ) {
                toRemove.add(key)
            }
        }

        for (key in toRemove) {
            remove(key)
        }

        if (toRemove.isNotEmpty()) {
            Log.d(TAG, "Cleaned up ${toRemove.size} expired connections, " +
                    "${connections.size} remaining")
        }
    }

    /**
     * Remove all connections.
     */
    fun clear() {
        Log.d(TAG, "Clearing all ${connections.size} connections")
        for (key in connections.keys) {
            remove(key)
        }
        connections.clear()
    }

    /**
     * Number of active connections.
     */
    val activeCount: Int get() = connections.size
}
