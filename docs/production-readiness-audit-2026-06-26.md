# AI Privacy Gateway v2.0 — 生产就绪审计报告

> 审计日期：2026-06-26 | 仓库：github.com/gunxueqiu6/ai-privacy-gateway | 许可证：MIT

---

## 系统全景

```
核心网关 (Python/FastAPI)   ← 反向代理，PII 检测+屏蔽+恢复
├── 5 个 SDK（JS / Flutter / Android / iOS / 浏览器扩展）
├── 网站 (Astro v6)         ← 公开站点，privacygw.pages.dev
├── Docker 镜像              ← GHCR 分发
├── 安装器 (Windows + macOS) ← PyInstaller + DMG
└── 营销自动化工具            ← Selenium 多平台内容发布
```

---

## 一、核心网关（Python）— 已生产就绪，有盲区

### 已有能力

- Docker 多阶段构建 + GHCR 推送
- GitHub Actions CI/CD（test.yml + release.yml）
- 全测试套件（9 个测试文件，覆盖 mask/ner/config/audit/vault/lb/integration）
- 安全扫描（bandit + pip-audit + Trivy）
- Windows/macOS 安装器（PyInstaller + Inno Setup + DMG）
- JWT 认证 + bcrypt 密码哈希
- 审计日志哈希链 + AES-256-GCM vault 加密
- 速率限制 + 登录锁定
- 多上游负载均衡（轮询/随机/最少连接）
- SSE 流式处理

### 缺失

| # | 问题 | 严重度 |
|---|-------|---------|
| 1 | 测试覆盖率 ~60-75%，不到 80% | 高 |
| 2 | NER 依赖 jieba/onnxruntime，缺失时静默降级为纯正则——用户不知道准确度打了多少折扣 | 中 |
| 3 | 无端到端测试——没有"启动网关→发请求→验证屏蔽→验证恢复"的完整流程 | 高 |
| 4 | 无可观测性——无 Prometheus metrics、无结构化日志、health check 端点简陋 | 中 |
| 5 | 管理面板是纯 HTML + 内联 JS，无构建工具、无测试 | 低 |
| 6 | 数据库无迁移机制，schema 变更靠 `CREATE TABLE IF NOT EXISTS` | 中 |
| 7 | 无 gRPC 支持，只有 HTTP 代理 | 低 |
| 8 | 无 OpenAPI 文档公开托管（FastAPI 自带了 `/docs` 但没部署） | 低 |

---

## 二、SDK — 写好了，没发布

| SDK | 代码 | 测试 | 文档 | 发布状态 |
|-----|------|------|------|---------|
| JS/TS | 有 | Jest 20+ | 有 | npm 已配置，缺 publish CI |
| Flutter | 有 | flutter_test | 有 | **未发布到 pub.dev** |
| Android | 有 | JUnit | 有 | **未发布到 Maven Central** |
| iOS | 有 | Quick+Nimble | 有 | **未发布到 CocoaPods** |
| 浏览器扩展 | 有 | **无** | 有 | **未上架 Chrome Web Store** |

**5 个 SDK 中只有 JS 接近可分发状态。SDK 是获客第一入口，这是最大的断层。**

---

## 三、网站（website-astro）— 已部署，缺防护和内容

### 已有

- Astro v6 静态生成，部署到 Cloudflare Pages
- 中英文双语路由（`/xxx` + `/en/xxx`）
- SEO：OG/Twitter Card/JSON-LD/hreflang/sitemap/robots
- 暗色主题 + 玻璃拟态设计
- 100 页构建输出

### 缺失

| # | 问题 | 严重度 |
|---|-------|---------|
| 1 | 无 404/500 错误页 | 阻塞 |
| 2 | 无安全头（CSP/HSTS/X-Frame-Options/X-Content-Type-Options） | 阻塞 |
| 3 | 博客 10 篇文章全英文，无中文版 | 高 |
| 4 | Docs 6 个 .md 全中文，无英文版 | 高 |
| 5 | SEO 落地页 8 个硬编码英文，无中文文案 | 高 |
| 6 | 零测试（无 vitest/Playwright） | 高 |
| 7 | 字体 `@import` 阻塞渲染 | 中 |
| 8 | 键盘无障碍缺失（语言切换器不可 Tab） | 中 |
| 9 | 缺少隐私政策、服务条款页 | 中 |
| 10 | 无 `prefers-reduced-motion` 支持 | 低 |
| 11 | BlogCard 硬编码 "Read Article" | 低 |
| 12 | hreflang 在英文页错误声明为 zh-CN | 低 |

---

## 四、跨组件缺失

| # | 问题 |
|---|-------|
| 1 | 无集成测试跨组件（SDK → 网关 → 屏蔽 → 恢复） |
| 2 | 无版本兼容性矩阵（网关 API vs SDK 版本） |
| 3 | 无 SDK 发布自动化 CI |
| 4 | 无 CONTRIBUTING.md |
| 5 | 无 CHANGELOG.md |
| 6 | 无社区频道（只有 GitHub Issues + 个人 Telegram） |
| 7 | Docker 镜像无 semver tag 策略 |

---

## 五、优先级行动清单

### P0 — 阻塞产品可用

1. 网站：加 404/500 页 + 安全头（`public/_headers`）
2. 创建 CONTRIBUTING.md + CHANGELOG.md
3. 网站：i18n 补完（博客中文化、Docs 英文化、SEO 页双语化）

### P1 — 影响产品质量

4. 核心网关测试覆盖率提到 80%+
5. 端到端集成测试（SDK → 网关全链路）
6. 网站：法律页面（隐私政策 + 服务条款）
7. SDK 发布到各包管理器（Chrome Store / pub.dev / Maven / CocoaPods）
8. OpenAPI 文档公开部署

### P2 — 增强专业度

9. Prometheus metrics + 结构化日志
10. Docker semver tag 策略
11. 网站：vitest 单元测试 + Playwright 冒烟测试
12. 网站：性能优化（字体自托管、图片优化）

### P3 — 锦上添花

13. 管理面板现代化
14. 数据库迁移框架（alembic）
15. gRPC 支持
16. 社区频道搭建
