# Consumer ProGuard rules for Privacy Gateway SDK

# Keep all public API classes
-keep class com.privacygw.sdk.PrivacyGateway { *; }
-keep class com.privacygw.sdk.GatewayConfig { *; }
-keep class com.privacygw.sdk.MaskResult { *; }
-keep class com.privacygw.sdk.RestoreResult { *; }
-keep class com.privacygw.sdk.EntityType { *; }
-keep class com.privacygw.sdk.EntitiesResponse { *; }
-keep class com.privacygw.sdk.BatchMaskResponse { *; }

# Keep all public methods
-keepclassmembers class com.privacygw.sdk.* {
    public *;
}

# OkHttp
-dontwarn okhttp3.**
-keep class okhttp3.** { *; }

# Gson
-keepattributes Signature
-keep class com.google.gson.** { *; }
-keep class * implements com.google.gson.TypeAdapterFactory
-keep class * implements com.google.gson.JsonSerializer
-keep class * implements com.google.gson.JsonDeserializer