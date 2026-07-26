# Reddit + Hacker News Launch Posts — AI Privacy Gateway

**Product**: https://privacygw.pages.dev
**GitHub**: github.com/gunxueqiu6/ai-privacy-gateway
**License**: MIT
**Stack**: Python/FastAPI, regex + NER hybrid engine, SSE streaming, AES-256-GCM vault, SQLite

---

## 5 Reddit Posts

### Post 1: r/selfhosted

**Best posting time**: Sunday 10:00 AM ET (peak selfhosted browsing)

**Title**: I built a self-hosted proxy that masks PII before it reaches ChatGPT — 30s deploy, 100% local

**Body**:

Been running this in production for a couple months now and thought the selfhosted crowd might find it useful.

The problem: my team uses Cursor and ChatGPT daily. Code gets sent to third-party APIs. Sometimes that code contains API keys, internal IPs, customer emails, database connection strings. It's a compliance time bomb.

The solution: a local HTTP proxy that sits between your AI tools and the LLM providers. It intercepts every request, detects 14+ PII types (phone, email, ID, bank card, API keys, IPs, names, locations), and replaces them with typed placeholders. The original data never leaves your network.

```
docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

Point your AI client to `http://localhost:9999/v1` — that's it. Works with ChatGPT, Claude, DeepSeek, Cursor, Copilot, anything speaking OpenAI-compatible API.

**What I like about this approach vs alternatives**:

1. Zero code changes. No SDK integration. Just change the base URL.
2. Streaming SSE works. Most privacy proxies buffer the entire response first — this one processes chunks in flight with minimal context tracking. No perceived latency.
3. Encrypted vault. Placeholder mappings stored locally in AES-256-GCM encrypted SQLite. Optional stateless mode if you don't need reversibility.
4. Admin dashboard at `http://localhost:9999` — real-time stats, custom entity rules, health checks.

The NER model (spaCy) adds about 2ms per request as a fallback for unstructured entities. If you only care about structured PII (which covers 95%+ of actual leaks), regex-only mode is <200 microseconds.

MIT licensed. No telemetry. No cloud dependency. No "upgrade to pro."

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Website: privacygw.pages.dev

Open to questions, PRs, and honest criticism.

---

### Post 2: r/opensource

**Best posting time**: Tuesday 12:00 PM ET

**Title**: AI Privacy Gateway — MIT-licensed local PII masking for any OpenAI-compatible API

**Body**：

I'm open sourcing a project I've been using internally for a few months. Short pitch: it's a transparent proxy that detects and masks PII in AI API traffic. The masking happens on your machine — the LLM provider never sees the raw data.

**Why I built it**:

I work in fintech. Our compliance team flagged that developers sending code to Cursor/ChatGPT could leak customer data. The enterprise solutions we evaluated (Nightfall, Private AI) were expensive and sent data to yet another third party. The open-source alternatives (Presidio, LLM Guard) either required hours of setup or didn't support streaming.

So I wrote something that hit the sweet spot:

**Architecture highlight**: Two-stage detection pipeline

```
Input → Regex Pattern Matcher (<200µs) → spaCy NER (~2ms) → Masker → Output
         ↑ 70% of entities caught here      ↑ only for fuzzy entities
```

Regex handles structured types (phones, emails, IDs, bank cards, API keys). NER only runs on text spans that regex didn't already match. This cuts total processing time by ~60% compared to running both on the full input.

**What's included**:

- 14+ entity types out of the box (Chinese + English)
- SSE streaming with per-chunk latency under 3ms
- Encrypted vault (AES-256-GCM) for reversible mapping
- Admin dashboard with real-time interception stats
- Multi-upstream load balancing (round-robin / random / least-connections)
- Docker one-liner, pip, or standalone binary
- Audit event bus (pub/sub) for enterprise integration
- Browser extension SDK (Chrome/Edge)
- K8s sidecar deployment support

**What's NOT included** (and why):

- No ML-based entity recognition at scale — transformer models add 50-100ms latency. For AI chat, that's noticeable. Regex + lightweight NER is the right tradeoff for this use case.
- No cloud dependency — the whole point is you run it yourself.
- No telemetry — zero data leaves your network except the masked API request.

**Stack**: Python/FastAPI, spaCy, SQLite, AES-256-GCM, SSE streaming

**License**: MIT — do whatever you want with it.

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Docs: privacygw.pages.dev

---

### Post 3: r/LocalLLaMA

**Best posting time**: Thursday 2:00 PM ET

**Title**: Tool to protect privacy when using cloud LLM APIs — masks PII locally before sending

**Body**：

I know the LocalLLaMA crowd runs models locally. But most of us still hit cloud APIs sometimes — coding assistants, long context windows, tasks where local models fall short.

