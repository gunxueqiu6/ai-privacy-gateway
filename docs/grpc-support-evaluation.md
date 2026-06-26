# gRPC Support Evaluation

> Date: 2026-06-26
> Scope: Evaluate the feasibility and effort of adding gRPC proxy support to AI Privacy Gateway

## 1. Current Architecture: HTTP Proxy Flow

The gateway runs as a FastAPI HTTP server (port 9999). The core processing pipeline for
`/v1/chat/completions` is:

```
Client HTTP Request
       |
       v
  [mask_request]  -- PII detection + replacement (phone, email, idcard, ...)
       |
       v
  [proxy_request / proxy_stream_request]  -- forward masked payload to upstream LLM
       |
       v
  [unmask_response]  -- restore original PII in the LLM response
       |
       v
Client HTTP Response
```

Key characteristics:
- **Transport**: HTTP/1.1 with optional SSE streaming (`text/event-stream`)
- **Payload format**: JSON (`{"messages": [{"role": "user", "content": "..."}]}`)
- **Upstream targets**: OpenAI-compatible REST APIs (`/v1/chat/completions`)
- **Masking scope**: Only the `content` field of message objects
- **Auth passthrough**: `Authorization` header is extracted and forwarded

The `proxy_generic_request()` method handles non-chat routes (models, embeddings, moderations)
as pass-through without masking.

## 2. gRPC for AI APIs: Current Landscape

### Which AI providers support gRPC?

| Provider | gRPC Support | Notes |
|----------|-------------|-------|
| **OpenAI** | No | REST/SSE only. No official gRPC endpoint. |
| **Anthropic** | No | REST/SSE only. |
| **Google Gemini** | Yes | `generativelanguage.googleapis.com` supports gRPC and gRPC-TLS |
| **AWS Bedrock** | Yes (via SDK) | gRPC used internally by SDK clients |
| **Azure OpenAI** | No | REST-only, same as OpenAI |
| **Together AI** | No | REST/SSE |
| **vLLM / TGI** | Partial | vLLM has an experimental gRPC serving option; TGI is REST-only |
| **Triton Inference Server** | Yes | Native gRPC endpoint for model inference |
| **TensorFlow Serving** | Yes | Native gRPC endpoint with `Predict`/`Classify` RPCs |
| **Ray Serve** | Yes | Supports gRPC deployment via `grpc_servicer` |
| **Custom LLM (self-hosted)** | Optional | Depends on inference framework (Triton, TFServing, custom) |

### When gRPC is used for AI

gRPC is primarily used in **internal service-to-service** AI pipelines, not for end-user-facing
chat completions:

- **Model serving**: TensorFlow Serving, Triton, TorchServe expose gRPC `Predict` RPCs for
  high-throughput inference (protobuf-encoded tensors, not chat messages)
- **Microservice orchestration**: Internal AI pipelines where one service calls another's
  gRPC endpoint for embedding/reranking
- **Streaming inference**: Bidirectional streaming for real-time transcription or token-by-token
  generation (gRPC streaming can be more efficient than SSE)

The most common public AI API surface remains REST/SSE. gRPC is mostly relevant for
**enterprise private deployments** where models are served on Triton/TFServing behind a
corporate firewall.

## 3. Feasibility: Can We Wrap gRPC Calls Too?

**Yes**, the same concept applies. The core masking/unmasking logic operates on the semantic
content of messages, not on the transport protocol. The difference is in the interception layer:

```
Current (HTTP):
  HTTP JSON payload  -->  parse JSON  -->  mask content  -->  forward HTTP  -->  unmask response

gRPC:
  gRPC proto message  -->  decode proto  -->  mask content  -->  forward gRPC  -->  unmask response
```

The `mask_engine` and `unmask` functions are transport-agnostic -- they operate on plain text
strings. The work is in:

1. **Intercepting** the gRPC call (before it hits the upstream server)
2. **Decoding** the protobuf message to extract text fields
3. **Re-encoding** after masking
4. **Forwarding** the modified message to the upstream gRPC server
5. **Reverse** the process on the response

## 4. Implementation Approaches

### Option A: gRPC Interceptor Pattern

Use `grpc.aio.ServerInterceptor` / `grpc.aio.UnaryUnaryClientInterceptor` to intercept
proto messages flowing through a gRPC channel.

- **How it works**: Register an interceptor on the gRPC channel that inspects every
  `UnaryUnary` or `UnaryStream` call. For requests, decode the proto, locate string
  fields (by known field paths or reflection), pass them through the mask engine,
  re-encode and forward. Same for responses.
