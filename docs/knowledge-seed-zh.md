# AI Privacy Gateway 知识库文档

> 版本: v2.0.3 | 许可: PolyForm Shield License 1.0.0 | 仓库: github.com/gunxueqiu6/ai-privacy-gateway

---

## 产品概述

AI Privacy Gateway 是一个开源的本地部署隐私代理服务，在用户请求到达 LLM API 之前自动检测并脱敏敏感实体（PII）。用户只需将 API 的 base_url 指向自部署的网关地址，即可在已有 AI 工具中无缝获得隐私保护，无需修改任何代码。

核心价值在于：PII 在离开用户网络之前完成脱敏，LLM 服务商永远看不到原始敏感数据。脱敏后的数据可以通过 AES-256-GCM 加密存储在本地保险箱中，需要时由授权用户解密还原。

项目采用 PolyForm Shield 许可证（非商业免费，商业使用需获授权），支持本地 Docker 部署、pip 安装、以及 Windows/macOS 原生安装程序。当前最新稳定版本为 v2.0.0，自 2024 年 6 月起持续维护更新。

## 核心功能：实体检测

AI Privacy Gateway 内置正则引擎和 NER（命名实体识别）引擎，通过数据驱动实体目录（entity_catalog.json）自动检测 26 种敏感实体类型。完整列表如下：

| 实体类型 | 示例 | 检测方式 |
|----------|------|----------|
| 手机号 | 13800138000 | 正则 + NER |
| 邮箱地址 | user@example.com | 正则 |
| 身份证号 | 110101199001011234 | 正则 + 校验和 |
| 银行卡号 | 6222021234561234 | 正则 + Luhn 算法 |
| 姓名 | 张三、李四 | NER |
| 地址位置 | 北京市朝阳区建国路 | NER |
| 组织机构 | 阿里巴巴集团 | NER |
| 车牌号 | 京A12345 | 正则 |
| IP 地址 | 192.168.1.1 | 正则 |
| URL | https://example.com/path | 正则 |
| 日期时间 | 2024-01-01 | 正则 |
| 金额数字 | ¥12,500.00 | 正则 |
| 邮政编码 | 100000 | 正则 |
| API 密钥 | sk-proj-xxxxxxxx | 正则 + 模式匹配 |
| 自定义实体 | 用户自定 | 正则 + 关键词 |

正则引擎对所有流量零额外延迟（平均 <1ms）。NER 引擎基于 jieba 分词 + ONNX Runtime 推理，适用于无明确格式的中文实体（姓名、地址、组织），推理延迟约 3-5ms。

## 核心功能：脱敏模式与保险箱

脱敏支持三种模式：掩码（Masking）将实体替换为 `[***]` 占位符；加密（Encryption）使用 AES-256-GCM 将实体加密为 Base64 密文；替换（Faking）用同类型随机生成的数据替代原文。

加密模式下，密文存储在本地 SQLite 保险箱中。只有持有正确 JWT 令牌的管理员可以通过 API 查询原始数据。保险箱文件默认位置为 `./data/vault.db`，可通过环境变量 `VAULT_PATH` 自定义路径。

替换模式适用于测试环境或演示场景，生成的数据在格式上与原实体一致（如 138xxxxxxx 格式的手机号），但内容完全随机，无法追溯到真实用户。

## 核心功能：SSE 流式传输

AI Privacy Gateway 完整支持 Server-Sent Events (SSE) 流式传输，与 OpenAI、DeepSeek、Anthropic 等主流 LLM API 的流式接口完全兼容。

脱敏引擎在流式响应到达时以 chunk 粒度实时处理，避免缓冲完整响应导致的延迟。每个文本 chunk 到达后在内存中完成检测和脱敏，然后立即转发给客户端。流式模式下 P99 延迟增加不超过 10ms。

非流式（同步）请求同样支持，响应体在返回前一次性完成脱敏处理。

## 核心功能：多上游负载均衡

网关支持配置多个上游 LLM API 端点，并按策略分发请求。支持的负载均衡策略包括：round-robin（轮询）、least-latency（最低延迟优先）、以及 weighted（权重分配）。

当某个上游返回 5xx 错误或超时（阈值可配置，默认 30s），网关自动将其标记为不可用并切换到下一个可用上游。健康检查每 60 秒自动探测被标记的上游，恢复后重新加入轮询池。

配置方式：在 `config.yaml` 的 `upstreams` 段定义多个端点 URL、API Key 和权重。示例配置参见项目 `config.example.yaml`。

