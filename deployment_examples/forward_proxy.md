# 正向 HTTP 代理接入方案

## 方案 B：环境变量代理配置

适用于无法修改应用代码的场景，通过环境变量让所有 HTTP 请求经过隐私网关。

---

## 1. Linux / macOS 配置

```bash
# 在 ~/.bashrc 或 ~/.zshrc 中添加
export HTTP_PROXY="http://internal-gateway-ip:9999"
export HTTPS_PROXY="http://internal-gateway-ip:9999"
export NO_PROXY="localhost,127.0.0.1,10.*,192.168.*"
```

---

## 2. Windows 配置

### PowerShell（临时）
```powershell
$env:HTTP_PROXY = "http://internal-gateway-ip:9999"
$env:HTTPS_PROXY = "http://internal-gateway-ip:9999"
```

### 系统环境变量（永久）
1. 打开「系统属性」 → 「高级」 → 「环境变量」
2. 新建系统变量：
   - `HTTP_PROXY` = `http://internal-gateway-ip:9999`
   - `HTTPS_PROXY` = `http://internal-gateway-ip:9999`

---

## 3. Docker 容器配置

```yaml
services:
  your-app:
    environment:
      - HTTP_PROXY=http://ai-privacy-gateway:9999
      - HTTPS_PROXY=http://ai-privacy-gateway:9999
```

---

## 4. Python 应用配置

```python
import os
os.environ['HTTP_PROXY'] = 'http://internal-gateway-ip:9999'
os.environ['HTTPS_PROXY'] = 'http://internal-gateway-ip:9999'

# 或使用 requests 库
import requests
session = requests.Session()
session.proxies = {
    'http': 'http://internal-gateway-ip:9999',
    'https': 'http://internal-gateway-ip:9999'
}
```

---

## 5. Node.js 应用配置

```javascript
// 使用全局代理
process.env.HTTP_PROXY = 'http://internal-gateway-ip:9999';
process.env.HTTPS_PROXY = 'http://internal-gateway-ip:9999';

// 或使用 node-fetch
const fetch = require('node-fetch');
fetch('https://api.openai.com/v1/chat/completions', {
    agent: new HttpsProxyAgent('http://internal-gateway-ip:9999')
});
```

---

## 注意事项

1. **NO_PROXY 配置**：确保内网地址不走代理，避免循环请求
2. **网关地址**：使用内网 IP 或 Docker 服务名，不要用 localhost
3. **SSL 验证**：部分应用可能需要禁用 SSL 验证（网关内部已处理）
4. **超时设置**：代理会增加少量延迟，适当增加应用超时时间

---

## 适用场景

- 无法修改应用代码的老旧系统
- 批量配置多台服务器
- CI/CD 流水线统一配置
- 开发环境全局代理