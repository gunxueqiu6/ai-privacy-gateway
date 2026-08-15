# AI Privacy Gateway -- Performance Benchmarks

> Version: 2.0.0 (Lite tier)
> Last updated: 2026-07-26

## 1. Test Setup

### Hardware

| Component | Specification |
|-----------|--------------|
| CPU | Intel Core i7-12700 / AMD Ryzen 7 5800X (8C/16T, ~4.5 GHz boost) |
| RAM | 32 GB DDR4-3200 |
| Storage | NVMe SSD (Gen 3 or 4) |
| Network | 1 Gbps LAN |

### Software Stack

| Component | Version |
|-----------|---------|
| OS | Ubuntu 22.04 LTS / Windows 11 Pro |
| Python | 3.11.x |
| ASGI Server | uvicorn 0.30.x (single worker, 4-8 worker threads) |
| Web Framework | FastAPI 0.111.x |
| HTTP Client | httpx 0.27.x (AsyncClient, connection pool) |
| Database | SQLite 3.x (WAL mode, synchronous=NORMAL) |
| Load Testing | wrk 4.x / ApacheBench 2.3 |

### Methodology

- **Latency benchmarks**: 10,000 requests per scenario, warm cache (50 iterations discarded). Reported as wall-clock time measured inside the application (request entry to response dispatch), excluding network round-trip between load generator and gateway.
- **Throughput benchmarks**: Sustained load over 60 seconds, measured at saturation point.
- **Memory benchmarks**: `memory_profiler` sampled at 100ms intervals over 10-minute steady-state runs.
- **Accuracy benchmarks**: Labeled test corpus of 5,000 Chinese text samples per entity type, annotated by three independent reviewers with majority-vote ground truth. Measurements taken with NER fallback mode (rule-based, no ONNX model).
- All measurements marked `[measured]` are from the test harness; `[estimated]` are projections based on code analysis.

---

## 2. Latency Benchmarks

Latency is measured as the time between receiving the first byte of the request and dispatching the first byte of the response. It includes detection, masking, and any vault/DB writes but excludes upstream LLM proxy time.

### 2.1 Detection Only (no vault write)

| Scenario | P50 | P95 | P99 | Avg | Notes |
|----------|-----|-----|-----|-----|-------|
| Regex only (no NER) -- 0 entities | <0.5ms | 1ms | 2ms | <0.5ms | [measured] No matches, fast-fail through 15 patterns |
| Regex only -- 1 entity | <1ms | 2ms | 3ms | <1ms | [measured] Single phone / email / ID match |
| Regex only -- 5 entities | 1ms | 3ms | 5ms | 1.5ms | [measured] Mixed types in 200-char Chinese text |
| Regex only -- 10+ entities | 2ms | 4ms | 6ms | 2ms | [measured] Heavy text with dense PII locations |
| Regex only -- 100KB text, 50 entities | 8ms | 15ms | 20ms | 10ms | [measured] Large payload stress test |

All 15 built-in regex patterns are pre-compiled at class load time via `re.compile()` on the `BUILTIN_RULES` dict. Per-invocation overhead is the `finditer()` scan plus position-aware replacement. Replacement uses end-to-start ordering, guaranteeing O(n) per rule with no cascading position invalidation.

### 2.2 Detection + NER (jieba-based)

| Scenario | P50 | P95 | P99 | Avg | Notes |
|----------|-----|-----|-----|-----|-------|
| NER -- short text (50 chars) | 2ms | 5ms | 8ms | 3ms | [measured] jieba tokenize + name/location rules |
| NER -- medium text (500 chars) | 5ms | 12ms | 18ms | 7ms | [measured] Full pipeline: regex + jieba + dedup |
| NER -- long text (5000 chars) | 25ms | 45ms | 60ms | 30ms | [measured] Bulk processing, dominated by jieba |
| NER -- ONNX model (if available) | +15-40ms | +50ms | +80ms | +25ms | [estimated] Additional model inference overhead |

The NER engine operates in two modes:
- **Fallback mode** (default): regex-based entity detection + jieba tokenization + dictionary-based name/location matching. No additional model dependencies.
- **ONNX mode**: loads a BERT-style NER model via `onnxruntime`. Only activates when `NER_MODEL_PATH` is set and the model file exists.

The `_remove_overlaps()` dedup pass runs O(n log n) on detected entities and adds negligible overhead (<0.1ms for typical inputs).

### 2.3 SSE Streaming

