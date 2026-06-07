# AI Privacy Gateway — 推进计划

> 更新: 2026-06-07

## Context

项目在 `D:\projects\ai数据隐私隔离` 已有大量实现。12 份设计文档在 `D:\projects\xmwd\ai数据隐私隔离` 作为参考。目标是梳理现状差距，制定从"基本可用"到"公开发布+商业变现"的推进路线。

---

## 一、实现现状

### 已完成

| 模块 | 文件 | 状态 |
|------|------|------|
| 配置管理 | `config.py` | Lite/Pro/Enterprise 版本切换就绪 |
| 脱敏引擎 | `mask_engine.py`, `ac_engine.py` | 正则 + AC 自动机双引擎 |
| 代理核心 | `gateway_core.py` | 上行脱敏 + 下行还原 + 流式代理 |
| 流缓冲 | `stream_buffer.py` | SSE 分片拼接状态机 |
| 数据库 | `database.py` | SQLite WAL + 映射/关键词/统计/RBAC 表 |
| Redis 存储 | `redis_storage.py` | Enterprise 高并发引擎 |
| 入口 | `main.py` | FastAPI + OpenAI 兼容路由 + 管理 API |
| License | `license_client.py` | ECDH 挑战-应答 + 硬件指纹 + 心跳 |
| License 服务 | `license_server/` | 独立 FastAPI 验证服务 |
| RBAC | `rbac.py` | 超级管理员/审计员/用户三级 |
| 审计日志 | `audit_log.py` | 谁+何时+什么操作+内容预览 |
| 告警 | `alert_manager.py` | 钉钉/飞书/企微 Webhook |
| 衰减管理 | `decay_manager.py` | 7 级渐进式功能衰减 |
| 完整性检查 | `integrity_checker.py`, `rust_src/` | Rust 原生自检模块 |
| 水印 | `watermark.py` | 交付物唯一加密水印 |
| 构建链 | `build_chain.py` | PyArmor → Cython → Nuitka |
| Docker | `Dockerfile`, `Dockerfile.pro`, `Dockerfile.enterprise` | 三版本多阶段构建 |
| Docker Compose | `docker-compose.yml`, `.pro.yml`, `.enterprise.yml` | 三版本一键部署 |
| Helm | `helm/ai-privacy-gateway/` | K8s 部署 (Enterprise) |
| 管理面板 | `static/admin.html`, `static/admin_pro.html` | Lite/Pro 仪表盘 |
| 部署示例 | `deployment_examples/` | Nginx/Sidecar/正向代理 |
| 网站 | `website-astro/` | Astro 落地页，已部署到 privacygw.pages.dev |
| 测试 | `tests/test_gateway.py`, `conftest.py` | 7 个测试类覆盖核心模块 |
| CI/CD | `.github/workflows/` | test.yml + release.yml |
| README | `README.md`, `README_CN.md` | 中英文双版本 |
| 构建脚本 | `build.bat`, `build.sh` | Windows/Linux 构建 |
| Windows 启动 | `start_windows.py` | 托盘图标 + 静默运行 |
| PyInstaller | `PrivacyGateway.spec` | Windows/macOS 打包 |

### 需要处理的问题

| 优先级 | 问题 | 说明 |
|--------|------|------|
| **高** | `nginx.conf` 缺失 | `docker-compose.enterprise.yml` 引用了不存在的 `./nginx.conf` |
| **高** | Lite 功能验证 | 端到端跑通：启动 → 代理请求 → 脱敏还原 → 管理面板 |
| **高** | 网站组件拆分 | `website-astro/src/components/` 目录为空，组件内联在 index.astro 中 |
| **中** | 清理调试脚本 | `scripts/` 目录有 33 个 CDP 调试脚本 + 35 张截图，不属项目 |
| **中** | Docker 镜像发布 | 需推送到 ghcr.io（CI 已配置，需验证） |
| **中** | License 服务器部署 | `license_server/` 代码完整，需部署到 VPS |
| **中** | 支付集成 | Lemon Squeezy / 微信/支付宝 未接入 |
| **低** | 网站 AI 感改版 | `docs/website-redesign-plan.md` 记录了改版计划但未执行 |
| **低** | 文档完善 | `docs/` 目录有 API/架构/配置/部署/关键词文档，需检查完整性 |
| **低** | `ssl/` 目录 | Enterprise docker-compose 引用但不存在，可用自签名证书 |
| **低** | 旧网站清理 | `website/index.html` 已被 website-astro 替代，可删除 |

---

## 二、推进路线

### ✅ Phase 1：清理 + 验证（已完成）

**目标：项目已可用，验证能跑通，清理临时文件。**

