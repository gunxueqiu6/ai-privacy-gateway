---
layout: ../../../layouts/DocsLayout.astro
title: Configuration Reference
description: AI Privacy Gateway complete configuration reference — environment variables, masking rules, custom keywords, NER model selection.
canonicalURL: https://privacygw.pages.dev/en/docs/config
---

# Configuration Reference

Complete environment variable and configuration file reference.

## Core Environment Variables

| Variable | Default | Description |
|------|--------|------|
| `TARGET_LLM` | `https://api.openai.com` | Target AI API endpoint (OpenAI-compatible) |
| `LISTEN_PORT` | `9999` | Gateway listen port |
| `UPSTREAM_API_KEY` | (empty) | Upstream LLM API key |
| `ADMIN_PASSWORD` | (auto-generated) | Admin dashboard password |
| `JWT_SECRET` | (auto-generated) | JWT signing secret |
| `VAULT_ENCRYPT_KEY` | (auto-generated) | AES-256-GCM vault encryption key |

## Database Configuration

| Variable | Default | Description |
|------|--------|------|
| `DB_PATH` | `./vault_data/privacy_vault.db` | SQLite database path |
| `DB_TYPE` | `sqlite` | Database type (currently sqlite only) |
| `MAPPING_TTL` | `259200` (72h) | PII mapping retention (seconds) |
| `STATELESS_MODE` | `0` | Set to 1 for memory-only mode (no disk writes) |
| `DRY_RUN_MODE` | `0` | Set to 1 for detection-only mode (no masking) |

## Upstream Load Balancing

| Variable | Default | Description |
|------|--------|------|
| `UPSTREAM_LLM_URLS` | (empty) | Comma-separated upstream API URLs |
| `UPSTREAM_LB_STRATEGY` | `round_robin` | Strategy: `round_robin` / `random` / `least_connections` |
| `UPSTREAM_HEALTH_CHECK_INTERVAL` | `30` | Health check interval (seconds) |
| `UPSTREAM_MODEL_MAP` | `{}` | JSON model-to-upstream routing map |

## Performance Controls

| Variable | Default | Description |
|------|--------|------|
| `MAX_CONCURRENT_REQUESTS` | `50` | Maximum concurrent requests |
| `MAX_REQUEST_BODY_SIZE` | `10485760` (10MB) | Max request body size (bytes) |
| `SHUTDOWN_TIMEOUT` | `30` | Graceful shutdown timeout (seconds) |
| `RATE_LIMIT_STORAGE` | `memory://` | Rate limit storage backend |

## Logging & TLS

| Variable | Default | Description |
|------|--------|------|
| `LOG_FORMAT` | `json` | Log format: `json` or `text` |
| `LOG_LEVEL` | `INFO` | Log level: DEBUG / INFO / WARNING / ERROR |
| `SSL_CERTFILE` | (empty) | SSL certificate path |
| `SSL_KEYFILE` | (empty) | SSL private key path |

## Masking Rules

Custom keyword file: `vault_data/keywords.txt`

```text
# Custom keywords (one per line)
# Format: sensitive_word:replacement_label
Internal Project X:PROJECT_X
Client Alpha:CLIENT_ALPHA
Secret Project Phoenix:SECRET_PHOENIX
```

Custom regex file: `vault_data/patterns.json`

```json
{
  "custom": [
    {"name": "Employee ID", "pattern": "EMP\\d{6}"},
    {"name": "Project Code", "pattern": "PRJ-[A-Z]{3}-\\d{4}"},
    {"name": "Passport Number", "pattern": "E\\d{8}"}
  ]
}
```

## Enable/Disable Entity Detection

Modify the `enabled` field in `keywords.json`:

```json
{
  "entities": {
    "phone": {"enabled": true},
    "email": {"enabled": true},
    "idcard": {"enabled": true},
    "bankcard": {"enabled": true},
    "ip": {"enabled": false}
  }
}
```

## Next Steps

- [Architecture](/en/docs/architecture) — Data flow and module design
- [Deployment Guide](/en/docs/deploy) — Production deployment options
- [API Reference](/en/docs/api) — Admin API and stats endpoints
