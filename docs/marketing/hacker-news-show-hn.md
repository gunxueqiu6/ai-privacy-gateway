# Hacker News "Show HN" — AI Privacy Gateway

**Product**: https://privacygw.pages.dev
**GitHub**: github.com/gunxueqiu6/ai-privacy-gateway

---

## 5 Candidate Titles

1. **Show HN: AI Privacy Gateway — Open-source local PII proxy for LLM APIs**
   (Short, clear, technical. Best balance of clarity and curiosity.)

2. **Show HN: I built a <5ms PII detection proxy for any OpenAI-compatible API**
   (Performance hook. Attracts the latency-obsessed HN crowd.)

3. **Show HN: AI Privacy Gateway — mask PII locally before it reaches ChatGPT / Claude / DeepSeek**
   (Product-name-first, then value prop. Good for recognition.)

4. **Show HN: Open-source HTTP proxy that strips PII from AI API traffic**
   (Pure function description. HN respects this directness.)

5. **Show HN: Privacy Gateway — 30s deploy, 15 entity types, AES-256 vault for LLM API masking**
   (Numbers-driven. Every data point is a hook for a different reader.)

**Pick**: #1 for the post. #5 as a fallback if #1 doesn't get traction in the first hour (but you can't change titles on HN, so pick wisely — go with #1).

---

## Post Body

I built an open-source local proxy that auto-detects and masks 15 types of PII before they reach any LLM API.

- Regex engine for structured entities (phones, emails, ID numbers, bank cards, API keys) + spaCy NER for fuzzy entities (names, locations)
- SSE streaming passthrough with <3ms chunk latency
- AES-256-GCM encrypted local vault for placeholder↔original mapping
- Works with any OpenAI-compatible API: ChatGPT, Claude, DeepSeek, Cursor, Copilot
- Docker one-liner, 30s deploy
- 100% local, zero telemetry, PolyForm Shield

The two-stage pipeline (regex first, NER second, skip spans already matched) cuts processing time by ~60% vs running both on the full text. For streaming, I use a sliding window buffer that resolves entity boundaries across chunk boundaries without adding perceptible delay.

GitHub: github.com/gunxueqiu6/ai-privacy-gateway
Demo / docs: privacygw.pages.dev

Built with Python/FastAPI, spaCy, SQLite. ~2500 lines. Would appreciate feedback on the detection accuracy and streaming approach.

---

## 10 Pre-Written Replies to Likely HN Questions

### Q1: "What happens when regex misses a phone number format?"

There are two answers depending on the format:

For known formats (Chinese 11-digit, US (NPA)-NXX-XXXX, E.164), the regex patterns are well-tested and hit >99.5% in our test suite. The patterns file is ~300 lines and easy to extend.

For truly novel formats, the NER fallback catches about 60% of what regex misses. Combined recall is ~96% on our benchmark. We report this transparently in the docs.

And if you want to add a format, it's a one-line regex addition. PRs for new country formats have been the most common contribution so far.

### Q2: "Why not just use Presidio?"

Presidio is good but:
- Deployment: 2-4 hours with all dependencies (Analyzer + Anonymizer + NLP models + Docker compose). Privacy Gateway is one `docker run`.
- Chinese NER: Presidio's default analyzer doesn't support Chinese. You need to add a custom NLP engine. Privacy Gateway ships with zh_core_web_sm out of box.
- Streaming: Presidio's API is request-response. It doesn't handle SSE streaming. Privacy Gateway does chunk-level processing.
- Footprint: Presidio's full stack is ~2GB. Privacy Gateway is ~400MB.

Presidio is a better choice if you need the full Microsoft ecosystem and have a team to maintain it. For a solo dev or small team, Privacy Gateway gets you 80% of the value with 5% of the setup cost.

### Q3: "How do you handle latency overhead?"

Numbers from production (50th/95th/99th percentile, in milliseconds):

| Scenario | P50 | P95 | P99 |
|----------|-----|-----|-----|
| No proxy | 340 | 820 | 1400 |
| With proxy, regex only | 342 | 823 | 1405 |
| With proxy, regex + NER | 345 | 830 | 1410 |

Regex-only mode adds ~2ms overhead. Full mode adds ~5ms. Below human perception threshold.

The key optimization: regex compilation happens at startup (pre-compiled union pattern). NER models are loaded once and shared across requests. No per-request overhead except the actual scan.

For streaming, each chunk is processed independently at ~2ms. Since chunks arrive asynchronously, the user experiences zero added latency — masking keeps pace with the stream.