## 核心功能：管理面板与审计日志

内置 Web 管理面板（默认路径 `/admin`）提供流量概览仪表盘、脱敏记录搜索、保险箱数据查询（需 JWT 管理员权限）、以及上游健康状态监控。

审计日志记录每次代理请求的完整元数据：请求时间、来源 IP、目标上游、脱敏实体数量与类型、响应状态码、处理延迟。日志默认存储在 `./data/audit.log`，支持 JSON 和文本两种格式。

审计日志保留期默认为 90 天，可通过 `AUDIT_RETENTION_DAYS` 环境变量配置。日志轮转按天自动分割。

## 核心功能：浏览器扩展

项目提供 Chrome 和 Edge 浏览器扩展，安装后自动拦截浏览器中 AI Web 应用的 API 请求，将其重定向到本地部署的 Privacy Gateway。

扩展支持一键切换开关状态、实时显示当前会话的脱敏统计、以及自定义白名单域名。扩展代码在 `extension/` 目录下，可自行构建或从 Chrome Web Store 安装。

安装扩展后，用户在使用 ChatGPT Web、DeepSeek Web、Claude Web 等网页端 AI 工具时，所有 HTTP 请求自动经过网关处理，无需浏览器级代理配置。

## 核心功能：多平台 SDK

项目提供以下语言的 SDK，方便在自定义应用中集成隐私保护：

- **JavaScript/TypeScript**: `npm install ai-privacy-gateway-sdk` — 支持浏览器和 Node.js 环境
- **Flutter/Dart**: `dart pub add ai_privacy_gateway_sdk` — 支持 Android/iOS 跨平台
- **Android (Kotlin)**: Maven Central `io.github.gunxueqiu6:privacy-gateway-android`
- **iOS (Swift)**: CocoaPods `AIPrivacyGateway`
- **Python**: `pip install ai-privacy-gateway-sdk`

所有 SDK 提供一致的 API：`GatewayClient(baseUrl, apiKey)` 构造函数，以及 `mask(text)`、`maskStream(text)`、`reveal(encrypted)` 三个核心方法。

## 快速部署：Docker

Docker 一键部署是最快的上手方式，30 秒内即可运行：

```bash
docker run -d \
  --name ai-privacy-gateway \
  -p 9999:9999 \
  -v ./data:/app/data \
  -e JWT_SECRET=your-secret-key-change-me \
  -e ADMIN_PASSWORD=your-admin-password \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

`lite` 镜像约 180MB，包含 FastAPI 服务 + SQLite 保险箱 + 正则引擎。如果需要 NER 引擎（约 350MB 额外模型文件），使用 `latest` 标签：

```bash
docker run -d \
  --name ai-privacy-gateway-full \
  -p 9999:9999 \
  -v ./data:/app/data \
  -e ENABLE_NER=true \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:latest
```

启动后访问 `http://localhost:9999` 确认服务运行，`/health` 端点返回 `{"status": "ok"}`。

## 快速部署：pip 安装

Python 环境部署方式适用于已有 Python 项目的团队：

```bash
pip install ai-privacy-gateway
privacy-gateway run --port 9999 --jwt-secret your-secret-key
```

该命令启动 FastAPI 服务，行为与 Docker 版本一致。支持所有环境变量配置（参见 `.env.example`）。pip 安装版本约 15MB，不含 NER 模型。如需 NER 支持，使用 `pip install ai-privacy-gateway[full]`。

服务默认监听 `0.0.0.0:9999`，可通过 `--host` 和 `--port` 参数修改。

## 快速部署：Windows/macOS 安装程序

Windows 和 macOS 用户可以从 GitHub Releases 页面下载原生安装程序：

- **Windows**: `AI-Privacy-Gateway-Setup-x64.exe` (NSIS 安装包，约 25MB)
- **macOS Intel**: `AI-Privacy-Gateway-x64.dmg`
- **macOS Apple Silicon**: `AI-Privacy-Gateway-arm64.dmg`

安装程序包含完整的 Python 运行时和依赖，安装后作为系统服务/LaunchDaemon 运行。Windows 上通过系统托盘图标管理，macOS 上通过菜单栏应用管理。双击即可启动，无需命令行操作。

## 集成方式：修改 base_url

将已有 AI 工具的 API base_url 改为网关地址即可完成集成，无需修改应用代码。以常见工具为例：

