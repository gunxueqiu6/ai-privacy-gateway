# Changelog

All notable changes to AI Privacy Gateway are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- Multi-language translations for the website (i18n support)
- Japanese and Korean entity detection patterns

### Fixed

- CI branch trigger alignment (main -> master)
- Node.js CI version bump to 22 for Astro v6 compatibility
- Test timeout configuration and JS SDK jest module compatibility

---

## [2.0.0] - 2026-06-21

### Added

- **AES-256-GCM vault encryption** — PII mappings encrypted at rest in SQLite with automatic key management
- **Multi-upstream load balancer** — round-robin, random, and least-connections strategies for distributing requests across multiple LLM providers
- **Pub/sub audit event bus** — real-time audit events with JSON and syslog output support
- **One-click installers** — `install.bat` / `install.sh` with auto-setup, venv creation, secret generation, and desktop shortcuts
- **iOS Network Extension** — `NEFilterDataProvider` with local PII masking for iOS/macOS network traffic
- **Android VPN packet processor** — HTTP interception and PII masking for Android VPN traffic
- **Website v2 redesign** — dark theme, glass morphism, before/after PII demo, bento grid layout
- **Rate limiting** on proxy endpoint to prevent abuse
- **Multi-engine search console verification** meta tags for SEO

### Fixed

- SSE stream double-prefix — responses no longer prefix masked content twice
- Header case-sensitivity — proxy correctly forwards headers regardless of casing
- SQLite `ON CONFLICT` clause syntax for upsert operations
- Placeholder regex edge cases in masking engine
- PyInstaller executable path resolution for static files and `.env`
- Auto-generated secret persistence across server restarts
- GBK encoding errors on Windows when reading/writing config files
- Browser extension: notifications permission request, custom keyword endpoint
- SDK authentication header — changed from `X-API-Key` to `Authorization: Bearer`
- iOS SDK: compile errors, keychain migration, thread safety issues
- Android SDK: thread-safe singleton pattern, encrypted shared preferences, foreground service lifecycle
- Flutter SDK: bankcard field mapping, model serialization, equality checks
- Batch mask endpoint: added type and position fields to entity response
- Astro v6 migration: content collection loader using glob pattern, `.id` slugs
- Docker Compose: removed `env_file` directive, fixed startup script description
- Download page updated to point to v2.0.0 release assets

### Changed

- Refactored custom regex routes — deduplicated redundant code, improved masking accuracy
- Stripped project to MIT-licensed Lite edition only (removed Pro/Enterprise tier)

---

## [1.1.0] - 2026-06-08

### Added

- **NER entity recognition engine** — machine learning-based PII detection complementing regex engine
- **AC automaton** — Rust PyO3 native module for fast multi-pattern matching across 1000+ patterns
- **JavaScript/TypeScript SDK** — full-featured SDK with browser and Node.js support
- **Chrome/Edge browser extension** — popup UI, per-site toggle, custom keyword management
- **Flutter/Dart SDK** — cross-platform mobile SDK with platform-specific storage adapters
- **Android SDK** — Kotlin SDK with EncryptedSharedPreferences and foreground service
- **iOS SDK** — Swift SDK with Keychain storage and Network Extension integration
- **Website inner pages redesign** — DocsLayout, AI-feel dark theme, unified navigation
- **All 13 entity types enabled** in admin panel with per-type toggle
- **Security baseline**: bcrypt password hashing, rate limiting, login lockout, secure HTTP headers
- **Ops platform**: deployment tracking, enterprise API key management, Prometheus metrics endpoint
- **PayPal Live payment integration** for Pro/Enterprise tiers
- **Cloudflare Pages auto-deploy** CI workflow for the website
- **Custom sensitive words** CRUD in admin dashboard
- **Docker images** automatically pushed to GitHub Container Registry (GHCR)
- Multi-engine search console verification meta tags
- QQ and Telegram contact info to website footer

### Fixed

