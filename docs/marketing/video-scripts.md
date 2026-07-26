# Video Scripts — AI Privacy Gateway

> 5 video scripts for YouTube (English) and Bilibili (Chinese).
> Format: timestamped sections, narration text, screen overlay, shot descriptions.
> Target audience: developers, tech leads, security engineers.

---

## Video 1: "30秒部署演示 — AI Privacy Gateway"

**Title (EN):** Install an AI Data Firewall in 30 Seconds — Docker Demo
**Title (ZH):** 30秒部署AI数据防火墙，你的ChatGPT/Cursor数据不再裸奔
**Format:** Screen recording + talking head (optional)
**Duration:** 2:30

### Script

| Timestamp | Narration (EN) | Narration (ZH) | Overlay Text | Shot Description |
|-----------|---------------|----------------|--------------|------------------|
| 0:00-0:10 | "When you send a prompt to ChatGPT or Cursor, how many servers does your data pass through before reaching the model?" | "你发送一条提示词给ChatGPT，你的数据在到达模型之前，经过了几个服务器？" | Your data travels through: Your Machine → OpenAI Gateway → Model Server | Split screen: left shows a user typing in ChatGPT, right shows a network route animation with hops |
| 0:10-0:25 | "One? Two? The answer might surprise you. Every phone number, email address, and API key in your prompt lands unmodified on the provider's server." | "一个？两个？答案是：所有数据原封不动地到达了AI服务商的服务器。你的手机号、邮箱、API密钥，每一件都在别人的机器上明文展示。" | PII in prompts: [PHONE] [EMAIL] [API_KEY] — Sent in plaintext | Screen recording of a packet capture showing raw prompt data with PII highlighted in red |
| 0:25-0:45 | "Meet AI Privacy Gateway: an open-source reverse proxy that sits between you and the AI API. It automatically detects 14+ types of sensitive data and masks them before they leave your machine." | "AI Privacy Gateway 是一个开源的反向代理网关，放在你和AI API之间。它能自动识别14种以上的敏感数据，在离开你机器之前就完成脱敏。" | AI Privacy Gateway v2.0 — MIT Licensed — github.com/gunxueqiu6/ai-privacy-gateway | Product logo animation, then architecture diagram showing Client → Gateway (masks PII) → AI API |
| 0:45-1:15 | "Here's the demo. Open your terminal, type three commands: pull the image, run the container, change your API base URL. That's it." | "来看演示。打开终端，三条命令：拉镜像、启动容器、改API地址。完成。" | ```docker pull ghcr.io/...\ndocker run -d --name ai-privacy-gw -p 9999:9999 ...\n# Change base_url to http://localhost:9999``` | Full screen recording of terminal: typing commands, container starting, logs showing "Gateway running on :9999" |
| 1:15-1:50 | "Now watch what happens. I send a prompt with my email and phone number. On the left, the raw request — see the plaintext PII? On the right, what actually reaches the AI provider — everything is masked." | "看效果。我发送一条包含邮箱和手机号的提示词。左边是原始请求——明文敏感数据。右边是实际到达AI服务商的内容——全部脱敏。" | BEFORE → AFTER comparison | Split screen terminal: left shows incoming request with PII in red, right shows outgoing request with [EMAIL_1] [PHONE_1] in green |
| 1:50-2:10 | "The AI responds normally. On the way back, the gateway unmaskes the placeholders so you see your real data. Zero impact on the conversation." | "AI正常回复。返回时网关把占位符恢复成真实数据。你完全感觉不到中间发生了什么。" | Round-trip: Prompt → Mask → AI → Unmask → You | Animation showing: User sends → Gateway masks → AI processes → Gateway unmaskes → User sees original |
| 2:10-2:30 | "30 seconds, zero code changes, works with any OpenAI-compatible API. Star the repo on GitHub, try it yourself. Link in the description." | "30秒，不改一行代码，兼容所有OpenAI兼容的API。GitHub上点个星，自己试试。链接在简介。" | github.com/gunxueqiu6/ai-privacy-gateway | Final screen: repo QR code + "Star on GitHub" CTA button. Text overlay with download links |

### Thumbnail Concept

Split screen: "With Gateway" (green shield, masked data) vs "Without Gateway" (red alert, exposed PII). Text: "Your AI Data Is Leaking."