Every time I paste code or data into a cloud API, I'm sending whatever's in that text. API keys. Internal IPs. Personal data. The problem is: I don't always know what's in the text I'm pasting.

I built a proxy that checks for you. It sits on localhost, intercepts your API calls, detects 14+ types of PII, and masks them before forwarding to the cloud.

```bash
docker pull ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
docker run -d -p 9999:9999 \
  -e TARGET_LLM=https://api.openai.com \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

Point Open WebUI, SillyTavern, or anything OpenAI-compatible to `http://localhost:9999/v1`.

**Key design decisions**:

1. **Proxy, not SDK** — because you can't add SDK middleware to Cursor, Open WebUI, or most third-party tools. Proxy works at the network level, zero integration needed.

2. **Hybrid regex + NER** — spaCy's sm models are ~15MB and run in ~2ms. That's the right tradeoff for real-time masking. If the model were 500MB (BERT), the latency would be 50-100ms and you'd feel it.

3. **Streaming-aware** — SSE chunks can split a phone number across packets. The proxy maintains a sliding window buffer that resolves entity boundaries across chunks. This was the hardest part to get right.

**When you don't need this**: If you're 100% local (Ollama, llama.cpp, no cloud APIs at all), you don't need masking — your data never leaves. This tool is for the hybrid setup: local for most tasks, cloud for the rest.

**When you do need it**: Cloud coding assistants, API-based LLM access, team environments where you can't control what others paste.

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Online demo (browser-local, nothing uploaded): privacygw.pages.dev/demo

---

### Post 4: r/programming

**Best posting time**: Monday 1:00 PM ET

**Title**: How I built a sub-2ms PII detection proxy with SSE streaming support

**Body**：

I wanted to share some technical decisions from building an AI privacy proxy — specifically around the performance engineering and streaming architecture. Maybe useful for anyone doing text processing middleware.

**The problem**: Detect and replace 14+ types of PII in LLM API calls with <5ms overhead, while supporting SSE streaming (where text arrives token-by-token).

**Design decision 1: Two-stage pipeline with span dedup**

The naive approach is to run regex AND NER on the full text. That wastes time because if regex already identified a span as a phone number, there's no reason to ask NER what it is.

Instead: scan with a pre-compiled union regex first, record matched spans, exclude those spans from NER processing, run NER on the remaining text. This cuts processing by ~60% on typical inputs.

```python
# Simplified: pre-compiled union pattern scans once
combined_pattern = re.compile(
    '|'.join(f'(?P<{name}>{pattern})' for name, pattern in PATTERNS.items())
)

def mask_text(text: str) -> str:
    already_masked = set()
    def replace(match):
        entity_type = match.lastgroup
        start, end = match.start(), match.end()
        already_masked.add((start, end))
        # ... generate placeholder
    text = combined_pattern.sub(replace, text)
    # NER only runs on non-masked spans
    text = ner_on_unmasked_spans(text, already_masked)
    return text
```

**Design decision 2: SSE streaming without buffering**

AI chat responses arrive as SSE chunks. Each chunk is typically a few tokens. If you buffer the entire response before processing, you negate the benefit of streaming — the user waits for the full response.

The solution: a per-connection streaming buffer that tracks context across chunks.

```python
class ChunkProcessor:
    def __init__(self):
        self.partial = ""
        self.mask_context = {}

    async def process(self, raw_chunk: bytes) -> bytes:
        # Extract delta content from SSE frame
        content = self._extract_delta(raw_chunk)
        if not content:
            return raw_chunk

        # Append to sliding window
        self.partial += content

        # Find safest cut point (sentence boundary, not mid-number)
        safe_cut = self._find_safe_boundary()
        if safe_cut <= 0:
            return b""  # Hold until we have a safe boundary

        # Process safe portion
        ready = self.partial[:safe_cut]
        self.partial = self.partial[safe_cut:]
        masked = mask_text(ready)

        return self._rebuild_sse(masked)
```

The `_find_safe_boundary` method is the critical piece. It searches backwards from `window_size` for punctuation, whitespace, or newline — any boundary that won't split a token. If the buffer contains a partial phone number like "13812", processing holds until the next chunk completes it.

**Design decision 3: Pre-compiled pattern union**

All 14+ regex patterns are compiled at startup into a single combined pattern with named groups. This means the entire scan is one pass over the text, not 14 passes. Regex compilation (which is expensive) happens once. Per-request scan is O(n) with a small constant.

**Performance results** (MacBook Pro M1, 16GB):

```
Regex-only mode:      0.18ms / KB
Regex + NER mode:     2.30ms / KB
Streaming overhead:   0.05ms / chunk
Memory baseline:      180MB
Memory @ 100 concurrent: 420MB
Memory @ 1000 concurrent: 1.8GB
```

The 0.18ms/KB for regex means even a 10KB prompt adds under 2ms overhead. Below human perception.

