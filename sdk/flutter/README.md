# AI Privacy Gateway — Flutter SDK

Protect sensitive data in Flutter apps by routing AI API calls through the
[AI Privacy Gateway](https://github.com/gunxueqiu6/ai-privacy-gateway).

Automatically mask phone numbers, email addresses, ID card numbers, bank card
numbers, and 10+ other entity types before they reach third-party AI services.
Restore them from masked placeholders when responses come back.

## Features

- **Cross-platform** — iOS, Android, Web, macOS, Windows, Linux
- **13+ entity types** — phone, email, ID card, bank card, name, address, and
  more
- **Singleton client** — static convenience methods, no manual wiring
- **Input validation** — clear error messages for missing or malformed config
- **HTTPS enforcement** — non-localhost endpoints require TLS

## Installation

Add to your `pubspec.yaml`:

```yaml
dependencies:
  privacy_gateway_sdk: ^1.0.0
```

Or install from the repository:

```yaml
dependencies:
  privacy_gateway_sdk:
    git: https://github.com/gunxueqiu6/ai-privacy-gateway.git
    path: sdk/flutter
```

## Quick Start

```dart
import 'package:privacy_gateway_sdk/privacy_gateway_sdk.dart';

void main() async {
  // Initialize the gateway client
  PrivacyGateway.initialize(
    GatewayConfig(
      baseUrl: 'http://localhost:9999',
      timeout: Duration(seconds: 10),
    ),
  );

  // Mask PII in text
  final result = await PrivacyGateway.maskText('My phone is 13812345678');
  print(result.maskedText);
  // → "My phone is [PII_PHONE_00000001]"

  // Restore masked text
  final restored = await PrivacyGateway.restoreText(
    result.maskedText,
    {'[PII_PHONE_00000001]': '13812345678'},
  );
  print(restored.originalText);
  // → "My phone is 13812345678"

  // Batch mask
  final batch = await PrivacyGateway.maskTextBatch([
    'Phone: 13900001111',
    'Email: test@example.com',
  ]);
  print('Masked ${batch.results.length} texts');

  // List supported entity types
  final entities = await PrivacyGateway.getEntityList();
  print('${entities.total} entity types supported');
}
```

## API

| Method                    | Description                                |
|---------------------------|--------------------------------------------|
| `maskText(text)`          | Mask PII entities in a single text string  |
| `restoreText(text, map)`  | Restore masked placeholders to originals   |
| `maskTextBatch(texts)`    | Batch mask up to 50 texts at once          |
| `getEntityList()`         | List entity types supported by the gateway |

## Requirements

- Dart 3.0+
- Flutter 3.10+ (for Flutter apps)
- AI Privacy Gateway backend service running on a reachable host

## About the Backend

This SDK requires a running instance of
[AI Privacy Gateway](https://github.com/gunxueqiu6/ai-privacy-gateway), the
open-source backend that performs the actual PII detection and masking. You can
deploy it via Docker or run it directly with Python.

## License

MIT
