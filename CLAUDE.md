# AI Privacy Gateway — AI API 隐私防火墙

> 最后更新: 2026-08-07 | v2.0.2 | 孵化产品 ①

## 职责
AI API的PII掩码反向代理。14+实体类型，<1ms延迟。AES-256-GCM加密保险库。

## 启动
```bash
uvicorn main:app --host 0.0.0.0 --port 9999
```

## 部署
- 网站: privacygw.pages.dev
- VPS license容器: 149.104.12.203
- GitHub Releases + Docker + 浏览器扩展

## 定价
Free + Enterprise ($199-999/月)

## 推广
GEO-SaaS + 分发与截流 负责推广

## 开源/付费隔离（提交前必读）

**免费版开源 + 付费版私有化。** 本目录是免费版 checkout，remote `origin` = 公开仓库，`private` = 私有仓库。

### 付费文件（只进 private，绝不进 origin）
以下文件已被 `.gitignore` 排除，物理隔离到私有仓库：
- `license.py` — Ed25519 离线授权码
- `audit_signer.py` — 审计链签名
- `routers/enterprise.py` — 企业端点（`/admin/audit/export`、`/admin/license`）

### 提交规则
1. 提交前确认上面 3 个文件没有被 `git add`（已被 gitignore，正常不会）。
2. 新的付费功能写在 `routers/enterprise.py` 或独立新文件，**不要写进免费版已有文件**（config.py / routers/admin.py 等）。
3. 公开仓库永远保持「不含付费源码」；`config.tier` 恒为 `"lite"`，license 逻辑不进公开版。
4. 企业版维护在 `E:\projects\ai数据隐私隔离-private`（clone `private` remote）。

### 验证
免费版独立可跑：临时移走 3 个付费文件后 `python -m pytest -q` 应全绿；`register_routers()` 里 enterprise 路由靠 `try/except ImportError` 自动跳过。
