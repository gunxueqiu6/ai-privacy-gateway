# Reddit Launch Posts — AI Privacy Gateway

**Product**: https://privacygw.pages.dev
**GitHub**: github.com/gunxueqiu6/ai-privacy-gateway
**License**: MIT
**Stack**: Python/FastAPI, regex + NER, SSE streaming, AES-256-GCM vault

---

## Post 1: r/selfhosted (2M members)

**Best posting time**: Sunday 10:00 AM ET

**Title**: I built a self-hosted proxy that masks PII before it reaches ChatGPT — 30s deploy, 100% local

**Body**:

Been meaning to share this for a while. I use ChatGPT/Claude/Cursor daily for work, and I kept worrying about what happens when I paste code with API keys, or a config file with internal IPs, or a DB dump with real user emails.

So I built a local proxy that sits between you and any OpenAI-compatible API. It auto-detects 15 types of PII — phone numbers, emails, ID numbers, bank cards, API keys, IPs — and replaces them with placeholders before the data leaves your machine. The originals stay in a local encrypted vault (AES-256-GCM). Nothing touches the LLM provider.

```
docker run -d -p 8111:8111 gunxueqiu/ai-privacy-gateway
```

Point your client to `http://localhost:8111/v1` and done. Works with ChatGPT, Claude, DeepSeek, Cursor — anything that speaks the OpenAI API format.

Why I went self-hosted:
- Zero trust in cloud providers for my team's data
- No monthly fee, no data leaves my VPS
- Full control — can extend entity types, audit the code, tune the regex
- SSE streaming works (no buffering, no added latency)

The NER model runs locally via spaCy, ~2ms per request. For a team of 50, this costs basically nothing to run.

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Demo: privacygw.pages.dev

Would love feedback from folks who've dealt with the same problem.

**Follow-up strategy if it gains traction**:
- "How does this compare to Presidio?" — Presidio takes 2-4 hours to deploy with all deps. This is one docker command. Also, Presidio has no Chinese NER out of box.
- "Does it work with Ollama?" — Technically yes since Ollama serves OpenAI-compatible API, but you probably don't need masking if you're fully local. This is for hybrid setups.
- "Can I add custom entity types?" — Yes, edit the patterns file and rebuild. PRs welcome.

---

## Post 2: r/opensource (1M members)

**Best posting time**: Tuesday 12:00 PM ET

**Title**: AI Privacy Gateway — MIT-licensed local PII masking for any OpenAI-compatible API

**Body**:

I've been dogfooding this for a few months with my team. Wanted to get the community's eyes on it before calling it 1.0.

**What it is**:
A transparent HTTP proxy that intercepts requests to LLM APIs, detects personally identifiable information, replaces it with deterministic placeholders, and stores the mapping in an encrypted local vault. When the LLM returns a response containing placeholders, the proxy reverses the mapping so the user sees the real data.

**Why open source**:
- Privacy tools should be auditable. Period.
- We wanted companies in regulated industries (fintech, healthcare, legal) to be able to self-host behind their own VPC
- Community contributions for new entity types and language support

**The stack**:
- Python/FastAPI for the proxy layer
- spaCy (zh_core_web_sm + en_core_web_sm) for NER-based detection
- Regex engine for structured patterns (phones, emails, IDs, bank cards)
- AES-256-GCM for the local vault
- SSE passthrough for streaming responses

**Speed**:
- Regex detection: <200 microseconds
- NER detection: ~2ms
- Total latency added: ~5ms on average

**Compared to alternatives**:
- Microsoft Presidio: ~2-4 hours to deploy, heavy dependency tree, no Chinese NER out of box
- Kiji: good but no streaming support
- Most SaaS solutions: your data hits their servers

This is MIT. No telemetry, no cloud dependency, no "upgrade to pro" upsell.

github.com/gunxueqiu6/ai-privacy-gateway

**Follow-up strategy if it gains traction**:
- Expect questions about accuracy — report numbers honestly: regex is 99%+ for structured types, NER is ~85-90% for Chinese entities. Share the test harness methodology.
- PR discussion is the real goal here. Engage substantive comments.
- If someone asks about contributing, point to CONTRIBUTING.md and open issues.

---

## Post 3: r/LocalLLaMA (300K members)

**Best posting time**: Thursday 2:00 PM ET

**Title**: Tool to protect privacy when using cloud LLM APIs — masks PII locally before sending

**Body**:

I know most people here run local models. But realistically, a lot of us still hit cloud APIs for tasks where local models fall short — coding assistants like Cursor, Claude for longer reasoning, GPT-4 for certain structured outputs.

The problem: I kept catching myself pasting proprietary code with embedded credentials into web UIs. Or customer data into API requests.

This is a dead-simple proxy that sits between your client and the API:

1. You send your prompt to localhost:8111
2. It scans for PII (phone, email, ID, bank card, IP, API key, address, etc.)
3. Masks them before forwarding
4. Stores original values locally in an encrypted vault
5. Unmasks responses on the way back

```
docker pull gunxueqiu/ai-privacy-gateway
docker run -d -p 8111:8111 \
  -v ./vault:/app/vault \
  gunxueqiu/ai-privacy-gateway
```

Then configure Open WebUI / SillyTavern / anything -> `http://localhost:8111/v1`.

Even if you're 90% local, that 10% of cloud API calls is where the risk is. This covers it.

