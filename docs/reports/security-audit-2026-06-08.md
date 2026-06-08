# AI Privacy Gateway — 全面安全审计报告

**审计日期**: 2026-06-08  
**审计范围**: Python 后端 / SDK(JS/Android/Flutter/iOS) / 浏览器插件 / CI/CD / Docker  
**审计方法**: 静态代码分析 + 架构审查 + 依赖分析 + CI/CD 管线审计  
**总发现数**: 53 (16 CRITICAL / 18 HIGH / 13 MODERATE / 6 LOW)

---

## 综合评级: CRITICAL — 生产部署前必须修复 Tier 1

---

## 一、CRITICAL（必须立即修复 — 16 项）

### 1.1 认证与授权

#### C-1: 默认管理员密码 `admin123`
- **文件**: `config.py:23`
- **代码**: `ADMIN_PASSWORD: str = os.environ.get("ADMIN_PASSWORD", "admin123")`
- **描述**: 未设环境变量时使用公开记录的默认密码。README.md 中明文记载，攻击者 5 秒即可获得管理员权限（查看统计、管理关键词、清空映射表）。
- **修复**: 移除默认值，强制通过环境变量设置，启动时若未设则拒绝启动。

#### C-2: 会话 Cookie `secure=False` — HTTP 会话劫持
- **文件**: `main.py:370`
- **代码**: `response.set_cookie(key="session_token", ..., secure=False, max_age=86400)`
- **描述**: JWT session token 通过明文 HTTP 传输。同网络下任何人均可抓包获取 session token，冒充管理员 24 小时。
- **修复**: 非 localhost 时强制 `secure=True` + `samesite="strict"`。

#### C-3: 管理员接口无 CSRF 保护
- **文件**: `main.py:412-502`
- **描述**: 所有 POST 管理端点（/admin/keywords/add、/admin/keywords/delete、/admin/clear、/admin/logout）仅依赖 cookie 鉴权，无 CSRF token。攻击者构造恶意页面即可在管理员浏览器中静默执行操作。
- **修复**: 设置 `samesite="strict"`，或将管理端点改为纯 Bearer token 鉴权。

#### C-4: JWT 24 小时有效 + 登出不失效
- **文件**: `main.py:58, 374`
- **代码**: `expire = datetime.utcnow() + timedelta(hours=24)`
- **描述**: token 被窃后 24 小时内一直可用（即使管理员已登出）。同时 JWT secret 每进程重启随机生成（`os.urandom(32).hex()`），重启后所有旧 token 反而无法使用，长有效期无实际意义。
- **修复**: 缩短至 1 小时，登出时加入服务端 token 黑名单。

#### C-5: 代理端点零认证 — 开放 LLM 中继
- **文件**: `main.py:102-166`
- **描述**: `/v1/chat/completions` 和 `/v1/{path:path}` 不验证客户端身份。任何能访问网关端口的人都在用你的 API key 调用 LLM。
- **修复**: 至少验证 `Authorization` header 非空再转发。

### 1.2 数据泄漏

#### C-6: Prompt 注入可提取数据库中任意 PII（最严重设计漏洞）
- **文件**: `gateway_core.py:71-79` + `mask_engine.py:217-222`
- **代码**: 
  ```python
  # unmask 做的是简单字符串替换
  for placeholder, real_value in mappings.items():
      result = result.replace(placeholder, real_value)
  ```
- **攻击路径**:
  1. 用户在消息中埋入占位符 `[PII_PHONE_00000042]`
  2. 诱导 LLM 回显该占位符（"请重复: [PII_PHONE_00000042]"）
  3. 网关 unmask 时直接替换为真实手机号
  4. 攻击者拿到他人明文 PII
- **修复**: 仅还原请求中实际存在的占位符；用 HMAC 签名占位符防止枚举。

#### C-7: 所有客户端请求头原文转发 — Host 头注入
- **文件**: `main.py:119`
- **代码**: `headers = dict(request.headers)`
- **描述**: 客户端的 Host、Cookie、X-Forwarded-* 等逐跳头全部原文转发给上游 LLM。攻击者可注入 `Host: internal-service.local` 导致虚拟主机混淆。
- **修复**: 白名单机制——只转发 Content-Type 和 Authorization。

#### C-8: 错误响应泄露内部信息
- **文件**: `gateway_core.py:123, 167`
- **代码**: `return 502, {"error": str(e)}, {}`
- **描述**: httpx 原始异常消息（连接拒绝/DNS 失败/TLS 错误/超时细节）直接返回给客户端。攻击者可据此探测内网拓扑。
- **修复**: 返回 "Upstream service unavailable"，完整错误只记服务端日志。

### 1.3 SDK 与浏览器插件

#### C-9: Android API Key 明文存储
- **文件**: `sdk/android/vpn/src/main/java/com/privacygw/vpn/MainActivity.kt:71-82`
- **代码**: `prefs.getString("api_key", "")`
- **描述**: SharedPreferences 以明文 XML 存储 API key。任何有 ADB 或物理访问的人均可读取。
- **修复**: 改用 `EncryptedSharedPreferences`。

