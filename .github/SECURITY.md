# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.x     | :x:                |
| 0.x     | :x:                |

## Reporting a Vulnerability

**Please do NOT report security vulnerabilities through public GitHub Issues.**

Instead, please report them via email to: **contact@privacygw.dev**

You should receive a response within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity.

## Security Design

AI Privacy Gateway is designed with security-first principles:

- **100% Local**: All data processing happens on your machine. No data leaves your infrastructure unencrypted.
- **Zero Telemetry**: No usage data, no crash reports, no analytics are collected.
- **AES-256-GCM Vault**: PII mappings are encrypted at rest with AES-256-GCM when `VAULT_ENCRYPT_KEY` is configured.
- **Audit Hash Chain**: All audit log entries are linked with SHA-256 hash chain for tamper evidence.
- **PolyForm Shield**: Source code available for audit.

## What to Include in Your Report

- A description of the vulnerability
- Steps to reproduce
- Affected versions
- Any potential mitigations you've identified

## Disclosure Policy

We follow responsible disclosure:

1. Reporter submits vulnerability
2. We acknowledge within 48 hours
3. We validate and develop a fix
4. We release the fix and publish a security advisory
5. Credit is given to the reporter (unless anonymity is requested)

## Security Headers for Deployment

When deploying behind a reverse proxy (Nginx/Caddy), ensure these headers are set:

```nginx
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
```

## Dependencies

- Run `pip-audit` or `safety check` to scan Python dependencies
- Run `npm audit` for the website (`website-astro/`)
- Dependabot is configured for automated updates

---

**Security is not an afterthought — it's the core value proposition of this project.**