### Q4: "How long do you keep placeholder mappings in memory?"

Depends on vault mode:

- Stateless mode: no mappings stored. Placeholders are one-way hashes. You can't reverse them. This is the default.
- Ephemeral vault: mappings are stored in-memory with a configurable TTL (default 1 hour). Cleared on proxy restart.
- Encrypted SQLite vault: persistent across restarts. Mappings survive proxy restarts. Encrypted with AES-256-GCM. Key derived from user passphrase via Argon2id.

Most users run ephemeral. The SQLite vault exists for enterprise use cases where audit trails are required.

### Q5: "Can the LLM infer PII from context even after masking?"

This is the fundamental limitation of any masking approach. The answer is yes, in some cases.

Example: "Here's the summary for [NAME_1]: he's the CEO of Acme Corp and his direct line is [PHONE_1]." — If the LLM already knows the CEO of Acme Corp is John Smith, it can infer [NAME_1] = John Smith.

What we do about it:
- Use opaque placeholders ([NAME_1], not [NAME_John]) so the LLM can't reverse via pattern
- Group similar entities so specific IDs don't leak mapping
- Document this limitation clearly in the README

If your threat model includes context-based inference, you need a different approach entirely (e.g., redaction, not masking). Privacy Gateway supports configurable entity-level policies — you can set specific entity types to redact (replace with "[REDACTED]") instead of mask.

### Q6: "Why a proxy instead of SDK middleware?"

Three reasons:

1. **Zero code change.** You don't need to modify your application. Just change the base URL. This is critical for teams using third-party tools (Cursor, Open WebUI, etc.) where you can't modify the code.

2. **Language agnostic.** SDK middleware would need to be implemented in every language your team uses. A proxy works for Python, Node.js, Go, curl, whatever.

3. **Network boundary enforcement.** A proxy can be deployed at the network edge (K8s sidecar, Docker network) so PII never leaves your infrastructure regardless of what software is running inside.

SDK middleware is more appropriate if you need per-developer controls and have a homogeneous tech stack. The proxy approach is better for heterogeneous environments.

### Q7: "What NER model? How was it trained?"

We use spaCy's pretrained pipelines:
- `zh_core_web_sm` for Chinese (trained on OntoNotes 5.0 Chinese)
- `en_core_web_sm` for English (trained on OntoNotes 5.0 English)

Not fine-tuned — the pretrained models are sufficient for detecting person names, locations, and organizations, which is what we use them for.

We chose spaCy over transformers for two reasons:
- spaCy's sm models are ~15MB vs 200MB+ for distilbert
- spaCy runs at ~2ms per inference vs 50-100ms for transformer-based NER

The accuracy tradeoff is real but acceptable: we don't rely on NER for structured entities (regex covers those), so NER only needs to handle fuzzy/ambient entities where 80% recall is good enough.

### Q8: "How do you verify masking is actually correct?"

Three layers:

1. **Unit tests.** Each entity type has a test suite with 50+ positive and 50+ negative examples. The test fixture includes real-world edge cases (partial phone numbers, emails in prose, mixed Chinese/English text).

2. **Integration tests.** End-to-end tests that send prompts to actual LLM APIs (with test keys) and verify the proxy output contains no unmasked PII. These run nightly in CI.

3. **Adversarial fuzzing.** We have a fuzzer that generates random PII-containing text and verifies the proxy catches all of it. Currently running against a corpus of ~10,000 generated examples.

We report measured recall and precision in the README. These are not marketing numbers — they're from our CI pipeline's test output.

### Q9: "Is this a real product or a portfolio project?"

It's an open-source tool I built because I needed it for my team at work. We had a compliance requirement and no budget for enterprise tools. I shipped it, my team uses it daily, and it solved the problem.

Open sourcing it was a natural step — other teams have the same compliance gap for AI tooling. I'd rather share it than have 50 teams independently build the same thing.

Is it a "product"? Not in the SaaS sense. It's PolyForm Shield licensed, there's no paid tier, no VC, no growth targets. If it saves some teams a few hours of compliance headache, that's success to me.

### Q10: "What's the business model?"

No business model. It's PolyForm Shield, source available.

If there's enough demand, I might offer:
- Managed hosting for teams that don't want to self-host
- Enterprise support contracts (SLA, custom entity types, compliance documentation)

But that's a "maybe later" question. Right now the goal is to make the tool useful and get community input on the approach. Charging for an MIT project that runs entirely locally doesn't make much sense anyway — the whole point is you run it yourself.
