package com.privacygw.vpn

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

/**
 * 开机启动接收器
 *
 * 用户可选择开机自动启动VPN保护
 */
class BootReceiver : BroadcastReceiver() {

    companion object {
        const val TAG = "BootReceiver"
        const val PREFS_NAME = "privacy_vpn_prefs"
        const val KEY_AUTO_START = "auto_start"
    }

    override fun onReceive(context: Context, intent: Intent) {
        Log.i(TAG, "Received boot completed intent")

        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            val prefs = context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)
            val autoStart = prefs.getBoolean(KEY_AUTO_START, false)

            if (autoStart) {
                Log.i(TAG, "Auto-start enabled, starting VPN service")
                val vpnIntent = Intent(context, PrivacyVpnService::class.java).apply {
                    action = PrivacyVpnService.ACTION_START
                }
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(vpnIntent)
                } else {
                    context.startService(vpnIntent)
                }
            }
        }
    }
}