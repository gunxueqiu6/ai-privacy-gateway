---
layout: ../../layouts/DocsLayout.astro
title: 部署指南
description: 生产环境部署 AI Privacy Gateway — Docker Compose、裸机部署、systemd 服务、Nginx 反向代理。
canonicalURL: https://privacygw.pages.dev/docs/deploy
---

# 部署指南

生产环境部署方案。

## Docker Compose（推荐）

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

启动：

```bash
docker-compose up -d
```

## 裸机部署（systemd）

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

## Nginx 反向代理

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

## 下一步

- [配置环境变量](/docs/config)
- [自定义敏感词](/docs/keywords)
- [架构说明](/docs/architecture)
