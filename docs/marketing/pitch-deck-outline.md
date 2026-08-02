# AI Privacy Gateway — Pitch Deck Outline

> 10 slides for investor presentations
> Target audience: Angel investors, seed-stage VCs, strategic investors in AI/security
> Style: Professional, data-driven, bilingual (Chinese with English terms)

---

## Slide 1: Title Slide

**Headline:**
AI Privacy Gateway — Protect Your Data Before It Reaches AI

**Bullets:**
- 30-second deploy, zero-code proxy for any LLM API (OpenAI, Claude, Gemini, local models)
- Auto-detect, redact, and encrypt PII in real time — no code changes, no infra changes
- Open core (PolyForm Shield) + enterprise licensing, targeting the $4.1B AI data privacy market

**Suggested Visual:**
A clean architecture diagram showing: [User Data] → [AI Privacy Gateway shield icon] → [LLM API]. The shield sits in the middle with a green "Protected" badge. Below, a small inset shows "Before: 'My name is Alice Zhang, SSN: 123-45-6789'" vs "After: 'My name is [REDACTED], SSN: [REDACTED]'".

---

## Slide 2: Problem — Every AI API Call Exposes Sensitive Data

**Headline:**
Your Data Is Leaking Through Every AI Call

**Bullets:**
- Companies send customer PII, financial data, source code, and legal documents to LLM APIs daily — often without any protection layer
- Three unaddressed risks: data leakage to third-party providers, regulatory non-compliance (GDPR / China PIPL / HIPAA), and inability to audit what data left the perimeter
- Result: enterprises stall AI adoption entirely — not because AI doesn't work, but because no safe pipe exists between their data and the model

**Suggested Visual:**
A split-screen comparison. Left side: a chaotic red flow with data icons (credit card, passport, contract) flowing unchecked into an LLM, with warning signs. Right side: the same flow but filtered through a green shield, with only sanitized output reaching the LLM. Below: a quote from a real enterprise CISO ("We can't trust our data going to OpenAI — so we just don't use it").

---

## Slide 3: Solution — 30-Second Deploy, Zero-Code Proxy

**Headline:**
AI Privacy Gateway: Deploy in 30 Seconds, No Code Change

**Bullets:**
- Drop-in proxy: set your API endpoint to `https://your-gateway:8080` — that's it. PII detection, redaction, and encryption happen automatically on every request/response
- 15 PII entity types out of the box (name, phone, email, ID number, address, credit card, bank account, passport, etc.) with real-time SSE streaming support (<10ms latency overhead)
- AES-256-GCM local vault: original data is encrypted before leaving your network; authorized recovery via SDK or CLI

**Suggested Visual:**
A 3-step deployment flow graphic: Step 1 "Docker run" (one-line command) → Step 2 "Set API endpoint" (config screenshot) → Step 3 "Done" (green checkmark + "Protecting 15 PII types"). Below, a timing diagram showing SSE streaming with the tiny latency bubble labeled "<10ms".

---

## Slide 4: Market — $4.1B and Growing at 27.5% CAGR

**Headline:**
Explosive Market, Wide-Open Category

**Bullets:**
- AI data privacy market: **$4.1B** in 2025, growing at **27.5% CAGR** — driven by enterprise AI adoption exploding and global data regulation tightening simultaneously
- No dominant open-source player in this space: incumbents (Skyflow, Nightfall, Private AI) are proprietary, expensive (typically $2K+/mo), and don't offer self-hosted deployment
- Target segments: fintech (transaction data in AI), healthcare (PHI in clinical AI), legal (confidential documents in AI review), BPO/SaaS (customer PII in support AI)

**Suggested Visual:**
A market growth chart (line/area chart) from 2024 to 2030 showing the $4.1B → projected $12B+ trajectory. Overlaid bubbles or callouts showing key drivers: "Enterprise AI adoption +34% YoY", "GDPR fines +50% YoY", "China PIPL enforcement ramping". A small table below showing TAM breakdown by region (NA, EU, APAC).

