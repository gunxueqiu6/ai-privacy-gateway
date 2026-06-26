# Privacy Policy — AI Privacy Gateway Browser Extension

**Last updated:** 2024-03-15

## Overview

The AI Privacy Gateway browser extension ("the Extension") helps protect your
sensitive data when interacting with AI chat platforms (ChatGPT, Claude,
DeepSeek, Kimi, Yuanbao, Doubao). All data processing is performed locally on
your device. **No data is sent to external servers controlled by us.**

## What Data the Extension Processes

### Actively processed data

- **AI prompt text** — The content you type into supported AI chat platforms.
  The Extension reads this text locally to detect and mask sensitive entities
  (phone numbers, email addresses, ID numbers, bank card numbers, etc.) before
  the text is sent to the AI service.
- **AI response text** — The text returned by the AI platform. The Extension may
  read this to offer restoration of masked placeholders.

### Stored data (local only)

- **Gateway connection settings** — The base URL and timeout for your local
  Privacy Gateway instance (stored in `chrome.storage.local`).
- **Custom sensitive words** — Any user-defined keywords you add for additional
  masking (stored in `chrome.storage.local`).
- **Entity detection preferences** — Your toggle settings for which entity types
  to mask (stored in `chrome.storage.local`).

## What Data the Extension Does NOT Collect

The Extension does **not** collect, transmit, or share:

- Personal information (name, email, address, etc.)
- AI prompt content or conversation history
- Usage statistics or analytics
- Telemetry data
- Browser history or bookmarks
- IP address or location data
- Cookies or session data
- Any data for advertising or profiling purposes

## How Data Processing Works

1. When you type or send a message on a supported AI platform, the Extension
   reads the text **locally** in your browser.
2. The text is sent to your **local** Privacy Gateway instance at
   `http://localhost:9999` (or a URL you configure) for PII detection and
   masking.
3. The masked text is then forwarded to the AI service you are using.
4. The entire flow runs on your machine. The Extension has no cloud backend,
   no telemetry endpoint, and no external data processing pipeline.

## Data Retention

- All configuration data is stored locally in `chrome.storage.local`.
- No data is retained on any remote server.
- Uninstalling the Extension removes all locally stored configuration.

## Third-Party Services

The Extension communicates only with:

1. **Your local Privacy Gateway** — at `http://localhost:9999` (configurable).
   This is an open-source service you run yourself.
2. **The AI platform you are using** — the Extension interacts with the page's
   DOM to read and modify text. The masked text is sent to the AI service via
   the normal page flow. The Extension does not independently transmit data to
   the AI platform outside of your intended use.

## Permissions Justification

| Permission | Reason |
|------------|--------|
| `storage` | Save gateway URL, custom words, and entity toggle preferences locally |
| `contextMenus` | Provide right-click "Copy masked version" menu item |
| `activeTab` | Access the active AI platform page to detect and mask text |
| `scripting` | Inject content scripts into supported AI platform pages |
| `clipboardWrite` | Copy masked text to clipboard when using context menu |
| `notifications` | Notify you of masking status and connection state |
| Host permissions | Only granted for supported AI platforms and local gateway |

## Changes to This Policy

We may update this policy as the Extension evolves. Changes will be reflected
in the Extension's version history and this document. Continued use after
changes constitutes acceptance of the updated policy.

## Contact

If you have questions about this privacy policy, please open an issue at:

https://github.com/gunxueqiu6/ai-privacy-gateway/issues

---

**TL;DR:** This extension does everything locally. It does not collect, store,
or transmit your data to any server you do not explicitly control.