---

## Video 2: "技术深度解析 — 架构、NER vs 正则、SSE流式处理、性能优化"

**Title (EN):** AI Privacy Gateway: Deep Dive into Architecture, PII Detection, and Performance
**Title (ZH):** 手撕AI数据隐私网关源码：架构、检测引擎、流式处理、性能优化
**Format:** Talking head + code walkthrough + architecture diagrams
**Duration:** 9:00

### Script

| Timestamp | Narration (EN) | Narration (ZH) | Overlay Text | Shot Description |
|-----------|---------------|----------------|--------------|------------------|
| 0:00-0:30 | "Last video I showed you a 30-second deploy. Today we're going deep: how the gateway actually works under the hood." | "上期视频演示了30秒部署。今天来拆源码：这个网关内部到底怎么工作的。" | AI Privacy Gateway — Architecture Deep Dive | Talking head with architecture diagram floating beside |
| 0:30-1:30 | **Module 1: Core Architecture.** "The gateway is a TCP reverse proxy written in Python. It listens on port 9999, intercepts HTTP requests, applies PII masking, then forwards to the upstream AI API. The response goes through the reverse process." | "核心架构：这是一个Python写的TCP反向代理。监听9999端口，拦截HTTP请求，做PII脱敏，然后转发到上游AI API。响应回来时做逆处理。" | Architecture: Client → Proxy (:9999) → Mask Engine → Upstream (OpenAI/Claude) | Animated architecture diagram with data flow arrows. Highlight each component as it's mentioned |
| 1:30-2:00 | "Let's look at the main loop. 150 lines. It parses the HTTP request, runs it through mask_engine, forwards it, gets the response, runs demask, and sends it back to the client." | "看主循环。150行代码。解析HTTP请求 → mask引擎 → 转发 → 收到响应 → demask → 返回给客户端。" | ```python\n# main loop (simplified)\nrequest = parse_http(raw_data)\nmasked = mask_engine.process(request.body)\nresponse = forward_to_upstream(masked)\nresult = demask_engine.process(response)\nreturn result``` | Code walkthrough with highlighting. Main loop function being explained line by line |
| 2:00-3:30 | **Module 2: PII Detection — Regex vs NER.** "The mask engine has two detection strategies. First: regex patterns — fast, deterministic, <1ms. We have 14+ patterns: phone numbers, emails, ID cards, bank cards, API keys, IP addresses, and more." | "PII检测引擎有两种策略。第一：正则匹配——快、确定性强、<1ms。14种以上模式：手机号、邮箱、身份证、银行卡、API密钥、IP地址等等。" | Regex Engine: 14+ patterns, <1ms per request | Animated regex patterns being matched against sample text. Green highlights for matches |
| 3:30-3:50 | "Second: the NER engine. For entity types that regex can't handle well — person names, locations, organizations — we use a fine-tuned BERT model." | "第二：NER引擎。对于正则不好处理的实体类型——人名、地名、组织机构——我们用微调的BERT模型。" | NER Engine: BERT-based, catches names, locations, orgs | Diagram showing BERT model processing text, outputting entity tags |
| 3:50-4:30 | "But wait — NER is slower. We only run it when the user enables 'deep detection' mode. By default we use regex for speed and fall back to NER when regex confidence is low. This hybrid approach keeps p99 latency under 3ms." | "但NER比较慢。我们只在用户开启"深度检测"时才跑它。默认用正则保证速度，正则置信度低时回退到NER。混合策略让p99延迟保持在3ms以内。" | Hybrid Strategy: Regex (fast path) → Low confidence? → NER (deep path) | Flowchart showing decision tree. Performance numbers in callout boxes |
| 4:30-5:15 | **Module 3: SSE Streaming.** "AI APIs stream responses token by token. The gateway can't wait for the full response — it has to process each chunk in real-time. This is the hardest part." | "AI API是流式返回的，一个token一个token地吐。网关不能等完整响应——它必须实时处理每个数据块。这是最难的。" | Challenge: Streaming SSE — process tokens in real-time, no buffering | Animation showing SSE stream: tokens arriving one by one through the gateway |
| 5:15-6:00 | "The solution: a token-level buffer. We accumulate incoming tokens until we have a complete sentence or a pause longer than 100ms. Then we run demask on that buffer. This keeps the streaming feel while still recovering all the original values." | "解决方案：token级缓冲区。积累进来的token直到形成一个完整句子或停顿超过100ms，然后对这个缓冲区做demask。这样既保持流式体验又能恢复所有原始值。" | Token Buffer: Wait for sentence boundary or 100ms pause → Demask → Send | Code showing the stream_buffer.py logic. Animated buffer filling and flushing |
| 6:00-6:30 | "And the masking is applied to the request body before it's sent as chunks. So the AI never sees PII even in streaming mode." | "脱敏在请求发送前就完成了。所以在流式模式下AI也永远看不到PII。" | Mask at request time, demask at response time — never in the middle | Sequence diagram showing request flow |
| 6:30-7:30 | **Module 4: Performance Benchmarks.** "Let's talk numbers. Without NER: p50 is 0.3ms, p99 is 1.1ms. With NER: p50 is 1.2ms, p99 is 2.8ms. That's the full round-trip overhead including both mask and demask." | "看性能数据。不开NER：p50延迟0.3ms，p99延迟1.1ms。开NER：p50是1.2ms，p99是2.8ms。这是完整往返的额外开销。" | Performance: Without NER: p50=0.3ms p99=1.1ms | Animated dashboard showing latency metrics, comparing with/without NER |
| 7:30-8:00 | "Memory footprint: ~45MB idle, ~120MB under load with NER. For comparison, Presidio uses ~800MB with its NLP models." | "内存占用：空闲~45MB，NER负载下~120MB。对比Presidio需要~800MB来跑它的NLP模型。" | Memory: 45MB idle / 120MB (loaded) vs Presidio ~800MB | Bar chart comparing memory usage across tools |
| 8:00-8:30 | "We also benchmarked throughput: 2,500 requests/second on a single core. The bottleneck is almost never the gateway — it's the upstream AI API." | "吞吐量测试：单核2,500请求/秒。瓶颈几乎从来不在网关上——永远是上游AI API。" | Throughput: 2,500 req/s per core | Animated counter showing requests per second |
| 8:30-9:00 | "All these numbers are reproducible. The repo has a benchmark script. Run it yourself. And if you find a faster approach, submit a PR. Link in description." | "所有数据可复现。仓库里有benchmark脚本。自己跑跑看。如果你找到更快的方案，欢迎提PR。链接在简介。" | Reproduce: `python benchmark.py` — GitHub: link | Final screen: repo link, benchmark chart, "Contribute" CTA |

