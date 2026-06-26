---
layout: ../../../layouts/DocsLayout.astro
title: Deployment Guide
description: Production deployment of AI Privacy Gateway — Docker Compose, bare metal, systemd service, Nginx reverse proxy.
canonicalURL: https://privacygw.pages.dev/en/docs/deploy
---

# Deployment Guide

Production deployment options.

## Docker Compose (Recommended)

```yaml
version: "3.8"
services:
  gateway:
    image: ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
    ports:
      - "9999:9999"
    volumes:
      - ./vault_data:/app/vault_data
    environment:
      - TARGET_LLM=https://api.deepseek.com
    restart: unless-stopped
```

Start:

```bash
docker-compose up -d
```

## Bare Metal (systemd)

```ini
[Unit]
Description=AI Privacy Gateway
After=network.target

[Service]
Type=simple
User=nobody
WorkingDirectory=/opt/ai-privacy-gateway
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Nginx Reverse Proxy

```nginx
server {
    listen 443 ssl;
    server_name gateway.internal;

    location / {
        proxy_pass http://127.0.0.1:9999;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 300s;
    }
}
```

## Next Steps

- [Configure Environment Variables](/docs/config)
- [Custom Keywords](/docs/keywords)
- [Architecture Overview](/docs/architecture)