- Comprehensive security audit — 20 vulnerabilities resolved (XSS, CSRF, input validation, error leakage)
- NER engine reflection in `/api/entities` endpoint
- XSS vulnerabilities in admin panel error messages and template rendering
- JS SDK test suite — all 20 tests passing against actual GatewayClient API
- macOS download filename mismatch between CI artifact and website link
- Deprecated `datetime.utcnow()` replaced with `datetime.now(UTC)` throughout
- Bandit security scan — zero MEDIUM or HIGH findings
- Type annotation gaps across all public interfaces
- Rollup plugin compatibility — migrated to `@rollup/plugin-typescript`
- Website version number consistency (v2.0 -> v1.1.0) across pages
- Docker deployment instructions aligned with GitHub Release assets
- Pricing page — removed fake email addresses, replaced with real QQ/TG contacts
- Website metrics updated from placeholder to verified real numbers

### Changed

- Open Core boundary enforced — Pro/Enterprise admin panel removed from public repository
- Gitignore expanded for Rust targets, JS coverage artifacts, temp/debug scripts
- README and website documentation synced across all deployment methods

---

## [1.0.1] - 2026-06-07

### Fixed

- Missing Kubernetes ServiceAccount template in deployment manifests
- GHCR CI build — image tagging and push steps corrected
- `VersionType` crash in test environment configurations
- Pricing page rendering on test environments
- Docker deployment failures with `.env` configuration

---

## [1.0.0] - 2026-06-07

### Added

- **Core PII masking engine** — regex-based detection for 14+ entity types including phone numbers, ID cards, emails, bank cards, names, locations, organizations, plate numbers, IP addresses, URLs, dates, amounts, postcodes, and API keys
- **HTTP reverse proxy core** — intercepts and forwards AI API requests (OpenAI-compatible) with transparent PII masking
- **FastAPI entry point** — `main.py` with startup/shutdown lifecycle, configuration loading
- **SSE streaming buffer** — real-time masking for Server-Sent Events streams
- **Admin dashboard** — real-time interception statistics, trend charts, entity type management
- **Configuration management** — environment variable-based config with `.env` file loading
- **SQLite database** — encrypted vault for PII mapping storage with TTL-based cleanup
- **AES-CBC encryption** for PII mapping storage in the vault
- **Entity type detection**: phone, ID card (Chinese), email, bank card (Luhn check), person name (Chinese + English), location, organization, plate number, IP address, URL, date, amount, postcode, API key
- **API endpoints**: `/api/mask`, `/api/restore`, `/api/mask/batch`, `/api/entities`, `/api/stats`
- **Dockerfile** and **docker-compose.yml** for containerized deployment
- **PyInstaller packaging** — `PrivacyGateway.spec` for standalone executable builds
- `robots.txt` and SEO basics for website
- MIT License

### Changed

- Initial project structure and architecture established

---

## [0.1.0] - 2026-06-07

### Added

- Initial prototype release
- Basic proxy functionality proof-of-concept
- Core project scaffolding and build system

---

## Version Index

- **Unreleased**: Current development on `master` branch
- **[2.0.0]**: Vault encryption, load balancer, audit bus, installers, mobile SDKs, website v2
- **[1.1.0]**: NER engine, AC automaton, all SDKs, security hardening, CI/CD automation
- **[1.0.1]**: Bug fixes, CI repairs, deployment polish
- **[1.0.0]**: First stable release — core proxy, masking engine, admin dashboard
- **[0.1.0]**: Initial prototype

[Unreleased]: https://github.com/gunxueqiu6/ai-privacy-gateway/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/gunxueqiu6/ai-privacy-gateway/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/gunxueqiu6/ai-privacy-gateway/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/gunxueqiu6/ai-privacy-gateway/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/gunxueqiu6/ai-privacy-gateway/compare/v0.1.0...v1.0.0
[0.1.0]: https://github.com/gunxueqiu6/ai-privacy-gateway/releases/tag/v0.1.0
