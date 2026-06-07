# AI Privacy Gateway

> Your AI data is exposed. Install a firewall in 30 seconds.

A high-performance reverse proxy that automatically masks sensitive data (phone numbers, ID cards, emails, bank cards, names, locations, etc.) in AI API requests/responses, supporting all OpenAI-compatible services including DeepSeek, Claude, ChatGPT, and Cursor.

[简体中文](README_CN.md) | [English](README.md)

## Quick Start

### Docker (Recommended)

```bash
docker run -d \
  --name ai-privacy-gw \
  -p 9999:9999 \
  -v ./vault_data:/app/vault_data \
  -e TARGET_LLM=https://api.openai.com \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

### Docker Compose

```bash
docker-compose up -d
```

### Python

```bash
pip install -r requirements.txt
python main.py
```

### Windows Executable

Download from [Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases) and run `PrivacyGateway.exe`.

## Configuration

Set your AI client's API endpoint to `http://localhost:9999`:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9999/v1",
    api_key="your-api-key"
)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_LLM` | https://api.openai.com | Target AI API endpoint |
| `LISTEN_PORT` | 9999 | Gateway listen port |
| `DB_PATH` | ./vault_data/privacy_vault.db | SQLite database path |
| `ADMIN_PASSWORD` | admin123 | Admin dashboard password |

## Supported Entity Types

| Type | Pattern | Example |
|------|---------|---------|
| Phone | 1[3-9]\d{9} | 13812345678 |
| ID Card | 18 digits | 110101199001011234 |
| Email | Standard format | user@example.com |
| Bank Card | 16-19 digits | 6222021234567890123 |
| Person Name | Chinese names | 张三 |
| Location | Cities, districts | 北京市海淀区 |
| Organization | Company names | 北京科技有限公司 |
| Plate Number | Chinese format | 京A12345 |
| IP Address | IPv4 | 192.168.1.100 |
| URL | HTTP/HTTPS | https://example.com |
| Date | Various formats | 2024年1月15日 |
| Amount | Currency values | ¥999.99 |
| Postcode | 6 digits | 100080 |
| Custom | User-defined | API keys, passwords |

## Enterprise & Team

This is the free **Lite** edition. For team collaboration, RBAC, AC automaton engine, audit logging, SSO, and dedicated support, please visit **[privacygw.pages.dev](https://privacygw.pages.dev)** for Pro and Enterprise editions.

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

## Admin Dashboard

Open `http://localhost:9999` and login with your admin password to:

- View interception statistics
- Manage custom sensitive words
- Check system health

## API Usage

```bash
# Mask text
curl -X POST http://localhost:9999/api/mask \
  -H "Content-Type: application/json" \
  -d '{"text": "张三住在北京市，电话13812345678"}'

# Restore text
curl -X POST http://localhost:9999/api/restore \
  -H "Content-Type: application/json" \
  -d '{"text": "[PII_PER_00000001]住在[PII_LOC_00000001]，电话[PII_PHONE_00000001]", "mappings": {...}}'

# Batch mask
curl -X POST http://localhost:9999/api/mask/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["text1", "text2", "text3"]}'
```

## Project Structure

```
ai-privacy-gateway/
├── config.py              # Configuration
├── mask_engine.py         # Regex masking engine
├── ner_engine.py          # NER entity recognition
├── stream_buffer.py       # Streaming buffer
├── gateway_core.py        # Proxy core
├── database.py            # SQLite storage
├── main.py                # FastAPI entry
├── static/                # Admin dashboard
├── tests/                 # Test cases
└── website-astro/         # Website (Astro)
```

## Development

```bash
# Setup
git clone https://github.com/gunxueqiu6/ai-privacy-gateway
cd ai-privacy-gateway
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run
python main.py
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Links

- [Documentation](https://privacygw.pages.dev/docs)
- [Website](https://privacygw.pages.dev)
- [Online Demo](https://privacygw.pages.dev/demo)
- [GitHub Issues](https://github.com/gunxueqiu6/ai-privacy-gateway/issues)
