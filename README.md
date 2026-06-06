# AI Privacy Gateway

> **你的 AI 数据正在裸奔，30 秒装上防火墙**

[English](#english) | [中文](#中文)

---

## 中文

### 什么是 AI Privacy Gateway？

一个本地运行的**反向代理服务**，拦截你发往 AI 大模型的请求，自动脱敏敏感信息后转发，返回时自动还原。**用户完全无感知**。

### 核心功能

- **敏感信息识别与替换**
  - 中国手机号（1开头11位）
  - 身份证号（18位）
  - 邮箱地址
  - 银行卡号（16-19位）
  - 自定义关键词

- **请求转发**
  - 完全兼容 OpenAI 接口格式
  - 支持流式输出（stream 模式）
  - 支持自定义上游 API（DeepSeek、Claude 等）

- **本地数据库**
  - SQLite 存储"占位符↔真实值"映射
  - 数据绝不上传云端
  - 一键清除

- **管理后台**
  - 查看今日拦截统计
  - 添加/删除自定义敏感词

### 快速开始

#### 方式一：Docker（推荐）

```bash
docker-compose up -d
```

#### 方式二：Python

```bash
pip install -r requirements.txt
python main.py
```

#### 方式三：Windows 单文件（即将发布）

下载 `PrivacyGateway.exe`，双击运行。

### 使用方法

将你的 AI 客户端 API 地址从：

```
https://api.openai.com
```

改为：

```
http://localhost:9999
```

就这么简单！

### 支持的 AI 客户端

- Cursor
- ChatGPT Desktop
- DeepSeek API
- Claude API
- 任何兼容 OpenAI 接口的客户端

### 企业接入方案

三种无缝接入企业原有服务器的方式：

| 方案 | 适用场景 | 配置文件 |
|------|---------|---------|
| Nginx Upstream | 已有 Nginx 反向代理 | [nginx_upstream.conf](deployment_examples/nginx_upstream.conf) |
| Docker Sidecar | Docker Compose 环境 | [docker_sidecar.yml](deployment_examples/docker_sidecar.yml) |
| 正向 HTTP 代理 | 无法修改代码的老旧系统 | [forward_proxy.md](deployment_examples/forward_proxy.md) |

### 版本对比

| 功能 | Lite（免费） | Pro（¥99/月） | Enterprise |
|------|-------------|--------------|------------|
| 正则脱敏 | ✅ | ✅ | ✅ |
| 流式代理 | ✅ | ✅ | ✅ |
| 自定义敏感词 | ✅ | ✅ | ✅ |
| 多人并发 | ❌ | ✅ 20人 | ✅ 100+ |
| 团队看板 | ❌ | ✅ | ✅ |
| AC 自动机 | ❌ | ❌ | ✅ |
| Redis 存储 | ❌ | ❌ | ✅ |
| 审计日志 | ❌ | ❌ | ✅ |

### 技术栈

- Python 3.11
- FastAPI
- SQLite
- Docker

### 安全保障

- 所有敏感数据仅存储在本地 SQLite
- 映射关系不上传任何云端
- 支持一键物理销毁所有记录

---

## English

### What is AI Privacy Gateway?

A **local reverse proxy service** that intercepts your requests to AI LLMs, automatically masks sensitive information before forwarding, and restores it on return. **Completely transparent to users**.

### Core Features

- **Sensitive Data Detection & Replacement**
  - Chinese phone numbers (11 digits starting with 1)
  - ID card numbers (18 digits)
  - Email addresses
  - Bank card numbers (16-19 digits)
  - Custom keywords

- **Request Forwarding**
  - Fully compatible with OpenAI API format
  - Supports streaming (SSE mode)
  - Custom upstream API (DeepSeek, Claude, etc.)

- **Local Database**
  - SQLite stores "placeholder↔real value" mappings
  - Data never leaves your machine
  - One-click clear

### Quick Start

#### Option 1: Docker (Recommended)

```bash
docker-compose up -d
```

#### Option 2: Python

```bash
pip install -r requirements.txt
python main.py
```

### Usage

Change your AI client's API base URL from:

```
https://api.openai.com
```

to:

```
http://localhost:9999
```

That's it!

### Supported AI Clients

- Cursor
- ChatGPT Desktop
- DeepSeek API
- Claude API
- Any OpenAI-compatible client

### License

MIT License - Free for personal use.

---

## Topics

`llm-security` `ai-privacy` `deepseek-proxy` `cursor-privacy` `data-masking` `pii-detection` `openai-proxy` `chatgpt-privacy` `sensitive-data` `privacy-gateway`

---

[🌐 官方网站](https://gunxueqiu6.github.io/ai-privacy-gateway/) | [📖 文档](https://gunxueqiu6.github.io/ai-privacy-gateway/docs/) | [📥 下载](https://gunxueqiu6.github.io/ai-privacy-gateway/download/) | **Enterprise 定制** → [联系我们](mailto:support@aiprivacygateway.com)