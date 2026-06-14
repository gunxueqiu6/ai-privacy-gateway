---
layout: ../../layouts/DocsLayout.astro
title: Enterprise 功能
description: AI Privacy Gateway Enterprise — AC 自动机、Redis 集群、RBAC、加密存储、告警
canonicalURL: https://privacygw.pages.dev/docs/enterprise
---

# Enterprise 功能

Enterprise 版本专为大规模、高安全性需求的生产环境设计。

## AC 自动机（Aho-Corasick）

大规模关键词匹配引擎，适用于十万级敏感词库的场景。

```text
Lite 模式：  逐条正则匹配   O(n × m)  适合 < 1000 词条
Pro 模式：   编译 AC 自动机  O(n + m)  适合 < 10000 词条
Enterprise：  分片 AC 自动机  O(n + m)  适合 100000+ 词条
```

AC 自动机预编译敏感词为状态机，匹配复杂度与词库大小无关：

```python
# Enterprise 自动启用 AC 自动机加速
from integrity_check import AhoCorasick

automaton = AhoCorasick.build(keywords)  # 预编译状态机
matches = automaton.search(text)         # 线性扫描，百万字耗时 < 10ms
```

## Redis 缓存层

高并发场景下降低数据库负载，提升响应速度。

```yaml
# docker-compose.yml — Enterprise 附加服务
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  gateway:
    image: ghcr.io/gunxueqiu6/ai-privacy-gateway:enterprise
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_CACHE_TTL=3600
```

缓存策略：

| 缓存对象 | TTL | 失效条件 |
|----------|-----|----------|
| 关键词状态机 | 3600s | 关键词变更 |
| 映射表查询 | 300s | 映射表写入 |
| 脱敏规则 | 600s | 规则更新 |
| 统计计数 | 60s | 实时写入 |

Redis 集群支持：

```bash
REDIS_URL=redis://redis-node1:6379,redis-node2:6379,redis-node3:6379
REDIS_CLUSTER_MODE=true
REDIS_POOL_SIZE=20
```

## RBAC 权限控制

细粒度的基于角色的访问控制，适用于多人协作场景。

### 内置角色

| 角色 | 管理后台 | 敏感词管理 | 统计查看 | 系统设置 | 许可证管理 |
|------|----------|------------|----------|----------|------------|
| super_admin | 全部 | 全部 | 全部 | 全部 | 全部 |
| admin | 全部 | 全部 | 全部 | 全部 | 只读 |
| operator | 只读 | 读写 | 只读 | 无 | 无 |
| auditor | 只读 | 只读 | 只读 | 无 | 无 |

### 自定义角色

```json
{
  "name": "安全审计员",
  "permissions": [
    "keyword:read",
    "stats:read",
    "log:read",
    "alert:read"
  ]
}
```

## 加密存储库

敏感词映射表使用 AES-256-GCM 加密存储。

```bash
# 启用加密（需设置密钥）
export VAULT_ENCRYPT_KEY="0123456789abcdef0123456789abcdef"
```

```python
# 加密存储原理
from cryptography.fernet import Fernet

key = Fernet.generate_key()  # 实际使用 VAULT_ENCRYPT_KEY 派生
fernet = Fernet(key)

# 写入时加密
encrypted = fernet.encrypt(mapping_data)
db.save("mappings", encrypted)

# 读取时解密
raw = db.load("mappings")
mapping_data = fernet.decrypt(raw)
```

密钥管理建议：

- 使用密钥管理服务（Vault、AWS KMS）存储 `VAULT_ENCRYPT_KEY`
- 定期轮换加密密钥
- 密钥丢失将导致映射表无法解密，数据不可恢复

## 告警引擎

支持 SMTP 邮件和 Webhook 两种通知渠道。

### SMTP 配置

```bash
export ALERT_SMTP_HOST=smtp.company.com
export ALERT_SMTP_PORT=587
export ALERT_SMTP_USER=alert@company.com
export ALERT_SMTP_PASSWORD=xxxxx
export ALERT_EMAIL_TO=security@company.com
```

### Webhook 配置

```bash
export ALERT_WEBHOOK_URL=https://hooks.company.com/security
export ALERT_WEBHOOK_SECRET=whsec_xxxxx
```

### 告警规则

| 告警类型 | 触发条件 | 默认动作 |
|----------|----------|----------|
| 高频率脱敏 | 单分钟脱敏次数 > 1000 | 邮件 + Webhook |
| 异常流量 | QPS > 阈值 3 倍 | 邮件 + Webhook |
| 许可证即将过期 | 剩余天数 < 30 | 邮件通知 |
| 加密校验失败 | Rust 完整性校验不通过 | 邮件 + Webhook（紧急） |
| 节点离线 | 心跳中断超过 60s | 邮件 + Webhook |

Webhook 负载格式：

```json
{
  "event": "high_masking_rate",
  "severity": "warning",
  "timestamp": "2026-06-14T10:30:00Z",
  "details": {
    "rate": 1250,
    "threshold": 1000,
    "window": "1m"
  }
}
```

## 高级报表

自动生成 CSV 格式的数据安全报表。

```bash
# 手动触发报表生成
POST /admin/reports/generate
Content-Type: application/json

{
  "type": "weekly",
  "format": "csv"
}
```

报表类型：

| 报表 | 内容 | 适用场景 |
|------|------|----------|
| 日报 | 当日脱敏量、Top 敏感词类型、异常事件 | 日常监控 |
| 周报 | 趋势分析、周同比、Top 脱敏用户 | 周会汇报 |
| 月报 | 汇总统计、合规摘要、风险评分 | 月度合规 |

自动发送配置：

```bash
export REPORT_SCHEDULE="0 8 * * 1"  # 每周一早 8 点发送周报
export REPORT_EMAIL_TO="compliance@company.com"
```

## 审计日志增强

Enterprise 版本记录完整的操作审计日志：

```json
{
  "timestamp": "2026-06-14T10:30:00Z",
  "actor": "user_admin",
  "action": "keyword.create",
  "resource": "keyword/123",
  "detail": "添加敏感词: 某项目代号",
  "ip": "10.0.1.100",
  "user_agent": "Mozilla/5.0 ..."
}
```

审计日志不可篡改，支持导出和 SIEM 对接。

## SLA 与支持

| 项目 | Enterprise |
|------|------------|
| 可用性 SLA | 99.9% |
| 响应时间 | 生产故障 < 2 小时 |
| 支持渠道 | 专属技术支持群 |
| 现场支持 | 可选（按需） |
| 部署咨询 | 架构评审 + 部署指导 |
| 安全通告 | CVE 24 小时内通知 |

## 下一步

- [许可证管理](/docs/license)
- [团队管理](/docs/team)
- [部署指南](/docs/deploy)
