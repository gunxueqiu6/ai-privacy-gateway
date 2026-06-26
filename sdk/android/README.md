# AI Privacy Gateway — Android SDK

Protect sensitive data in Android apps by routing AI API calls through the Privacy Gateway.

## Features

- **Android Library** (`library/`) — Drop-in SDK for masking PII before sending to LLMs
- **Android VPN** (`vpn/`) — System-wide VPN-based packet interception with HTTP PII masking

## Installation

### Library SDK

Add to `settings.gradle`:

```groovy
include ':privacygw-sdk'
project(':privacygw-sdk').projectDir = new File('sdk/android/library')
```

Add to `app/build.gradle`:

```groovy
implementation project(':privacygw-sdk')
```

### VPN Module

```groovy
include ':privacygw-vpn'
project(':privacygw-vpn').projectDir = new File('sdk/android/vpn')
```

## Quick Start

```kotlin
import com.privacygw.sdk.PrivacyGateway
import com.privacygw.sdk.GatewayConfig

// Initialize
PrivacyGateway.initialize(
    GatewayConfig(
        baseUrl = "http://localhost:9999",
        timeout = 10000
    )
)

// Mask PII
val result = PrivacyGateway.mask("My phone is 13812345678")
println(result.maskedText)

// Restore
val restored = PrivacyGateway.restore(
    result.maskedText,
    mapOf("[PII_PHONE_00000001]" to "13812345678")
)
println(restored.originalText)
```

## VPN Module

The VPN module intercepts all device traffic and masks PII in HTTP requests to AI APIs. Requires VPN permission.

See `vpn/src/main/java/com/privacygw/vpn/` for the core packet processing logic.

## Requirements

- Android 8.0+ (API 26+)
- Kotlin 1.9+

## License

MIT