---

## Slide 5: Product — Architecture and Key Features

**Headline:**
Enterprise-Grade Privacy, Developer-Friendly Experience

**Bullets:**
- **Core engine** (Rust): high-performance PII detection with regex + ML hybrid approach, zero-copy proxy architecture, concurrent stream handling — handles thousands of requests per second on a single VPS
- **5 SDKs + browser extension**: Python, JS/TS, Flutter, Android, iOS SDKs for app-level integration; Chrome/Edge extension for zero-code browser protection
- **Deployment flexibility**: Docker (docker run -p 8080:8080 ai-privacy-gateway), pip install (CLI tool), Windows/macOS installers — works on-prem, VPS, or air-gapped

**Suggested Visual:**
A layered architecture diagram. Bottom layer: "Rust Core Engine" (PII detector, encryptor, proxy). Middle layer: "SDK & Integration Layer" (5 SDK icons + browser extension icon). Top layer: "Deployment" (Docker icon, pip icon, Windows/macOS icons). Arrows showing data flow: API Request → PII Scanner → Redactor → Encryptor → Vault → LLM → Response → De-redactor → Client. Clean, technical, professional.

---

## Slide 6: Traction — Launched and Live

**Headline:**
Shipping Fast, Building in Public

**Bullets:**
- **Product**: v2.0.1 launched June 2026, updated July 2026 — active development with monthly releases
- **Website**: 150-page bilingual site (zh/en) at privacygw.pages.dev, with Dify AI chatbot and llms.txt for AI discoverability
- **GitHub**: github.com/gunxueqiu6/ai-privacy-gateway — PolyForm Shield licensed, accepting contributions
- **Deployment**: VPS backend running, Docker image published, all installers available for download

**Suggested Visual:**
A metrics dashboard mockup showing: "v2.0.1" (version badge), "150 pages" (website), "5 SDKs" (language icons), "Docker | pip | .exe | .dmg" (deployment methods). Below, a timeline graphic showing releases from v1.0.0 (prototype) → v2.0.0 (launch) → v2.0.1 (current). GitHub star count and download stats placeholders.

---

## Slide 7: Competition — We Win on Openness and Price

**Headline:**
Only Open-Core Player in a Proprietary Market

**Bullets:**
- Skyflow ($2K+/mo, proprietary, no self-hosted option) targets large enterprises with full data privacy platform — expensive and overkill for most teams
- Nightfall AI ($0.015/scan, SaaS-only, no streaming support) focused on cloud DLP scanning — good at batch, weak at real-time API proxy
- Private AI (custom pricing, limited SDK languages, no browser extension) offers on-prem deployment but closed-source and limited integration options
- **AI Privacy Gateway differentiators**: only open-core option (PolyForm Shield), 5 SDKs + browser extension, self-hosted deployment with Docker/pip/installers, SSE streaming support, AI-discoverable via llms.txt

**Suggested Visual:**
A competitive comparison matrix with 4 columns (AI Privacy Gateway, Skyflow, Nightfall AI, Private AI) and 8 rows (Pricing model, Open source, Self-hosted, SDK count, SSE streaming, Browser extension, llms.txt support, Free tier). AI Privacy Gateway column highlighted with green checkmarks in most rows. Below: a positioning map (2x2) with X-axis = "Open source → Proprietary", Y-axis = "Simple → Complex". AI Privacy Gateway sits in the top-left sweet spot (open + simple).

---

## Slide 8: Business Model — Open Core, Enterprise Revenue

**Headline:**
Open Core That Actually Makes Business Sense

**Bullets:**
- **PolyForm Shield license** (free for non-commercial): individual developers, academic researchers, internal tools — builds community, brand, and bottom-up adoption. No revenue from this tier, intentionally.
- **Enterprise license** ($199-999/month): commercial use — includes self-hosted deployment, audit logging, RBAC, SSO, priority support. Target buyer: engineering managers / CISO at companies with 10-500 employees using LLM APIs.
- **Revenue model logic**: free tier drives adoption and GitHub visibility → enterprise features create upgrade incentive → community contributions improve the product → network effects strengthen the moat. Target $10K MRR within 12 months.

