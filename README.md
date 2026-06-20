# AI Privacy Gateway

> Your AI data is exposed. Install a firewall in 30 seconds.

**v1.1.0** — Open-source AI API privacy gateway. Masks sensitive data before it leaves your machine.

A high-performance reverse proxy that automatically masks sensitive data (phone numbers, ID cards, emails, bank cards, names, locations, etc.) in AI API requests/responses, supporting all OpenAI-compatible services including DeepSeek, Claude, ChatGPT, and Cursor.

[简体中文](README_CN.md) | [English](README.md)

## Quick Start

### One-Click Start (New users start here)

No manual configuration needed. The script guides you through setup interactively.

```bash
# Windows: double-click start.bat, or:
python start.py

# macOS / Linux:
./start.sh
# or:
python3 start.py
```

What the wizard does:
- Detects your environment and dependencies
- Walks you through AI provider selection (OpenAI / DeepSeek / Custom)
- Generates secure JWT and encryption keys automatically
- Writes configuration to `.env`
- Installs dependencies if needed
- Starts the gateway on `http://localhost:9999`

> Non-interactive mode for CI/CD: `python start.py --non-interactive`

### Docker (Recommended)

```bash
docker run -d \
  --name ai-privacy-gw \
  -p 9999:9999 \
  -v ./vault_data:/app/vault_data \
  -e TARGET_LLM=https://api.openai.com \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite

# Check the auto-generated admin password:
docker logs ai-privacy-gw
```

### Docker Compose

```bash
docker-compose up -d

# Check the auto-generated admin password:
docker logs ai-privacy-vault
```

### Python (Manual)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start (secrets auto-generated on first run)
python main.py
```

On first start, an admin password is auto-generated and displayed in the console banner. Save it immediately to access the admin dashboard at `http://localhost:9999/admin`.

To customize settings, create a `.env` file or run `python start.py` for guided setup.

### Windows Executable

Download `PrivacyGateway.exe` from [Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases) and double-click to run.

### macOS Binary

Download from [Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases), make it executable (`chmod +x PrivacyGateway`), and run `./PrivacyGateway`.

## Configuration

Set your AI client's API endpoint to `http://localhost:9999`:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9999/v1",
    api_key="your-api-key"
)
```

### Cursor / VS Code

Settings → API Key → Base URL → `http://localhost:9999`

### Systemd (Linux Server)

```ini
[Unit]
Description=AI Privacy Gateway
After=network.target

[Service]
Type=simple
User=privacygw
WorkingDirectory=/opt/privacy-gateway
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name gw.example.com;

    location / {
        proxy_pass http://127.0.0.1:9999;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_LLM` | https://api.openai.com | Target AI API endpoint |
| `LISTEN_PORT` | 9999 | Gateway listen port |
| `DB_PATH` | ./vault_data/privacy_vault.db | SQLite database path |
| `ADMIN_PASSWORD` | (auto-generated) | Admin dashboard password |
| `JWT_SECRET` | (auto-generated) | JWT signing secret |
| `VAULT_ENCRYPT_KEY` | (auto-generated) | Vault encryption key |

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

- View real-time interception statistics and trend charts
- Manage custom sensitive words (add, test, delete)
- Check system health and version information
- Browse supported entity types

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
├── main.py                # FastAPI entry point
├── routers/               # Route modules
│   ├── proxy.py           # Core proxy routes
│   ├── api.py             # Mask/restore API
│   ├── admin.py           # Admin dashboard
│   └── auth.py            # Auth status
├── static/                # Admin dashboard UI
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