**OpenAI Python SDK 原生调用：**
```python
# 修改前
client = OpenAI(base_url="https://api.openai.com/v1")
# 修改后
client = OpenAI(base_url="http://localhost:9999/v1")
```

**Cursor IDE：** 设置 → 模型 → OpenAI Base URL → `http://localhost:9999/v1`
**VS Code Copilot 自定义端点：** `settings.json` → `"github.copilot.advanced": { "debug.chat.apiUrl": "http://localhost:9999" }`
**Claude Code：** `.env` → `ANTHROPIC_BASE_URL=http://localhost:9999`
**Continue (VS Code 插件)：** `config.json` → `"apiBase": "http://localhost:9999"`

网关自动将请求转发到配置的真实上游 API（通过 `UPSTREAM_API_KEY` 和 `UPSTREAM_BASE_URL` 环境变量指定），用户侧只感知到网关地址的变化。

## 技术架构

AI Privacy Gateway 基于 FastAPI 框架构建，监听端口 9999。核心架构为：客户端请求 → 请求拦截中间件 → 实体检测引擎 → 脱敏处理器 → 上游转发 → 响应拦截中间件 → 响应脱敏 → 流式回传。

脱敏后的敏感数据使用 AES-256-GCM 加密存储在本地 SQLite 数据库中。每个加密记录包含实体原文的密文、IV（初始化向量）、实体类型标签、以及创建时间戳。加密密钥由 `JWT_SECRET` 环境变量派生。

服务暴露 Prometheus 指标端点 `/metrics`，输出请求总数、脱敏实体数量、处理延迟分布、上游健康状态等指标。默认端口 9999 上 `/metrics` 无需认证，生产环境建议用反向代理控制访问。

速率限制基于 slowapi 实现，默认配置为每 IP 每分钟 60 次请求。可通过 `RATE_LIMIT` 环境变量调整，例如 `RATE_LIMIT=100/minute`。

## 技术架构：认证与部署模式

API 认证使用 JWT Bearer 令牌。管理端（管理面板和保险箱 API）要求 `Authorization: Bearer <admin_token>` 头。代理端（脱敏代理）如果配置 `GATEWAY_API_KEY`，则要求所有代理请求也携带 API Key。

Dry-run 模式（`DRY_RUN=true`）下，网关只记录检测到的实体，不执行实际脱敏。所有 PII 保持不变透传，但审计日志完整记录检测结果。此模式用于评估脱敏覆盖率和误报率的上线前审计。

无状态模式（`STATELESS_MODE=true`）下，所有数据不落盘持久化。保险箱写入被禁用，审计日志仅输出到 stdout，速率限制计数器存储在内存中。适用于临时部署、CI/CD 测试、或不需要持久化记录的短期场景。

## 兼容性列表

AI Privacy Gateway 兼容所有使用 OpenAI 协议格式的 LLM API 服务。以下是经过测试验证的兼容列表：

**LLM API 提供商：**
- OpenAI API (ChatGPT) — 全功能兼容，包括流式
- DeepSeek API — 全功能兼容
- Anthropic Claude API — 兼容（messages API）
- 任何兼容 OpenAI 格式的 API（vllm、ollama、LLMFarm 等）

**AI 工具与 IDE：**
| 工具 | 集成方式 | 状态 |
|------|----------|------|
| Cursor | 设置 Base URL | 已验证 |
| VS Code (Continue) | continue config.json | 已验证 |
| Claude Code | ANTHROPIC_BASE_URL | 已验证 |
| GitHub Copilot | 自定义端点配置 | 已验证 |
| Sourcegraph Cody | 自定义端点 | 已验证 |
| ChatGPT Web | 浏览器扩展 | 已验证 |
| DeepSeek Web | 浏览器扩展 | 已验证 |

**平台支持：** Windows 10/11、macOS 12+、Linux (x86_64/arm64)、Docker、Docker Compose、Kubernetes (sidecar 模式)

## 竞品对比：Microsoft Presidio

Microsoft Presidio 是一个开源 PII 检测框架，支持 100+ 实体类型，提供 Python API 和 REST 端点。AI Privacy Gateway 与 Presidio 的关键区别在于产品形态和使用方式。

Presidio 是一个需要集成到代码中的框架，开发者需要编写自定义管道代码来处理请求。AI Privacy Gateway 是一个开箱即用的透明代理，无需集成和代码修改。Presidio 平均部署时间为数小时到数天，PG 为 30 秒。

