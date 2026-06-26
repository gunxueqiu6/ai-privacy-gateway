# Chrome Web Store — Listing Copy

---

## Title (30 chars max)

**Primary (Chinese):**
AI Privacy Gateway — AI 对话隐私保护插件

**Backup (English):**
AI Privacy Gateway — Protect AI Chat Privacy

---

## Short Description (132 chars max)

**Chinese:**
在 ChatGPT、Claude、DeepSeek、Kimi、豆包中自动检测并脱敏手机号、邮箱、身份证、银行卡等 13+ 种敏感信息。

**English:**
Auto-detect and mask phone numbers, emails, IDs, bank cards, and 10+ more PII types across ChatGPT, Claude, DeepSeek, and other AI platforms.

---

## Detailed Description

### Product Overview

AI Privacy Gateway is a privacy protection browser extension designed for AI
chat interactions. When you converse with ChatGPT, Claude, DeepSeek, Kimi,
Yuanbao, Doubao, or other AI platforms, it automatically detects and replaces
sensitive information in your messages, preventing private data from leaking to
third-party AI services.

Unlike cloud-based privacy tools, all detection and masking runs through your
own local Privacy Gateway instance, keeping your data under your control at
every step.

### Core Features

- **Automatic PII masking** — Detects and replaces 13+ entity types on-the-fly:
  phone numbers, email addresses, ID card numbers, bank card numbers, names,
  addresses, organization names, license plates, IP addresses, URLs, dates,
  monetary amounts, and postal codes.
- **6 supported platforms** — ChatGPT, Claude.ai, DeepSeek, Kimi, Yuanbao,
  Doubao.
- **Real-time entity detection** — Inline highlight badge on supported pages
  shows detected entity count as you type.
- **Right-click masking** — Select text, right-click, and choose "Copy masked
  version" to get a sanitized clipboard copy.
- **Custom sensitive words** — Add organization- or project-specific keywords
  to the detection list via the options page.
- **One-click toggle** — A floating button lets you enable or disable masking
  on any supported page.
- **Fully local processing** — Requires a local or self-hosted Privacy Gateway
  backend. No data leaves your network boundary.

### How to Use

1. Install the extension.
2. **Important:** Start the Privacy Gateway backend service (default:
   `http://localhost:9999`). See the [GitHub repo](https://github.com/gunxueqiu6/ai-privacy-gateway)
   for quick-start instructions.
3. Open any supported AI platform (ChatGPT, Claude, etc.).
4. A floating badge reading "Masking On" appears at the bottom right of the
   page when the extension is active.
5. Type your message and send it as normal — sensitive data is automatically
   replaced with placeholders before reaching the AI.
6. AI responses with masked placeholders can be restored via the gateway's
   restore API.

### Privacy First

- All PII detection and masking runs on your local gateway.
- The extension has **no cloud backend**, **no telemetry**, and **no analytics**.
- Configuration (gateway URL, custom words, entity toggles) is stored in
   `chrome.storage.local` and never transmitted.
- See our full privacy policy at the link below.

### Requires Local Backend Service

This extension requires the open-source
[AI Privacy Gateway](https://github.com/gunxueqiu6/ai-privacy-gateway) backend
to function. The backend is free, open-source (PolyForm Shield / MIT), and can
be deployed via Docker in one command:

```bash
docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

---

## Category

Productivity

## Language

Chinese (Simplified) — primary
English — secondary

---

## Store Assets

### Required Screenshots (1280 x 800 or 640 x 400 PNG)

| # | Screenshot | Content |
|---|------------|---------|
| 1 | **Main demo** | A supported AI chat page (e.g., ChatGPT) showing a message with phone number and email detected. Floating badge shows entity count. |
| 2 | **Masking in action** | Same page after sending — the AI receives masked text with `[PII_PHONE_0001]` placeholders visible in the conversation. |
| 3 | **Right-click menu** | Text selected on any page, context menu showing "Copy masked version" option. |
| 4 | **Options page** | Full options page showing: gateway URL config, entity type toggles, custom sensitive words list. |
| 5 | **Popup overview** | Extension popup showing connection status, masking statistics, and on/off toggle. |

### Promotional Tiles (optional, PNG)

| Size | Purpose | What to show |
|------|---------|--------------|
| 440 x 280 | Small marquee | Logo + tagline on dark background |
| 920 x 680 | Large marquee | Screenshot of masking flow with feature callouts |
| 1400 x 560 | Product marquee | Feature overview with 3 panels (detect → mask → restore) |

### Required Icons (already in `icons/`)

- 16 x 16
- 48 x 48
- 128 x 128

---

## Submission Checklist

### Pre-submit

- [ ] 5 screenshots prepared (1280 x 800 PNG)
- [ ] 128 x 128 icon is clear and legible at small sizes
- [ ] `manifest.json` version matches the release tag
- [ ] Developer email verified in Chrome Web Store dashboard
- [ ] Privacy policy URL points to this repo's
      `sdk/browser-extension/privacy-policy.md`
- [ ] Single-purpose declaration accurate: "PII masking for AI chat platforms"
- [ ] Host permissions are justified in the developer dashboard
- [ ] Offline/local functionality tested without internet

### Post-submit

- [ ] Automated review passed
- [ ] Manual review (can take 1-3 business days)
- [ ] Published — verify from a fresh Chrome profile
