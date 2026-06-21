package com.privacygw.sdk

import androidx.annotation.WorkerThread
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking
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
                    val errorBody = response.body?.string()
                    throw IOException("Request failed with code ${response.code()}: $errorBody")
                }
                val body = response.body()?.string()
                    ?: throw IOException("Empty response body")
                gson.fromJson(body, clazz)
            }
        }
    }

    companion object {
        private var instance: PrivacyGateway? = null

        @Synchronized
        fun initialize(config: GatewayConfig): PrivacyGateway {
            instance = PrivacyGateway(
                baseUrl = config.baseUrl.removeSuffix("/"),
                timeout = config.timeout,
                headers = buildHeaders(config)
            )
            return instance!!
        }

        @Synchronized
        fun getInstance(): PrivacyGateway {
            return instance ?: throw IllegalStateException("PrivacyGateway not initialized. Call initialize() first.")
        }

        private fun buildHeaders(config: GatewayConfig): Map<String, String> {
            val headers = mutableMapOf<String, String>()
            config.headers.forEach { headers[it.key] = it.value }
            config.apiKey?.let { headers["X-API-Key"] = it }
            return headers
        }

        @WorkerThread
        @JvmStatic
        fun mask(text: String): MaskResult {
            return runBlocking(Dispatchers.IO) { getInstance().mask(text) }
        }

        @WorkerThread
        @JvmStatic
        fun restore(maskedText: String, mappings: Map<String, String>): RestoreResult {
            return runBlocking(Dispatchers.IO) { getInstance().restore(maskedText, mappings) }
        }

        @WorkerThread
        @JvmStatic
        fun maskBatch(texts: List<String>): BatchMaskResponse {
            return runBlocking(Dispatchers.IO) { getInstance().maskBatch(texts) }
        }

        @WorkerThread
        @JvmStatic
        fun getEntities(): EntitiesResponse {
            return runBlocking(Dispatchers.IO) { getInstance().getEntities() }
        }
    }
}