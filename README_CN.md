# AI Privacy Gateway

> 你的 AI 数据正在裸奔。30 秒装上防火墙。

**v1.1.0** — 开源 AI API 隐私网关。在数据离开你机器之前自动脱敏。

高性能反向代理，自动脱敏 AI API 请求/响应中的敏感数据（手机号、身份证、邮箱、银行卡、人名、地名等），支持所有 OpenAI 兼容服务，包括 DeepSeek、Claude、ChatGPT 和 Cursor。

[English](README.md) | [简体中文](README_CN.md)

## 快速开始

### 一键启动（新手从这里开始）

无需手动配置环境变量，交互式向导自动完成所有设置。

```bash
# Windows: 双击 start.bat，或：
python start.py

# macOS / Linux:
./start.sh
# 或：
python3 start.py
```

启动向导会完成以下步骤：
- 检测 Python 环境和依赖
- 引导选择 AI 服务提供商（OpenAI / DeepSeek / 自定义）
- 自动生成安全的 JWT 和加密密钥
- 写入 `.env` 配置文件
- 自动安装缺失的依赖
- 启动网关服务 `http://localhost:9999`

> 非交互模式（用于 CI/CD）：`python start.py --non-interactive`

### Docker（推荐）

```bash
docker run -d \
  --name ai-privacy-gw \
  -p 9999:9999 \
  -v ./vault_data:/app/vault_data \
  -e TARGET_LLM=https://api.openai.com \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite

# 查看自动生成的管理员密码：
docker logs ai-privacy-gw
```

### Docker Compose

```bash
docker-compose up -d

# 查看自动生成的管理员密码：
docker logs ai-privacy-vault
```

### Python（手动）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动（首次运行自动生成密钥）
python main.py
```

首次启动时，管理员密码会自动生成并显示在控制台横幅中。请立即保存，用于访问管理后台 `http://localhost:9999/admin`。

如需自定义配置，创建 `.env` 文件或运行 `python start.py` 进入引导式设置。

### Windows 可执行文件

从 [Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases) 下载 `PrivacyGateway.exe`，双击运行。

### macOS 可执行文件

从 [Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases) 下载，添加执行权限（`chmod +x PrivacyGateway`），然后运行 `./PrivacyGateway`。

## 配置

将 AI 客户端 API 地址改为 `http://localhost:9999`：

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9999/v1",
    api_key="your-api-key"
)
```

### Cursor / VS Code

设置 → API Key → Base URL → `http://localhost:9999`

### Systemd（Linux 服务器）

```ini
[Unit]
Description=AI Privacy Gateway
After=network.target

[Service]
Type=simple
User=privacygw
WorkingDirectory=/opt/privacy-gateway
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name gw.example.com;

    location / {
        proxy_pass http://127.0.0.1:9999;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TARGET_LLM` | https://api.openai.com | 目标 AI API 地址 |
| `LISTEN_PORT` | 9999 | 网关监听端口 |
| `DB_PATH` | ./vault_data/privacy_vault.db | SQLite 数据库路径 |
| `ADMIN_PASSWORD` | （自动生成） | 管理后台密码 |
| `JWT_SECRET` | （自动生成） | JWT 签名密钥 |
| `VAULT_ENCRYPT_KEY` | （自动生成） | Vault 加密密钥 |

## 支持的数据类型

| 类型 | 模式 | 示例 |
|------|------|------|
| 手机号 | 1[3-9]\d{9} | 13812345678 |
| 身份证 | 18位 | 110101199001011234 |
| 邮箱 | 标准格式 | user@example.com |
| 银行卡 | 16-19位 | 6222021234567890 |
| 人名 | 中文人名 | 张三 |
| 地名 | 省市/区县 | 北京市海淀区 |
| 机构名 | 公司名称 | 北京科技有限公司 |
| 车牌号 | 中国车牌 | 京A12345 |
| IP地址 | IPv4 | 192.168.1.100 |
| URL | HTTP/HTTPS | https://example.com |
| 日期 | 多种格式 | 2024年1月15日 |
| 金额 | 货币金额 | ¥999.99 |
| 邮编 | 6位数字 | 100080 |
| 自定义 | 用户定义 | API密钥、密码 |

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
2. 网关拦截并将敏感数据脱敏 → `[PII_PHONE_00000001]`
3. 脱敏后的请求转发到目标 AI API
4. 收到 AI 响应并还原为原始值
5. 将还原后的响应返回给客户端

## 管理后台

打开 `http://localhost:9999`，用管理员密码登录后可以：

- 查看实时拦截统计与趋势图表
- 管理自定义敏感词（添加、测试、删除）
- 检查系统健康与版本信息
- 浏览支持的实体类型

## API 使用

```bash
# 脱敏
curl -X POST http://localhost:9999/api/mask \
  -H "Content-Type: application/json" \
  -d '{"text": "张三住在北京市，电话13812345678"}'

# 还原
curl -X POST http://localhost:9999/api/restore \
  -H "Content-Type: application/json" \
  -d '{"text": "[PII_PER_00000001]住在[PII_LOC_00000001]，电话[PII_PHONE_00000001]", "mappings": {...}}'

# 批量脱敏
curl -X POST http://localhost:9999/api/mask/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["text1", "text2", "text3"]}'
```

## 项目结构

```
ai-privacy-gateway/
├── config.py              # 配置
├── mask_engine.py         # 正则脱敏引擎
├── ner_engine.py          # NER 实体识别
├── stream_buffer.py       # 流式缓冲
├── gateway_core.py        # 代理核心
├── database.py            # SQLite 存储
├── main.py                # FastAPI 入口
├── routers/               # 路由模块
│   ├── proxy.py           # 核心代理路由
│   ├── api.py             # 脱敏/还原 API
│   ├── admin.py           # 管理后台
│   └── auth.py            # 认证状态
├── static/                # 管理后台前端
├── tests/                 # 测试用例
└── website-astro/         # 官网 (Astro)
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

# 启动
python main.py
```

## License

MIT License。详见 [LICENSE](LICENSE)。

## 链接

- [文档](https://privacygw.pages.dev/docs)
- [官网](https://privacygw.pages.dev)
- [在线演示](https://privacygw.pages.dev/demo)
- [GitHub Issues](https://github.com/gunxueqiu6/ai-privacy-gateway/issues)
