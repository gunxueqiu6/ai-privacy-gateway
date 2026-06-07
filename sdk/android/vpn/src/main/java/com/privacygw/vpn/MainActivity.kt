package com.privacygw.vpn

import android.app.Activity
import android.content.Intent
import android.net.VpnService
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.Switch
import android.widget.TextView
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.launch

/**
 * 主配置Activity
 *
 * 极简UI：开关 + 统计 + 网关配置
 */
class MainActivity : Activity() {

    companion object {
        const val TAG = "MainActivity"
        const val VPN_REQUEST_CODE = 1001
    }

    private lateinit var switchVpn: Switch
    private lateinit var textStats: TextView
    private lateinit var editGatewayUrl: EditText
    private lateinit var editApiKey: EditText
    private lateinit var btnSaveConfig: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        loadConfig()
        updateStats()
    }

    private fun initViews() {
        switchVpn = findViewById(R.id.switch_vpn)
        textStats = findViewById(R.id.text_stats)
        editGatewayUrl = findViewById(R.id.edit_gateway_url)
        editApiKey = findViewById(R.id.edit_api_key)
        btnSaveConfig = findViewById(R.id.btn_save_config)

        switchVpn.setOnCheckedChangeListener { _, isChecked ->
            if (isChecked) {
                requestVpnPermission()
            } else {
                stopVpn()
            }
        }

        btnSaveConfig.setOnClickListener {
            saveConfig()
        }

        // 定期更新统计
        lifecycleScope.launch {
            while (true) {
                kotlinx.coroutines.delay(5000)
                updateStats()
            }
        }
    }

    private fun loadConfig() {
        val prefs = getSharedPreferences(PrivacyVpnService.PREFS_NAME, MODE_PRIVATE)
        editGatewayUrl.setText(prefs.getString("gateway_url", "http://localhost:9999"))
        editApiKey.setText(prefs.getString("api_key", ""))
        switchVpn.isChecked = PrivacyVpnService.isRunning
    }

    private fun saveConfig() {
        val prefs = getSharedPreferences(PrivacyVpnService.PREFS_NAME, MODE_PRIVATE)
        prefs.edit()
            .putString("gateway_url", editGatewayUrl.text.toString())
            .putString("api_key", editApiKey.text.toString())
            .apply()

        PrivacyVpnService.gatewayUrl = editGatewayUrl.text.toString()
        PrivacyVpnService.gatewayApiKey = editApiKey.text.toString()

        Log.i(TAG, "Config saved: gateway=${PrivacyVpnService.gatewayUrl}")
    }

    private fun requestVpnPermission() {
        val intent = VpnService.prepare(this)
        if (intent != null) {
            startActivityForResult(intent, VPN_REQUEST_CODE)
        } else {
            // 已授权，直接启动
            startVpn()
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        if (requestCode == VPN_REQUEST_CODE) {
            if (resultCode == RESULT_OK) {
                Log.i(TAG, "VPN permission granted")
                startVpn()
            } else {
                Log.w(TAG, "VPN permission denied")
                switchVpn.isChecked = false
            }
        }
    }

    private fun startVpn() {
        saveConfig()

        val intent = Intent(this, PrivacyVpnService::class.java).apply {
            action = PrivacyVpnService.ACTION_START
            putExtra(PrivacyVpnService.EXTRA_GATEWAY_URL, PrivacyVpnService.gatewayUrl)
            putExtra(PrivacyVpnService.EXTRA_API_KEY, PrivacyVpnService.gatewayApiKey)
        }
        startService(intent)

        Log.i(TAG, "VPN service started")
        updateStats()
    }

    private fun stopVpn() {
        val intent = Intent(this, PrivacyVpnService::class.java).apply {
            action = PrivacyVpnService.ACTION_STOP
        }
        startService(intent)

        Log.i(TAG, "VPN service stopped")
        updateStats()
    }

    private fun updateStats() {
        val masked = PrivacyVpnService.maskedCount
        val total = PrivacyVpnService.totalRequests
        val running = PrivacyVpnService.isRunning

        textStats.text = if (running) {
            "🛡️ 保护已开启\n已拦截 $masked 条敏感信息\n共处理 $total 次请求"
        } else {
            "⚠️ 保护未开启"
        }

        switchVpn.isChecked = running
    }
}