### Thumbnail Concept

Architecture diagram with magnifying glass on "Mask Engine" component. Small performance chart in corner. Text: "AI Privacy Gateway — Full Architecture Deep Dive."

---

## Video 3: "竞品对比评测 — Presidio vs Kiji vs Privacy Gateway"

**Title (EN):** AI Privacy Tools Compared: Presidio vs Kiji vs Privacy Gateway (Benchmarked)
**Title (ZH):** AI数据隐私工具横评：Presidio、Kiji、Privacy Gateway 实测对比
**Format:** Side-by-side screen recordings + benchmark results
**Duration:** 6:30

### Script

| Timestamp | Narration (EN) | Narration (ZH) | Overlay Text | Shot Description |
|-----------|---------------|----------------|--------------|------------------|
| 0:00-0:25 | "You want to protect your AI API data. What are your options? Today I'm deploying three tools side by side and measuring latency, accuracy, and memory." | "你要保护AI API数据安全。有什么选择？今天我把三个工具同时部署一遍，测延迟、准确率和内存占用。" | AI Privacy Tools: Presidio vs Kiji vs Privacy Gateway | Three logos on screen. Talking head intro |
| 0:25-1:00 | **Setup.** "Same machine, same test dataset: 100 prompts with various PII types. Same upstream: OpenAI GPT-4. I measure three things: end-to-end latency, PII detection accuracy, and memory usage." | "相同环境、相同测试集：100条含各种PII类型的提示词。相同上游：OpenAI GPT-4。测三项：端到端延迟、PII检测准确率、内存占用。" | Test Environment: Ubuntu 22.04, 4C/8G, Docker | Screen showing test setup, dataset samples scrolling |
| 1:00-1:45 | **Tool 1: Microsoft Presidio.** "Presidio is Microsoft's PII detection framework. Powerful NLP — but heavyweight. Let's deploy it." | "Presidio是微软的PII检测框架。NLP能力强，但太重了。" | Presidio: pip install presidio-analyzer presidio-anonymizer | Screen recording: pip install (scrolling), docker compose up with postgres. Show memory usage climbing |
| 1:45-2:00 | "Result: ~47 seconds to first request due to model loading. 780MB RAM. Accuracy is good — 92% on our test set — but 15-20ms latency per request." | "结果：首次请求约47秒（模型加载）。内存780MB。准确率不错——92%——但每次请求延迟15-20ms。" | Presidio: 47s cold start, 780MB, 15-20ms latency, 92% accuracy | Benchmark card appearing |
| 2:00-2:30 | **Tool 2: Kiji (by Tensorlake).** "Kiji is lighter — it uses a smaller model. Deploy via Docker Compose with Postgres and indexing." | "Kiji轻一些——用更小的模型。Docker Compose部署，需要Postgres做索引。" | Kiji: docker compose up | Screen recording: docker compose with multiple services. Show config files |
| 2:30-2:50 | "Result: ~15s cold start, 320MB RAM, 88% accuracy, 8-12ms latency. Better than Presidio on resource usage, slightly lower on accuracy." | "结果：~15s冷启动，320MB内存，88%准确率，8-12ms延迟。资源占用比Presidio好，准确率略低。" | Kiji: 15s cold start, 320MB, 8-12ms latency, 88% accuracy | Benchmark card appearing beside Presidio's |
| 2:50-3:30 | **Tool 3: AI Privacy Gateway.** "Our tool. Docker pull, one command. No external dependencies." | "Privacy Gateway。Docker pull，一条命令。零外部依赖。" | Privacy Gateway: docker run | Screen recording: single docker run command, gateway starts in <2s |
| 3:30-3:50 | "Result: <1s cold start, 45MB RAM, 93% accuracy (regex + optional NER), 0.3ms latency without NER. Memory is 17x less than Presidio." | "结果：<1s冷启动，45MB内存，93%准确率（正则+Ner），延迟0.3ms。内存只有Presidio的十七分之一。" | Privacy Gateway: <1s cold start, 45MB, 0.3ms latency, 93% accuracy | Benchmark card appearing. Comparison table builds up |
| 3:50-4:30 | **Comparison Table.** "Here's the side-by-side. Privacy Gateway wins on speed, memory, and cold start. Presidio wins on customization — it has more entity types and pipelines. Kiji is in the middle." | "并排对比。Privacy Gateway在速度、内存和冷启动上赢。Presidio在可定制性上赢——更多实体类型和管道。Kiji在中间。" | | Full comparison table builds on screen with animated bars |
| 4:30-5:00 | **When to use what.** "Use Presidio if you need a full enterprise DLP pipeline with custom NLP models. Use Kiji if you need a managed API. Use Privacy Gateway if you want a lightweight, zero-config proxy for AI APIs specifically." | "什么时候用什么。需要完整的企业DLP管道和自定义NLP模型→Presidio。需要托管API→Kiji。需要一个轻量、零配置、专门为AI API设计的代理→Privacy Gateway。" | Decision Tree: Enterprise DLP → Presidio \| Managed API → Kiji \| AI API Security → Privacy Gateway | Decision tree animation |
| 5:00-5:30 | **Limitations.** "Privacy Gateway is focused on AI API traffic only. It doesn't do batch processing, database scanning, or document redaction. That's by design — it's a specialized tool for a specific problem." | "局限：Privacy Gateway只专注AI API流量。不做批处理、数据库扫描、文档编辑。这是设计选择——专门工具解决专门问题。" | Note: Privacy Gateway is AI-API-specific. Not a general DLP tool. | Honest disclaimer card |
| 5:30-6:00 | **Accuracy Deep Dive.** "Let me show you where each tool fails. Privacy Gateway misses uncommon names and mixed-language contexts. Presidio catches more but at 17x the resource cost." | "来看每个工具在哪失败。Privacy Gateway漏检不常见人名和中英混杂语境。Presidio抓得多但代价是17倍的资源。" | False Negatives: Privacy Gateway misses → uncommon names. Presidio catches → at 17x cost | Side-by-side: same prompt with missed entities highlighted in yellow |
| 6:00-6:30 | "Bottom line: if you're a team using AI APIs and want instant protection with zero ops overhead, Privacy Gateway is the sweet spot. Links to all three tools in the description. Run your own benchmarks." | "总结：如果你是使用AI API的团队，想要零运维开销的即时保护，Privacy Gateway是甜点位置。三个工具的链接都在简介。自己跑跑基准测试。" | github.com/gunxueqiu6/ai-privacy-gateway | Final comparison summary card. Links to all three repos. "Which one fits your use case?" CTA |

