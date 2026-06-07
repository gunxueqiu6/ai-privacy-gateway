---
layout: ../../layouts/DocsLayout.astro
title: 配置参考
---

# 配置参考

完整环境变量说明。

## 必需变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `VERSION` | 版本类型 | `lite` / `pro` / `enterprise` |
| `UPSTREAM_URL` | 上游 AI API | `https://api.deepseek.com` |

## 可选变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `9999` | 监听端口 |
| `HOST` | `0.0.0.0` | 监听地址 |
| `DB_PATH` | `./vault_data/vault.db` | 数据库路径 |
| `LOG_LEVEL` | `info` | 日志级别 |
| `MAX_BODY_SIZE` | `10485760` | 最大请求体 (10MB) |
| `LICENSE_KEY` | 无 | Pro/Enterprise 激活码 |

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

## License 激活

```bash
curl -X POST http://localhost:9999/admin/license \
  -H "Content-Type: application/json" \
  -d '{"key": "APG-XXXX-XXXX-XXXX"}'
```