#### C-10: iOS API Key 明文存储
- **文件**: `sdk/ios/PrivacyFilter/FilterDataProvider.swift:188-191`
- **代码**: `UserDefaults(suiteName: "group.com.privacygw.filter").string(forKey: "api_key")`
- **描述**: UserDefaults 以明文 plist 文件存储 API key。
- **修复**: 改用 iOS Keychain（SecItemAdd/SecItemCopyMatching）。

#### C-11: 浏览器插件 content.js XSS 漏洞
- **文件**: `sdk/browser-extension/content.js:149, 286-288`
- **代码**: `badge.innerHTML = ...` + `highlighted.replace(pattern, (match) => { return '<span ...>${match}</span>' })`
- **描述**: 匹配文本未经转义直接注入 HTML。页面输入中若包含 `<img src=x onerror=alert(1)>` 会被渲染执行。
- **修复**: 全部改用 `document.createTextNode()` 或 `textContent`。

#### C-12: 浏览器插件 + 所有 SDK 默认 HTTP 传输
- **文件**: `background.js:3`, `client.ts:66`, `GatewayConfig.kt`, `privacy_gateway.dart`, `PrivacyGateway.swift`
- **描述**: 所有 SDK 默认 baseUrl 均为 `http://localhost:9999`。用户部署到远程服务器时若未加 `https://`，API key + 全部 PII 明文传输。
- **修复**: 所有 SDK 强制 HTTPS（localhost 例外）。

### 1.4 基础设施

#### C-13: Android SDK runBlocking 阻塞主线程（ANR 风险）
- **文件**: `sdk/android/src/main/java/com/privacygw/sdk/PrivacyGateway.kt:137-151`
- **代码**: 便捷方法使用 `runBlocking { }` 调用 suspend 函数
- **描述**: 若从主线程调用，直接阻塞 UI → ANR crash。
- **修复**: 删除阻塞便捷方法，要求调用方使用协程。

#### C-14: iOS DispatchSemaphore 阻塞 Network Extension 过滤线程
- **文件**: `sdk/ios/PrivacyFilter/FilterDataProvider.swift:273-285`
- **代码**: `DispatchSemaphore(value: 0)` 同步网络请求
- **描述**: 在 Network Extension 过滤线程上阻塞 → 内核可能驱逐过滤器。
- **修复**: 重新设计为异步操作。

#### C-15: Docker 以 root 运行
- **文件**: `Dockerfile` — 无 `USER` 指令
- **描述**: 若网关进程被攻破 → 容器内 root 权限，可写任意文件。
- **修复**: 添加非 root 用户。

#### C-16: Release 产物无校验和/签名
- **文件**: `.github/workflows/release.yml`
- **描述**: 用户下载的 .exe/Docker 镜像无 SHA256 校验和、无数字签名，无法验证完整性。被篡改的 CI 产物无法检测。
- **修复**: 生成 SHA256 校验和文件并与 artifact 一起上传。

---

## 二、HIGH（应尽快修复 — 18 项）

| # | 问题 | 文件:行号 |
|---|------|-----------|
| H-1 | X-Forwarded-For 可伪造绕过限速和登录锁定 | `main.py:45` |
| H-2 | PII 映射无 TTL 永久存储 → 数据库失窃后所有历史 PII 暴露 | `database.py:103-110` |
| H-3 | 审计日志无完整性保护，可被静默篡改/删除 | `database.py:166-175` |
| H-4 | mask/restore API 无输入大小限制 → 内存耗尽 DoS | `main.py:175` |
| H-5 | 登录失败返回剩余尝试次数 → 攻击者可精确控速 | `main.py:353` |
| H-6 | 通配代理路由 `/v1/{path:path}` 可探测任意上游端点（SSRF） | `main.py:152-166` |
| H-7 | 请求体被就地修改（mutate），重试时数据已变化 | `gateway_core.py:53` |
| H-8 | 自定义关键词无长度/字符集验证 | `main.py:419` |
| H-9 | login_attempts check-then-increment 非原子操作 | `database.py:206-239` |
| H-10 | Android VPN 直通模式 — 声称保护但实际不过滤任何数据 | `PrivacyVpnService.kt:228-230` |
| H-11 | iOS Network Extension 无法解密 HTTPS → 过滤完全无效（架构级） | `FilterDataProvider.swift:133-163` |
| H-12 | CI 无安全扫描（bandit/semgrep/pip-audit 均缺失） | `.github/workflows/test.yml` |
| H-13 | Docker 镜像构建后未经漏洞扫描直接推送 | `.github/workflows/release.yml` |
| H-14 | Android VPN 硬编码 Google DNS 8.8.8.8，绕过用户 DNS | `PrivacyVpnService.kt:171-172` |
| H-15 | iOS URL 强制解包 crash（`URL(string: ...)!`） | `FilterDataProvider.swift:258` |
| H-16 | 浏览器插件 chrome.runtime.onMessage 不验证 sender.id | `background.js:101` |
| H-17 | 浏览器插件原始错误消息返回给调用方 | `background.js:144` |
| H-18 | Docker 无 HEALTHCHECK（docker-compose 外运行时） | `Dockerfile` |

