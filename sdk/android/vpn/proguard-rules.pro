# Add project specific ProGuard rules here.

# Keep VPN service
-keep class com.privacygw.vpn.PrivacyVpnService { *; }
-keep class com.privacygw.vpn.VpnTileService { *; }

# Keep data classes
-keep class com.privacygw.vpn.data.** { *; }

# OkHttp
-dontwarn okhttp3.**
-keep class okhttp3.** { *; }

# Kotlin coroutines
-keepclassmembers class kotlinx.coroutines.** {
    volatile <fields>;
}