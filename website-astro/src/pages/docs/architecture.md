---
layout: ../../layouts/DocsLayout.astro
title: 架构说明
description: AI Privacy Gateway 架构说明 — 数据流设计、SSE 流式处理、请求/响应脱敏还原链路。
canonicalURL: https://privacygw.pages.dev/docs/architecture
---

# 架构说明

AI Privacy Gateway 的工作原理。

## 数据流

```text
用户请求
    │
    ▼
┌─────────────────────────────────┐
│  AI Privacy Gateway (:9999)     │
│                                 │
│  ┌───────────┐  ┌────────────┐ │
│  │ 检测引擎  │──│ 映射表存储  │ │
│  │ Python/RS │  │   SQLite   │ │
│  └─────┬─────┘  └────────────┘ │
│        │                        │
│  ┌─────▼─────┐                  │
│  │ 代理转发  │                  │
│  │  HTTP/SSE │                  │
│  └─────┬─────┘                  │
└────────┼────────────────────────┘
         │
         ▼
    ┌─────────┐
    │ AI API  │  (DeepSeek/Claude/ChatGPT)
    └─────────┘
```

## 请求处理流程

```
1. 接收请求 → 提取 messages.content
2. 敏感信息检测 → 正则 + AC 自动机（Rust PyO3）
3. 创建占位符 → 写入映射表
4. 转发脱敏后请求 → 上游 AI API
5. 接收响应 → 还原占位符
6. 返回原始响应 → 用户无感知
```

## 流式处理 (SSE)

对 stream 模式的特殊处理：

- SSE 事件在缓冲区中累积
- 达到完整语义单元时触发检测
- 逐 chunk 还原占位符
- 延迟 < 50ms（用户无感知）

## 检测引擎

网关使用 Python 实现的正则 + NER 双引擎进行敏感数据检测：

- 正则引擎：覆盖手机号、身份证、邮箱、银行卡等结构化数据
- NER 引擎：基于 jieba 分词 + ONNX 模型推理识别中文人名、地名、机构名
- 所有检测在本地完成，数据不出网关

## 数据安全

- 映射表仅存本地 SQLite（`vault_data/vault.db`）
- 一键物理销毁：`rm -rf vault_data/`
- 不上传任何数据到云端