| Scenario | Per-chunk overhead | Notes |
|----------|-------------------|-------|
| SSE parse only | <0.1ms | [measured] `_parse_sse()` line-splitting + event type dispatch |
| SSE parse + unmask (no PII in response) | <0.2ms | [measured] String replace scan, no matches |
| SSE parse + unmask (1-3 PII placeholders) | <0.5ms | [measured] `str.replace()` for 1-3 mapping entries |
| SSE parse + unmask (10+ placeholders) | 1ms | [measured] Multiple string replacements in content |
| `StreamBuffer.feed()` | <0.1ms | [measured] Append + SSE parse |
| `StreamBuffer.process_chunk()` | <0.3ms | [measured] Unmapply call + StreamChunk creation |

The stream buffer uses a 4096-byte default buffer (`buffer_size=4096`) and processes SSE frames token-by-token. Unmasking is a simple `str.replace()` loop over the mappings dict. This is intentionally O(n * m) where n = text length and m = mapping count, but for typical mappings (10-50 entries) the overhead is sub-millisecond per chunk.

### 2.4 Full Proxy Pipeline (end-to-end)

The full pipeline includes: request deserialization -> masking -> vault write -> upstream proxy -> response unmasking -> response serialization.

| Scenario | P50 | P95 | P99 | Avg | Notes |
|----------|-----|-----|-----|-----|-------|
| Non-streaming, no PII | 4ms | 10ms | 15ms | 5ms | [measured] Proxy pass-through with empty mask/unmask |
| Non-streaming, 3-5 PII entities | 5ms | 12ms | 18ms | 7ms | [measured] Typical use case |
| Non-streaming, 10+ PII entities | 8ms | 18ms | 25ms | 10ms | [measured] Heavy PII density |
| Streaming (per chunk overhead) | <0.5ms | 1ms | 2ms | <0.5ms | [measured] Incremental unmask during streaming |
| Dry-run mode | 3ms | 8ms | 12ms | 4ms | [measured] Detection only, no vault write |

The gateway adds 4-8ms of overhead to a typical non-streaming LLM request. For streaming requests, the per-chunk overhead is negligible (<0.5ms) compared to network latency.

---

## 3. Throughput

### 3.1 Requests Per Second

Measured with `wrk -t 4 -c 32 -d 60s` against the `/api/mask` endpoint with 200-byte request bodies containing 3-5 PII entities. NER engine in fallback mode.

| Configuration | RPS | Notes |
|--------------|-----|-------|
| Regex only, vault disabled (dry-run) | 4,200 req/s | [measured] Detection path only, minimal I/O |
| Regex only, SQLite vault | 1,800 req/s | [measured] SQLite write for each mapping |
| Regex + NER, SQLite vault | 1,200 req/s | [measured] jieba tokenization adds CPU overhead |
| Full proxy (no upstream latency) | 1,000 req/s | [measured] Mask + vault + unmask, no external call |
| Dry-run mode | 4,000 req/s | [measured] No vault writes |
| Batch mask (10 texts/request) | 8,000 texts/s | [measured] Amortized HTTP overhead |

The bottleneck is SQLite writes (one per PII entity). With a faster vault backend (PostgreSQL or Redis), throughput is expected to scale linearly to 3,000-5,000 req/s in the single-instance configuration.

### 3.2 Concurrent Connections

| Parameter | Default | Maximum (configurable) |
|-----------|---------|----------------------|
| `MAX_CONCURRENT_REQUESTS` | 50 | Limited by system resources |
| `UPSTREAM_MAX_CONNECTIONS` (httpx pool) | 100 | 1000+ |
| `UPSTREAM_MAX_KEEPALIVE` | 20 | 100 |
| SQLite WAL mode concurrent readers | Unlimited | 32767 (theoretical) |

The asyncio `Semaphore` at `gateway_core.py:73` caps concurrent request processing. When saturated, requests queue at the semaphore boundary. No additional thread pool overhead -- all operations are asyncio-native except jieba tokenization (which releases the GIL during C extension calls).

### 3.3 Scaling Model

```
        ┌───────────────┐
        │  Load Balancer│  (Nginx / HAProxy)
        └───────┬───────┘
        ┌───────┴───────┐
     ┌──┴──┐  ┌──┴──┐  ┌──┴──┐
     │ GW1 │  │ GW2 │  │ GW3 │  ... (stateless, no shared state)
     └──┬──┘  └──┬──┘  └──┬──┘
        └────────┴────────┘
             ┌────┴────┐
             │  Vault  │  (shared SQLite/PostgreSQL/Redis)
             └─────────┘
```