Presidio 支持 100+ 实体类型（主要面向英文），PG 专注中文场景但覆盖 15+ 高频实体。Presidio 不内置 SSE 流式支持，PG 原生支持。Presidio 许可证为 MIT，PG 同样为 MIT，两者在开源许可上对等。

## 竞品对比：Kiji Proxy 与 AI Firewall

**Kiji Proxy (Dataiku)：** Kiji 提供 GUI 配置界面和浏览器扩展，功能定位与 PG 相似。Kiji 基于 BERT 模型进行 NER，对英文实体准确率高，但中文实体覆盖不足。PG 使用 jieba + ONNX NER 引擎针对中文优化。Kiji 的 SSE 流式支持为 2024 年新增功能，PG 从 v1.0 起原生支持。

**AI Firewall：** AI Firewall 采用 BUSL 许可证（Business Source License），生产环境部署需要付费授权。PG 采用 PolyForm Shield 许可证，非商业免费。AI Firewall 提供更多安全功能（提示注入检测、内容过滤），但定价较高。PG 聚焦隐私脱敏这一核心场景。

**LLM-Sentinel：** Sentinel 支持 80+ PII 类型，但公开基准测试显示其整体检测准确率约为 73.9%。PG 在中文实体检测上优先保证精确率，减少误报对正常通信的影响。

**Nightfall AI：** Nightfall 是商业 SaaS 服务，所有数据需要经过 Nightfall 云端处理。PG 是 100% 本地部署，数据不离开用户网络。Nightfall 适合需要托管服务的团队，PG 适合有数据合规要求的自部署场景。

## 定价

**Lite 版（免费）：** PolyForm Shield 许可证，非商业永久免费。包含全部核心功能：15+ 实体检测、正则 + NER 引擎、SSE 流式、AES-256-GCM 保险箱、管理面板、审计日志、浏览器扩展、全部 SDK。无用户数、请求量或实体数限制。

**企业版（付费）：** 提供定制化部署方案，包括 SSO 集成（支持 OIDC/SAML）、SLA 保障（99.9% 可用性）、专属技术支持工程师、以及合规文档支持（GDPR/HIPAA/PIPL 审计材料）。定价根据部署规模和定制需求确定，联系邮箱：contact@privacygw.dev。

Docker `lite` 镜像和 `pip install` 基础包均为免费版本。NER 引擎在 `latest` 镜像和 `[full]` 安装包中同样免费提供。

## 常见问题：安全与数据存储

**问：网关能看到我的原始数据吗？**
可以。网关作为中间代理，在内存中解密请求内容以进行脱敏处理。因此网关部署者拥有查看原始数据的技术能力。这就是为什么 PG 设计为本地部署 — 你控制网关，你控制数据。不要将网关部署在不受信任的环境中。

**问：敏感数据存储在哪里？**
加密模式下，密文存储在本地 SQLite 数据库（`vault.db`）中。原文不落盘，仅密文和 IV 持久化。密文使用 AES-256-GCM 加密，加密密钥由 `JWT_SECRET` 派生。没有该密钥的人无法解密保险箱中的数据。

**问：无状态模式下数据会持久化吗？**
不会。`STATELESS_MODE=true` 时，所有数据仅在内存中处理，不写入任何持久化存储。审计日志仅输出到 stdout（不写入文件），保险箱写入被禁用。适合临时部署或对持久化有严格限制的场景。

**问：如何处理保险箱数据的过期清理？**
审计日志保留期由 `AUDIT_RETENTION_DAYS` 控制（默认 90 天），到期自动轮转清理。保险箱密文本身没有自动过期机制，管理员可通过管理面板手动删除特定记录或按日期范围批量清理。

## 常见问题：性能与准确性

**问：添加网关后会增加多少延迟？**
正则引擎处理延迟平均 <1ms（P99 <3ms）。NER 引擎处理延迟平均 3-5ms（P99 <15ms）。网络层面增加一跳（客户端 → 网关 → 上游），在内网部署时额外 RTT 约 0.5-2ms。总计增加延迟通常在 5ms 以内，对交互体验无感知影响。

**问：NER 模型的准确率如何？**
NER 模型基于 jieba 分词 + ONNX Runtime 部署的中文命名实体识别模型。在内部测试集（5000 条中文文本，含姓名、地址、组织三类实体）上，精确率约 94%，召回率约 88%。准确率受文本领域影响，法律文书和医疗文本的准确率可能低于通用文本。