### Thumbnail Concept

Three tools side by side with giant numbers: latency (0.3ms vs 15ms vs 8ms), memory (45MB vs 780MB vs 320MB). Text: "AI Privacy Tools COMPARED."

---

## Video 4: "企业场景实战 — 500人团队统一管控AI API数据安全"

**Title (EN):** How a 500-Person Company Uses AI Privacy Gateway for Enterprise Data Security
**Title (ZH):** 500人团队如何统一管控AI API数据安全 — 企业落地实战
**Format:** Case study / whiteboard animation + architecture walkthrough
**Duration:** 5:30

### Script

| Timestamp | Narration (EN) | Narration (ZH) | Overlay Text | Shot Description |
|-----------|---------------|----------------|--------------|------------------|
| 0:00-0:20 | "A fintech company with 500 employees. Every team uses AI — engineers use Cursor, support uses ChatGPT, marketing uses Claude, analysts use DeepSeek. No one knows what data is going where." | "一家500人的金融科技公司。每个团队都在用AI——工程师用Cursor，客服用ChatGPT，市场用Claude，分析师用DeepSeek。没人知道什么数据去了哪里。" | The Problem: Shadow AI in a 500-person company | Animated office with different teams illustrated, each using different AI tools. Data streams flying out the roof |
| 0:20-0:40 | "Here's the scenario: support team pastes a customer's bank statement into ChatGPT to help debug an issue. That statement goes to OpenAI's servers in plaintext. The customer's PII — account numbers, transactions — all exposed." | "场景：客服把客户银行流水粘贴到ChatGPT来排查问题。那份流水明文发到了OpenAI的服务器。客户的账号、交易记录全部暴露。" | Incident: Customer bank statement → ChatGPT → Exposed | Animated: support agent copies bank statement → ChatGPT sends → alert icon |
| 0:40-1:15 | "The solution: deploy a company-wide AI Privacy Gateway. One Docker container on internal infrastructure. All AI API traffic routes through it. Central policy, centralized audit logging." | "解决方案：部署公司级AI Privacy Gateway。内部基础设施上一个Docker容器。所有AI API流量经过它。统一策略、统一审计日志。" | Architecture: Employee → Company Gateway → AI APIs | Architecture diagram: multiple employee laptops → central gateway (with shield icon) → OpenAI/Anthropic/DeepSeek |
| 1:15-1:45 | "Setup takes one afternoon. Deploy the gateway with Docker Compose, add the audit module, configure allowed upstreams. Each team just changes their API base URL." | "部署一个下午搞定。用Docker Compose部署网关、添加审计模块、配置允许的上游。每个团队只需要改API base URL。" | Setup: Docker Compose → Configure Upstreams → Point Teams to Gateway | Screen recording of deploying with yaml config, teams receiving instructions |
| 1:45-2:15 | **Audit Trail.** "Every AI API call is logged — who sent it, what tool they used, which PII types were detected and masked. The gateway has a pub/sub audit bus that feeds into the company's SIEM." | "审计日志：每一次AI API调用都被记录——谁发的、用什么工具、检测到和脱敏了哪些PII类型。网关内置了发布/订阅审计总线，对接公司的SIEM。" | Audit Log: User | Tool | PII Types Detected | Action | Dashboard showing audit log entries scrolling in real-time. Filters by team, tool, PII type |
| 2:15-2:45 | **Policy Enforcement.** "The compliance team sets a single policy: mask all PII before it reaches any AI API. The gateway enforces it uniformly. No more relying on individual employees to 'be careful'." | "策略执行：合规团队设置一条策略：所有PII到达AI API前必须脱敏。网关统一执行。不再依赖员工个人"小心一点"。" | Policy: Mask ALL PII on ALL AI API calls — Enforced by Gateway | Policy config screen: dropdown showing all PII types, all toggled to "MASK" |
| 2:45-3:15 | **Zero Trust for AI.** "This is Zero Trust applied to AI. The gateway assumes no API call is safe. Every request is inspected, every response is sanitized. Even internal tools go through the gateway." | "这就是AI版的零信任。网关假设没有API调用是安全的。每个请求都被检查，每个响应都被净化。甚至内部工具也走网关。" | Zero Trust for AI: Verify every request, sanitize every response | Zero Trust diagram: Never Trust, Always Verify with shield in center |
| 3:15-3:45 | **Performance at Scale.** "500 employees making ~10,000 API calls per day. The gateway handles it on a single 4-core machine at ~30% CPU. P99 latency added: 1.2ms. Employees don't notice it exists." | "500人每天约10,000次API调用。网关在单台4核机器上以~30% CPU处理。P99额外延迟：1.2ms。员工完全感觉不到它的存在。" | 500 Users | 10K Calls/Day | 1.2ms P99 Overhead | Dashboard showing: active users, requests/minute, CPU/memory, latency heatmap |
| 3:45-4:15 | **Compliance Wins.** "The company passed their SOC 2 audit on AI data handling. The auditor reviewed the gateway's audit logs instead of interviewing employees about their AI usage." | "合规成果：公司通过了SOC 2中AI数据处理的审计。审计员直接审查网关的审计日志，而不是找员工逐个谈话问AI使用习惯。" | SOC 2: Passed — AI Data Handling Audit | Compliance checklist with green checkmarks. SOC 2 badge |
| 4:15-4:50 | **Rollout Lessons.** "What we learned: start with a pilot team, document the PII types your teams actually encounter, set up the audit dashboard before going live, and have a rollback plan. The actual rollout took 3 days for 500 people." | "落地经验：从小团队试点开始、记录各团队实际遇到的PII类型、上线前搭好审计面板、准备回滚方案。实际铺开到500人只用了3天。" | Rollout: Pilot (Day 1) → 3 Teams (Day 2) → All 500 (Day 3) | Timeline graphic showing phased rollout |
| 4:50-5:10 | "The key metric: in the first month, the gateway detected and blocked 1,247 instances of PII that would have been sent to AI APIs. That included 89 API keys, 312 phone numbers, and 46 national ID numbers." | "关键数据：第一个月，网关检测并拦截了1,247个即将发送到AI API的PII实例。包括89个API密钥、312个手机号、46个身份证号。" | Month 1: 1,247 PII incidents blocked — 89 API keys, 312 phones, 46 IDs | Counter animation: each number counting up. Shield icon absorbing red alerts |
| 5:10-5:30 | "One container, one afternoon, zero employee training. That's enterprise AI data security in 2026. Download the enterprise deployment guide — link in description." | "一个容器、一个下午、零员工培训。这就是2026年的企业AI数据安全。企业部署指南在简介链接。" | Start protecting your AI data today → github.com/gunxueqiu6/ai-privacy-gateway | Final screen: "Deploy in Your Company" CTA with link to enterprise docs |