**What I'd do differently**: The vault encryption (AES-256-GCM) adds noticeable overhead when you enable persistent mapping storage. In stateless mode, we skip the vault entirely and use one-way hashed placeholders — much faster, but you can't reverse them. Should have made stateless the default from the start.

Full source: github.com/gunxueqiu6/ai-privacy-gateway
Benchmark methodology in the repo's tests/ directory.

---

### Post 5: r/SideProject

**Best posting time**: Saturday 9:00 AM ET

**Title**: My side project: A privacy-first proxy for AI APIs — built solo, MIT open source

**Body**：

Started this on a weekend, ended up shipping it for real.

**Backstory**: I work at a company where everyone uses AI coding tools. Compliance came to me and said "we need to make sure nobody pastes customer data into ChatGPT." I said "okay, let me find a tool." Looked around. Enterprise tools wanted $15k/year. Open source alternatives had hours of setup and didn't support streaming.

So I built one.

**Week 1**: A janky Python script that regex-replaces phone numbers and emails. Hardcoded paths. No config. Worked for exactly one use case: me.

**Week 2-3**: Realized I needed a proper proxy. Added FastAPI, proper routing, SSE streaming support. The streaming part was brutal — phone numbers split across chunks, JSON parsing edge cases, connection handling.

**Week 4**: Added the NER layer for Chinese names and locations. spaCy models are surprisingly light (15MB) and fast (2ms). Worth the tradeoff.

**Month 2**: Dogfooding with my team. Found the real edge cases:
- Prompts with no PII at all (most common case — need to route through with zero added latency)
- Binary content in streaming responses
- Custom entity types that different teams needed
- Load testing under concurrent usage

**Month 3**: Docker image, documentation, admin dashboard, website. Open sourced it.

**Where it stands now**:

```
GitHub: github.com/gunxueqiu6/ai-privacy-gateway
License: MIT
Stars: ★ growing
Users: a few teams I don't know (they found it, I didn't promote)
Revenue: $0 (not the goal)
```

**The stack**:
- Python/FastAPI for the proxy layer (~2500 lines of Python)
- spaCy for NER (Chinese + English)
- SQLite + AES-256-GCM for the encrypted vault
- Preact + Chart.js for the admin dashboard
- Docker multi-stage builds (image is ~400MB)

**Hardest technical problem**: SSE streaming buffer. An 11-digit Chinese phone number `13812345678` can arrive across 5-8 separate SSE chunks. If you cut at the wrong boundary, you break the number and neither half matches the regex. The solution was a sliding window with sentence-boundary detection — took three rewrites to get right.

**What I'd tell past me**: Don't overthink the architecture. A simple regex engine + fastapi router + streaming buffer covers 90% of the value. Everything else (NER, vault, admin dashboard) is polish. Ship the ugly version first.

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Demo (browser-local): privacygw.pages.dev/demo

---

## Hacker News Show HN

### 3 Candidate Titles

1. **Show HN: AI Privacy Gateway — open-source proxy that masks PII before it reaches LLM APIs**
   (Best balance. Clear function + value prop. No hype.)

2. **Show HN: Privacy Gateway — I built a <2ms PII masking proxy for any LLM API**
   (Performance angle. HN loves latency numbers.)

3. **Show HN: AI Privacy Gateway — 30-second deploy, masks 14+ PII types, runs entirely local**
   (Deployment speed hook. Appeals to the "try it now" impulse.)

**Recommended**: #1. It's clear, honest, and tells you exactly what it is.

---

### Full Post Body

I built an open-source local proxy that auto-detects and masks PII before it reaches any LLM API. It runs entirely on your machine — the provider never sees the raw sensitive data.

**How it works**:
- Sits as a reverse proxy on localhost:9999
- Intercepts all requests to any OpenAI-compatible API
- Two-stage detection: pre-compiled regex union (<200µs) + spaCy NER (~2ms)
- Masks 14+ entity types: phone, email, ID card, bank card, person name, location, API keys (20+ formats), IP, URL, date, amount, organization, license plate, postcode
- SSE streaming passthrough with per-chunk latency under 3ms
- Optional AES-256-GCM encrypted vault for placeholder-to-original mapping

**Deployment**:

```bash
docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

Point your AI client to `http://localhost:9999/v1` — zero code changes needed.

**Key specs**:
- Regex detection: 180 microseconds average
- NER detection: 2.1ms average
- Total overhead (non-streaming): ~5ms
- SSE overhead: ~0.05ms per chunk
- 100% local, zero telemetry, MIT license
- Works with ChatGPT, Claude, DeepSeek, Cursor, Copilot — anything OpenAI-compatible

**Stack**: Python/FastAPI (proxy), spaCy (NER), SQLite + AES-256-GCM (vault), Preact (admin dashboard)

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Website: privacygw.pages.dev