---

## 三、MODERATE（计划修复 — 13 项）

| # | 问题 | 文件:行号 |
|---|------|-----------|
| M-1 | update_stats 动态 SQL 列名拼接（当前安全但危险模式） | `database.py:259-275` |
| M-2 | 未使用的硬编码 `SECRET_KEY = "ai_privacy_vault_key_2024"`（死代码+审计干扰） | `mask_engine.py:64` |
| M-3 | jieba/onnxruntime/pystray/Pillow 未列入 requirements.txt | `requirements.txt` |
| M-4 | FastAPI 无 CORS 中间件配置 | `main.py` |
| M-5 | 邮编正则 `[1-9]\d{5}` 误匹配非邮编 6 位数字（订单号等） | `mask_engine.py:77` |
| M-6 | JS SDK detectEntities() 身份证正则有 ReDoS 风险 | `sdk/js/src/index.ts:97-103` |
| M-7 | JS SDK mask.ts 使用非加密自定义哈希 | `sdk/js/src/mask.ts:8-14` |
| M-8 | 浏览器插件 content.js 读取页面所有输入框（含密码框） | `content.js:87, 96` |
| M-9 | Flutter SDK apiKey 强制解包 `!`（null 时 crash） | `sdk/flutter/lib/models.dart:22` |
| M-10 | 所有 5 个 SDK 无证书固定 | 全局 |
| M-11 | 所有 SDK mask() 无输入大小限制 | 全局 |
| M-12 | start_windows.py 不监控子进程崩溃/不重启 | `start_windows.py:47` |
| M-13 | docker-compose healthcheck 缺少 start_period | `docker-compose.yml:19-22` |

---

## 四、LOW（技术债务 — 6 项）

| # | 问题 | 文件 |
|---|------|------|
| L-1 | `_mappings_cache` 死代码 — 每请求刷新但从未被读取 | `main.py:50, 93-97` |
| L-2 | login_attempts check-then-increment 在并发下可多试 | `database.py:206-239` |
| L-3 | `.coveragerc` omit 规则与实际路径不匹配 | `.coveragerc:2` |
| L-4 | Android SDK minifyEnabled false — 未混淆易逆向 | `sdk/android/build.gradle:23` |
| L-5 | 测试代码硬编码密码可能触发自动扫描告警 | `tests/test_auth.py` |
| L-6 | build.sh/build.bat 使用 --noconfirm 静默覆盖 | `build.sh:12, build.bat:12` |

---

## 五、修复优先级路线图

### 第一梯队（本周 — 立即修复）
```
C-1:  移除默认密码（config.py:23）
C-2:  会话 Cookie secure=True + SameSite（main.py:370）
C-3:  管理接口 CSRF 保护（main.py:412-502）
C-6:  Prompt 注入修复——验证占位符（gateway_core.py + mask_engine.py）
C-7:  Headers 白名单过滤（main.py:119）
C-8:  错误信息脱敏（gateway_core.py:123, 167）
C-11: 浏览器插件 XSS——innerHTML → textContent（content.js）
C-12: 浏览器插件强制 HTTPS（background.js）
```

### 第二梯队（本月）
```
C-4:  JWT 短期化 + 登出黑名单（main.py）
C-5:  代理端点加认证（main.py）
C-9:  Android EncryptedSharedPreferences
C-10: iOS Keychain 存储
C-13: Android 移除 runBlocking
C-14: iOS 异步网络请求
C-15: Docker USER 非 root
C-16: Release 校验和签名
H-1:  限速 IP 获取修复（main.py）
H-2:  PII TTL 过期机制（database.py）
H-4:  API 输入大小限制（main.py）
H-5:  登录错误信息脱敏（main.py）
H-6:  代理路由限制（main.py）
H-7:  请求体深拷贝（gateway_core.py）
H-12: CI 安全扫描（test.yml）
H-13: Docker 镜像漏洞扫描（release.yml）
H-14-18: SDK/VPN/插件修复
H-3:  审计日志完整性（database.py）
```

### 第三梯队（下月及后续）
```
M-1  ~ M-13: 代码质量 + 模式改进
L-1  ~ L-6:  技术债务清理
Android VPN 实现真正的包过滤
iOS 架构重新设计（Network Extension → HTTP Proxy）
SDK 证书固定
```

---

## 六、已排除的风险（验证通过）

- `.env` 文件：已 gitignore，仓库中不存在 ✓
- 硬编码生产密钥（sk-/ghp_ 等）：全局搜索未发现 ✓
- Pro/Enterprise 代码残留：公开仓库已清理（仅 Lite） ✓
- 已知 CVE 依赖：当前所有 pinned 版本无已知 CVE ✓
- SSH 密钥/证书文件：仓库中不存在 ✓

---

*本报告由自动化安全审计 Agent 生成，覆盖 Python 后端、4 个 SDK、浏览器插件、CI/CD 管线及 Docker 部署配置。*
