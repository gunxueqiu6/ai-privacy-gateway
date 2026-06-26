# Changelog

## 1.0.0 (2024-03-15)

### Initial Release

- Cross-platform PII masking client for Flutter (iOS, Android, Web, macOS, Windows, Linux)
- Singleton-based `PrivacyGateway` client with static convenience methods
- `maskText()` — Mask PII entities in a single text string
- `restoreText()` — Restore masked placeholders to original values
- `maskTextBatch()` — Batch mask up to 50 texts in a single request
- `getEntityList()` — Retrieve supported entity types from the gateway
- `GatewayConfig` with configurable `baseUrl` and `timeout`
- Input validation with clear error messages
- HTTPS enforcement for non-localhost endpoints
