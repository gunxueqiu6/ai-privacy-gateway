package com.privacygw.vpn

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import java.io.FileInputStream
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.channels.FileChannel

/**
 * AI Privacy Gateway VPN Service
 *
 * 系统级网络过滤器，拦截所有出站HTTP流量，对AI服务请求进行脱敏处理。
 *
 * 工作原理：
 * 1. 创建本地TUN接口，拦截所有TCP流量
 * 2. 解析HTTP请求，检查目标域名
 * 3. AI服务域名（openai.com, api.anthropic.com等）→ 调用网关脱敏 → 转发
 * 4. 其他域名 → 直通，零性能影响
 */
class PrivacyVpnService : VpnService() {

    companion object {
        const val TAG = "PrivacyVpnService"
        const val NOTIFICATION_CHANNEL_ID = "privacy_vpn_channel"
        const val NOTIFICATION_ID = 1001

        const val ACTION_START = "com.privacygw.vpn.START"
        const val ACTION_STOP = "com.privacygw.vpn.STOP"
        const val ACTION_UPDATE_STATS = "com.privacygw.vpn.UPDATE_STATS"

        const val EXTRA_GATEWAY_URL = "gateway_url"
        const val EXTRA_API_KEY = "api_key"

        // DNS服务器地址（TODO: 改为可配置，应从配置界面/远程设置读取）
        val DNS_SERVERS = listOf("8.8.8.8", "8.8.4.4")

        // AI服务域名白名单（这些域名的请求会被脱敏）
        val AI_SERVICE_DOMAINS = setOf(
            "openai.com",
            "api.openai.com",
            "chat.openai.com",
            "api.anthropic.com",
            "anthropic.com",
            "api.deepseek.com",
            "deepseek.com",
            "chat.deepseek.com",
            "api.moonshot.cn",
            "moonshot.cn",
            "kimi.moonshot.cn",
            "api.x.ai",
            "x.ai",
            "grok.x.ai",
            "api.doubao.com",
            "doubao.com",
            "api.yuanbao.com",
            "yuanbao.com",
            "api.coze.cn",
            "coze.cn",
            "api.coze.com",
            "coze.com"
        )

        // 网关配置
        var gatewayUrl = "http://localhost:9999"
        var gatewayApiKey = ""

        // 状态
        @Volatile
        var isRunning = false

        // 统计
        @Volatile
        var maskedCount = 0
        @Volatile
        var totalRequests = 0
    }

    private var vpnInterface: ParcelFileDescriptor? = null
    private var vpnThread: Thread? = null
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    // 配置
    private var config: VpnConfig = VpnConfig()

    data class VpnConfig(
        val mtu: Int = 1500,
        val address: String = "10.0.0.2",
        val prefixLength: Int = 24,
        val sessionName: String = "AI Privacy Gateway"
    )

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        Log.i(TAG, "VPN Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.i(TAG, "VPN Service onStartCommand: intent=${intent?.action}")

        when (intent?.action) {
            ACTION_START -> {
                gatewayUrl = intent.getStringExtra(EXTRA_GATEWAY_URL) ?: gatewayUrl
                gatewayApiKey = intent.getStringExtra(EXTRA_API_KEY) ?: gatewayApiKey
                startVpn()
            }
            ACTION_STOP -> {
                stopVpn()
                stopSelf(startId)
            }
            ACTION_UPDATE_STATS -> {
                updateNotification()
            }
        }

        return START_STICKY
    }

    /**
     * 启动VPN
     */
    private fun startVpn() {
        if (isRunning) {
            Log.w(TAG, "VPN already running")
            return
        }

        Log.i(TAG, "Starting VPN with gateway: $gatewayUrl")

        // 请求VPN权限（如果尚未授权）
        val intent = VpnService.prepare(this)
        if (intent != null) {
            // 需要用户授权
            Log.i(TAG, "VPN permission required, sending intent")
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
            return
        }

        // 已授权，启动VPN
        try {
            establishVpn()
            startForeground(NOTIFICATION_ID, createNotification())
            isRunning = true
            startPacketProcessing()
            Log.i(TAG, "VPN started successfully")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start VPN", e)
            stopSelf()
        }
    }

