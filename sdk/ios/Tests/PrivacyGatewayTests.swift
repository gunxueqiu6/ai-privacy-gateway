import XCTest
@testable import PrivacyGateway

final class PrivacyGatewayTests: XCTestCase {

    func testMaskResultDecoding() throws {
        let json = """
        {
            "masked_text": "Hello [PHONE_0001]",
            "entities": [
                {
                    "type": "PII_PHONE",
                    "value": "13812345678",
                    "placeholder": "[PHONE_0001]",
                    "position": 6
                }
            ],
            "stats": {"phone": 1}
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let result = try decoder.decode(MaskResult.self, from: json)

        XCTAssertEqual(result.maskedText, "Hello [PHONE_0001]")
        XCTAssertEqual(result.entities.count, 1)
        XCTAssertEqual(result.entities[0].type, "PII_PHONE")
        XCTAssertEqual(result.entities[0].value, "13812345678")
        XCTAssertEqual(result.stats.phone, 1)
    }

    func testRestoreResultDecoding() throws {
        let json = """
        {"original_text": "Hello World"}
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let result = try decoder.decode(RestoreResult.self, from: json)

        XCTAssertEqual(result.originalText, "Hello World")
    }

    func testEntitiesResponseDecoding() throws {
        let json = """
        {
            "entities": [
                {
                    "type": "PII_PHONE",
                    "name": "手机号",
                    "description": "中国大陆手机号",
                    "enabled": true
                }
            ],
            "total": 1,
            "version": "Lite"
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(EntitiesResponse.self, from: json)

        XCTAssertEqual(response.entities.count, 1)
        XCTAssertEqual(response.total, 1)
        XCTAssertEqual(response.version, "Lite")
        XCTAssertEqual(response.entities[0].type, "PII_PHONE")
        XCTAssertTrue(response.entities[0].enabled)
    }

    func testGatewayConfig() {
        let config = GatewayConfig(
            baseUrl: "http://localhost:9999",
            apiKey: "test-key",
            timeout: 5000
        )

        XCTAssertEqual(config.baseUrl, "http://localhost:9999")
        XCTAssertEqual(config.apiKey, "test-key")
        XCTAssertEqual(config.timeout, 5000)
    }

    func testGatewayConfigDefaultTimeout() {
        let config = GatewayConfig(baseUrl: "http://localhost:9999")

        XCTAssertEqual(config.timeout, 10000)
        XCTAssertNil(config.apiKey)
    }

    func testPrivacyGatewayError() {
        let error = PrivacyGatewayError.serverError(404)
        XCTAssertEqual(error.errorDescription, "Server returned error code 404")
    }

    func testBatchMaskResponseDecoding() throws {
        let json = """
        {
            "results": [
                {
                    "original": "test",
                    "masked": "masked",
                    "entities": [],
                    "stats": {}
                }
            ],
            "total_count": 1
        }
        """.data(using: .utf8)!

        let decoder = JSONDecoder()
        let response = try decoder.decode(BatchMaskResponse.self, from: json)

        XCTAssertEqual(response.results.count, 1)
        XCTAssertEqual(response.totalCount, 1)
        XCTAssertEqual(response.results[0].original, "test")
        XCTAssertEqual(response.results[0].masked, "masked")
    }
}