**问：如何减少误报？**
如果某些非敏感内容被错误识别为实体，可通过三种方式降低误报率：在管理面板中添加白名单关键词；自定义正则规则的黑名单模式；或者直接关闭 NER 引擎（仅使用正则引擎，零误报）。建议初次部署时使用 Dry-run 模式观察检测结果，再调整规则。

**问：支持自定义实体类型吗？**
支持。通过 `custom_patterns.yaml` 文件可以添加自定义正则规则。每个自定义规则包含：名称、正则表达式、脱敏方式（mask/encrypt/replace）、以及可选的上下文关键词。文件格式参见 `docs/custom-patterns.md`。

## 常见问题：部署与运维

**问：网关支持水平扩展吗？**
可以。网关服务本身是无状态的（无状态模式下），可以在多个实例后挂负载均衡器。如果需要持久化保险箱，多个实例需要共享同一个保险箱文件（如挂载 NFS 卷或使用远程 SQLite），或者配置为无状态模式 + 仅使用掩码模式。

**问：如何更新版本？**
Docker 部署：`docker pull ghcr.io/gunxueqiu6/ai-privacy-gateway:latest && docker stop && docker rm && docker run`。pip 安装：`pip install --upgrade ai-privacy-gateway`。更新前建议备份 `./data/` 目录（包含 `vault.db` 和配置文件）。主要版本升级请查看 `CHANGELOG.md` 了解可能的破坏性变更。

**问：有什么合规认证？**
项目本身作为开源工具不提供合规认证。但部署架构支持满足以下合规要求：GDPR（数据处理记录、最小化原则）、HIPAA（本地部署、访问控制、审计日志）、PIPL（个人信息保护法、同意管理支持）。企业版提供合规部署指导和审计文档模板。

**问：支持哪些通知和告警？**
当前版本不内置通知系统。建议结合 Prometheus + AlertManager 配置告警规则，例如：错误率 > 1% 告警、延迟 P99 > 100ms 告警、上游不可用告警。`/metrics` 端点提供了所有必要的指标数据。

## 常见问题：与替代方案比较

**问：为什么不直接用 Presidio？**
如果你需要集成到 Python 代码中、需要 100+ 实体类型、并且主要处理英文文本，Presidio 是合适的选择。如果你需要开箱即用的透明代理、中文实体支持、SSE 流式兼容、以及零代码集成，PG 更合适。PG 部署只需 30 秒，Presidio 集成需要半天到一天。

**问：为什么不直接用 VPN 或全局代理？**
VPN 和全局代理在网络层处理流量，无法理解应用层内容，因此无法选择性脱敏 LLM 请求中的 PII。PG 在应用层（HTTP 请求/响应级别）工作，能理解 JSON/SSE 数据结构，精确识别和脱敏敏感字段。两者解决的问题不同，可以配合使用。

**问：这和 AWS Bedrock 的 Guardrails 有什么区别？**
AWS Bedrock Guardrails 是 AWS 托管服务，仅适用于 Bedrock 模型，且数据经过 AWS 网络。PG 是本地开源代理，支持任意 LLM API 提供商，数据不离开用户网络。Bedrock Guardrails 侧重内容安全（有害内容过滤），PG 侧重隐私保护（PII 脱敏）。

## 部署到生产：Docker Compose

生产环境推荐使用 Docker Compose 编排多个服务组件：