- **Strength**: Minimal infrastructure; no separate proxy process.
- **Weakness**: Requires designing or knowing the exact proto schema. Different AI
  models have different proto definitions. Schema-aware mapping is fragile.
- **Effort**: 3-5 days for a working prototype with a single known proto schema.
  Additional 2-3 days per new schema.

```
Client  -->  gRPC Interceptor  -->  Decode Proto  -->  Mask Strings  -->  Forward to Server
                     ^                                                        |
                     |----------  Unmask Response  <---  Encode Proto  <------+
```

### Option B: gRPC Proxy/Gateway (Envoy + WASM)

Deploy a sidecar proxy (Envoy) in front of the gRPC server. Use a WASM filter to
intercept and modify proto payloads.

- **How it works**: Envoy terminates the client gRPC connection, applies a WASM
  filter that reads/modifies proto fields, then forwards to the upstream gRPC server.
- **Strength**: Battle-tested at scale; hot-reloadable WASM filters; no application
  changes needed.
- **Weakness**: Significant operational complexity (Envoy control plane, WASM SDK).
  Debugging proto mutations in WASM is difficult. Overkill for most deployments.
- **Effort**: 2-3 weeks for a production-grade WASM filter + Envoy config.
  Requires Rust/C++ WASM SDK knowledge.

```
Client  -->  Envoy (WASM filter: mask/unmask)  -->  Upstream gRPC Server
```

### Option C: Sidecar gRPC Decode/Re-encode

Run a lightweight gRPC server alongside the upstream that accepts gRPC, decodes the
protobuf to JSON, runs the existing masking pipeline, re-encodes to protobuf, and
forwards to the real server.

- **How it works**: A thin Python service using `grpcio` + `protobuf` that acts as a
  transparent gRPC intermediary. The client is configured to point at this service
  instead of the real upstream. The service uses proto reflection (`google.protobuf`)
  or a compiled `.proto` file to know which fields contain text.
- **Strength**: Reuses the existing Python masking pipeline directly. No new language.
  Proto reflection enables handling unknown schemas at runtime.
- **Weakness**: Adds a network hop. Latency overhead from decode/re-encode. Must
  manage proto file compatibility.
- **Effort**: 4-6 days for a functional prototype using proto reflection.
  1-2 weeks with proper error handling, streaming support, and tests.

```
Client  -->  Sidecar (decode -> mask -> encode)  -->  Upstream gRPC Server
                     ^--- existing mask_engine ---^
```

## 5. Work Estimate Summary

| Option | Approach | Effort | Complexity | Production Readiness |
|--------|----------|--------|-----------|---------------------|
| **A** | gRPC Interceptor | 5-8 days | Medium | Medium (schema coupling) |
| **B** | Envoy + WASM | 2-3 weeks | High | High (but heavy ops) |
| **C** | Sidecar decode/re-encode | 1-2 weeks | Medium | Medium (extra hop) |

All estimates assume:
- Single known proto schema (e.g., Triton `ModelInferRequest`)
- Text-based string masking only (no tensors, no embeddings)
- Non-streaming unary calls (streaming adds 50%+ effort)

## 6. Recommendation

**Do not implement gRPC support at this time.** Specifically:

1. **No public AI API uses gRPC for chat**. OpenAI, Anthropic, and the vast majority of
   LLM API consumers use REST/SSE. Adding gRPC support would serve a near-zero subset of
   the current user base.

2. **Primary gRPC use case is self-hosted**. The users who need gRPC are enterprises
   running Triton/TFServing internally. These deployments typically have their own PII
   pipeline or operate on non-text data (embeddings, tensors).

3. **The existing HTTP proxy covers 99%+ of real-world usage**. The `mask_engine` is
   already transport-agnostic, so when gRPC demand materializes, Option C (sidecar) can
   be built quickly by reusing the existing code.

4. **Maintenance cost is real**. Every proto schema change requires updates to the
   masking layer. There is no standard proto definition for "chat completions" across
   different gRPC-based AI deployments.

### When to Revisit

- A user/customer explicitly requests gRPC masking support
- A major AI provider ships a gRPC-first chat API
- An enterprise deployment requires masking for a Triton/TFServing pipeline with
  text-based models

At that point, Option C (sidecar) is the recommended starting point because it reuses
the existing Python codebase with minimal new infrastructure.

---

**Conclusion**: gRPC support is technically feasible but currently unnecessary.
The existing HTTP proxy covers the overwhelming majority of AI API usage patterns.
Revisit when there is documented user demand.
