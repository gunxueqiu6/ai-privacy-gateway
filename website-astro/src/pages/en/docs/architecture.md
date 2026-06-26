---
layout: ../../../layouts/DocsLayout.astro
title: Architecture
description: AI Privacy Gateway architecture — data flow design, SSE streaming, request/response masking and restoration pipeline.
canonicalURL: https://privacygw.pages.dev/en/docs/architecture
---

# Architecture

How AI Privacy Gateway works.

## Data Flow

```text
User Request
    │
    ▼
┌─────────────────────────────────┐
│  AI Privacy Gateway (:9999)     │
│                                 │
│  ┌───────────┐  ┌────────────┐ │
│  │ Detection │──│ Vault DB   │ │
│  │ Engine    │  │  SQLite    │ │
│  └─────┬─────┘  └────────────┘ │
│        │                        │
│  ┌─────▼─────┐                  │
│  │  Proxy    │                  │
│  │  HTTP/SSE │                  │
│  └─────┬─────┘                  │
└────────┼────────────────────────┘
         │
         ▼
    ┌─────────┐
    │ AI API  │  (DeepSeek/Claude/ChatGPT)
    └─────────┘
```

## Request Processing

```
1. Receive request → extract messages.content
2. Detect sensitive info → regex + AC automaton (Rust PyO3)
3. Create placeholders → write to vault DB
4. Forward masked request → upstream AI API
5. Receive response → restore placeholders
6. Return original response → user is unaware
```

## SSE Streaming

Special handling for stream mode:

- SSE events accumulate in buffer
- Detection triggers when a complete semantic unit is reached
- Restore placeholders chunk by chunk
- < 50ms latency (imperceptible to user)

## Detection Engine

The gateway uses Python-based regex + NER dual-engine for sensitive data detection:

- Regex engine: phone numbers, ID cards, emails, bank cards and other structured data
- NER engine: jieba segmentation + ONNX model inference for Chinese person names, locations, organizations
- All detection is local — data never leaves the gateway

## Data Security

- Vault is local SQLite only (`vault_data/vault.db`)
- One-click physical destruction: `rm -rf vault_data/`
- No data uploaded to any cloud
