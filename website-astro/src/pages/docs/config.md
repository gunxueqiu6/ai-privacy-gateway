---
layout: ../../layouts/DocsLayout.astro
title: 配置参考
description: AI Privacy Gateway 完整配置参考 — 环境变量、脱敏规则、自定义敏感词配置。
canonicalURL: https://privacygw.pages.dev/docs/config
---

# 配置参考

完整环境变量说明。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TARGET_LLM` | https://api.openai.com | 目标 AI API 地址 |
| `LISTEN_PORT` | `9999` | 监听端口 |
| `DB_PATH` | `./vault_data/privacy_vault.db` | SQLite 数据库路径 |
| `ADMIN_PASSWORD` | `admin123` | 管理后台密码 |

## 脱敏规则配置

敏感词规则文件：`vault_data/keywords.txt`

```text
# 自定义敏感词（一行一个）
公司内部项目:PROJECT_NAME
客户A:CLIENT_ALPHA
```

正则规则文件：`vault_data/patterns.json`

```json
{
  "custom": [
    {"name": "员工工号", "pattern": "EMP\\d{6}"},
    {"name": "项目编号", "pattern": "PRJ-[A-Z]{3}-\\d{4}"}
  ]
}
```
