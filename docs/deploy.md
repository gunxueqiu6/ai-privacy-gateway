# 部署教程

## 30 秒快速启动（Lite 版）

```bash
# 1. 拉取镜像
docker pull ghcr.io/gunxueqiu6/ai-privacy-gateway:lite

# 2. 启动
docker run -d -p 9999:9999 --name privacy-gw \
  ghcr.io/gunxueqiu6/ai-privacy-gateway:lite

# 3. 验证
curl http://localhost:9999/health
```

打开浏览器访问 `http://localhost:9999/admin` 进入管理面板。

## 配置你的 AI 工具

### Cursor
Settings → Models → 添加 OpenAI Compatible 端点:
- Base URL: `http://localhost:9999/v1`
- API Key: `cursor`

### DeepSeek
```
export DEEPSEEK_API_BASE="http://localhost:9999/v1"
```

### 通用 OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:9999/v1",
    api_key="any-key"
)
```

## Nginx 反向代理（推荐）

在现有 AI API 代理前面加一层：

```nginx
location /v1/chat/completions {
    proxy_pass http://localhost:9999;
    proxy_set_header Host $host;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    proxy_buffering off;
}
```

3 行改动，全团队生效。

## Docker Compose 部署

### Lite 版

```bash
docker-compose up -d
```

### Pro 版

```bash
# 1. 购买 License → 获取 LICENSE_KEY
# 2. 设置环境变量
export LICENSE_KEY="pro-xxxx-xxxx"
export VERSION="pro"

# 3. 启动
docker-compose -f docker-compose.yml -f docker-compose.pro.yml up -d
```

### Enterprise 版

```bash
export LICENSE_KEY="ent-xxxx-xxxx"
export VERSION="enterprise"
export REDIS_PASSWORD="your-redis-password"

docker-compose -f docker-compose.yml -f docker-compose.enterprise.yml up -d
```

## Windows/macOS 桌面版

从 [GitHub Releases](https://github.com/gunxueqiu6/ai-privacy-gateway/releases) 下载 .exe 或 .dmg:

1. 下载 `PrivacyGateway.exe`
2. 双击运行（系统托盘图标启动）
3. 右键托盘图标 → 打开管理面板

## K8s / Helm (Enterprise)

```bash
helm install privacy-gw ./helm/ai-privacy-gateway \
  --set licenseKey=$LICENSE_KEY \
  --set redis.password=$REDIS_PASSWORD
```

## 验证部署

```bash
# 健康检查
curl http://localhost:9999/health

# 脱敏测试
curl -X POST http://localhost:9999/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"我的手机是13812345678"}],"stream":false}'

# 预期输出:
# 手机号被替换为 [VAULT_PH_XXXXXXXX]
```

## 常见问题

**Q: 端口冲突？**
修改 `LISTEN_PORT` 环境变量: `LISTEN_PORT=8888 docker-compose up -d`

**Q: 如何查看日志？**
```bash
docker logs -f privacy-gw
```

**Q: 如何更新自定义关键词？**
管理面板 → 关键词配置 → 添加关键词 → 保存
或直接编辑 `vault_data/custom_keywords.json`
