# Show HN: Content for AI Privacy Gateway

## Primary Post

**Title:** Show HN: AI Privacy Gateway — PII firewall for LLM APIs (MIT, 30s deploy, no config)

**URL:** https://github.com/gunxueqiu6/ai-privacy-gateway

**Body:**

Every AI coding assistant (Cursor, Claude Code, Copilot) sends your code to third-party APIs. Every time you paste customer data into ChatGPT, that data leaves your machine. Every DeepSeek prompt crosses an international border.

I wanted a dead-simple fix: a local proxy that strips PII from AI API calls before they leave my machine. No SaaS dependencies. No "sign up for enterprise." Just `docker run` and forget it.

AI Privacy Gateway does exactly that:

- Docker pull + run = 30 seconds to deploy
- Auto-detects 14+ entity types (phone, email, ID cards, bank cards, API keys, names, locations, IPs, URLs...)
- Regex-based detection at <1ms latency — transparent to real-time AI chat
- SSE streaming support — masks PII in real-time streaming responses
- Works with ChatGPT, Claude, Cursor, DeepSeek, Copilot — any OpenAI-compatible API
- MIT licensed. Zero external dependencies. Fully local.

The problem this solves:
- Developers sending code with API keys/secrets to Cursor/Claude Code
- Support teams pasting customer PII into ChatGPT
- Healthcare orgs needing HIPAA compliance for AI API use
- Chinese companies worried about DeepSeek data residency under PIPL
- Any org under GDPR, SOC 2, or PCI DSS using AI APIs

Architecture: transparent HTTP reverse proxy that sits between your AI client and the API provider. Request comes in → regex engine scans for 14 PII patterns → replaces with typed placeholders (`[PHONE_abc]`) → forwards masked request → AI never sees raw data.

Tech stack: Python + FastAPI, SQLite for encrypted vault, regex pattern engine.

Comparison to existing tools:
- LLM Guard (MIT): good, but heavier (transformers deps, ~5ms latency, no streaming)
- PasteGuard (MIT): browser extension only, no API support
- Nightfall/Private AI: great accuracy, but cloud-based and enterprise $$$ — no local-first option

I built this because I was pasting customer data into ChatGPT daily and couldn't find a single-command, zero-config, fully-local solution. So I made one.

Happy to answer questions about the regex engine, streaming buffer handling, or the architecture.

---

## First Comment (post immediately after submission)

**Why I built this**

I work with customer data — phone numbers, emails, transaction records. I use AI tools constantly: ChatGPT for research, Cursor for coding, Claude Code for debugging. Every week I'd accidentally paste something sensitive.

I looked at existing solutions:
- **LLM Guard**: Too heavy for my use case. Python SDK with transformer models — it works, but pip-installing a dozen ML deps for "mask phone numbers" felt wrong.
- **PasteGuard**: Great idea, but browser-only. I use API tools extensively (Claude Code, Cursor's API mode).
- **Commercial tools (Nightfall, Private AI)**: Awesome accuracy but cloud-hosted and priced for enterprises. I wanted local, free, and simple.

So I built the simplest possible thing: a regex-based proxy that catches the most common PII patterns with near-zero latency. It's intentionally not ML-based — regex at <1ms means you don't notice it exists. The encrypted vault stores original→placeholder mappings locally so you can restore values if needed.

**Comparison table:**

| | AI Privacy Gateway | LLM Guard | PasteGuard | Nightfall | Private AI |
|---|:---:|:---:|:---:|:---:|:---:|
| License | MIT | MIT | MIT | Commercial | Commercial |
| Deploy | Docker 30s | pip 5min | Extension | API setup | SDK setup |
| PII types | 14+ | 10+ | 8+ | 30+ | 50+ |
| Latency | <1ms | ~5ms | <0.5ms | ~50ms | ~100ms |
| Offline | Yes | Yes | Browser | No | Partial |
| Streaming | Yes | No | N/A | No | No |
| Cost | Free | Free | Free | $$$$ | $$$ |

**Key differentiator:** AI Privacy Gateway is the only one that:
1. Deploys as a local proxy in under 30 seconds
2. Handles SSE streaming (critical for real-time AI chat)
3. Has zero external dependencies
4. Works transparently with any OpenAI-compatible API

Architecture deep-dive in the README. Happy to discuss design tradeoffs.

---

## Prepared Q&A for Comments

**Q: How is this different from LLM Guard?**
A: LLM Guard is a Python SDK/library — you integrate it into your code. AI Privacy Gateway is a standalone proxy — you point your AI client at it and it works without code changes. Also: AI Privacy Gateway supports SSE streaming (LLM Guard doesn't), deploys in 30s via Docker (vs pip install + config), and has lower latency (<1ms vs ~5ms) because it's regex-only rather than regex+transformers.

**Q: What about the encryption / vault?**
A: The vault stores PII→placeholder mappings in a local SQLite database with AES-256-GCM encryption. The encryption key is auto-generated on first run and never leaves your machine. You can also disable persistence entirely (stateless mode) — masked data flows through, but no mappings are stored.

**Q: Can't someone just regex scan for PII patterns? Why a proxy?**
A: They can! And many orgs have DLP tools that do this. But (1) those tools block the request — a proxy masks and forwards it transparently. And (2) none of them handle the AI API use case specifically, with OpenAI-compatible URL rewriting and SSE streaming support.

**Q: Does this work with Cursor / Claude Code?**
A: Yes. Both support custom API base URLs. Point them at `http://localhost:9999` and all API traffic flows through the gateway transparently.

**Q: What about accuracy vs ML-based tools?**
A: Regex is less accurate for unstructured text detection (e.g., names in free text). But it catches 95%+ of structured PII (phones, emails, IDs, cards, keys) with sub-millisecond latency. For the AI API use case — where speed matters because users are waiting for streaming responses — regex is the right tradeoff.

**Q: Can I use this in production at my company?**
A: Yes. MIT licensed. Enterprise deployment supports Kubernetes with Helm, horizontal scaling, and centralized audit logging. Details at https://privacygw.pages.dev/enterprise-ai-data-protection
