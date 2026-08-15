---
layout: ../../layouts/DocsLayout.astro
title: 配置参考
description: AI Privacy Gateway 完整配置参考 — 环境变量、脱敏规则、自定义敏感词配置。
canonicalURL: https://privacygw.pages.dev/docs/config
---

# 配置参考

完整环境变量与配置文件参考。

## 核心环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TARGET_LLM` | `https://api.openai.com` | 目标 AI API 地址（OpenAI 兼容） |
| `LISTEN_PORT` | `9999` | Gateway 监听端口 |
| `UPSTREAM_API_KEY` | (空) | 上游 LLM API 密钥 |
| `ADMIN_PASSWORD` | (自动生成) | 管理后台登录密码 |
| `JWT_SECRET` | (自动生成) | JWT 签名密钥 |
| `VAULT_ENCRYPT_KEY` | (自动生成) | AES-256-GCM Vault 加密密钥 |

## 数据库配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DB_PATH` | `./vault_data/privacy_vault.db` | SQLite 数据库文件路径 |
| `DB_TYPE` | `sqlite` | 数据库类型（当前仅支持 sqlite） |
| `MAPPING_TTL` | `259200` (72h) | PII 映射保留时间（秒） |
| `STATELESS_MODE` | `0` | 设为 1 启用无状态模式（仅内存，不写磁盘） |
| `DRY_RUN_MODE` | `0` | 设为 1 启用干运行模式（仅检测，不脱敏） |

## 上游负载均衡

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `UPSTREAM_LLM_URLS` | (空) | 上游 API 地址列表，逗号分隔 |
| `UPSTREAM_LB_STRATEGY` | `round_robin` | 负载均衡策略：`round_robin` / `random` / `least_connections` |
| `UPSTREAM_HEALTH_CHECK_INTERVAL` | `30` | 健康检查间隔（秒） |
| `UPSTREAM_MODEL_MAP` | `{}` | JSON 格式的模型→上游路由映射 |

## 性能控制

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MAX_CONCURRENT_REQUESTS` | `50` | 最大并发请求数 |
| `MAX_REQUEST_BODY_SIZE` | `10485760` (10MB) | 最大请求体大小（字节） |
| `SHUTDOWN_TIMEOUT` | `30` | 优雅关闭超时（秒） |
| `RATE_LIMIT_STORAGE` | `memory://` | 限流存储后端 |

## 日志配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LOG_FORMAT` | `json` | 日志格式：`json` 或 `text` |
| `LOG_LEVEL` | `INFO` | 日志级别：DEBUG / INFO / WARNING / ERROR |

## TLS 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SSL_CERTFILE` | (空) | SSL 证书路径 |
| `SSL_KEYFILE` | (空) | SSL 私钥路径 |

## 脱敏规则配置

敏感词规则文件：`vault_data/keywords.txt`

```text
# 自定义敏感词（一行一个）
# 格式：敏感词:替换标签
公司内部项目:PROJECT_NAME
客户A:CLIENT_ALPHA
机密项目X:SECRET_PROJECT
```

正则规则文件：`vault_data/patterns.json`

```json
{
  "custom": [
    {"name": "员工工号", "pattern": "EMP\\d{6}"},
    {"name": "项目编号", "pattern": "PRJ-[A-Z]{3}-\\d{4}"},
    {"name": "护照号码", "pattern": "E\\d{8}"}
  ]
}
```

## 启用/禁用特定实体检测

通过修改 `entity_catalog.json` 中的 `enabled` 字段控制：

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

## 下一步

- [架构说明](/docs/architecture) — 了解数据流和模块设计
- [部署指南](/docs/deploy) — 生产环境部署方案
- [API 参考](/docs/api) — 管理 API 和统计接口

