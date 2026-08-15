# AI Privacy Gateway — Knowledge Base (English)

> Version: v2.0.3 | License: PolyForm Shield 1.0.0 | Repo: github.com/gunxueqiu6/ai-privacy-gateway

---

## Product Overview

AI Privacy Gateway is a **locally-deployed, multi-jurisdiction AI data compliance gateway** that sits
between AI clients and LLM APIs. It detects and masks sensitive data (PII) before it leaves your
machine. Point your AI client's `base_url` at the self-hosted gateway and you get privacy protection
with zero code changes.

Core value: PII is masked before it leaves your network, so the LLM provider never sees raw sensitive
data. Masked mappings are stored in a local AES-256-GCM encrypted vault, restorable by authorized
users. The project uses the PolyForm Shield license (free for non-commercial use; commercial use
requires a license key).

## Entity Detection (Data-Driven)

The gateway uses a data-driven entity catalog (`entity_catalog.json`) to detect **26 entity types**:

| Entity | Example | Method |
|--------|---------|--------|
| Phone | 13800138000 | regex + NER |
| Email | user@example.com | regex |
| China ID Card | 110101199001011234 | regex + checksum |
| Bank Card | 4111111111111111 | regex + Luhn |
| Unified Social Credit Code | 91310000306245892U | regex |
| Passport | E12345678 | regex |
| HK/Macau Permit | C12345678 | regex |
| Taiwan Permit | L12345678 | regex |
| Taiwan ID | A123456789 | regex |
| Org Code | 12345678-X | regex |
| Person Name | 张三 | NER (opt-in) |
| Location | 北京市海淀区 | NER (opt-in) |
| Organization | 阿里巴巴集团 | NER (opt-in) |
| Plate | 京A12345 / 京AD12345 | regex |
| IP / URL / Date / Amount / Postcode | ... | regex |
| API Key | sk-... / AKIA... / ghp_... | regex |
| Custom | user-defined | regex + keyword |

The regex engine adds <1ms average latency. Chinese NER (person/location/organization) is rule-based
and **disabled by default** to avoid false positives on common words; enable per-entity via the catalog.

## Compliance Classification

Each entity is tagged with a compliance class: `personal_info`, `important_data`, or `core_data`
(aligned with PIPL/DSL classification). Each request's highest-sensitivity tag is stored in the
vault for data-export assessment.

## Audit & Evidence

- **Per-decision audit**: every request records `team_id`, `client_ip`, `user_agent`, upstream URL,
  model name, content hash, and per-entity detail (value hash only, never plaintext).
- **Tamper-evident**: SHA-256 hash chaining over the audit log.
- **Signed evidence export**: `GET /admin/audit/export` returns the audit log with an Ed25519
  signature + integrity check — suitable for GDPR Art. 30, EU AI Act Art. 12, NIST AI RMF, and PIPL
  cross-border transfer records.

## License & Monetization

- **Lite**: free for non-commercial use (PolyForm Shield).
- **Team / Enterprise**: offline Ed25519 license key (`scripts/issue_license.py`), paid by seats/teams/tier.
  Unlocks audit export, long retention (~10 years vs 7 days), and multi-team.

## Deployment

- Docker: `docker run -d --name ai-privacy-gw -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite`
- pip, Windows/macOS one-click installers, Kubernetes sidecar, browser extension.
- Multi-upstream load balancing (OpenAI / Anthropic / DeepSeek), SSE streaming with round-trip restore.

---

*Maintained by the AI Privacy Gateway project. Contact enterprise@privacygw.dev for licensing.*