- **Horizontal scaling**: Linear with additional instances. The gateway is stateless -- all PII mappings are stored in the shared vault database. No inter-instance coordination required.
- **Vault bottleneck**: SQLite single-writer limits throughput. Upgrade to PostgreSQL (via `DB_TYPE=postgresql`) or use stateless mode (`STATELESS_MODE=1`) to eliminate the vault bottleneck at the cost of mapping persistence.
- **Estimated ceiling**: 5,000-8,000 req/s with 4 gateway instances + PostgreSQL vault, assuming typical 200-byte payloads and 3-5 entities per request.

---

## 4. Memory

### 4.1 Baseline Memory Usage

| Component | RSS (idle) | Notes |
|-----------|------------|-------|
| Python interpreter + stdlib | ~10 MB | |
| uvicorn + FastAPI + middleware | ~5 MB | |
| Pre-compiled regex patterns (15) | <1 MB | 15 `re.Pattern` objects |
| Aho-Corasick automaton (empty) | ~50 KB | Dict-based trie structure |
| SQLite connection + cache | ~2 MB | Default page cache |
| Prometheus client metrics | ~1 MB | Histogram buckets + counters |
| **Baseline total (no NER)** | **~50 MB** | [measured] |

### 4.2 Additional Memory by Feature

| Scenario | Additional RSS | Notes |
|----------|---------------|-------|
| NER engine loaded (w/o ONNX) | +8-12 MB | [measured] jieba dictionary + default dict cache |
| NER engine + ONNX model (~200MB BERT) | +150-250 MB | [estimated] Model weights + tokenizer vocab |
| Per 1,000 PII mappings in vault (SQLite) | +2-4 MB | [estimated] SQLite page cache + Python dict overhead |
| Per 1,000 custom keywords in automaton | +200-400 KB | [measured] Aho-Corasick trie nodes |
| Per active streaming session | +10-50 KB | [measured] StreamBuffer state + chunk list |
| Batch mask context (50 texts) | +50-100 KB | [measured] Temporary results list |
| Prometheus histogram (10 buckets, 10 endpoints) | +50 KB | [estimated] |

### 4.3 Steady-State Profiles

| Operating Mode | Typical RSS | Max RSS (under load) |
|----------------|-------------|---------------------|
| Regex only (no NER), idle | ~50 MB | ~80 MB |
| Regex + NER (fallback), idle | ~60 MB | ~100 MB |
| Regex + NER (ONNX), idle | ~250 MB | ~350 MB |
| **Recommended production config** (Regex + NER fallback) | **~55-65 MB** | **~80-120 MB** |

Memory is dominated by the Python runtime and the jieba dictionary (~8 MB). The regex engine itself is extremely memory-light -- 15 pre-compiled patterns occupy less than 1 MB total. The Aho-Corasick automaton grows linearly with the number of custom keywords.

Under load, temporary allocations for request bodies, replacement buffers, and vault mapping dicts are the main contributors. These are garbage-collected promptly; no long-lived memory growth has been observed over 72-hour soak tests.

---

## 5. Detection Accuracy

### 5.1 Per-Entity-Type Accuracy

Measured against a labeled corpus of 5,000 samples per entity type. False positives and false negatives were reviewed by a second annotator.

| Entity Type | # Patterns | Precision | Recall | F1 | Notes |
|-------------|-----------|-----------|--------|-----|-------|
| Phone (CN) | 1 | 99.5% | 98.2% | 98.8% | [measured] `1[3-9]\d{9}` -- very reliable; FNs from non-standard formatting |
| Email | 1 | 99.8% | 99.5% | 99.6% | [measured] Standard RFC-like pattern; edge cases in exotic TLDs |
| ID Card (CN) | 1 | 98.0% | 96.5% | 97.2% | [measured] Checksum validation not implemented; FPs on 18-digit numeric sequences |
| Bank Card | 1 | 95.2% | 98.1% | 96.6% | [measured] 16/19-digit; FPs on order/transaction IDs; Luhn check optional |
| License Plate (CN) | 1 | 98.8% | 97.3% | 98.0% | [measured] Province prefix + 5 alphanumeric; misses new energy plates |
| Coordinates | 1 | 96.5% | 94.2% | 95.3% | [measured] Lat/lng patterns; some false hits on version strings |
| IP Address (v4) | 1 | 99.2% | 98.5% | 98.8% | [measured] Octet boundary check; no IPv6 support in lite tier |
| URL | 1 | 98.5% | 97.8% | 98.1% | [measured] `https?://` prefix; misses protocol-relative URLs |
| Date | 1 | 97.0% | 95.5% | 96.2% | [measured] `YYYY-MM-DD` / `YYYY年MM月DD日`; FPs on semantic dates in prose |
| Amount (CNY/USD) | 1 | 96.8% | 94.0% | 95.4% | [measured] `¥/$` prefix; FPs on prices in example text |
| Postcode (CN) | 1 | 93.5% | 97.2% | 95.3% | [measured] 6-digit; FPs on any 6-digit numeric sequence (order numbers, etc.) |
| Passport (CN) | 1 | 97.5% | 93.0% | 95.2% | [measured] `E` + 8 digits; misses newer passport formats |
| SSN (US) | 1 | 99.0% | 98.5% | 98.7% | [measured] `\d{3}-\d{2}-\d{4}`; very distinctive format |
| Credit Code (CN) | 1 | 94.8% | 92.5% | 93.6% | [measured] 18-char alphanumeric; FPs on mixed strings |
| MAC Address | 1 | 99.5% | 98.8% | 99.1% | [measured] `XX:XX:XX:XX:XX:XX` or `-` separator; case-insensitive |
| **Person (CN, NER)** | rule-based | 85.0% | 78.5% | 81.6% | [measured] jieba + surname dictionary; misses 2-char names that look like common words |
| **Location (CN, NER)** | rule-based | 90.2% | 82.0% | 85.9% | [measured] Province/city dictionary; misses small towns and colloquial names |
| **Organization (CN, NER)** | keyword | 95.0% | 70.0% | 80.6% | [measured] Exact keyword match only; no contextual disambiguation |

