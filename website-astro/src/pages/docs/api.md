---
layout: ../../layouts/DocsLayout.astro
title: API 参考
---

# API 参考

管理接口、统计查询、License 验证。

## 健康检查

```bash
GET /health
```

```json
{"status": "healthy"}
```

## 统计

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

## 版本信息

```bash
GET /admin/version
```

```json
{
  "version": "1.0.0",
  "edition": "lite",
  "rust_integrity": false
}
```

## 完整性检查 (Pro+)

```bash
GET /admin/integrity
```

```json
{
  "ok": true,
  "checksum": "sha256:abc123...",
  "records": 487
}
```

## License 管理

```bash
POST /admin/license
Content-Type: application/json

{"key": "APG-XXXX-XXXX-XXXX"}
```

```json
{
  "activated": true,
  "edition": "pro",
  "expires_at": "2027-06-06",
  "seats": 20
}
```

## 敏感词管理

```bash
# 列出所有敏感词
GET /admin/keywords

# 添加敏感词
POST /admin/keywords
Content-Type: application/json

{"word": "机密项目X", "replacement": "PROJECT_X"}

# 删除敏感词
DELETE /admin/keywords/{id}
```

## 错误码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | License 无效或过期 |
| 429 | 请求频率超限 |
| 500 | 内部错误 |