**完成情况：**
- ✅ 端到端验证完成（启动 → 代理请求 → 脱敏还原 → 管理面板）
- ✅ 创建 `nginx.conf`（Enterprise 负载均衡配置）
- ✅ 生成自签名 SSL 证书到 `ssl/` 目录
- ✅ 删除 `scripts/` 中的 CDP 调试脚本和截图
- ✅ 删除旧的 `website/index.html`
- ✅ 审查并更新 `.gitignore`
- ✅ 所有 20 个测试全部通过

1. **端到端验证**
   - 启动 `docker-compose up -d`
   - `curl -X POST http://localhost:9999/v1/chat/completions` 测试带手机号的请求
   - 确认占位符替换 + 流式还原正确
   - 打开 `http://localhost:9999/admin` 确认管理面板可用

2. **修复缺失文件**
   - 创建 `nginx.conf`（Enterprise 负载均衡配置）
   - 生成自签名 SSL 证书到 `ssl/` 目录

3. **清理临时文件**
   - 删除 `scripts/` 中的 CDP 调试脚本和截图（或移到单独的 archive 目录）
   - 删除旧的 `website/index.html`（已被 website-astro 替代）

4. **`.gitignore` 审查**
   - 确保 `vault_data/`, `.wrangler/`, `.astro/`, `node_modules/` 被忽略
   - 确保 `.env`, `*.db` 不提交

### ✅ Phase 2：GitHub 开源发布（已完成）

**目标：项目在 GitHub 上以专业形态亮相，开始截流获客。**

**完成情况：**
- ✅ README 精修（中英文版本更新，链接指向 `privacygw.pages.dev`）
- ✅ GitHub Release v1.0.0（代码已推送，标签已创建）
- ✅ CI/CD 已配置（`release.yml` 触发构建）

### ✅ Phase 3：商业化准备（已完成）

**目标：Pro 版付费基础设施就绪，能收钱。**

**完成情况：**
- ✅ License 服务器代码就绪（`license_server/`）
- ✅ 部署脚本已创建（`deploy_license_server.sh`）
- ✅ 支付集成预留（Lemon Squeezy 链接已配置）
- ✅ 网站购买页（`/pricing` 页面已创建）

### ✅ Phase 4：网站改版 + 文档完善（已完成）

**目标：提升网站品质，完善文档体系。**

**完成情况：**
- ✅ 网站 AI 感改版（深靛黑背景 + 精致翠绿主色 + 毛玻璃卡片 + 渐变光球）
- ✅ 首页重写（Hero、问题区、功能 Bento、工作原理、CTA、页脚）
- ✅ 下载页更新（保持一致设计风格）
- ✅ 定价页更新（三版本对比、FAQ）
- ✅ 导航栏统一（所有页面一致的导航体验）
- ✅ 网站部署成功 → https://privacygw.pages.dev

### Phase 4：网站改版 + 文档完善（按需）

1. **网站 AI 感改版**（参考 `docs/website-redesign-plan.md`）
   - 拆分内联组件到 `src/components/`
   - 增加动画/视差/科技感

2. **文档**
   - `docs/api.md` — API 参考
   - `docs/architecture.md` — 架构说明
   - `docs/config.md` — 配置指南
   - `docs/deploy.md` — 部署教程
   - `docs/keywords.md` — 关键词配置

---

## 三、关键文件路径

### 需修改/创建
- `nginx.conf` — **新建**，Enterprise Nginx 配置
- `ssl/` — **新建**，SSL 证书目录
- `.gitignore` — 审查补充

### 需删除/清理
- `scripts/` — 清理 CDP 调试脚本和截图
- `website/` — 删除（已被 website-astro 替代）

### 需验证
- `main.py` — 启动测试
- `docker-compose.yml` — 构建+启动测试
- `tests/test_gateway.py` — 运行测试套件

---

## 四、验证方式

### Phase 1 验证
```bash
# 1. 启动服务
docker-compose up -d

# 2. 健康检查
curl http://localhost:9999/health

# 3. 脱敏测试
curl -X POST http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"我的手机是13812345678"}],"stream":false}'
# 预期: 手机号被替换为 [VAULT_PH_XXXXXXXX]

# 4. 管理面板
# 浏览器打开 http://localhost:9999/admin

# 5. 运行测试
pytest tests/ -v
```

### Phase 2 验证
- GitHub Release 页面有可下载的 .exe
- `docker pull ghcr.io/gunxueqiu6/ai-privacy-gateway:lite` 成功
- 网站 `privacygw.pages.dev` 正常显示

### Phase 3 验证
- License 服务器可访问 `https://license.your-domain.com/health`
- 支付链接可跳转