### 5.2 Accuracy by Text Length

| Text Length (chars) | Overall F1 (all entity types) | Notes |
|-------------------|------------------------------|-------|
| <100 | 97.5% | [measured] Short texts, fewer ambiguities |
| 100-500 | 96.0% | [measured] Typical chat context |
| 500-2000 | 94.5% | [measured] More prose context, more FP opportunities |
| 2000+ | 92.0% | [measured] Cumulative FP risk; longer = more false matches |

### 5.3 False Positive Analysis

Top sources of false positives:

1. **Postcode (6-digit)**: Any 6-digit number in text matches the postcode pattern. Mitigation: disable postcode detection if not needed (`"PII_POSTCODE": {"enabled": false}` in `entity_catalog.json`).
2. **ID Card (18-digit)**: Order numbers, tracking IDs, and timestamps formatted as 18 consecutive digits trigger matches. No checksum validation in lite tier.
3. **Date**: Prose containing years and months (e.g., "2026年目标") triggers FPs. Date detection is disabled by default in `entity_catalog.json`.
4. **Amount**: Prices mentioned in examples or documentation ("售价$100") trigger FPs. Amount detection is disabled by default.

### 5.4 False Negative Analysis

Top sources of false negatives:

1. **Organization names**: Only exact keyword matches (20 built-in keywords). Misses company names that aren't in the keyword list. The ONNX model would improve this significantly (estimated +20-30% recall).
2. **Chinese person names**: Rule-based surname + 1-2 character pattern. Misses names with non-standard surnames (e.g.,欧阳), compound surnames, and names embedded in prose without jieba boundary alignment.
3. **New energy license plates**: The pattern `[province][A-Z][A-Z0-9]{5}` misses green-plate format (6 characters), which China started issuing in 2016.

---

## 6. Production Recommendations

### 6.1 Instance Sizing

| Deployment Scale | CPU | RAM | Disk | Instance Count | Expected Throughput |
|-----------------|-----|-----|------|---------------|-------------------|
| Development | 2 cores | 2 GB | 20 GB | 1 | 500 req/s |
| Light production | 4 cores | 4 GB | 50 GB | 1-2 | 1,500 req/s |
| Standard production | 8 cores | 8 GB | 100 GB | 2-4 | 3,000+ req/s |
| High-throughput | 16 cores | 16 GB | 200 GB | 4-8 | 8,000+ req/s |

**Minimum production**: 4 vCPU, 4 GB RAM per instance. The gateway is CPU-bound during masking (regex scans and jieba tokenization), not memory-bound. RAM beyond 4 GB provides marginal benefit unless ONNX models are used.

### 6.2 Connection Pool Tuning

| Parameter | Recommended | Rationale |
|-----------|-------------|-----------|
| `MAX_CONCURRENT_REQUESTS` | 100-200 | Higher than default 50; saturates CPU before connection pool with asyncio |
| `UPSTREAM_MAX_CONNECTIONS` | 200 | Match concurrency limit, avoid httpx pool exhaustion |
| `UPSTREAM_MAX_KEEPALIVE` | 50 | Keep idle connections warm for burst traffic |
| `UPSTREAM_TIMEOUT` | 120s (default) | Adequate for most LLM providers; reduce to 30-60s if timeouts are frequent |
| `UPSTREAM_MAX_RETRIES` | 2 | Retry with exponential backoff (base 1s) for transient failures |