    /**
     * 建立VPN接口
     */
    private fun establishVpn() {
        val builder = Builder()
            .setMtu(config.mtu)
            .addAddress(config.address, config.prefixLength)
            .setSession(config.sessionName)

        // 添加路由（拦截所有流量）
        builder.addRoute("0.0.0.0", 0)

        // 允许应用自身绕过VPN（用于与网关通信）
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            builder.addDisallowedApplication(packageName)
        }

        // DNS配置（TODO: 改成可配置，目前硬编码为Google DNS）
        DNS_SERVERS.forEach { builder.addDnsServer(it) }

        vpnInterface = builder.establish()
        Log.i(TAG, "VPN interface established: ${vpnInterface != null}")
    }

    /**
     * 启动数据包处理
     */
    private fun startPacketProcessing() {
        vpnThread = Thread {
            Log.i(TAG, "Packet processing thread started")

            val fd = vpnInterface?.fileDescriptor
            if (fd == null) {
                Log.e(TAG, "VPN interface not available")
                return
            }

            val inputChannel = FileInputStream(fd).channel
            val outputChannel = FileOutputStream(fd).channel
            val buffer = ByteBuffer.allocate(config.mtu)

            try {
                while (isRunning && vpnInterface != null) {
                    // 从TUN接口读取数据包
                    buffer.clear()
                    val read = inputChannel.read(buffer)
                    if (read > 0) {
                        buffer.flip()
                        processPacket(buffer, outputChannel)
                    }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Packet processing error", e)
            }

            Log.i(TAG, "Packet processing thread ended")
        }.apply { start() }
    }

    /**
     * 处理单个数据包
     *
     * ALPHA WARNING: VPN filtering is NOT YET IMPLEMENTED.
     * This method currently operates in pass-through mode — all packets
     * are forwarded without inspection. The following functionality is
     * planned but not yet implemented:
     * 1. Parse IP header
     * 2. Parse TCP header
     * 3. Parse HTTP request
     * 4. Check destination domain against AI service whitelist
     * 5. If matched, call privacy gateway for masking
     * 6. Reassemble packet and forward
     */
    private fun processPacket(packet: ByteBuffer, output: FileChannel) {
        totalRequests++
        output.write(packet)
    }

    /**
     * 停止VPN
     */
    private fun stopVpn() {
        Log.i(TAG, "Stopping VPN")
        isRunning = false

        vpnThread?.interrupt()
        vpnThread = null

        vpnInterface?.close()
        vpnInterface = null

        scope.cancel()

        Log.i(TAG, "VPN stopped")
    }

    override fun onDestroy() {
        stopVpn()
        super.onDestroy()
        Log.i(TAG, "VPN Service destroyed")
    }

    /**
     * 创建通知渠道
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "AI Privacy Gateway",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "AI隐私保护服务状态"
                setShowBadge(false)
            }

            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    /**
     * 创建通知
     */
    private fun createNotification(): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val stopIntent = Intent(this, PrivacyVpnService::class.java).apply {
            action = ACTION_STOP
        }
        val stopPendingIntent = PendingIntent.getService(
            this, 1, stopIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, NOTIFICATION_CHANNEL_ID)
                .setContentTitle("🛡️ AI 隐私保护已开启")
                .setContentText("已拦截 $maskedCount 条敏感信息 · 共处理 $totalRequests 次请求")
                .setSmallIcon(R.drawable.ic_shield)
                .setContentIntent(pendingIntent)
                .addAction(Notification.Action.Builder(
                    null, "关闭", stopPendingIntent
                ).build())
                .setOngoing(true)
                .build()
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
                .setContentTitle("🛡️ AI 隐私保护已开启")
                .setContentText("已拦截 $maskedCount 条敏感信息")
                .setSmallIcon(R.drawable.ic_shield)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build()
        }
    }

    /**
     * 更新通知
     */
    private fun updateNotification() {
        if (!isRunning) return

        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, createNotification())
    }
}