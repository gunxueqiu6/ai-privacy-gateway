# OpenAPI Documentation Integration

> Date: 2026-06-26
> Scope: How to export and host the FastAPI-generated OpenAPI spec for the AI Privacy Gateway

## 1. Exporting the OpenAPI Spec

FastAPI auto-generates an OpenAPI 3.1 spec based on route definitions, Pydantic models, and
docstrings. It is served at two endpoints at runtime:

- `/docs` -- Swagger UI interactive documentation
- `/openapi.json` -- Raw OpenAPI JSON

### One-time Export

Run this from the project root (`ai数据隐私隔离/`):

```bash
cd /app
python scripts/export_openapi.py
```

This writes the spec to `website-astro/public/openapi.json` so it can be served as a
static asset on the marketing website.

### Automated Export (CI)

Add a step in the deployment pipeline to regenerate the spec on every release:

```yaml
# GitHub Actions snippet
- name: Export OpenAPI spec
  run: python scripts/export_openapi.py

- name: Deploy website
  run: |
    cd website-astro
    npm run build
    npx wrangler pages deploy dist/
```

The export script is intentionally kept simple -- it imports the FastAPI `app` object
from `main.py` and calls `app.openapi()`. No server needs to be running.

## 2. Options for Hosting Public API Docs

### Option A: Static Files on the Astro Website (Recommended)

Export the spec and render it with Swagger UI or Redoc as a static page on the existing
website at `/docs/api`.

**How it works**:
1. `scripts/export_openapi.py` writes `website-astro/public/openapi.json`
2. Create an Astro page at `website-astro/src/pages/docs/api.astro` that embeds Swagger UI
   or Redoc
3. Deploy the website normally -- the OpenAPI spec is a static asset

**Pros**:
- Same domain, same deployment pipeline
- No extra infrastructure
- Works with Cloudflare Pages, Vercel, or any static host
- The spec file in `public/` is served as-is (no build step needed for it)

**Cons**:
- Spec must be regenerated when routes change
- Interactive "try it out" requires CORS configuration or a proxy (the gateway is
  typically local-only, so "try it out" won't work unless the user has a public
  gateway instance)

### Option B: Subdomain (api-docs.privacygw.pages.dev)

Host the Swagger UI on a separate Cloudflare Pages project.

**How it works**:
1. Create a separate Pages project tied to `api-docs.privacygw.pages.dev`
2. The build step exports the OpenAPI spec and builds a static Swagger UI/Redoc site
3. Automate with the same CI pipeline

**Pros**:
- Clean separation from the marketing site
- Can add versioned docs (`v1.api-docs.privacygw.pages.dev`, `v2...`)
- Independent deploy cadence

**Cons**:
- Extra project to maintain
- Domain fragmentation for users
- Still can't "try it out" without a public gateway

### Option C: Postman Public Workspace / SwaggerHub

Upload the spec to a third-party API documentation platform.

**How it works**:
1. Export `openapi.json`
2. Import into Postman (public workspace) or SwaggerHub
3. These platforms host the interactive docs and optionally provide "try it out" with
   their own API client infrastructure

**Pros**:
- Zero hosting infrastructure
- Built-in "try it out" with environment variables for API keys
- Collection sharing (Postman) for team workflows
- Version history (SwaggerHub)

**Cons**:
- Third-party dependency
- Spec must be manually uploaded or synced via CI
- Less control over branding/UX
- Postman free tier has limitations on public workspaces

## 3. Embedding Swagger UI or Redoc in Astro

### Swagger UI

Create `website-astro/src/pages/docs/api.astro`:

```astro
---
// File: src/pages/docs/api.astro
// Static page for interactive API docs
---

<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>API Reference - AI Privacy Gateway</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>
      html { background: #1e1e2e; }
      body { margin: 0; padding: 0; }
    </style>
  </head>
  <body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
      SwaggerUIBundle({
        url: '/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset,
        ],
        layout: 'StandaloneLayout',
      });
    </script>
  </body>
</html>
```

### Redoc (lighter alternative)

Create `website-astro/src/pages/docs/api.astro`:

```astro
---
---

<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>API Reference - AI Privacy Gateway</title>
    <link href="https://fonts.googleapis.com/css?family=Inter:400,600" rel="stylesheet" />
  </head>
  <body>
    <div id="redoc-container"></div>
    <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
    <script>
      Redoc.init('/openapi.json', {
        scrollYOffset: 0,
        hideDownloadButton: false,
        expandResponses: '200,201',
      }, document.getElementById('redoc-container'));
    </script>
  </body>
</html>
```

### Adding a Nav Link

To link the docs from the website navigation, add a menu item pointing to `/docs/api` in
the relevant navigation component (typically in `website-astro/src/components/`).

## 4. Important Caveats

### "Try it out" Requires CORS

Swagger UI's interactive test feature sends requests directly to the API server from the
browser. This requires the gateway to include the website's origin in its CORS allowlist.

The current CORS config in `main.py` only allows `localhost:9999`:

```python
allow_origins=["http://localhost:9999", "http://127.0.0.1:9999"],
```

To enable cross-origin requests from the production website, add the production origin:

```python
allow_origins=[
    "http://localhost:9999",
    "http://127.0.0.1:9999",
    "https://privacygw.pages.dev",
],
```

### The API is Not Public

The gateway is designed to run locally (localhost:9999). The OpenAPI docs hosted on the
website serve as **reference documentation only**. Users cannot call their local gateway
from the website without:

1. Exposing the gateway publicly (not recommended)
2. Configuring a tunnel (ngrok, Cloudflare Tunnel)
3. Using the docs as a reference and calling the gateway from their local environment

### Spec Staleness

The exported `openapi.json` is a snapshot. It must be regenerated when:
- New routes are added
- Request/response models change
- Route descriptions or tags are updated

A CI step or pre-commit hook is the best way to keep it in sync.
