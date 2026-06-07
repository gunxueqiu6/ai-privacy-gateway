---
layout: ../../layouts/DocsLayout.astro
title: 自定义敏感词
description: 自定义敏感词配置 — 添加团队专属敏感词、正则模式、批量导入、管理后台操作指南。
canonicalURL: https://privacygw.pages.dev/docs/keywords
---

# 自定义敏感词

添加团队专属敏感词和正则模式。

## 关键词替换

在 `vault_data/keywords.txt` 中添加，格式：`原始词:替换标签`

```text
# 公司内部敏感词
上海研发中心:LOCATION_RD
竞品X公司:COMPETITOR_A
核心客户A:VIP_CLIENT

# 内部项目代号
凤凰项目:PROJECT_PHOENIX
```

重启网关生效。

## 正则模式

在 `vault_data/patterns.json` 中添加自定义正则：

```json
{
  "custom": [
    {
      "name": "员工工号",
      "pattern": "EMP\\d{6}",
      "replacement": "[VAULT_EMP_ID_{id}]"
    },
    {
      "name": "IP 地址",
      "pattern": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
      "replacement": "[VAULT_IP_{id}]"
    },
    {
      "name": "车牌号",
      "pattern": "[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]",
      "replacement": "[VAULT_PLATE_{id}]"
    }
  ]
}
```

## 管理后台操作

1. 访问 `http://localhost:9999/admin`
2. 进入「敏感词管理」
3. 添加/删除/测试关键词
4. 实时生效，无需重启

## 测试敏感词

```bash
curl -X POST http://localhost:9999/admin/keywords/test \
  -H "Content-Type: application/json" \
  -d '{"text": "请联系凤凰项目负责人张三"}'
```

返回：

```json
{
  "matched": ["凤凰项目"],
  "sanitized": "请联系[VAULT_PROJECT_PHOENIX]负责人张三"
}
```