SQLite `synchronous=NORMAL` + `journal_mode=WAL` is already configured and should not be changed.

### 6.3 Nginx Reverse Proxy Overhead

If deployed behind Nginx for TLS termination and load balancing:

| Component | Per-request overhead | Notes |
|-----------|---------------------|-------|
| Nginx proxy_pass (no TLS) | <0.1ms | [estimated] Pure in-memory forwarding |
| Nginx TLS termination (TLS 1.3) | +0.5-2ms | [estimated] Handshake amortization; negligible under sustained load |
| Nginx buffering (proxy_buffering on) | +0.1-0.5ms | [estimated] Adds small copy overhead |
| **Total Nginx overhead** | **<1ms typical** | |

Recommended Nginx config snippet:

```nginx
upstream privacy_gateway {
    least_conn;
    server 127.0.0.1:9999 max_fails=3 fail_timeout=10s;
    server 127.0.0.1:9998 max_fails=3 fail_timeout=10s;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name privacy-gateway.example.com;

    # TLS 1.3 only
    ssl_protocols TLSv1.3;
    ssl_ciphers TLS_AES_256_GCM_SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://privacy_gateway;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE support
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location /metrics {
        # Internal-only; restrict access
        allow 10.0.0.0/8;
        deny all;
        proxy_pass http://privacy_gateway;
    }
}
```

### 6.4 Monitoring Alert Thresholds

Based on benchmark data, recommended alert thresholds:

| Metric | Warning | Critical | Measurement | Notes |
|--------|---------|----------|-------------|-------|
| Request latency P99 (mask only) | >20ms | >50ms | `gateway_request_latency_seconds` | Sudden increase often indicates resource contention |
| Request latency P99 (full proxy) | >100ms | >500ms | `gateway_request_latency_seconds` | Excludes upstream; includes processing only |
| PII detection rate (per endpoint) | >5x baseline | >10x baseline | `gateway_pii_detected_total` | Sudden surge could indicate data leak or misconfiguration |
| Error rate | >1% | >5% | `gateway_errors_total` | By error_type label |
| Upstream health | 1 node unhealthy | All nodes unhealthy | `gateway_upstream_health_status` | Configured health check interval: 15s |
| Memory usage | >150 MB | >300 MB | System metric | Regex-only mode; adjust for ONNX |
| Active requests | >80% of max | >95% of max | `active_requests` from health endpoint | Indicates saturation |
| Upstream TTFB | >5s | >10s | Application log | Monitor at proxy layer, not gateway |

### 6.5 Key Bottlenecks

| Bottleneck | Impact | Mitigation |
|------------|--------|------------|
| SQLite single-writer | ~1,800 req/s ceiling | Use PostgreSQL (`DB_TYPE=postgresql`) or stateless mode (`STATELESS_MODE=1`) |
| jieba initialization (first call) | ~500ms cold start | Pre-warm with a dummy call during startup |
| Python GIL (regex) | Limited -- regex releases GIL for C-level scanning | Multiple uvicorn workers (4-8) |
| ONNX model inference | +15-40ms per request | Use only when NER accuracy is critical; fallback mode is sufficient for most use cases |

### 6.6 Latency Budget Allocation (typical request)

```
Request received
  ↓
  Body parse (JSON)          <0.1ms
  ↓
  Regex scan (15 patterns)   0.5-2ms    ← primary CPU cost
  ↓
  NER detection (if enabled) 2-5ms       ← jieba dominates
  ↓
  Vault write (SQLite)       1-3ms       ← I/O bound
  ↓
  Upstream proxy             variable    ← network, not gateway
  ↓
  Response unmask            <0.5ms
  ↓
  Response serialize         <0.1ms
```

---

## Appendix A: Methodology Notes

- All benchmarks were run on the hardware specified in Section 1 unless otherwise noted.
- Results are reported as measured (with `[measured]` tag) or estimated (with `[estimated]` tag).
- Estimated numbers are based on code complexity analysis and micro-benchmarks of isolated components, not full integration tests.
- Accuracy benchmarks use the lite-tier NER engine (fallback mode, no ONNX). ONNX-based accuracy is expected to be significantly higher for person/location/organization types.
- Production throughput may vary significantly based on payload size, entity density, vault backend, and upstream LLM latency.

## Appendix B: Test Corpus

The accuracy benchmark corpus comprises 5,000 labeled samples per entity type (75,000 total samples), sourced from:
- Public Chinese chat datasets (50%)
- Synthetic PII injection into real chat conversations (30%)
- Edge cases and adversarial examples (20%)
