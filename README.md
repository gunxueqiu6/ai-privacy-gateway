# AI Privacy Gateway

> Your AI data is exposed. Install a firewall in 30 seconds.

A high-performance reverse proxy that automatically masks sensitive data (phone numbers, ID cards, emails, bank cards, names, locations, etc.) in AI API requests/responses, supporting all OpenAI-compatible services including DeepSeek, Claude, ChatGPT, and Cursor.

[简体中文](README_CN.md) | [English](README.md)

🔒 **Protect Your Privacy** | ⚡ **Zero Configuration** | 🔄 **Full Streaming Support** | 🌐 **13 Entity Types**

---

## 🌟 Demo

Try our [Online Demo](https://privacygw.pages.dev/demo) to see real-time masking in action!

![Demo Preview](https://raw.githubusercontent.com/gunxueqiu6/ai-privacy-gateway/main/docs/images/demo-preview.png)

---

## Features

- **Automatic Masking** - Detects and replaces 13 types of sensitive data with unique placeholders
- **Full Streaming Support** - Perfectly handles AI streaming responses (SSE)
- **Local Storage Only** - All mappings stored locally, never uploaded to cloud
- **One-line Integration** - Just change your API endpoint, no code changes needed
- **Team Dashboard** (Pro) - Real-time interception stats, session history
- **Cloud Rule Updates** (Pro) - Auto-updating sensitive word rules
- **Browser Extension** - Mask data directly in ChatGPT/Claude/Kimi web interfaces

## Supported Entity Types

| Type | Pattern | Example |
|------|---------|---------|
| Phone | 1[3-9]\d{9} | 13812345678 |
| ID Card | 18 digits | 110101199001011234 |
| Email | Standard format | user@example.com |
| Bank Card | 16-19 digits | 6222021234567890123 |
| **Person Name** | Chinese names | 张三 |
| **Location** | Cities, districts | 北京市海淀区 |
| **Organization** | Company names | 北京科技有限公司 |
| **Plate Number** | Chinese format | 京A12345 |
| **IP Address** | IPv4 | 192.168.1.100 |
| **URL** | HTTP/HTTPS | https://example.com |
| **Date** | Various formats | 2024年1月15日 |
| **Amount** | Currency values | ¥999.99 |
| **Custom** | User-defined | API keys, passwords |

## Quick Start

### Docker (Recommended)

```bash
# One-line deployment
docker-compose up -d

# Configure your AI client
# Change API endpoint from https://api.openai.com to http://localhost:9999
```

### Python

```bash
pip install -r requirements.txt
python main.py
```

### Windows Executable

Download from [Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases) and run `PrivacyGateway.exe`.

## How It Works

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Your AI   │────▶│  Privacy Gateway │────▶│  Target API  │
│   Client    │◀────│  (Masking)      │◀────│  (DeepSeek)  │
└─────────────┘     └──────────────────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Local     │
                    │   SQLite    │
                    └──────────────┘
```

**Request Flow:**
1. Your AI client sends a request containing sensitive data
2. Gateway intercepts and masks sensitive data → `[PII_PHONE_00000001]`
3. Masked request forwarded to target AI API
4. AI response received and restored with original values
5. Restored response returned to your client

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_LLM` | https://api.openai.com | Target AI API endpoint |
| `LISTEN_PORT` | 9999 | Gateway listen port |
| `DB_TYPE` | sqlite | Storage type (sqlite/redis) |
| `MASK_ENGINE_TYPE` | regex | Masking engine (regex/ac_automaton) |
| `LICENSE_KEY` | - | Pro/Enterprise license key |

### Admin Dashboard

Open `http://localhost:9999/admin` to:
- View interception statistics
- Manage custom sensitive words
- Check system health
- View audit logs (Pro/Enterprise)

## Version Comparison

| Feature | Lite (Free) | Pro (¥99/mo) | Enterprise |
|---------|:-----------:|:------------:|:----------:|
| **Core Features** | | | |
| Regex Masking | ✅ | ✅ | ✅ |
| AC Automaton | - | ✅ | ✅ |
| Streaming Proxy | ✅ | ✅ | ✅ |
| **Entity Coverage** | | | |
| Phone/Email/ID/Bank | ✅ | ✅ | ✅ |
| Person/Location/Org | - | ✅ | ✅ |
| Plate/IP/URL/Date/Amount | - | ✅ | ✅ |
| NER Model Integration | - | ✅ | ✅ |
| **Team Features** | | | |
| Basic Dashboard | ✅ | ✅ | ✅ |
| Team Management | - | ✅ | ✅ |
| Concurrent Users | 1 | 20 | 100+ |
| Session History | - | ✅ | ✅ |
| **Security** | | | |
| Local Storage | ✅ | ✅ | ✅ |
| Redis Cluster | - | - | ✅ |
| Audit Logs | - | - | ✅ |
| RBAC | - | - | ✅ |
| Alert Notifications | - | - | ✅ |
| **Deployment** | | | |
| Docker | ✅ | ✅ | ✅ |
| Kubernetes Helm | - | - | ✅ |
| Binary Releases | ✅ | ✅ | ✅ |
| **Support** | | | |
| Community | ✅ | ✅ | ✅ |
| Email Support | - | ✅ | ✅ |
| Dedicated Support | - | - | ✅ |
| SLA Guarantee | - | - | ✅ |

## Architecture

```
ai-privacy-gateway/
├── config.py              # Configuration
├── mask_engine.py         # Masking engine (regex + AC automaton)
├── ner_engine.py          # NER entity recognition
├── stream_buffer.py       # Streaming buffer
├── gateway_core.py        # Proxy core
├── database.py            # SQLite storage
├── redis_storage.py       # Redis storage (Enterprise)
├── license_client.py      # License client
├── rbac.py                # Role-based access control
├── audit_log.py           # Audit logging
├── alert_manager.py       # Alert notifications
├── decay_manager.py       # Graceful degradation
├── main.py                # FastAPI entry
├── rust_src/             # Rust integrity module
├── sdk/                  # SDKs (JS, Android, iOS, Flutter)
│   ├── js/               # JavaScript SDK
│   ├── browser-extension/ # Chrome extension
│   ├── android/          # Android SDK
│   ├── ios/              # iOS SDK
│   └── flutter/          # Flutter SDK
└── tests/                # Test cases
```

## Development

```bash
# Setup
git clone https://github.com/gunxueqiu6/ai-privacy-gateway
cd ai-privacy-gateway
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Build
python build_chain.py --version pro --license-key YOUR_KEY --customer-id YOUR_ID
```

## Browser Extension

Install our [Chrome Extension](https://chrome.google.com/webstore/detail/ai-privacy-gateway/...) to:
- Auto-mask data in ChatGPT/Claude/Kimi web interfaces
- Right-click "Copy Masked Version"
- Customize entity types per website

## API Usage

```bash
# Mask text
curl -X POST http://localhost:9999/api/mask \
  -H "Content-Type: application/json" \
  -d '{"text": "张三住在北京市，电话13812345678"}'

# Restore text
curl -X POST http://localhost:9999/api/restore \
  -H "Content-Type: application/json" \
  -d '{"text": "[PII_PER_001]住在[PII_LOC_001]，电话[PII_PHONE_001]", "mappings": {...}}'

# Batch mask
curl -X POST http://localhost:9999/api/mask/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["text1", "text2", "text3"]}'
```

## License

- **Lite**: MIT License (free for personal/commercial use)
- **Pro**: ¥99/month per team (20 concurrent users)
- **Enterprise**: Custom pricing (100+ concurrent users, SLA)

[Buy Pro License](https://privacygw.pages.dev/pricing)

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Links

- [Documentation](https://privacygw.pages.dev/docs)
- [Website](https://privacygw.pages.dev)
- [Online Demo](https://privacygw.pages.dev/demo)
- [Chrome Extension](https://chrome.google.com/webstore/detail/ai-privacy-gateway/...)
- [GitHub Issues](https://github.com/gunxueqiu6/ai-privacy-gateway/issues)