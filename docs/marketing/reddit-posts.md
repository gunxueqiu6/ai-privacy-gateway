# Reddit Posts — AI Privacy Gateway

## Posting Strategy

- **r/selfhosted** and **r/privacy**: weekend posts (best engagement)
- **r/programming**: Tuesday-Thursday morning EST
- Don't copy-paste across subreddits — unique angles only
- Answer questions in comments within 1-2 hours
- Don't mention competitors unless asked

---

## r/selfhosted — "I built a self-hosted PII firewall for AI APIs"

**Title:** I built a self-hosted PII firewall for AI APIs — 30s Docker deploy, MIT license

**Body:**

I was pasting customer data into ChatGPT daily. Names, phone numbers, emails — all going straight to OpenAI's servers. I looked for a self-hosted fix. Everything I found was either:
- A SaaS product with per-seat pricing
- A Python library that needed code changes
- A browser extension that only works on chat.openai.com

So I built one. A dead-simple proxy that strips PII from AI API traffic before it leaves your network:

- Docker pull + run. Done. 30 seconds.
- Auto-detects phones, emails, ID cards, bank cards, API keys, names, locations — 14+ types
- <1ms latency — you don't notice it's there
- Works with ChatGPT, Claude, Cursor, DeepSeek, Copilot — any OpenAI-compatible API
- MIT license. Zero external dependencies.
- SSE streaming supported (live chat message masking)
- Encrypted local vault if you need PII restoration

GitHub: https://github.com/gunxueqiu6/ai-privacy-gateway
Demo: https://privacygw.pages.dev/demo

This sits on my home server. All my AI tools point at it. I haven't leaked a phone number to an AI API in months.

Curious what r/selfhosted thinks — overkill for a home setup? Would you run this?

**Post timing:** Saturday or Sunday morning (US time)

---

## r/ChatGPT — "How to stop ChatGPT from seeing your personal data"

**Title:** PSA: You're probably sending PII to ChatGPT right now — here's how to stop it

**Body:**

Every time you paste customer data, debug logs, or support tickets into ChatGPT, that data goes to OpenAI's servers. Their privacy policy says they may use it for training (unless you opt out). And if your company handles healthcare, financial, or customer data, this could be a compliance violation.

The fix: a local proxy that masks PII in your prompts before they reach OpenAI.

1. Run: `docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite`
2. Set your ChatGPT API client's base URL to `http://localhost:9999`
3. Done. All PII (phones, emails, IDs, names) auto-masked before it leaves your machine.

Open source (MIT), free, 30 second setup.

What gets masked:
- Phone numbers, emails, names
- ID cards, bank cards
- Physical addresses, IPs
- API keys and credentials
- And 8+ more types

The AI doesn't need your customer's real phone number — it just needs to know there IS a phone number.

Project: https://github.com/gunxueqiu6/ai-privacy-gateway
Online demo (runs in your browser, no upload): https://privacygw.pages.dev/demo

If you're using ChatGPT for work, you really should be running something like this.

**Post timing:** Weekday morning EST

---

## r/ClaudeAI — "Protect sensitive code when using Claude Code"

**Title:** Claude Code sends your code to Anthropic — here's how to mask API keys first

**Body:**

Claude Code (the CLI tool) sends your code to Anthropic's API for processing. If your codebase contains:
- API keys in config files
- Database connection strings
- Customer data in test fixtures
- Hardcoded secrets you forgot about

...those all go to Anthropic's servers.

The fix: point Claude Code through a local PII proxy.

```bash
# Start the proxy
docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite

# Configure Claude Code to use it
# Settings → API Base URL → http://localhost:9999
```

