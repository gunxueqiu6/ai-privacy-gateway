---
layout: ../../layouts/DocsLayout.astro
title: API 参考
description: AI Privacy Gateway 管理 API 参考 — 健康检查、统计查询、版本信息、敏感词管理接口。
canonicalURL: https://privacygw.pages.dev/docs/api
---

# API 参考

管理接口、统计查询、敏感词管理。

## 健康检查

```bash
GET /health
```

```json
{"status": "healthy"}
```

## 统计

### 基础统计

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
| 401 | 未授权访问 |
| 429 | 请求频率超限 |
| 500 | 内部错误 |
