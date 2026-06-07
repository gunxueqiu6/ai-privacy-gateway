package com.privacygw.sdk

data class GatewayConfig(
    val baseUrl: String,
    val apiKey: String? = null,
    val timeout: Long = 10000L,
    val headers: Map<String, String> = emptyMap()
)