The proxy auto-detects and masks:
- API keys (OpenAI, GitHub, AWS, 20+ formats)
- Database connection strings (postgres://, mysql://, mongodb://)
- JWT tokens, passwords, private keys
- And other PII (phones, emails, etc.)

Everything gets masked with typed placeholders before it reaches Anthropic.

MIT licensed, open source, zero external dependencies: https://github.com/gunxueqiu6/ai-privacy-gateway

This is especially important if you work in fintech, healthcare, or any regulated industry where source code exposure is a compliance issue.

**Post timing:** Weekday (avoid weekends — dev tools subreddit)

---

## r/programming — Technical deep-dive

**Title:** How to intercept and mask PII in AI API calls at wire speed (<1ms)

**Body:**

I built an open-source proxy that intercepts AI API traffic and masks PII in transit. The core challenge: do it fast enough that users don't notice the latency hit. Here's how it works under the hood:

**The challenge:**

AI chat apps stream responses (SSE — Server-Sent Events). If masking adds 50ms, users feel the lag. The proxy has to:
1. Receive the complete prompt
2. Scan for PII patterns
3. Replace PII with placeholders
4. Forward to the AI API
— all before the user notices any delay

For streaming responses, it's even trickier — content arrives in chunks of 5-50 bytes. You can't buffer the whole response (that defeats streaming). So the proxy does chunk-by-chunk matching with a sliding window buffer.

**Architecture:**

```
Client → Proxy (:9999) → AI API
            ↓
    [Regex Engine] → [Vault (SQLite)]
```

- **Regex engine**: 14 pre-compiled regex patterns, matched in a single pass with a compiled regex union
- **Stream buffer**: Sliding window handles SSE chunks — buffered to the nearest token boundary, processes, then flushes immediately
- **Vault**: AES-256-GCM encrypted SQLite stores original→placeholder mappings. Optional — can run fully stateless
- **Latency**: <1ms average because regex compilation happens at startup, and the scan is O(n) single-pass

**Why regex, not ML/NER?**

ML-based NER (spaCy, transformers) gets better accuracy on unstructured text like names and locations. But:
- Transformers add 50-100ms latency — noticeable in streaming chat
- They require heavy dependencies (500MB+ models)
- For structured PII (phones, emails, IDs, keys), regex accuracy is 95%+ already

The tradeoff: speed for accuracy on unstructured entities. For AI API use, speed wins.

**Streaming (SSE) handling — the tricky part:**

SSE data comes in `data: {"choices":[{"delta":{"content":"hel"}}]}\n\n` chunks. The proxy:
1. Buffers each chunk into a sliding window
2. Checks if the window ends mid-token
3. If yes: hold the incomplete token, flush the rest
4. If no: apply regex, flush immediately

This keeps masking latency to <1ms per chunk while preserving the streaming UX.

GitHub: https://github.com/gunxueqiu6/ai-privacy-gateway (MIT)

**Post timing:** Tuesday-Thursday morning EST

---

## r/privacy — "Open-source tool to mask PII before it reaches AI"

**Title:** Stop sending your personal data to AI companies — open source, local, 30s setup

**Body:**

AI companies (OpenAI, Anthropic, DeepSeek) process billions of prompts daily. Every prompt you send is:
- Stored on their servers (retention varies by provider)
- Potentially reviewed by human annotators
- Possibly used for model training
- Subject to the data laws of the provider's jurisdiction (e.g., DeepSeek → Chinese PIPL)

The privacy-respecting solution: mask PII locally before it leaves your machine.

I built an open-source tool that does exactly this: https://github.com/gunxueqiu6/ai-privacy-gateway

- **Zero data leaves your machine unmasked** — PII replaced with `[PHONE_1]`, `[EMAIL_1]`
- **Runs locally** — Docker, pip, or standalone binary
- **30 second setup** — `docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite`
- **MIT license** — no corporate interests, no "free tier with limits"
- **No telemetry** — doesn't phone home, doesn't track, doesn't even download deps at runtime

Works with ChatGPT, Claude, Cursor, DeepSeek, Copilot, and any OpenAI-compatible API.

Demo (runs entirely in your browser, no data uploaded): https://privacygw.pages.dev/demo

**Post timing:** Weekend morning

---

## r/devops — "Add AI data protection to your infra in 30s"

**Title:** How to add AI data protection to your infrastructure in 30 seconds

**Body:**

If your team uses AI tools (and they do), here's a 30-second way to add PII masking to all outbound AI API traffic:

```bash
docker run -d \
  --name ai-privacy-gw \
  -p 9999:9999 \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

Then configure your team's AI tools to use `http://<your-server>:9999` as the API endpoint.

What you get:
- All PII (phones, emails, IDs, credit cards, API keys) auto-masked
- Kubernetes sidecar pattern supported
- Prometheus metrics for monitoring
- Audit logging (JSON + syslog)
- SOC 2 / HIPAA / GDPR compliance evidence
- <1ms latency — no performance impact
- 10K+ requests/second per instance

For K8s deployments:

```yaml
apiVersion: v1
kind: Pod
spec:
  containers:
    - name: app
      image: my-app
      env:
        - name: OPENAI_BASE_URL
          value: http://localhost:9999/v1
    - name: privacy-proxy
      image: ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
      ports:
        - containerPort: 9999
```

Helm chart available. Stateless design = horizontal scaling behind any load balancer.

Open source (MIT), no external dependencies, runs fully on-premise.

GitHub: https://github.com/gunxueqiu6/ai-privacy-gateway
Docs: https://privacygw.pages.dev/docs

**Post timing:** Weekday morning EST
