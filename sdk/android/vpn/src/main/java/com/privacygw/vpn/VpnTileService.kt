package com.privacygw.vpn

import android.content.Intent
import android.graphics.drawable.Icon
import android.os.Build
import android.service.quicksettings.Tile
import android.service.quicksettings.TileService
import android.util.Log

/**
 * 快捷设置Tile服务
 *
 * 系统下拉菜单一键开关VPN保护
 */
class VpnTileService : TileService() {

    companion object {
        const val TAG = "VpnTileService"
    }

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "Tile service created")
    }

    override fun onStartListening() {
        super.onStartListening()
        updateTile()
    }

    override fun onClick() {
        super.onClick()

        Log.i(TAG, "Tile clicked, current state: ${PrivacyVpnService.isRunning}")

        if (PrivacyVpnService.isRunning) {
            // 关闭VPN
            val intent = Intent(this, PrivacyVpnService::class.java).apply {
                action = PrivacyVpnService.ACTION_STOP
            }
            startServiceCompat(intent)
        } else {
            // 开启VPN
            if (isLocked) {
                // 设备锁定时需要解锁
                unlockAndRun {
                    requestVpnPermission()
                }
            } else {
                requestVpnPermission()
            }
        }

        updateTile()
    }

    private fun requestVpnPermission() {
        val intent = android.net.VpnService.prepare(this)
        if (intent != null) {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            startActivity(intent)
        } else {
            // 已授权，直接启动
            startVpn()
        }
    }

    private fun startVpn() {
        val intent = Intent(this, PrivacyVpnService::class.java).apply {
            action = PrivacyVpnService.ACTION_START
        }
        startServiceCompat(intent)
        updateTile()
    }

    private fun startServiceCompat(intent: Intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun updateTile() {
        val tile = qsTile

        if (PrivacyVpnService.isRunning) {
            tile.state = Tile.STATE_ACTIVE
            tile.label = "AI隐私保护"
            tile.subtitle = "已拦截 ${PrivacyVpnService.maskedCount} 条"
            tile.icon = Icon.createWithResource(this, R.drawable.ic_shield_active)
        } else {
            tile.state = Tile.STATE_INACTIVE
            tile.label = "AI隐私保护"
            tile.subtitle = "未开启"
            tile.icon = Icon.createWithResource(this, R.drawable.ic_shield)
        }

        tile.updateTile()
    }
}