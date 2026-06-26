# AI Privacy Gateway — 核心网关生产就绪差距

> 审计日期：2026-06-26 | 状态：**全部已修复** | 版本：v2.0.0 | 源码行数：~3,800

---

## P0 — 生产不可用（5 项）✅ 全部完成

### 1. 无背压控制
**文件**：`main.py`, `gateway_core.py`

没有任何并发限流机制——千级并发请求直接打穿网关。httpx 连接池（100 连接）耗尽后所有请求报错。需要 `asyncio.Semaphore` 限制最大并发请求数。

### 2. 优雅关闭缺失
**文件**：`main.py` lines 48-85

lifespan handler 取消了后台任务但**没有排空 in-flight 请求**——无活跃请求计数器、无关闭超时、无 asyncio 事件等待。重启/部署时客户端收到连接断开。

### 3. 代理端点无 body 大小限制
**文件**：`routers/proxy.py`, `gateway_core.py`

`/v1/chat/completions` 可接收无限大的请求体。独立 API 端点（`/api/mask`）有 100KB 限制，但主代理路径没有。单请求即可打爆内存。

### 4. 无 TLS 支持
**文件**：`main.py` lines 250-255

`uvicorn.run()` 未传入 `ssl_keyfile`/`ssl_certfile`。裸 HTTP 服务，必须前置 nginx/Caddy 才能暴露到公网。

### 5. 不支持 Anthropic API
**文件**：`routers/proxy.py` line 19, `gateway_core.py` line 96

白名单缺少 `/v1/messages`。且 Anthropic 的消息格式是 content block 数组（`[{"type":"text","text":"..."}]`），而非纯字符串。Claude 用户完全用不了。

---

## P1 — 运维痛感强烈（5 项）✅ 全部完成

### 6. 配置不能热更新
**文件**：`config.py`, `main.py`

改上游 URL/模型名/TTL/etc 必须重启，所有活跃连接断开。自定义关键词/正则规则可通过 admin API 热更新，但核心配置不行。

### 7. 就绪探针不检查上游
**文件**：`main.py` lines 146-186

`/health` 返回 healthy 即使所有上游已 crash。K8s/编排系统无法判断网关是否真能转发流量。

### 8. 多模型路由缺失
**文件**：`load_balancer.py`, `gateway_core.py`

GPT-4/Claude/DeepSeek 全打到同一个上游池。无法按模型名分流到不同 upstream。

### 9. Vault 无备份/恢复
**文件**：`database.py`

SQLite WAL 模式提供崩溃恢复，但无 `PRAGMA integrity_check`、无 `.backup` API、无定期 dump。SQLite 损坏 = 所有已脱敏数据映射丢失。

### 10. 无干跑模式
**文件**：`mask_engine.py`, `gateway_core.py`

没有"检测 PII 但不屏蔽"的模式。用户想先评估 PII 泄漏情况再决定是否开启屏蔽。

---

## P2 — 质量和鲁棒性（5 项）✅ 全部完成

### 11. 重试是线性退避
**文件**：`gateway_core.py` line 180

`retry_delay * attempt` 应该是 `retry_delay * 2^(attempt-1)` 指数退避。

### 12. 速率限制按 worker 独立计数
**文件**：`routers/dependencies.py`

多 uvicorn worker 部署时，每个 worker 有自己的 in-memory 计数器，实际限流是 N × 配置值。

### 13. 历史统计 API 缺失
**文件**：`database.py` lines 462-537, `routers/admin.py`

只能查今天的数据。无按日期范围/按周/按月聚合的 API。

### 14. 自定义规则无导入/导出
**文件**：`routers/admin.py`

关键词和正则规则只能逐个 CRUD。无批量导出备份或恢复的端点。

### 15. 图片/音频端点被屏蔽
**文件**：`routers/proxy.py` line 19

`images`/`audio` 等非 chat 端点被白名单拒绝返回 404。

---

## P3 — 锦上添花（3 项）✅ 全部完成

16. 超时体系粗糙 — 已实现 connect/read/write/pool 分离超时
17. DB 被锁时无重试逻辑 — 已实现指数退避重试（3 次）
18. 磁盘满时无降级处理 — 已实现 stateless 模式纯内存运行

---

## 最终验证

- **测试覆盖**: 236 tests, 0 failures
- **语法检查**: 所有核心文件通过 ast.parse
- **E2E**: 健康检查、脱敏/还原、管理 API 全部通过
- **实现文件**: config.py, gateway_core.py, main.py, database.py, routers/admin.py, routers/proxy.py, load_balancer.py, mask_engine.py, metrics.py, logging_config.py
