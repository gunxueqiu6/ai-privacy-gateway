---
layout: ../../../layouts/DocsLayout.astro
title: API Reference
description: AI Privacy Gateway admin API reference — health check, stats, version info, keyword management, mask/restore endpoints, error codes.
canonicalURL: https://privacygw.pages.dev/en/docs/api
---

# API Reference

Admin endpoints, stats queries, keyword management, and mask/restore API.

## Health Check

```bash
GET /health
```

```json
{"status": "healthy"}
```

## Statistics

### Basic Stats

```bash
GET /admin/stats
```

```json
{
  "today": {
    "requests": 1523,
    "masked": 487,
    "fields_masked": {
      "phone": 312,
      "email": 98,
      "id_card": 45,
      "bank_card": 32
    }
  },
  "total": {
    "requests": 28491,
    "masked": 9120
  }
}
```

## Version Info

```bash
GET /admin/version
```

```json
{
  "version": "2.0.0",
  "edition": "lite",
  "features": {
    "ac_automaton": false,
    "sso": false,
    "rbac": false,
    "audit_hash_chain": false,
    "alerts": false,
    "redis_cache": false
  }
}
```

## Keyword Management

```bash
# List all keywords
GET /admin/keywords

# Add a keyword
POST /admin/keywords
Content-Type: application/json

{"word": "Secret Project X", "replacement": "PROJECT_X"}

# Delete a keyword
DELETE /admin/keywords/{id}
```

## Mask / Restore API

```bash
# Mask PII in text (standalone, no upstream call)
POST /api/mask
Content-Type: application/json

{"text": "My phone is 13812345678 and email is user@example.com"}

# Response
{
  "masked_text": "My phone is [PHONE_1] and email is [EMAIL_1]",
  "mappings": {
    "[PHONE_1]": "13812345678",
    "[EMAIL_1]": "user@example.com"
  }
}

# Restore original values
POST /api/restore
Content-Type: application/json

{"text": "Contact [PHONE_1] or [EMAIL_1]", "mappings": {...}}

# Batch mask
POST /api/mask/batch
Content-Type: application/json

{"texts": ["text1", "text2", "text3"]}

# List supported entity types
GET /api/entities
```

## Error Codes

| Status | Description |
|--------|-------------|
| 200 | Success |
| 400 | Invalid request parameters |
| 401 | Unauthorized — check admin password |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Next Steps

- [Quick Start](/en/docs/quickstart) — Deploy in 5 minutes
- [Custom Keywords](/en/docs/keywords) — Add team-specific rules
- [Configuration Reference](/en/docs/config) — All environment variables
