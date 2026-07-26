# Dify 知识库上传清单 — AI Privacy Gateway

> ⚠️ **安全红线：本清单中的文件不含任何 API Key、密钥、密码。实际 .env 永远不上传。**

## 可安全上传的文件

| 文件 | 用途 | Dify 分段策略 |
|------|------|--------------|
| `docs/knowledge-seed-zh.md` | 产品知识主文档 | 按 H2 标题分段，500-1000 tokens/chunk |
| `README.md` | GitHub README | 按 ## 标题分段 |
| `README_CN.md` | 中文 README | 按 ## 标题分段 |
| `CHANGELOG.md` | 版本历史 | 父级文档，关联到产品知识 |
| `website-astro/src/pages/docs/quickstart.md` | 快速开始 | 按步骤分段 |
| `website-astro/src/pages/docs/deploy.md` | 部署指南 | 按部署方式分段 |
| `website-astro/src/pages/docs/config.md` | 配置参考 | 按配置类别分段 |
| `website-astro/src/pages/docs/architecture.md` | 架构说明 | 按模块分段 |
| `website-astro/src/pages/docs/api.md` | API 参考 | 按端点分段 |
| `website-astro/src/pages/docs/keywords.md` | 自定义规则 | 按规则类型分段 |
| `website-astro/src/pages/compare.astro` | 竞品对比 | 整个页面作为一个文档 |

## 绝对禁止上传的文件

| 文件 | 原因 |
|------|------|
| `.env` / `.env.local` | 包含真实 API 密钥 |
| `vault_data/` 整个目录 | 包含加密的 PII 映射数据 |
| `vault_data/.secrets.json` | 包含 JWT_SECRET、ADMIN_PASSWORD 等 |
| `*.pem` / `*.key` | SSL 私钥 |
| `bandit_results.json` | 可能暴露内部路径 |

## Dify 推荐的 System Prompt

```
你是 AI Privacy Gateway 的智能客服。基于知识库中的产品文档回答用户问题。

规则：
1. 只回答知识库中有依据的问题
2. 如果用户问价格，引导到 /pricing 页面
3. 如果问技术问题，提供准确的代码示例和命令
4. 不要编造不存在的信息
5. 回答尽量简短，复杂问题分点列出
```

## 知识库更新流程

1. 产品有新版本时，更新 `knowledge-seed-zh.md`
2. 在 Dify 中重新上传更新的文档
3. 删除旧版本的知识片段
4. 测试几个常见问题确认准确度
