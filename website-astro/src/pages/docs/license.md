---
layout: ../../layouts/DocsLayout.astro
title: 许可证管理
description: 如何激活和管理 AI Privacy Gateway Pro/Enterprise 许可证
canonicalURL: https://privacygw.pages.dev/docs/license
---

# 许可证管理

Pro/Enterprise 版本需激活许可证后方可使用高级功能。

## 版本对比

| 功能 | Lite | Pro | Enterprise |
|------|------|-----|------------|
| 基础脱敏 | 支持 | 支持 | 支持 |
| 自定义敏感词 | 支持 | 支持 | 支持 |
| 管理后台 | 支持 | 支持 | 支持 |
| Rust 完整性校验 | 不支持 | 支持 | 支持 |
| AC 自动机加速 | 不支持 | 支持 | 支持 |
| 加密存储 | 不支持 | 支持 | 支持 |
| Redis 缓存 | 不支持 | 不支持 | 支持 |
| RBAC 权限控制 | 不支持 | 不支持 | 支持 |
| 告警引擎 | 不支持 | 不支持 | 支持 |
| 高级报表 | 不支持 | 不支持 | 支持 |
| 团队管理 | 不支持 | 支持 | 支持 |
| 最大团队席位 | 不支持 | 20 | 100+ |

## 激活方式

### 环境变量（推荐）

```bash
# 设置许可证密钥
export LICENSE_KEY="pro_xxxxx_yyyyy_zzzzz"

# 或指定许可证文件路径
export LICENSE_FILE="/etc/privacy-gw/license.jwt"
```

### 管理后台激活

```bash
POST /admin/license/activate
Content-Type: application/json

{
  "key": "pro_xxxxx_yyyyy_zzzzz"
}
```

成功响应：

```json
{
  "success": true,
  "license": {
    "tier": "pro",
    "expires_at": "2027-06-14T00:00:00Z",
    "seats": 20
  }
}
```

## 许可证格式

许可证文件为 JWT 格式，包含以下声明：

```json
{
  "sub": "org_abc123",
  "tier": "enterprise",
  "seats": 100,
  "iat": 1747267200,
  "exp": 1778803200,
  "iss": "privacygw"
}
```

## 许可证管理

### 查看状态

```bash
GET /admin/license/check
```

```json
{
  "active": true,
  "tier": "pro",
  "expires_at": "2027-06-14T00:00:00Z",
  "days_remaining": 365,
  "features": [
    "rust_integrity",
    "ac_automaton",
    "encrypted_vault",
    "team_management"
  ]
}
```

### 刷新许可证

许可证即将过期时，可通过新密钥续期：

```bash
POST /admin/license/refresh
Content-Type: application/json

{
  "key": "pro_newkey_xxxxx"
}
```

## 排查指南

### 许可证过期

```
Error: License expired
```

重新购买并激活新许可证。过期后高级功能降级至 Lite，基础脱敏不受影响。

### 无效签名

```
Error: Invalid license signature
```

原因：许可证被篡改或来源不可信。请从官方渠道重新下载。

### 密钥已被吊销

```
Error: License revoked
```

联系支持团队了解原因。常见原因：违规使用、到期未续费。

### 席位超限

```
Error: Seat limit exceeded
```
当前成员数已超过许可证允许的最大席位。升级许可证或移除闲置成员。

## 离线激活

内网环境可离线激活：

1. 下载许可证文件至本地
2. 放置于 `vault_data/license.jwt`
3. 设置 `LICENSE_FILE` 环境变量指向该文件
4. 重启网关

```bash
cp license.jwt /opt/ai-privacy-gateway/vault_data/license.jwt
export LICENSE_FILE="/opt/ai-privacy-gateway/vault_data/license.jwt"
```

## 下一步

- [团队管理](/docs/team)
- [Enterprise 功能](/docs/enterprise)
- [部署指南](/docs/deploy)