### Thumbnail Concept

Office background with data streams converging into a central shield gateway. Text: "500 People, One Gateway: Enterprise AI Security."

---

## Video 5: "DocTrail预告 — AI数据隐私网关的下一个功能"

**Title (EN):** DocTrail Preview: Track Who Reads Your Contracts (Coming to AI Privacy Gateway)
**Title (ZH):** DocTrail 预告：发出去的合同谁看了、看了多久——AI Privacy Gateway 新功能预览
**Format:** Product teaser / feature preview
**Duration:** 2:00

### Script

| Timestamp | Narration (EN) | Narration (ZH) | Overlay Text | Shot Description |
|-----------|---------------|----------------|--------------|------------------|
| 0:00-0:15 | "You send a contract to a client. Did they read it? What did they read? Did they open page 7 where the pricing clause is?" | "你把合同发给客户。对方看了没有？看了哪些部分？翻到第7页看到定价条款了吗？" | The Problem: You send docs — but did they actually read them? | Animation: email flying from sender, disappearing into a void. Question marks appear |
| 0:15-0:35 | "Today, you have no idea. Maybe you use a read receipt — which tells you nothing about what was read. Maybe you just wait and hope." | "今天，你没有任何办法。也许你会开个已读回执——但它不告诉你对方看了什么。或者你只能干等。" | Current solutions: Read receipts (useless) | Wait and hope (worse) | Split screen: read receipt notification, then empty waiting room with clock ticking |
| 0:35-0:55 | "Introducing DocTrail: an intelligent document tracking system. You send a document, and DocTrail converts it to a trackable web page. You get real-time analytics on exactly what the reader engaged with." | "DocTrail：智能文档追踪系统。你发送一份文档，DocTrail把它转换成可追踪的网页。你能实时看到读者的阅读行为。" | DocTrail: Send → Convert → Track → Analyze | Animation: document entering DocTrail, emerging as web page with analytics dashboard |
| 0:55-1:15 | "Every page view, scroll depth, time spent per section — captured and displayed in a clean dashboard. See exactly which sections got attention and which got skipped." | "每一页的浏览次数、滚动深度、每段停留时间——都在一个干净的仪表盘上。精准看到哪些部分被关注、哪些被跳过。" | Analytics: Page views | Scroll depth | Time per section | Dashboard mockup: heatmap overlay on document showing reading patterns |
| 1:15-1:30 | "Coming as a module to AI Privacy Gateway v2.5. Same philosophy: deploy on your infrastructure. Your documents stay under your control. No third-party tracking servers." | "作为AI Privacy Gateway v2.5的模块推出。同样的理念：部署在你自己的基础设施上。你的文档始终在你的控制下。没有第三方追踪服务器。" | DocTrail: Coming in v2.5 — Self-hosted, private, trackable | Timeline showing v2.0 (current) and v2.5 (DocTrail) with arrow pointing to future |
| 1:30-1:50 | "Use cases: sales teams tracking proposals, legal tracking contracts, HR tracking offer letters, compliance tracking policy acknowledgments." | "使用场景：销售团队追踪方案书、法务追踪合同、HR追踪offer、合规追踪政策确认。" | Use Cases: Sales | Legal | HR | Compliance | Four quick-scene montage: each department using DocTrail |
| 1:50-2:00 | "We're building DocTrail now. Sign up for early access — link in description. Your feedback shapes the roadmap." | "DocTrail正在开发中。登记早期访问——链接在简介。你的反馈决定路线图。" | Early access: [link] — Help shape the roadmap | Sign-up form CTA. "Coming 2026 Q3" |

