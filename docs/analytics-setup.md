# Analytics & Monitoring Setup

## Cloudflare Web Analytics (Recommended — Free, Privacy-Friendly)

Privacy Gateway and DocTrail are both hosted on Cloudflare Pages. Cloudflare Web Analytics is zero-config and free.

### Enable for Privacy Gateway
1. Go to Cloudflare Dashboard → Web Analytics
2. Add site: `privacygw.pages.dev`
3. Copy the JS snippet
4. Add to `website-astro/src/layouts/Layout.astro` in the `<head>`

### Enable for DocTrail
1. Go to Cloudflare Dashboard → Web Analytics
2. Add site: `doctrail.pages.dev`
3. Copy the JS snippet
4. Add to `frontend/src/app/layout.tsx` in the `<head>`

## Key Events to Track

### Privacy Gateway
```
Page views (all pages)
"Deploy Now" button clicks → /download
"Watch Demo" button clicks → /demo
GitHub link clicks → github.com/gunxueqiu6/ai-privacy-gateway
"Load Sample" clicks on /demo
"Mask" button clicks on /demo
Download button clicks (per platform: Windows/macOS/Docker/pip/Extension)
Language switch events
/docs page dwell time
```

### DocTrail
```
Page views (all pages)
"Free Start" button clicks → /login
Registration completions
First document upload
First tracking link generated
Upgrade to paid plan
```

## Privacy Gateway — Prometheus Metrics (Built-in)

Already exposed at `http://localhost:9999/metrics`:
- `gateway_requests_total` — total proxied requests
- `gateway_request_duration_seconds` — latency histogram
- `gateway_pii_detected_total` — PII entities detected
- `gateway_pii_masked_total` — PII entities masked
- `gateway_errors_total` — error count
- `upstream_health_status` — upstream LLM health

### Grafana Dashboard (Optional)
```bash
# docker-compose.yml addition
grafana:
  image: grafana/grafana:latest
  ports: ["3000:3000"]
  volumes:
    - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
```

## DocTrail — Prometheus Metrics (To Add)

Recommended metrics for DocTrail backend:
- `doctrail_views_total` — total document views
- `doctrail_upload_total` — documents uploaded
- `doctrail_api_duration_seconds` — API latency
- `doctrail_tracking_events_processed` — Redis Stream events consumed

## Weekly Analytics Checklist
- [ ] Check Cloudflare Web Analytics for traffic trends
- [ ] Check GitHub stars/forks trend
- [ ] Review top-performing blog posts
- [ ] Check demo page conversion rate
- [ ] Review search console for new keyword rankings
