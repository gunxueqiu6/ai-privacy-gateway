---
layout: ../../layouts/DocsLayout.astro
title: 架构说明
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
2. 敏感信息检测 → 正则 + AC 自动机
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

## Rust 完整性检查

Pro/Enterprise 版本使用 PyO3 调用 Rust 模块：

```python
# Python 调用 Rust 编译的 .pyd/.so
from integrity_check import verify
assert verify(db_path)  # 验证映射表未被篡改
```

Rust 模块提供：
- 映射表完整性校验 (HMAC-SHA256)
- AC 自动机高速匹配
- 内存安全的敏感数据处理

## 数据安全

- 映射表仅存本地 SQLite（`vault_data/vault.db`）
- 支持加密存储（Pro+ 版本）
- 一键物理销毁：`rm -rf vault_data/`
- 不上传任何数据到云端
