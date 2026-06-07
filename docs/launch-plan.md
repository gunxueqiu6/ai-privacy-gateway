# AI Privacy Gateway 上线计划

## 目标

将项目从本地代码变为一个有流量、有转化的开源商业产品。

```
GitHub (代码+社区) ──→ 官网 (流量承接+转化) ──→ 付费用户
                            │
                    SEO 内容 → 自然流量
                    文档中心 → 降低使用门槛
                    下载页面 → 收集线索
```

## 阶段一：GitHub 仓库建设

### 1.1 仓库创建
- [x] 创建 GitHub 仓库 `gunxueqiu6/ai-privacy-gateway`
- [x] 推送代码
- [x] 设置仓库：description、topics、website link、About

### 1.2 README 重写
- [x] 中英双语 README（README.md + README_CN.md）
- [x] 一句话说清楚：30 秒部署的 AI API 数据脱敏反向代理
- [x] 快速开始：`docker-compose up -d` 一键跑通
- [x] 效果演示：终端 ASCII demo
- [x] 版本对比表（Lite / Pro / Enterprise）
- [x] README 末尾引流官网

### 1.3 社区建设
- [x] CONTRIBUTING.md
- [x] Issue 模板（bug report / feature request）
- [x] PR 模板
- [x] GitHub Actions CI（release.yml + test.yml）
- [x] 打第一个 release tag `v0.1.0`
- [x] Docker 镜像推送 GHCR (`ghcr.io/gunxueqiu6/ai-privacy-gateway:lite`)

## 阶段二：官网建设

### 2.1 技术选型
- **Astro** 静态站点生成（SEO 友好，Markdown 写文档）
- 部署到 **Cloudflare Pages** (`https://privacygw.pages.dev/`)
- 域名（待购买，建议 `aiprivacygateway.com`）

### 2.2 首页重构
Astro 完整官网已上线 (`website-astro/`)：

- [x] **Hero 区** — "你的团队 AI 数据正在裸奔" + CTA 按钮
- [x] **痛点区** — 三个真实场景：Cursor 里贴身份证号、飞书机器人泄露手机号、DeepSeek 训练数据被抓取
- [x] **功能矩阵** — 6 张功能卡片（自动脱敏、流式支持、本地存储、一键接入、团队看板、云端规则）
- [x] **版本对比** — Lite（免费）/ Pro（¥99/月）/ Enterprise（定制）
- [x] **FAQ** — 5 个高频问题
- [x] **CTA** — GitHub Star + 免费下载 + 购买 Pro
- [x] **AI 感重设计** — 深靛黑底色 + 翠绿主色 + 网点纹理 + 渐变光球 + 毛玻璃卡片 + Inter 字体

### 2.3 下载页面
- [x] Windows `.exe` 单文件下载
- [x] macOS 可执行文件下载
- [x] Docker 镜像拉取命令
- [ ] 各版本下载量统计（收集线索）

### 2.4 文档中心
- [x] 快速开始指南（`/docs/`）
- [x] 部署指南（`/docs/config` 含环境变量配置）
- [x] 配置指南（`/docs/config` 含自定义规则）
- [x] API 参考（`/docs/api`）
- [x] 架构文档（`/docs/architecture`）
- [x] 关键词覆盖（`/docs/keywords` — SEO）
- [ ] 常见问题排查（详细 troubleshooting 指南）

### 2.5 设计方向
- 深色主题（现有 `#0f172a` 背景保留）
- 品牌色：绿色 `#4ade80`（安全/信任感）+ 红色 `#f87171`（警示/痛点）
- 字体：系统默认中文字体栈
- 动效：轻量级 CSS 动画，不依赖重型 JS 框架

## 阶段三：SEO 内容矩阵

### 3.1 目标关键词
| 搜索意图 | 目标关键词 |
|----------|-----------|
| 问题意识 | DeepSeek 数据安全、Cursor 隐私保护、AI API 数据泄露 |
| 解决方案 | AI 数据脱敏工具、LLM 代理网关、AI 隐私防火墙 |
| 竞品对比 | AI 数据安全方案、企业 AI 合规 |
| 长尾教程 | 如何保护 AI 请求中的敏感数据、Cursor 配置代理 |

### 3.2 内容规划
- [ ] 5 篇博客文章（SEO 长尾关键词）
- [ ] 3 个使用教程（Cursor / DeepSeek / 飞书机器人 配置指南）
- [ ] 1 篇技术架构文章（Rust 完整性检查、流式缓冲设计）

### 3.3 分发渠道
- [ ] 掘金 / SegmentFault 技术文章
- [ ] V2EX 发布帖
- [ ] Twitter/X 英文推广
- [ ] 知乎专栏同步

## 阶段四：转化漏斗

### 4.1 Lite 用户获取
- GitHub Star → README 引流官网 → 下载试用
- Docker Hub 镜像发布 `aiprivacygateway/lite`
- 搜索引擎自然流量 → 落地页 → 下载

### 4.2 Lite → Pro 转化
- 管理后台内置升级提示（"团队用？升级 Pro 版"）
- 免费试用 Pro 版 14 天
- 下载页面收集邮箱 → 邮件序列自动跟进

### 4.3 Pro → Enterprise 转化
- 联系表单 → 人工跟进
- 客户案例展示
- 企业定制报价

## 当前进度

| 阶段 | 状态 | 完成项 |
|------|------|--------|
| GitHub 仓库 | ✅ 完成 | 仓库 `gunxueqiu6/ai-privacy-gateway`，CI/CD，Release v0.1.0，Docker GHCR |
| 官网建设 | ✅ 完成 | Astro 网站上线 `privacygw.pages.dev`，AI 感重设计，文档中心 |
| SEO 内容 | 🔜 待启动 | 目标关键词已规划（`docs/keywords.md`），内容待产出 |
| 转化漏斗 | 🔜 待启动 | Lite/Pro/Enterprise 定价页已上线，支付/邮箱收集待集成 |

## 下一步行动

**立即做：** 获取 Cloudflare Analytics token → 替换 Layout.astro 中的占位符 → 重新部署

**紧接着：** SEO 文章每周 1 篇 → 社区渠道分发（掘金、V2EX、知乎）

**持续推进：** 转化漏斗建设（支付集成、邮件序列、企业联系表单）