### Thumbnail Concept

Document with eye icon and analytics graph overlay. Text: "Who Actually Reads Your Contracts? DocTrail Preview."

---

## Production Notes

### Style Guide
- **Tone**: Direct, technical but not academic. Like a senior engineer explaining to a peer.
- **Pacing**: Video 1 fast (demo), Video 2 moderate (deep dive), Video 3 comparative, Video 4 case study, Video 5 teaser.
- **Music**: Video 1/5: upbeat electronic. Video 2: ambient/lo-fi. Video 3/4: minimal background, voice-forward.

### Recommended Equipment
- **Mic**: Any decent USB mic (Blue Yeti, Rode NT-USB, or similar)
- **Screen recording**: OBS Studio at 1440p/60fps
- **Editing**: DaVinci Resolve (free) or CapCut
- **Captions**: Burn in English for YouTube. Upload separate Chinese SRT for Bilibili dual-subtitle.

### Distribution
| Video | YouTube Primary Release | Bilibili Release | Shorts/Clips |
|-------|------------------------|------------------|--------------|
| V1: 30s Demo | Day 1 | Day 1+3 | Docker commands as Short |
| V2: Deep Dive | Day 4 | Day 7 | NER vs Regex comparison clip |
| V3: Comparison | Day 7 | Day 10 | Performance table clip |
| V4: Enterprise | Day 10 | Day 14 | Audit log dashboard clip |
| V5: DocTrail | Day 14 | Day 17 | Teaser as Short |
