---
layout: ../../layouts/DocsLayout.astro
title: 团队管理
description: Pro/Enterprise 团队管理 — 成员、角色、API Key、数据隔离
canonicalURL: https://privacygw.pages.dev/docs/team
---

# 团队管理

Pro/Enterprise 版本支持团队协作与多成员管理。

## 创建团队

首次激活 Pro/Enterprise 许可证后，系统自动创建与许可证关联的团队。

```bash
POST /admin/team/create
Content-Type: application/json

{
  "name": "研发团队",
  "description": "AI 网关研发部门"
}
```

## 用户角色

| 角色 | 权限 | 说明 |
|------|------|------|
| admin | 全部权限 | 管理设置、成员管理、许可证管理 |
| member | 读写权限 | 配置脱敏规则、查看日志、管理 API Key |
| viewer | 只读权限 | 查看统计、查看日志、查看配置 |

### 角色管理

```bash
# 邀请成员
POST /admin/team/invite
Content-Type: application/json

{
  "email": "user@company.com",
  "role": "member"
}

# 修改角色
PUT /admin/team/members/{user_id}/role
Content-Type: application/json

{
  "role": "admin"
}

# 移除成员
DELETE /admin/team/members/{user_id}
```

## 邀请流程

```
1. 管理员发起邀请 → 系统生成邀请链接
2. 邮件发送至被邀请人
3. 被邀请人点击链接接受
4. 自动分配对应角色权限
5. 成员加入团队后可见共享资源
```

邀请链接默认 48 小时有效，可在管理后台重新生成。

## API Key 管理

团队成员可拥有独立的 API Key，用于区分请求来源。

```bash
# 列出当前团队 API Key
GET /admin/team/keys

# 创建新 Key
POST /admin/team/keys
Content-Type: application/json

{
  "label": "CI/CD 环境",
  "role": "member"
}

# 重置 Key
POST /admin/team/keys/{key_id}/reset

# 删除 Key
DELETE /admin/team/keys/{key_id}
```

响应示例：

```json
{
  "keys": [
    {
      "id": "key_abc123",
      "label": "CI/CD 环境",
      "role": "member",
      "prefix": "gw_sk_abc...",
      "created_at": "2026-06-01T00:00:00Z",
      "last_used": "2026-06-14T08:30:00Z"
    }
  ]
}
```

创建新 Key 时仅返回一次完整密钥：

```json
{
  "id": "key_def456",
  "key": "gw_sk_def456_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "label": "CI/CD 环境",
  "role": "member"
}
```

## 席位限制

| 版本 | 最大席位 | 超限处理 |
|------|----------|----------|
| Pro | 20 | 无法邀请新成员，需移除闲置成员 |
| Enterprise | 100+ | 联系销售扩容 |

席位以当前活跃成员数计算，已禁用或已移除的成员不计入。

## 数据隔离

不同团队之间的数据完全隔离：

- 敏感词映射表独立存储
- 脱敏规则互不可见
- 统计和日志按团队隔离
- API Key 仅限所属团队使用

自托管部署下，数据隔离由本地 SQLite 数据库的命名空间机制保证，所有数据仍留存于本地，不上传外部。

## 团队设置

```bash
# 更新团队信息
PUT /admin/team/settings
Content-Type: application/json

{
  "name": "AI 安全团队",
  "description": "负责全公司 AI 数据安全",
  "default_role": "viewer"
}

# 查看团队信息
GET /admin/team/settings
```

## 下一步

- [许可证管理](/docs/license)
- [Enterprise 功能](/docs/enterprise)
- [API 参考](/docs/api)