I'd love feedback on the streaming approach and detection accuracy. The hardest engineering problem was handling PII split across SSE chunks — I ended up with a sliding window buffer that resolves entity boundaries across chunk boundaries without adding perceptible delay.

Built solo over ~3 months. ~2500 lines of Python. Used by my team in production.

---

### 5 Pre-Written Replies to Tough HN Questions

#### Q1: "What happens when the LLM returns PII in its response that wasn't in the prompt?"

Good question. There are two cases:

**Case 1: LLM echoes PII from the prompt**. If the prompt contained "my phone is [PHONE_1]", and the LLM response says "I see your phone is [PHONE_1]", the proxy can optionally reverse the placeholder on the response path. The user sees their real phone number in the response, but the LLM never saw it.

**Case 2: LLM generates new PII**. If the LLM invents a phone number or email in its response (which happens rarely but can happen), the proxy's response masking can detect and mask it the same way as request masking. You can configure this with `MASK_RESPONSE=true`.

By default, response masking is off — most users want the LLM's output returned as-is. But it's there if you need it.

#### Q2: "How is this different from a simple regex find-and-replace?"

It's not just regex — but honestly, regex does most of the heavy lifting. Here's what's layered on top:

1. **Luhn checksum validation for bank cards** — a 16-digit number isn't a bank card unless it passes the Luhn algorithm. This cuts false positives by ~40% on numeric data.

2. **NER fallback for unstructured entities** — personal names, locations, and organization names in free text. Regex can't handle these reliably. spaCy's NER catches about 80% of them.

3. **SSE streaming awareness** — a phone number split across two network packets needs reconstruction. Pure regex on each chunk in isolation would miss it.

4. **Context-aware placeholder generation** — same value gets the same placeholder across a conversation, so the LLM can reference it coherently.

5. **Vault + encryption for reversible masking** — you can restore the original text from the response if needed.

If you don't need any of the above, `sed` with a regex file would work. But for most real-world AI API usage, these layers matter.

#### Q3: "Why Python? The latency overhead seems high for a proxy."

Legitimate concern. Python adds ~2-5ms per request, primarily in the ASGI server overhead (uvicorn) and JSON serialization/deserialization.

Why I chose it anyway:
- **The bottleneck isn't the proxy.** LLM API calls take 1-30 seconds. Adding 5ms to a 5-second call is 0.1% overhead. The proxy latency is lost in the noise.
- **Development speed.** For a solo project, Python + FastAPI let me iterate fast. A Rust version (using actix-web or axum) would be ~50x faster at parsing but take 3x longer to build and iterate.
- **NER integration is trivial in Python.** spaCy is a pip install. Binding a C++ NER library or running a sidecar process adds complexity.

That said: if you're proxying millions of requests per day and every millisecond counts, Python would be a bottleneck. The k8s sidecar pattern mitigates this — the proxy handles the local pod's traffic, not the entire cluster's. And I'm open to rewrites in Rust or Go if someone from the community wants to contribute.

#### Q4: "Does this break ToS of the AI providers?"

I am not a lawyer and this is not legal advice.

That said: the gateway acts as a transparent HTTP proxy. It does not modify the API contract, bypass authentication, or access features you're not entitled to. It simply transforms the request body in transit.

OpenAI's API ToS prohibits sending certain categories of data (e.g., HIPAA PHI without a BAA). The Privacy Gateway actually helps you comply with those terms by ensuring sensitive data isn't sent in the first place.

For enterprise customers: the proxy can be deployed as an explicit MITM with certificate installation, or as a transparent forward proxy. The HTTPS MITM mode requires installing a CA certificate on client machines — standard practice in corporate environments.

#### Q5: "How do you handle false positives? What if the LLM needs to see a phone number to do its job?"

Two mechanisms:

**1. Whitelisting/ignore patterns**. You can configure patterns to exclude from masking. Common use case: blocklist of test phone numbers (`13800000000`), or domains you trust.

```yaml
# config.yaml
ignore_patterns:
  - "13800000000"           # test number, always safe
  - "*.internal.com"        # internal-only emails
```

**2. Entity-level policy configuration**. Each entity type can be set to one of three modes:

| Mode | Behavior | Use case |
|------|----------|----------|
| `mask` | Replace with typed placeholder | Default for all entities |
| `redact` | Replace with `[REDACTED]` | Entities where even the type is sensitive |
| `passthrough` | Leave as-is | Entities the LLM genuinely needs |

The key insight: most tasks don't need the actual phone number. They need to know _that_ a phone number is present. `[PHONE_1]` carriers enough semantic meaning for the LLM to work with.

For the rare case where the LLM truly needs the raw value (e.g., "extract all email addresses from this document"), you can use the `/api/mask` endpoint to get both the masked text AND the mappings, then selectively restore specific entities after the LLM returns its result.