**Suggested Visual:**
A two-tier pricing card layout. Left card: "Free (PolyForm Shield)" with features (PII detection, all SDKs, browser extension, community support). Right card (highlighted): "Enterprise" with "$199-999/mo" and premium features (RBAC, audit logs, SSO, priority support, compliance certs). Below: a unit economics diagram showing Free → Enterprise conversion funnel with estimated conversion rates. Bottom: "Target: $10K MRR in 12 months."

---

## Slide 9: Roadmap — What's Next

**Headline:**
Roadmap: From Tool to Platform

**Bullets:**
- **Q3 2026**: Enterprise RBAC + audit logging; API v1 stabilization with OpenAPI spec; Compliance certification kickoff (SOC 2 Type I); First 3-5 paid pilot customers onboarded
- **Q4 2026**: SSO integration (SAML/OIDC); Custom PII rules engine (regex + pattern builder); Privacy compliance dashboard ("see what data left your network"); Content marketing engine live
- **Q1 2027**: SOC 2 Type II; Multi-region deployment; Team expansion (hire 1-2 engineers); Expand to Japan/Korea markets

**Suggested Visual:**
A horizontal timeline (Gantt-style) with 3 columns for Q3 2026, Q4 2026, Q1 2027. Each column has 3-4 feature cards stacked vertically. Use color coding: Blue = "Product", Green = "Business", Purple = "Compliance". A dotted line showing the "Series A readiness" checkpoint at Q2 2027 with key metrics targets ($10K MRR, 50+ paid customers, SOC 2, 2K+ GitHub stars).

---

## Slide 10: Ask — Join Us in Building the Privacy Layer for AI

**Headline:**
We're Looking for Partners, Not Just Checks

**Bullets:**
- **Investment**: Seeking $50-100K (or equivalent in USDT/USDC) — flexible on amount, focused on finding the right partner with enterprise SaaS / AI security domain expertise
- **Use of funds**: 40% product development (enterprise features, compliance), 30% go-to-market (developer marketing, content, SEO), 15% infrastructure (VPS, CI/CD, monitoring), 15% legal & compliance (licensing, certifications)
- **What we offer**: First-mover advantage in a $4.1B market with 27.5% CAGR; two products sharing one distribution engine (Privacy Gateway + DocTrail); open-core model with proven community traction; solo founder with full-stack capability and 30+ years engineering experience

**Suggested Visual:**
Left side: A pie chart showing use of funds (Product 40%, Marketing 30%, Infra 15%, Legal 15%). Right side: A "Why Now" checklist — "Market exploding at 27.5% CAGR / No open-source leader / Enterprises desperate for solution / First-mover window open." Bottom: Contact info — GitHub link, website URL. Clean, confident, no clutter.

---

## Appendix: Investor Contact Notes

### Presentation Tips
- **Slide 5 (Product architecture)** and **Slide 7 (Competition)** are the most likely to get deep questions — be ready with live demo or detailed technical walkthrough
- **Slide 8 (Business model)** — investors will challenge the free tier → enterprise conversion logic. Prepare data on comparable open-core companies (GitLab, HashiCorp, Mattermost) conversion benchmarks
- **Slide 3 (Solution)** — the "30-second deploy" claim should be verifiable live. Have a Docker command ready to show

### Key Numbers to Memorize
- $4.1B market, 27.5% CAGR
- v2.0.1, launched June 2026
- 15 PII entity types
- 5 SDKs + browser extension
- $199-999/mo enterprise pricing
- Target: $10K MRR in 12 months

### One-Liner for Elevator Pitch
> "AI Privacy Gateway is the open-core privacy proxy that sits between your data and any LLM — deploy in 30 seconds, protect 15 types of PII, zero code changes. Think of it as Cloudflare for AI data privacy."

---

*AI Privacy Gateway — Your data, your control, even when AI processes it.*
