---
layout: ../../../layouts/DocsLayout.astro
title: Quick Start
description: Deploy AI Privacy Gateway in 5 minutes — Docker, Windows, macOS one-click setup. Protect sensitive data sent to AI.
canonicalURL: https://privacygw.pages.dev/en/docs/quickstart
---

# Quick Start

Deploy AI Privacy Gateway in 5 minutes.

## Docker Deploy (Recommended)

```bash
docker run -d \
  --name ai-privacy-gw \
  -p 9999:9999 \
  -v ./vault_data:/app/vault_data \
  -e TARGET_LLM=https://api.openai.com \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

Or use Docker Compose:

```bash
docker-compose up -d
```

Verify:

```bash
curl http://localhost:9999/health
# {"status":"healthy"}
```

## Windows Deploy

1. Download [PrivacyGateway.exe](https://github.com/gunxueqiu6/ai-privacy-gateway/releases/latest)
2. Double-click to run
3. Visit `http://localhost:9999/health`

## Configure AI Client

Change your AI client's API URL to `http://localhost:9999`:

### Cursor

Settings → API Key → Change Base URL to `http://localhost:9999`

### Code Call

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9999/v1",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "My phone is 13812345678"}]
)
# Gateway automatically replaces 13812345678 with [VAULT_PHONE_xxx]
# AI receives: "My phone is [VAULT_PHONE_xxx]"
# Gateway restores the original value before returning the response
```

## Next Steps

- [Custom Keywords](/docs/keywords)
- [Deployment Guide](/docs/deploy)
- [Config Reference](/docs/config)
