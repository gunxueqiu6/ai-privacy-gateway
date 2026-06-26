# AI Privacy Gateway — iOS SDK

Protect sensitive data in iOS/macOS apps by routing AI API calls through the Privacy Gateway.

## Features

- **PrivacyGateway** (`Sources/`) — Swift SDK for masking PII before sending to LLMs
- **PrivacyFilter** — NEFilterDataProvider-based network extension for system-wide PII interception

## Installation

### Swift Package Manager

```swift
// Package.swift
.package(url: "https://github.com/gunxueqiu6/ai-privacy-gateway", path: "sdk/ios")
```

Or in Xcode: File → Add Packages → add the repository with path `sdk/ios`.

### CocoaPods

```ruby
pod 'PrivacyGateway', :path => 'sdk/ios'
```

## Quick Start

```swift
import PrivacyGateway

// Initialize
let config = GatewayConfig(
    baseUrl: "http://localhost:9999",
    timeout: 10.0
)
PrivacyGateway.initialize(config: config)

// Mask PII
Task {
    do {
        let result = try await PrivacyGateway.mask(text: "My phone is 13812345678")
        print(result.maskedText)

        // Restore
        let restored = try await PrivacyGateway.restore(
            maskedText: result.maskedText,
            mappings: ["[PII_PHONE_00000001]": "13812345678"]
        )
        print(restored.originalText)
    } catch {
        print("Error: \(error)")
    }
}
```

## API

| Method | Description |
|--------|-------------|
| `mask(text:)` | Mask PII in a single text |
| `restore(maskedText:mappings:)` | Restore masked text to original |
| `maskBatch(texts:)` | Batch mask up to 50 texts |
| `getEntities()` | Get supported entity types |

## Network Extension (PrivacyFilter)

The `PrivacyFilter/` directory contains a `NEFilterDataProvider` implementation that intercepts network flows and masks PII at the system level. Requires Network Extension entitlement.

## Requirements

- iOS 15.0+ / macOS 12.0+
- Swift 5.9+

## License

MIT
