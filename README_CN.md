# AI Privacy Gateway

> 你的 AI 数据正在裸奔。30 秒装上防火墙。

高性能反向代理，自动脱敏 AI API 请求/响应中的敏感数据（手机号、身份证、邮箱、银行卡），支持所有 OpenAI 兼容服务，包括 DeepSeek、Claude、ChatGPT 和 Cursor。

[English](README.md) | [简体中文](README_CN.md)

🔒 **保护隐私** | ⚡ **零配置** | 🔄 **完整流式支持**

---

## 核心功能

- **自动脱敏** - 检测并替换敏感数据为唯一占位符
- **完整流式支持** - 完美处理 AI 流式响应（SSE）
- **仅本地存储** - 所有映射仅存储在本地，绝不上传云端
- **一键接入** - 只需修改 API 地址，无需改动任何代码
- **团队看板** (Pro) - 实时拦截统计、会话历史
- **云端规则更新** (Pro) - 敏感词规则自动同步

## 支持的数据类型

| 类型 | 模式 | 示例 |
|------|------|------|
| 手机号 | 1[3-9]\d{9} | 13812345678 |
| 身份证 | 18位 | 110101199001011234 |
| 邮箱 | 标准格式 | user@example.com |
| 银行卡 | 16-19位 | 6222021234567890 |
| 自定义 | 用户定义 | API密钥、密码 |

## 快速开始

### Docker（推荐）

```bash
# 一键部署
docker-compose up -d

# 配置 AI 客户端
# 将 API 地址从 https://api.openai.com 改为 http://localhost:9999
```

### Python

```bash
pip install -r requirements.txt
python main.py
```

### Windows 可执行文件

从 [Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases) 下载并运行 `PrivacyGateway.exe`。

## 工作原理

```
┌─────────────┐     ┌──────────────────┐     ┌──────────────┐
│   你的 AI   │────▶│  Privacy Gateway │────▶│   目标 API   │
│   客户端    │◀────│    (脱敏)       │◀────│   (DeepSeek) │
└─────────────┘     └──────────────────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   本地       │
                    │   SQLite     │
                    └──────────────┘
```

**请求流程：**
1. 你的 AI 客户端发送包含敏感数据的请求
2. 网关拦截并将敏感数据脱敏 → `[VAULT_PHONE_xxx]`
3. 脱敏后的请求转发到目标 AI API
4. 收到 AI 响应并还原为原始值
5. 将还原后的响应返回给客户端

## 配置

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TARGET_LLM` | https://api.openai.com | 目标 AI API 地址 |
| `LISTEN_PORT` | 9999 | 网关监听端口 |
| `DB_TYPE` | sqlite | 存储类型 (sqlite/redis) |
| `MASK_ENGINE_TYPE` | regex | 脱敏引擎 (regex/ac_automaton) |

### 管理后台

打开 `http://localhost:9999/admin` 可以：
- 查看拦截统计
- 管理自定义敏感词
- 检查系统健康状态

## 版本对比

| 功能 | Lite (免费) | Pro (¥99/月) | Enterprise |
|------|-------------|--------------|------------|
| 正则脱敏 | ✅ | ✅ | ✅ |
| 流式代理 | ✅ | ✅ | ✅ |
| 自定义敏感词 | 手动 | 自动同步 | 自动同步 |
| 管理后台 | 基础 | 团队 | 高级 |
| 并发用户 | 1 | 20 | 100+ |
| 审计日志 | - | - | ✅ |
| RBAC 权限 | - | - | ✅ |
| 告警通知 | - | - | ✅ |

## 项目结构

```
ai-privacy-gateway/
├── config.py              # 配置
├── mask_engine.py         # 脱敏引擎
├── stream_buffer.py       # 流式缓冲
├── gateway_core.py        # 代理核心
├── database.py            # SQLite 存储
├── license_client.py      # License 客户端
├── decay_manager.py       # 渐进衰减
├── main.py                # FastAPI 入口
├── rust_src/             # Rust 完整性模块
└── tests/                # 测试用例
```

## 开发

```bash
# 克隆
git clone https://github.com/gunxueqiu6/ai-privacy-gateway
cd ai-privacy-gateway

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/ -v

# 构建 Pro/Enterprise 版本
python build_chain.py --version pro --license-key YOUR_KEY --customer-id YOUR_ID
```

## License

- **Lite**: MIT License（免费用于个人/商业用途）
- **Pro/Enterprise**: 需要商业授权

详见 [LICENSE](LICENSE)。

## 贡献

欢迎贡献！详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 链接

- [文档](https://privacygw.pages.dev/docs)
- [官网](https://privacygw.pages.dev)
- [GitHub Issues](https://github.com/gunxueqiu6/ai-privacy-gateway/issues)
