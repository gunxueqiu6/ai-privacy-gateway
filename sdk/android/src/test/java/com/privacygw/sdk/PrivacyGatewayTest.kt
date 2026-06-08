package com.privacygw.sdk

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

class PrivacyGatewayTest {

    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
        val config = GatewayConfig(
            baseUrl = server.url("/").toString().removeSuffix("/"),
            timeout = 5000,
            apiKey = "test-key"
        )
        PrivacyGateway.initialize(config)
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    private val gateway: PrivacyGateway get() = PrivacyGateway.getInstance()

    @Test
    fun `mask returns result on success`() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("""
                    {
                        "masked_text": "Hello [PHONE_0001]",
                        "entities": [{"type": "PII_PHONE", "value": "13812345678", "placeholder": "[PHONE_0001]", "position": 6}],
                        "stats": {"phone": 1}
                    }
                """.trimIndent())
        )

        val result = runBlocking { gateway.mask("Hello 13812345678") }

        assertEquals("Hello [PHONE_0001]", result.maskedText)
        assertEquals(1, result.entities.size)
        assertEquals("PII_PHONE", result.entities[0].type)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `mask throws on empty text`() {
        runBlocking { gateway.mask("") }
    }

    @Test
    fun `restore returns original text`() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("""{"original_text": "Hello World"}""")
        )

        val result = runBlocking {
            gateway.restore("Hello [PHONE_0001]", mapOf("[PHONE_0001]" to "World"))
        }

        assertEquals("Hello World", result.originalText)
    }

    @Test
    fun `getEntities returns entity list`() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("""
                    {
                        "entities": [{"type": "PII_PHONE", "name": "手机号", "description": "手机号", "enabled": true}],
                        "total": 1,
                        "version": "Lite"
                    }
                """.trimIndent())
        )

        val result = runBlocking { gateway.getEntities() }

        assertEquals(1, result.total)
        assertEquals("Lite", result.version)
        assertEquals("PII_PHONE", result.entities[0].type)
        assertTrue(result.entities[0].enabled)
    }

    @Test(expected = IllegalArgumentException::class)
    fun `maskBatch throws on empty list`() {
        runBlocking { gateway.maskBatch(emptyList()) }
    }

    @Test(expected = IllegalArgumentException::class)
    fun `maskBatch throws when exceeds 50 items`() {
        runBlocking { gateway.maskBatch(List(51) { "text $it" }) }
    }

    @Test
    fun `maskBatch sends request correctly`() {
        server.enqueue(
            MockResponse()
                .setResponseCode(200)
                .setBody("""{"results": [], "total_count": 0}""")
        )

        val result = runBlocking { gateway.maskBatch(listOf("text1", "text2")) }

        assertEquals(0, result.totalCount)
        assertTrue(result.results.isEmpty())
    }
}
