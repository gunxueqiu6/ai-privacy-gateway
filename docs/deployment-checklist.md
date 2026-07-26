# Deployment Readiness Checklist

> Run through this before every production deployment.

## Pre-Deploy

### Code Quality
- [ ] All tests pass: `pytest tests/ -x`
- [ ] Bandit security scan clean: `bandit -r . -ll`
- [ ] No hardcoded secrets: `grep -r "sk-\|ghp_\|AKIA" --include="*.py" | grep -v test | grep -v placeholder`
- [ ] `.env` not in git: `git status | grep -v .env`

### Build
- [ ] PyInstaller builds: `python build.bat` (Windows) / `./build.sh` (Linux)
- [ ] Docker image builds: `docker build -t privacy-gateway .`
- [ ] Website builds: `cd website-astro && npm run build`

### Config
- [ ] `ADMIN_PASSWORD` set (not auto-generated default)
- [ ] `JWT_SECRET` set
- [ ] `VAULT_ENCRYPT_KEY` set
- [ ] `UPSTREAM_API_KEY` configured
- [ ] `LISTEN_PORT` matches firewall rules

## Deploy

### Docker
```bash
docker run -d --name ai-privacy-gw \
  -p 9999:9999 \
  -e ADMIN_PASSWORD=<strong-password> \
  -e JWT_SECRET=<random-64-chars> \
  -e VAULT_ENCRYPT_KEY=<random-32-bytes> \
  -v ./vault_data:/app/vault_data \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

### Systemd
```bash
sudo cp ai-privacy-gateway.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ai-privacy-gateway
```

## Post-Deploy Verification

- [ ] Health check: `curl http://localhost:9999/health` → `{"status": "healthy"}`
- [ ] Proxy test: Send a test request with `curl -X POST http://localhost:9999/v1/chat/completions`
- [ ] Admin dashboard: Open `http://localhost:9999/admin` — login works
- [ ] Masking test: `curl -X POST http://localhost:9999/api/mask -d '{"text":"My phone is 13812345678"}'`
- [ ] Metrics exposed: `curl http://localhost:9999/metrics` returns Prometheus data
- [ ] Rate limiting active: Check `X-RateLimit-*` headers

## Rollback

If something goes wrong:
```bash
# Docker
docker stop ai-privacy-gw
docker rm ai-privacy-gw
# Start previous version

# Systemd
sudo systemctl stop ai-privacy-gateway
# Restore previous binary
sudo systemctl start ai-privacy-gateway
```

## Monitoring (First 30 Minutes)

- [ ] Error rate < 1%
- [ ] P99 latency < 100ms
- [ ] Memory < 500MB
- [ ] No crash loops
- [ ] Upstream LLM reachable
