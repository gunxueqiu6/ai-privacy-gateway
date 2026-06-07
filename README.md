# AI Privacy Gateway

> Your team's AI data is exposed. Install a firewall in 30 seconds.

A high-performance reverse proxy that automatically masks sensitive data (phone numbers, ID cards, emails, bank cards) in AI API requests/responses, supporting all OpenAI-compatible services including DeepSeek, Claude, ChatGPT, and Cursor.

[简体中文](README_CN.md) | [English](README.md)

---

## Features

- **Automatic Masking** - Detects and replaces sensitive data with unique placeholders
- **Full Streaming Support** - Perfectly handles AI streaming responses (SSE)
- **Local Storage Only** - All mappings stored locally, never uploaded to cloud
- **One-line Integration** - Just change your API endpoint, no code changes needed
- **Team Dashboard** (Pro) - Real-time interception stats, session history
- **Cloud Rule Updates** (Pro) - Auto-updating sensitive word rules

## Supported Data Types

| Type | Pattern | Example |
|------|---------|---------|
| Phone | 1[3-9]\d{9} | 13812345678 |
| ID Card | 18 digits | 110101199001011234 |
| Email | Standard format | user@example.com |
| Bank Card | 16-19 digits | 6222021234567890 |
| Custom | User-defined | API keys, passwords |

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

Download from [Releases](https://github.com/your-repo/ai-privacy-gateway/releases) and run `PrivacyGateway.exe`.

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
2. Gateway intercepts and masks sensitive data → `[VAULT_PHONE_xxx]`
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

### Admin Dashboard

Open `http://localhost:9999/admin` to:
- View interception statistics
- Manage custom sensitive words
- Check system health

## Version Comparison

| Feature | Lite (Free) | Pro (¥99/mo) | Enterprise |
|---------|-------------|--------------|------------|
| Regex Masking | ✅ | ✅ | ✅ |
| Streaming Proxy | ✅ | ✅ | ✅ |
| Custom Words | Manual | Auto-sync | Auto-sync |
| Admin Dashboard | Basic | Team | Advanced |
| Concurrent Users | 1 | 20 | 100+ |
| Audit Logs | - | - | ✅ |
| RBAC | - | - | ✅ |
| Alert Notifications | - | - | ✅ |

## Architecture

```
ai-privacy-gateway/
├── config.py              # Configuration
├── mask_engine.py         # Masking engine
├── stream_buffer.py       # Streaming buffer
├── gateway_core.py        # Proxy core
├── database.py            # SQLite storage
├── license_client.py      # License client
├── decay_manager.py       # Graceful degradation
├── main.py                # FastAPI entry
├── rust_src/             # Rust integrity module
└── tests/                # Test cases
```

## Development

```bash
# Setup
git clone https://github.com/your-repo/ai-privacy-gateway
cd ai-privacy-gateway
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Build
python build_chain.py --version pro --license-key YOUR_KEY --customer-id YOUR_ID
```

## License

- **Lite**: MIT License (free for personal/commercial use)
- **Pro/Enterprise**: Commercial license required

See [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## Links

- [Documentation](https://docs.your-website.com)
- [Website](https://your-website.com)
- [GitHub Issues](https://github.com/your-repo/ai-privacy-gateway/issues)