GitHub: github.com/gunxueqiu6/ai-privacy-gateway

**Follow-up strategy if it gains traction**:
- LocalLLaMA users are technical and skeptical. Engage technical questions directly.
- Someone will ask "why not just use a local model" — acknowledge that's ideal, but reality is hybrid. This is a bridge solution.
- If someone finds a bug, thank them publicly and fix fast.

---

## Post 4: r/programming (6M members)

**Best posting time**: Monday 1:00 PM ET

**Title**: How I built a sub-2ms PII detection proxy with SSE streaming support

**Body**:

I spent the last few months building an AI privacy proxy, and I wanted to share some technical decisions that might be useful for anyone doing text processing middleware.

**Problem**: Detect and mask 15 types of PII (Chinese + English) across streaming and non-streaming LLM API calls, with <10ms overhead.

**Architecture decisions**:

**1. Two-stage detection pipeline**

```
Input -> Pattern Detector (regex) -> NER Detector (spaCy) -> Masker -> Output
        ^--- 200us -----------^     ^--- 2ms -----------^
```

Regex first because structured patterns (phones, emails, IDs) are unambiguous and fast. NER second for fuzzy entities (person names, locations). If regex already matched a span, NER skips it — no double-processing.

This matters: running NER on every token is wasteful when regex already caught 70% of entities. Cut processing time by ~60% vs running both on the full text.

**2. SSE streaming without buffering delays**

The naive approach: buffer the entire stream, process, then forward. Adds seconds of perceived latency.

The approach I took: process each chunk independently. Regex works on partial text naturally. For NER, I accumulate minimal context (last K tokens) to resolve entity boundaries, then flush. Average chunk-to-output latency: ~2ms.

```python
async def process_stream(stream, detector):
    context = ""
    async for chunk in stream:
        content = chunk["choices"][0]["delta"].get("content", "")
        if content:
            masked, context = detector.process_streaming(content, context)
            yield f"data: {json.dumps({'choices': [{'delta': {'content': masked}}]})}\n\n"
    yield "data: [DONE]\n\n"
```

**3. Encrypted vault design**

Placeholder-to-original mappings are stored in a local SQLite DB encrypted with AES-256-GCM. The encryption key is derived from a user-supplied passphrase via Argon2id. Key never touches disk unencrypted.

**Performance numbers**:

| Test | Result |
|------|--------|
| Regex detection (avg) | 180us |
| NER detection (avg) | 2.1ms |
| Total overhead (non-streaming) | 4.8ms |
| Total overhead (streaming) | 2.3ms/chunk |
| Memory, idle | 180MB |
| Memory, under load (100 concurrent) | 420MB |

**Tradeoffs I'm still thinking about**:
- Regex-only mode for max speed vs NER for better recall on unstructured entities
- In-memory vault vs SQLite vault vs Redis vault for different scaling needs
- False positives on masked content — LLM sees "[PHONE_1]" instead of real data, does context quality suffer?

Would love to hear how others have approached similar problems. There's a lot of "privacy middleware" for LLMs now but very few that are open source and streaming-compatible.

Full writeup with benchmarks: github.com/gunxueqiu6/ai-privacy-gateway

**Follow-up strategy if it gains traction**:
- r/programming is the toughest audience. Technical depth is expected. Engage every substantive technical question.
- If someone calls out a design mistake, concede quickly and explain the fix path.
- Expect architecture debates re: proxy vs SDK approach. State your reasoning clearly.

---

## Post 5: r/SideProject (200K members)

**Best posting time**: Saturday 9:00 AM ET

**Title**: My side project: A privacy-first proxy for AI APIs — built solo, PolyForm Shield

**Body**:

Started this because I needed it. Working at a fintech company, everyone's using ChatGPT/Cursor, and I kept asking "what happens when someone pastes a customer's ID number into a prompt?"

Company answer was "we're evaluating enterprise solutions." Three months later, nothing.

So I built it myself on weekends.

**The product in one sentence**: A local proxy that detects PII (15 types), masks it before it reaches the LLM API, and unmasks responses on the way back. Runs in Docker, 30s to deploy.

**Tech stack**: Python/FastAPI + spaCy + SQLite + AES-256-GCM

**Timeline**:
- Week 1: Basic regex proxy, 5 entity types, non-streaming only
- Week 2: Added SSE streaming support (hardest part by far)
- Week 3: NER integration for Chinese entities
- Week 4: Vault design with encryption
- Month 2: Testing with real team, fixing edge cases
- Month 3: Documentation, Docker image, website
- Now: Open sourcing it

**Hardest lesson**: Streaming. SSE chunks can split a phone number across two chunks. Had to implement a context-tracking state machine that holds partial token sequences and resolves them when the entity boundary is clear. Broke it three times before it worked.

**What I'd do differently**: Skip the regex-vs-NER debate and just use a two-stage pipeline from the start. Also, Docker multi-stage builds to keep the image from ballooning.

**Where it stands now**: PolyForm Shield licensed, used by a few small teams I don't know. No monetization plan — it's a tool I needed, shared in case others need it too.

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Demo: privacygw.pages.dev

**Follow-up strategy if it gains traction**:
- r/SideProject is supportive. Share your journey honestly, including failures.
- If someone asks about monetization, say "not yet, might do enterprise support if there's demand."
- Engage "how did you learn X" questions — the side project community loves the learning story.
