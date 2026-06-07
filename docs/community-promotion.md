# 社区推广素材

> 各平台推广文案，可直接复制使用。发帖后勾选 ✅。

---

## 小红书

**标题**: 🔒 用 Cursor/DeepSeek 写代码，你的 API Key 和数据库密码正在裸奔

**正文**:

AI 编程助手是好用，但你有没有想过——你发给 API 的所有内容，包括数据库密码、服务器 IP、用户隐私数据，都是**明文传输**的？😱

我写了一个开源工具，一行命令搞定隐私隔离：

```bash
docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

✅ 自动识别并替换敏感信息（手机号/邮箱/身份证/银行卡/API Key）
✅ AI 返回时自动还原，不影响使用体验
✅ 流式输出（SSE）完美支持
✅ 本地运行，数据不出机器
✅ 完全开源，MIT 协议

Cursor/DeepSeek/Kimi/通义千问 全部兼容。

开源地址：https://github.com/gunxueqiu6/ai-privacy-gateway

#AI安全 #开源 #Cursor #DeepSeek #程序员 #数据隐私

---

## DeepSeek 官方社区

**标题**: 【开源】AI Privacy Gateway — 你发给 AI 的敏感数据，30 秒加上防火墙

**正文**:

大家好，分享一个刚开源的 AI 隐私隔离网关。

**为什么要做这个？**
团队里有人用 Cursor 写代码，不小心把数据库连接串和线上 API Key 全发给 AI 了。这事儿比想象中常见——AI 编程工具的请求全是明文。

**它做什么？**
一个反向代理，部署在你和 AI API 之间：
- 上行 🔼 自动检测并替换敏感数据（正则 + AC 自动机双引擎）
- 下行 🔽 AI 返回时自动还原，完全透明
- 流式输出支持，不影响 SSE 体验
- 管理面板可视化配置

**三行 Nginx 改动，全团队生效**：
```nginx
location /v1/chat/completions {
    proxy_pass http://localhost:9999;
    proxy_set_header Host $host;
}
```

**三个版本**：
- Lite — 个人免费使用
- Pro — ¥99/月，20 人团队，云端规则更新
- Enterprise — 定制，Redis 集群，RBAC，审计日志

GitHub: https://github.com/gunxueqiu6/ai-privacy-gateway
网站: https://privacygw.pages.dev

欢迎 Star ⭐，欢迎提 Issue 和 PR！

---

## Cursor 官方社区/论坛

**标题**: Your AI coding assistant might be leaking secrets — here's a free open-source fix

**正文**:

You use Cursor every day. You trust it with your code. But did you know your code — including API keys, DB passwords, config files — is sent to the AI API in **plain text**?

I built a simple proxy that sits between your IDE and the AI API. It strips sensitive data before it leaves your machine, and restores it in the response. Fully transparent, works with streaming.

**Quick start**:
```bash
docker run -d -p 9999:9999 ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

Then set Cursor to use `http://localhost:9999/v1` as your API endpoint.

**Features**:
- Regex + AC automaton dual-engine detection (phones, emails, ID numbers, bank cards, API keys, custom keywords)
- SSE stream reassembly — works perfectly with real-time AI responses
- SQLite WAL storage with encryption at rest
- Admin dashboard for keyword management
- Open source, MIT license, runs entirely locally

GitHub: https://github.com/gunxueqiu6/ai-privacy-gateway
Website: https://privacygw.pages.dev

Stars and contributions welcome! ⭐

---

## V2EX

**标题**: 做了一个 AI API 隐私网关，保护你发给 AI 的敏感数据

**正文**:

# AI Privacy Gateway

给团队用 Cursor/DeepSeek 的同事做了一个隐私隔离网关，开源了。

## 解决了什么

写代码时 AI 助手会把你整个文件（包括密码、API Key、服务器 IP）原封不动发给 AI API。这些数据：
- 没有任何脱敏处理
- 明文传输
- API 提供商理论上可以看到所有内容

## 怎么用

```bash
docker run -d -p 9999:9999 --name privacy-gw \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite
```

然后 IDE 的 API endpoint 指向 `http://localhost:9999/v1` 就行。

## 技术点

- Python/FastAPI，OpenAI 兼容路由
- 正则 + AC 自动机双引擎脱敏
- SSE 流式分片拼接状态机（流式输出需要特殊处理，组装的 JSON 片段会被分片发送）
- SQLite WAL 模式本地存储（Pro 版支持 Redis）
- Lite/Pro/Enterprise 三版本

## 开源和付费

Lite 版完全免费开源（MIT），个人够用。
Pro 版 ¥99/月支持 20 人团队和云端规则更新。

GitHub: https://github.com/gunxueqiu6/ai-privacy-gateway
网站: https://privacygw.pages.dev

做得很糙，欢迎拍砖。

---

## 飞书/钉钉开发者社区

**标题**: 团队用 AI 编程工具的安全隐患 & 开源解决方案

**摘要**: 分享一个开源的 AI API 隐私网关，自动脱敏发给 AI 的敏感数据。

**项目**: https://github.com/gunxueqiu6/ai-privacy-gateway

**适用场景**: 企业开发团队使用 Cursor/DeepSeek/Kimi 等 AI 编程工具时，需要保护代码中的敏感信息。

**30 秒部署**:
```bash
docker compose up -d
```

**三版本**:
- Lite — 免费，个人使用
- Pro — ¥99/月，20 人团队
- Enterprise — 定制，100+ 人，Redis 集群

GitHub Star ⭐ 支持一下 → https://github.com/gunxueqiu6/ai-privacy-gateway

---

## 发帖计划

| 平台 | 文案 | 状态 |
|------|------|------|
| 小红书 | 标题+正文 | ⏳ |
| DeepSeek 社区 | 中文开发者 | ⏳ |
| V2EX | 分享创造 | ⏳ |
| Cursor Forum | 英文 | ⏳ |
| 飞书开发者社区 | 中文 | ⏳ |
| Hacker News | Show HN | ⏳ |
| 知乎 | 文章 | ⏳ |
