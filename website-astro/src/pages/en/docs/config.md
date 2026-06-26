---
layout: ../../../layouts/DocsLayout.astro
title: Configuration
description: AI Privacy Gateway complete configuration reference — environment variables, masking rules, custom keyword configuration.
canonicalURL: https://privacygw.pages.dev/en/docs/config
---

# Configuration

Complete environment variable reference.

## Basic Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TARGET_LLM` | https://api.openai.com | Target AI API URL |
| `LISTEN_PORT` | `9999` | Listen port |
| `DB_PATH` | `./vault_data/privacy_vault.db` | SQLite database path |
| `ADMIN_PASSWORD` | `admin123` | Admin panel password |

## Masking Rule Configuration

Keyword rule file: `vault_data/keywords.txt`

```text
# Custom keywords (one per line)
InternalProject:PROJECT_NAME
ClientA:CLIENT_ALPHA
```

Regex rule file: `vault_data/patterns.json`

```json
{
  "custom": [
    {"name": "Employee ID", "pattern": "EMP\\d{6}"},
    {"name": "Project Code", "pattern": "PRJ-[A-Z]{3}-\\d{4}"}
  ]
}
```
