---
layout: ../../layouts/DocsLayout.astro
title: 快速开始
description: 5 分钟部署 AI Privacy Gateway — Docker、Windows、macOS 一键启动，保护发往 AI 的敏感数据。
canonicalURL: https://privacygw.pages.dev/docs/quickstart
---

# 快速开始

5 分钟部署 AI Privacy Gateway。

## Docker 部署（推荐）

```bash
docker run -d \
  --name ai-privacy-gw \
  -p 9999:9999 \
  -v ./vault_data:/app/vault_data \
  -e VERSION=lite \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

验证：

```bash
curl http://localhost:9999/health
# {"status":"healthy"}
```

## Windows 部署

1. 下载 [PrivacyGateway.exe](https://github.com/gunxueqiu6/ai-privacy-gateway/releases/latest)
2. 双击运行
3. 访问 `http://localhost:9999/health`

## 配置 AI 客户端

将你的 AI 客户端 API 地址改为 `http://localhost:9999`：

### Cursor

设置 → API Key → Base URL 改为 `http://localhost:9999`

### 代码调用

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9999/v1",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "我的手机是13812345678"}]
)
# 网关自动将 13812345678 替换为 [VAULT_PHONE_xxx]
# AI 收到的内容:"我的手机是[VAULT_PHONE_xxx]"
# AI 返回后网关自动还原
```

## 下一步

- [自定义敏感词](/docs/keywords)
- [部署配置](/docs/deploy)
- [环境变量参考](/docs/config)