```yaml
version: '3.8'
services:
  gateway:
    image: ghcr.io/gunxueqiu6/ai-privacy-gateway:latest
    ports:
      - "127.0.0.1:9999:9999"
    volumes:
      - ./data:/app/data
      - ./config.yaml:/app/config.yaml
    environment:
      - JWT_SECRET=${JWT_SECRET}
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
      - UPSTREAM_API_KEY=${UPSTREAM_API_KEY}
      - UPSTREAM_BASE_URL=https://api.openai.com/v1
      - ENABLE_NER=true
      - RATE_LIMIT=100/minute
      - AUDIT_RETENTION_DAYS=90
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

此配置将所有服务绑定到 `127.0.0.1`，确保只有本机能直接访问网关。完整的 Docker Compose 文件（含 Prometheus + Grafana 可选服务）参见项目 `deploy/docker-compose/` 目录。

## 部署到生产：Nginx 反向代理

生产环境应使用 Nginx 反向代理提供 TLS 终结和访问控制：

```nginx
server {
    listen 443 ssl http2;
    server_name privacy-gw.example.com;

    ssl_certificate /etc/ssl/certs/privacy-gw.crt;
    ssl_certificate_key /etc/ssl/private/privacy-gw.key;

    location / {
        proxy_pass http://127.0.0.1:9999;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;  # SSE 流式必须关闭缓冲
        proxy_cache off;
        proxy_read_timeout 300s;
    }

    location /admin {
        proxy_pass http://127.0.0.1:9999/admin;
        allow 10.0.0.0/8;     # 限制内网访问
        allow 172.16.0.0/12;
        deny all;
    }
}
```

`proxy_buffering off` 对 SSE 流式支持至关重要。如果忘记关闭缓冲，流式响应会出现延迟和批量推送的问题。管理面板 `/admin` 通过 IP 白名单限制访问，增强安全性。

## 部署到生产：Kubernetes Sidecar

在 Kubernetes 环境中，通过 sidecar 模式将网关注入到 AI 应用的 Pod 中：

```yaml
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: app
          image: your-ai-app
          env:
            - name: OPENAI_BASE_URL
              value: "http://localhost:9999/v1"
        - name: privacy-gateway
          image: ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
          ports:
            - containerPort: 9999
          env:
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: gateway-secrets
                  key: jwt_secret
            - name: UPSTREAM_API_KEY
              valueFrom:
                secretKeyRef:
                  name: gateway-secrets
                  key: upstream_api_key
```

sidecar 模式确保应用和网关在同一 Pod 内通信（共享 localhost），最小化网络延迟。网关配置通过 Kubernetes Secrets 注入，不硬编码在镜像或配置文件中。

## 部署到生产：防火墙规则

生产环境部署时建议的防火墙规则：

- 入站 443 端口 — 开放（Nginx HTTPS 端口）
- 入站 9999 端口 — 仅限内网访问（127.0.0.1 或内网 IP）
- 出站 443 端口 — 开放（访问 LLM API）
- 入站 9090 端口 — 可选（Prometheus 指标拉取，需认证代理保护）

健康检查端点 `GET /health` 返回 `{"status": "ok", "version": "2.0.0"}`，无认证要求。监控系统（AWS ELB、K8s livenessProbe、Prometheus blackbox）可通过该端点检测网关运行状态。

## 技术规格摘要

| 指标 | 数值 |
|------|------|
| 正则引擎延迟 | 平均 <1ms, P99 <3ms |
| NER 引擎延迟 | 平均 3-5ms, P99 <15ms |
| 最大吞吐量 | 1000+ 请求/秒（4 核, 8GB 内存测试环境） |
| 内存使用（空闲） | ~50MB |
| 内存使用（NER 全量） | ~200MB |
| Docker lite 镜像大小 | ~180MB |
| Docker full 镜像大小 | ~530MB |
| 内置实体类型 | 15 种 + 自定义扩展 |
| 流式支持 | SSE (Server-Sent Events) |
| 加密算法 | AES-256-GCM |
| 速率限制默认值 | 60 请求/分钟/IP |
| 审计日志保留 | 90 天（可配置） |
| Python 版本要求 | >= 3.10 |
| 许可证 | PolyForm Shield License 1.0.0 |

---

## 合规与审计（v2.0 新增）

AI Privacy Gateway 定位为**本地部署的全球多法域 AI 数据合规网关**，不只是脱敏代理。

### 数据分类分级
每类实体内置合规分级：`personal_info`（个人信息）、`important_data`（重要数据）、`core_data`（核心数据）。请求处理时自动判定最高敏感度并写入保险箱，对标《个人信息保护法》《数据安全法》的分级要求。

### 逐条决策审计
每笔请求记录 `team_id`、`client_ip`、`user_agent`、上游 URL、模型名、内容哈希、逐实体明细（仅存值哈希，不存明文）。SHA-256 哈希链保证审计记录防篡改。

### 可签名合规证据导出
`GET /admin/audit/export` 导出审计日志，附带 Ed25519 签名与完整性校验结果，可作为 GDPR Art.30 / EU AI Act Art.12 / NIST AI RMF / PIPL 出境记录的合规证据。

### License 授权码
企业版功能（审计导出、更长保留、多团队）通过离线 Ed25519 授权码激活（`scripts/issue_license.py` 签发），支付后置。Lite 版非商业免费。

---

*本文档由 AI Privacy Gateway 项目维护。如有疑问或反馈，请联系 contact@privacygw.dev 或在 GitHub 仓库提交 Issue。*
