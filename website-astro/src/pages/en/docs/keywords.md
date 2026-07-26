---
layout: ../../../layouts/DocsLayout.astro
title: Custom Keywords
description: Custom sensitive word configuration — add team-specific keywords, regex patterns, bulk import, admin panel operations guide.
canonicalURL: https://privacygw.pages.dev/en/docs/keywords
---

# Custom Keywords

Add team-specific keywords and regex patterns for PII detection.

## Keyword Replacement

Add entries to `vault_data/keywords.txt` in format: `original:replacement_label`

```text
# Internal sensitive terms
Shanghai R&D Center:LOCATION_RD
Competitor X Inc:COMPETITOR_A
Key Client Alpha:VIP_CLIENT

# Internal project codenames
Project Phoenix:PROJECT_PHOENIX
Project Dragon:PROJECT_DRAGON
```

Restart the gateway to apply changes.

## Regex Patterns

Add custom regex patterns in `vault_data/patterns.json`:

```json
{
  "custom": [
    {
      "name": "Employee ID",
      "pattern": "EMP\\d{6}",
      "replacement": "[VAULT_EMP_ID_{id}]"
    },
    {
      "name": "IP Address",
      "pattern": "\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}",
      "replacement": "[VAULT_IP_{id}]"
    },
    {
      "name": "License Plate (China)",
      "pattern": "[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤川青藏琼宁][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9挂学警港澳]",
      "replacement": "[VAULT_PLATE_{id}]"
    }
  ]
}
```

## Admin Panel Operations

1. Visit `http://localhost:9999/admin`
2. Navigate to "Keyword Management"
3. Add / delete / test keywords
4. Changes take effect immediately — no restart required

## Testing Keywords

```bash
curl -X POST http://localhost:9999/admin/keywords/test \
  -H "Content-Type: application/json" \
  -d '{"text": "Contact Project Phoenix lead John Doe"}'
```

Response:

```json
{
  "matched": ["Project Phoenix"],
  "sanitized": "Contact [VAULT_PROJECT_PHOENIX] lead John Doe"
}
```

## Bulk Import

Import keywords from a CSV file via the admin panel:

```csv
word,replacement,type
Project Phoenix,PROJECT_PHOENIX,keyword
EMP\d{6},EMP_ID,regex
```

## Best Practices

- **Specific is better than broad**: `EMP\d{6}` catches employee IDs; `\w+` catches everything (don't do this)
- **Test before deploying**: Use the test endpoint with real examples
- **Whitelist false positives**: Add exceptions for terms that match patterns but aren't sensitive
- **Review monthly**: Teams change, projects rename — keep rules current

## Next Steps

- [Deployment Guide](/en/docs/deploy) — Production deployment
- [API Reference](/en/docs/api) — Admin API endpoints
- [Architecture](/en/docs/architecture) — How detection works
