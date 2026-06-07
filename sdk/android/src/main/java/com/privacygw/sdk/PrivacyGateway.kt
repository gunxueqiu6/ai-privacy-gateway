package com.privacygw.sdk

import com.google.gson.Gson
import okhttp3.*
import java.io.IOException

class PrivacyGateway private constructor(
    private val baseUrl: String,
    private val timeout: Long,
    private val headers: Map<String, String>
) {

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(timeout, java.util.concurrent.TimeUnit.MILLISECONDS)
        .readTimeout(timeout, java.util.concurrent.TimeUnit.MILLISECONDS)
        .writeTimeout(timeout, java.util.concurrent.TimeUnit.MILLISECONDS)
        .build()

    private val gson = Gson()

    suspend fun mask(text: String): MaskResult {
        if (text.isBlank()) {
            throw IllegalArgumentException("text must be a non-empty string")
        }

        val body = RequestBody.create(
            MediaType.parse("application/json"),
            gson.toJson(mapOf("text" to text))
        )

        val request = Request.Builder()
            .url("$baseUrl/api/mask")
            .post(body)
            .applyHeaders()
            .build()

        return executeRequest(request, MaskResult::class.java)
    }

    suspend fun restore(maskedText: String, mappings: Map<String, String>): RestoreResult {
        if (maskedText.isBlank()) {
            throw IllegalArgumentException("maskedText must be a non-empty string")
        }

        val body = RequestBody.create(
            MediaType.parse("application/json"),
            gson.toJson(mapOf("text" to maskedText, "mappings" to mappings))
        )

        val request = Request.Builder()
            .url("$baseUrl/api/restore")
            .post(body)
            .applyHeaders()
            .build()

        return executeRequest(request, RestoreResult::class.java)
    }

    suspend fun maskBatch(texts: List<String>): BatchMaskResponse {
        if (texts.isEmpty()) {
            throw IllegalArgumentException("texts must be a non-empty list")
        }

        if (texts.size > 50) {
            throw IllegalArgumentException("Maximum 50 texts per batch")
        }

        val body = RequestBody.create(
            MediaType.parse("application/json"),
            gson.toJson(mapOf("texts" to texts))
        )

        val request = Request.Builder()
            .url("$baseUrl/api/mask/batch")
            .post(body)
            .applyHeaders()
            .build()

        return executeRequest(request, BatchMaskResponse::class.java)
    }

    suspend fun getEntities(): EntitiesResponse {
        val request = Request.Builder()
            .url("$baseUrl/api/entities")
            .get()
            .applyHeaders()
            .build()

        return executeRequest(request, EntitiesResponse::class.java)
    }

    private fun Request.Builder.applyHeaders(): Request.Builder {
        headers.forEach { (key, value) ->
            this.header(key, value)
        }
        this.header("Content-Type", "application/json")
        return this
    }

    private suspend fun <T> executeRequest(request: Request, clazz: Class<T>): T {
        return kotlinx.coroutines.withContext(kotlinx.coroutines.Dispatchers.IO) {
            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    throw IOException("Request failed with code ${response.code()}")
                }
                val body = response.body()?.string()
                    ?: throw IOException("Empty response body")
                gson.fromJson(body, clazz)
            }
        }
    }

    companion object {
        private var instance: PrivacyGateway? = null

        fun initialize(config: GatewayConfig): PrivacyGateway {
            instance = PrivacyGateway(
                baseUrl = config.baseUrl.removeSuffix("/"),
                timeout = config.timeout,
                headers = buildHeaders(config)
            )
            return instance!!
        }

        fun getInstance(): PrivacyGateway {
            return instance ?: throw IllegalStateException("PrivacyGateway not initialized. Call initialize() first.")
        }

        private fun buildHeaders(config: GatewayConfig): Map<String, String> {
            val headers = mutableMapOf<String, String>()
            config.headers.forEach { headers[it.key] = it.value }
            config.apiKey?.let { headers["X-API-Key"] = it }
            return headers
        }

        fun mask(text: String): MaskResult {
            return getInstance().mask(text)
        }

        fun restore(maskedText: String, mappings: Map<String, String>): RestoreResult {
            return getInstance().restore(maskedText, mappings)
        }

        fun maskBatch(texts: List<String>): BatchMaskResponse {
            return getInstance().maskBatch(texts)
        }

        fun getEntities(): EntitiesResponse {
            return getInstance().getEntities()
        }
    }
}