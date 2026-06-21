# 自动化发布方案

> 基于 2026 年各平台 API 能力和反自动化策略调研
> 核心原则：有 API 的全自动，无 API 的半自动（草稿同步+人工发布），高风险平台纯手动

---

## 一、平台分层

### Tier 1: 全自动（低风险，有官方 API）

| 平台 | API 类型 | 认证 | 频率限制 | 注意事项 |
|------|---------|------|---------|---------|
| **Dev.to** | REST API v1 | API Key (Header) | 10 次/30s | canonical_url 字段支持，最多 4 个标签 |
| **Hashnode** | GraphQL | PAT Token | 500 次/min | publication 需要先 allow-list |
| **Docker Hub** | REST v2 | JWT (用户名+密码) | 数千次/min | 仅更新描述，不发布内容 |
| **百度站长** | REST | Token (URL参数) | 新站 6 条/天，成熟站数千-10万 | 仅提交 URL，不发布内容 |

### Tier 2: 半自动（中等风险，无公开 API 但可逆向）

| 平台 | 方式 | 认证 | 频率限制 | 注意事项 |
|------|------|------|---------|---------|
| **Reddit** | PRAW/Snoowrap (OAuth) | OAuth 2.0 | 100 QPM | 账号需 30 天+100 karma，10% 自推广规则 |
| **CSDN** | HMAC-SHA256 签名 API | Cookie + 签名 | 无硬性限制 | AI+人工双审，SimHash 查重 |
| **掘金** | Cookie-based 内部 API | sessionid Cookie | 无硬性限制 | AI 内容检测，建议草稿+人工发布 |

### Tier 3: 纯手动（高风险，自动化极可能被封）

| 平台 | 原因 | 建议 |
|------|------|------|
| **Hacker News** | 无 POST API，Cloudflare 检测，headless 检测 | 手动发布 |
| **知乎** | JSVMP 保护，三层防御，WASM 签名 | 手动发布 |
| **ProductHunt** | 写 API 需人工审批 | 手动发布 |
| **Twitter/X** | 带链接推文 $0.20/条 | 手动或用 Buffer |

---

## 二、平台准入阶梯（养号路线图）

> 大部分平台不是注册就能发长文的。需要按阶梯逐步解锁权限。

### 2.0 通用养号框架（4 周）

所有平台通用的行为模式：

```
Week 1 (观察期):  仅浏览、点赞，不发文不评论
Week 2 (轻互动):  点赞 + 收藏 + 关注话题，每天 1-2 条评论
Week 3 (内容创作): 发布第一篇短内容，积极参与评论互动
Week 4 (正常运营): 按 50% 容量运营，逐步提升频率
```

**反自动化检测信号（所有平台共享）：**
- 速度异常：创建后立即大量活动 → 触发风控
- IP 信誉：VPN/机房 IP 注册 → HN/Reddit 直接 shadowban
- 内容均匀度：跨平台发完全相同的内容 → 查重标记
- 外链比例：高比例指向同一域名的外链 → 营销标记
- 互动不对称：只发不评、只赞不发 → 机器人标记
- 时间规律：固定时间间隔无波动 → 自动化标记

---

### 2.1 掘金 — 掘力值阶梯

| 等级 | 掘力值 | 解锁内容 |
|------|--------|---------|
| Lv1 | 1-99 | 可发文章（审核制），每日计分上限 2 篇 |
| Lv2 | 100-499 | 文章标签数增加 |
| Lv3 | 500-1,999 | 更多曝光权重 |
| Lv4 | 5,000+ | **首页自动推荐**（关键节点） |
| Lv5 | 10,000+ | 小册写作权限 |

**掘力值获取：**
- 发布原创专栏 +10 JP/篇（每天最多 2 篇计分）
- 高质量认定 +15 JP/篇
- 点赞 +1 JP/个，阅读量 /100
- 沸点动态不计分

**养号路径：**
1. 注册 → 手机验证 → 完善资料 → 关注 5-10 个标签
2. 前 3 天：每天浏览、点赞 5-10 篇、收藏 2-3 篇
3. 第 4-7 天：开始发沸点（短动态），每天 1-2 条，参与话题讨论
4. 第 2 周起：每天 1 篇原创技术文章（500-800 字，配图 2-3 张）
5. 预计 2-3 周 → Lv3，1-2 个月 → Lv4（获得推送流量）

**注意：** 掘金纯技术社区，非技术内容效果极差。不要互赞交易。

---

### 2.2 CSDN — 博客等级阶梯

| 等级 | 积分 | 每日发文上限 | 解锁 |
|------|------|-------------|------|
| Lv1 | 0-99 | 2 篇 | 评论 15 条/天 |
| Lv2 | 100-399 | 2 篇 | — |
| Lv3 | 400-1,599 | 5 篇 | — |
| Lv4 | 1,600-5,999 | 5 篇 | 自定义域名 |
| Lv5 | 6,000+ | 10 篇 | 付费资源 |

**积分获取：**
- 原创文章 +10 分/篇
- 转载 +2 分/篇
- 文章被评论 +1 分/次
- 阅读量 >100 +1 分/篇（每篇上限 100 分）

**养号路径：**
1. 注册 → 完善资料 → 关注 5+ 个相关领域
2. 前 3 天：浏览文章、收藏、在他人文章下评论（每天 5-10 条有内容的评论）
3. 第 4 天起：每天 2 篇原创 + 2 篇转载，评论区积极互动
4. 每天约 50 分增长 → 2-3 天 Lv2，1-2 周 Lv3

**注意：** 不要每天发满配额上限，会被识别为批量操作。Lv1 时点赞上限 15 次。

---

### 2.3 知乎 — 创作等级阶梯（最复杂）

| 等级 | 要求 | 解锁 |
|------|------|------|
| Lv1 | 绑定手机 + 发布 1 条内容（>100 字回答或 >30 字想法） | 基础发文 |
| Lv2 | 创作分 100+ | — |
| Lv3 | 创作分 500+ | 文章功能解锁 |
| Lv4 | 创作分 2,500+ | **致知计划**（变现），关键节点 |
| Lv5+ | 创作分 10,000+ | 更多流量权重 |

**创作分维度（六维）：**
- 创作活跃度、创作垂直度、社区成就分、创作影响力、内容优质分、关注者亲密度
- 500 字以上的回答/文章可获得优质分（每周更新）
- 每日创作任务奖励 20-65 分

**⚠ 关键限制：新号不能立即发文章！**
1. 先进入「创作中心」→ 完善资料 → 绑定手机
2. 发一条 >100 字回答或 >30 字想法 + 配图
3. 等待 10-30 分钟审核 → 达到 Lv1
4. 继续积累到 Lv3（创作分 500+）才能正常发布文章

**养号路径：**
1. 注册 → 完善资料 → 关注 10+ 个相关话题
2. 前 3 天：浏览、点赞、收藏回答，不评论
3. 第 4-7 天：每天回答 1-2 个推荐问题（500-1500 字），发 1-2 条想法
4. 第 2 周起：坚持每天回答 + 想法，争取 Lv3
5. 达到 Lv3 → 可发文章
6. 约 2 周 → Lv4（获得流量推荐）

**注意：** 一年只能修改 5 次垂直领域。删除内容直接扣分（有被扣 755 分的案例）。AI 内容需加 AI 辅助声明。点赞频率不要 >10 次/分钟。知乎有 JSVMP WASM 三层防御——**绝对不要尝试自动化**。

---

### 2.4 博客园 — 申请制（最低门槛）

**唯一门槛：** 人工审核申请表（理由 + 真实姓名 + 职位 + 公司 + 技术兴趣）
- 9:00-22:00 提交通常 1 小时内处理
- 理由写「记录技术成长」「分享学习笔记」即可通过
- 不要写「SEO」「推广」「营销」
- 通过后无任何限制：无每日上限、无等级系统、无复杂解锁

**策略：** 作为首发平台，通过后直接同步掘金/CSDN 内容。注意博客园偶尔会因服务器成本关闭注册。

---

### 2.5 SegmentFault — 声望系统

| 声望 | 解锁 |
|------|------|
| 0 | 注册后仅浏览 |
| 15+ | 完成 5 个新手任务 |
| 100 | 维基编辑、用户认证申请 |
| 500 | 参与众审中心 |
| 1000 | 头条发布权限 |

**⚠ 新号内容进众审中心**，由社区审核通过才能公开。首篇文章建议在积累声望后再发。

**养号路径：**
1. 注册 → 邮箱激活 → 完成 5 个新手任务（约 15 分钟）→ 声望 15+
2. 每天回答 1-2 个技术问题（>200 字详细回答）
3. 前 1-2 天不发文章，先靠回答积累声望
4. 声望 100+ 后再发文章，审核会宽松很多
5. 2-3 天可达 100 声望

---

### 2.6 Dev.to — 信任成员系统

**无硬性发文上限**，但算法对新号高频发文极度压制（实测：一天发 5 篇 = 总共 11 次浏览）。

**隐藏的「Trusted Member」系统：**
- 不公开评分，算法授予
- 解锁内容质量排名、经验等级评分、管理员标记
- 通常需要数月到数年的活跃

**养号路径：**
1. Week 1：浏览、点赞 1-2 篇，不发文不评论
2. Week 2：点赞 5-10 篇，关注 3-5 个账号，每天 1-2 条评论
3. Week 3：发第一篇文章，积极互动
4. Week 4+：按 50% 容量运营，最多每天 1 篇

**9:1 规则：** 每 1 篇自推广内容，需要 9 篇社区贡献（评论、点赞、分享他人内容）。

---

### 2.7 Hashnode — 几乎零门槛

- 注册即可发文，无数量限制
- 无 karma/声望系统
- 免费版 1 个 publication，Pro 版 10 个
- API 仅 Pro 版可用

**策略：** 首发友好平台，注册即发。无养号顾虑。

---

### 2.8 Reddit — 最严格的阶梯

**Karma 门槛：**

| 阶段 | Karma | 解锁 |
|------|-------|------|
| 0-50 | 大部分 subreddit 自动删帖 | 仅浏览 + 评论 |
| 50-500 | 基本访问 | 可在多数中型 sub 发帖 |
| 500-2,000 | 减少限速 | 稳定发文 |
| 2,000-10,000 | 高可见度 | 几乎无限制 |

**CQS（Contributor Quality Score，隐藏评分）：**
- 五档：Lowest → Highest
- 影响因素：邮箱/手机验证、赞踩比、内容被删历史、被举报数、发文速度、外链比例、VPN 使用
- CQS 可升可降，按 subreddit 分别计算
- 检测方式：r/WhatIsMyCQS

**养号路径：**
1. 前 2-5 天：纯浏览
2. 第 1 周：在 r/AskReddit、r/CasualConversation 等大 sub 评论
3. 第 2 周起：在目标 subreddit 的「new」排序中抢先评论，每天 2-3 条
4. 评论间隔 15-30 分钟以上
5. 预计到 100 karma：1-2 周。到 2000 karma：3-6 个月

---

### 2.9 Hacker News — 最敏感

**新号限制：**
- 绿色用户名标记
- VPN 注册 → 直接 shadowban
- 发链接权限：约需 5-7 天
- 发帖频率限制：约 4-5 条/小时

**提交过滤器：** 只提交自己的链接 → 系统自动过滤。需混合不同来源的高质量链接。

**养号路径：**
1. 前 1 周：只读、upvote
2. 第 2 周：发深度评论（不放链接）
3. 至少 5-7 天后才发链接，混合来源

**绝对不要尝试任何形式的自动化。** Cloudflare + headless 检测。

---

### 2.10 ProductHunt — 7 天冷却期

- 注册后 7 天等待期才能发产品
- 必须个人账号（真人头像 + 真实姓名）
- 公司号不能发帖/评论/投票
- 建议提前 30 天创建并预热

---

### 平台准入难度总表

| 平台 | 注册即发 | 等待期 | 核心门槛 | 养号周期 |
|------|:---:|------|------|:---:|
| Hashnode | ✅ | 无 | 无 | 0 天 |
| 博客园 | ✅ | 1h 审核 | 申请理由 | 0 天 |
| Dev.to | ✅ | 无 | 算法压制 | 2 周 |
| CSDN | ✅ | 无 | Lv1=2篇/天 | 1 周 |
| 掘金 | ✅ | 无 | 掘力值 Lv4 | 1-2 月 |
| Medium | ✅ | 无 | 2篇/天 | 1 周 |
| SegmentFault | ⚠ | 众审 | 声望 100 | 2-3 天 |
| 知乎 | ❌ | — | Lv3 才能发文章 | 2-3 周 |
| Reddit | ❌ | — | 100+ karma | 1-2 周 |
| HN | ❌ | 5-7 天 | 提交过滤器 | 1-2 周 |
| ProductHunt | ❌ | 7 天 | 个人号 | 30 天 |

---

## 三、自动化发布脚本

### 2.1 Dev.to + Hashnode 自动化发布器

```python
#!/usr/bin/env python3
"""
多平台自动化发布器 — Dev.to + Hashnode
用法:
  python auto_publisher.py --article docs/marketing/devto-hashnode.md --platform devto
  python auto_publisher.py --article docs/marketing/devto-hashnode.md --platform hashnode
  python auto_publisher.py --article docs/marketing/devto-hashnode.md --platform all
"""

import os
import json
import time
import random
import argparse
import requests
from pathlib import Path
from typing import Optional

# ========== 配置 ==========

def load_config():
    """从环境变量加载 API 密钥"""
    config = {
        'devto': {
            'api_key': os.environ.get('DEVTO_API_KEY', ''),
            'base_url': 'https://dev.to/api',
        },
        'hashnode': {
            'pat': os.environ.get('HASHNODE_PAT', ''),
            'publication_id': os.environ.get('HASHNODE_PUBLICATION_ID', ''),
            'api_url': 'https://gql.hashnode.com',
        }
    }

    missing = []
    if not config['devto']['api_key']:
        missing.append('DEVTO_API_KEY')
    if not config['hashnode']['pat']:
        missing.append('HASHNODE_PAT')
    if not config['hashnode']['publication_id']:
        missing.append('HASHNODE_PUBLICATION_ID')

    if missing:
        print(f"[!] 缺少环境变量: {', '.join(missing)}")
        print("[!] 请设置后重试，例如:")
        print("    export DEVTO_API_KEY=your_key_here")
        print("    export HASHNODE_PAT=your_pat_here")
        print("    export HASHNODE_PUBLICATION_ID=your_publication_id")
        print("[!] 或创建 .env 文件（不会被提交到 git）")
        return None

    return config


# ========== Dev.to 发布器 ==========

class DevToPublisher:
    """Dev.to Forem API v1 发布器"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://dev.to/api'
        self.session = requests.Session()
        self.session.headers.update({
            'api-key': api_key,
            'Content-Type': 'application/json',
            'accept': 'application/vnd.forem.api-v1+json',
        })

    def create_article(
        self,
        title: str,
        body_markdown: str,
        tags: list[str],
        canonical_url: Optional[str] = None,
        published: bool = True,
        series: Optional[str] = None,
        main_image: Optional[str] = None,
    ) -> dict:
        """
        发布文章到 Dev.to
        tags: 最多 4 个，仅字母数字（无空格、无连字符、无特殊字符）
        canonical_url: 用于跨平台 SEO 的规范链接
        """
        # 清理标签: 只保留字母数字
        clean_tags = []
        for tag in tags[:4]:
            cleaned = ''.join(c for c in tag.lower() if c.isalnum())
            if cleaned and len(cleaned) <= 30:
                clean_tags.append(cleaned)

        if not clean_tags:
            clean_tags = ['ai', 'privacy', 'security']

        payload = {
            'article': {
                'title': title,
                'body_markdown': body_markdown,
                'tags': clean_tags,
                'published': published,
            }
        }

        if canonical_url:
            payload['article']['canonical_url'] = canonical_url

        if series:
            payload['article']['series'] = series

        if main_image:
            payload['article']['main_image'] = main_image

        # 速率限制: 最多 10 次/30s，这里保守一点每次请求后等待 3 秒
        time.sleep(random.uniform(3, 5))

        resp = self.session.post(f'{self.base_url}/articles', json=payload)

        if resp.status_code == 201:
            data = resp.json()
            print(f"[Dev.to] ✓ 发布成功: {data.get('url', data.get('id'))}")
            return data
        elif resp.status_code == 429:
            retry_after = resp.headers.get('Retry-After', 30)
            print(f"[Dev.to] ⚠ 速率限制，等待 {retry_after}s")
            time.sleep(int(retry_after) + random.uniform(1, 5))
            return self.create_article(title, body_markdown, tags, canonical_url, published)
        else:
            print(f"[Dev.to] ✗ 发布失败 ({resp.status_code}): {resp.text[:200]}")
            return {}

    def get_published_articles(self, page: int = 1) -> list:
        """获取已发布文章列表"""
        resp = self.session.get(f'{self.base_url}/articles/me/published', params={'page': page})
        if resp.status_code == 200:
            return resp.json()
        return []

    def update_article(self, article_id: int, **kwargs) -> dict:
        """更新已有文章"""
        time.sleep(random.uniform(2, 4))
        resp = self.session.put(
            f'{self.base_url}/articles/{article_id}',
            json={'article': kwargs}
        )
        if resp.status_code == 200:
            print(f"[Dev.to] ✓ 更新成功: article/{article_id}")
            return resp.json()
        print(f"[Dev.to] ✗ 更新失败: {resp.status_code}")
        return {}


# ========== Hashnode 发布器 ==========

class HashnodePublisher:
    """Hashnode GraphQL API 发布器"""

    def __init__(self, pat: str, publication_id: str):
        self.pat = pat
        self.publication_id = publication_id
        self.api_url = 'https://gql.hashnode.com'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': pat,
            'Content-Type': 'application/json',
        })

    def publish_post(
        self,
        title: str,
        content_markdown: str,
        tags: list[dict] = None,
        canonical_url: Optional[str] = None,
        subtitle: Optional[str] = None,
        cover_image_url: Optional[str] = None,
    ) -> dict:
        """
        发布文章到 Hashnode
        tags: [{"slug": "ai", "name": "AI"}, ...]
        """
        if tags is None:
            tags = [
                {"slug": "ai", "name": "AI"},
                {"slug": "security", "name": "Security"},
                {"slug": "privacy", "name": "Privacy"},
            ]

        # 构建 GraphQL mutation
        query = """
        mutation PublishPost($input: PublishPostInput!) {
            publishPost(input: $input) {
                post {
                    id
                    slug
                    url
                    title
                }
            }
        }
        """

        variables = {
            'input': {
                'title': title,
                'publicationId': self.publication_id,
                'contentMarkdown': content_markdown,
                'tags': tags,
            }
        }

        if canonical_url:
            variables['input']['originalArticleURL'] = canonical_url

        if subtitle:
            variables['input']['subtitle'] = subtitle

        if cover_image_url:
            variables['input']['coverImageOptions'] = {
                'coverImageURL': cover_image_url
            }

        # Hashnode 速率限制: 500 次/min，每次请求间隔 2-3s
        time.sleep(random.uniform(2, 3))

        resp = self.session.post(
            self.api_url,
            json={'query': query, 'variables': variables}
        )

        if resp.status_code == 200:
            data = resp.json()
            if 'errors' in data:
                print(f"[Hashnode] ✗ GraphQL 错误: {data['errors']}")
                return {}
            post = data.get('data', {}).get('publishPost', {}).get('post', {})
            print(f"[Hashnode] ✓ 发布成功: {post.get('url', post.get('id'))}")
            return post
        elif resp.status_code == 429:
            retry_after = resp.headers.get('Retry-After', 30)
            print(f"[Hashnode] ⚠ 速率限制，等待 {retry_after}s")
            time.sleep(int(retry_after) + random.uniform(1, 5))
            return self.publish_post(title, content_markdown, tags, canonical_url)
        else:
            print(f"[Hashnode] ✗ 发布失败 ({resp.status_code}): {resp.text[:200]}")
            return {}


# ========== 主程序 ==========

def main():
    parser = argparse.ArgumentParser(description='多平台自动化发布器')
    parser.add_argument('--platform', choices=['devto', 'hashnode', 'all'], default='all')
    parser.add_argument('--title', required=True, help='文章标题')
    parser.add_argument('--content', help='Markdown 内容文件路径或直接内容')
    parser.add_argument('--tags', nargs='*', default=['ai', 'privacy', 'security'], help='标签(最多4个)')
    parser.add_argument('--canonical-url', help='规范链接（跨平台 SEO）')
    parser.add_argument('--dry-run', action='store_true', help='仅检查配置，不实际发布')
    parser.add_argument('--published', action='store_true', default=True, help='是否立即发布（默认是）')
    parser.add_argument('--draft', action='store_true', help='保存为草稿')

    args = parser.parse_args()

    # 加载配置
    config = load_config()
    if not config:
        return 1

    # 读取内容
    content = args.content
    if content and Path(content).exists():
        content = Path(content).read_text(encoding='utf-8')

    if not content:
        print("[!] 请提供 --content 参数")
        return 1

    if args.dry_run:
        print("[DRY RUN] 配置检查通过")
        print(f"  标题: {args.title}")
        print(f"  标签: {args.tags}")
        print(f"  Canonical URL: {args.canonical_url}")
        print(f"  内容长度: {len(content)} 字符")
        print(f"  平台: {args.platform}")
        return 0

    published = not args.draft

    # 发布到 Dev.to
    if args.platform in ('devto', 'all'):
        if config['devto']['api_key']:
            publisher = DevToPublisher(config['devto']['api_key'])
            publisher.create_article(
                title=args.title,
                body_markdown=content,
                tags=args.tags,
                canonical_url=args.canonical_url,
                published=published,
            )
        else:
            print("[Dev.to] 跳过: 缺少 API Key")

    # 发布到 Hashnode
    if args.platform in ('hashnode', 'all'):
        if config['hashnode']['pat'] and config['hashnode']['publication_id']:
            publisher = HashnodePublisher(
                config['hashnode']['pat'],
                config['hashnode']['publication_id']
            )

            # 转换标签格式
            hnode_tags = [{'slug': t.lower().replace(' ', ''), 'name': t} for t in args.tags[:5]]

            publisher.publish_post(
                title=args.title,
                content_markdown=content,
                tags=hnode_tags,
                canonical_url=args.canonical_url,
            )
        else:
            print("[Hashnode] 跳过: 缺少 PAT 或 Publication ID")

    print("\n✓ 发布完成")


if __name__ == '__main__':
    main()
```

**使用方法:**

```bash
# 1. 设置环境变量（或写入 .env）
export DEVTO_API_KEY="your_devto_api_key"
export HASHNODE_PAT="your_hashnode_pat"
export HASHNODE_PUBLICATION_ID="your_publication_id"

# 2. 发布文章
python auto_publisher.py \
  --title "What Happens to Your Data When You Use ChatGPT" \
  --content blog-article.md \
  --tags ai privacy security opensource \
  --canonical-url "https://privacygw.pages.dev/blog/what-happens-chatgpt-data" \
  --platform all

# 3. 仅检查配置
python auto_publisher.py --title "test" --content "test" --dry-run
```

### 2.2 Reddit 发布器（需养号）

```python
#!/usr/bin/env python3
"""
Reddit 自动化发布器 — 使用 PRAW
⚠ 使用前必须:
  1. 账号 >30 天
  2. 评论 karma >100
  3. 遵守 10% 自推广规则（90% 内容为非推广）
  4. 每天最多 2-3 篇
"""

import os
import time
import random
import argparse

try:
    import praw
except ImportError:
    print("[!] 请先安装: pip install praw")
    exit(1)


class RedditPublisher:
    """Reddit 安全发布器"""

    # 发布间隔 (秒): 最少 15 分钟，加随机抖动
    MIN_POST_INTERVAL = 900  # 15 分钟
    MAX_DAILY_POSTS = 3       # 每天最多

    def __init__(self):
        self.reddit = praw.Reddit(
            client_id=os.environ.get('REDDIT_CLIENT_ID', ''),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET', ''),
            user_agent="AI-Privacy-GW/1.0 by /u/YOUR_USERNAME (educational tool)",
            username=os.environ.get('REDDIT_USERNAME', ''),
            password=os.environ.get('REDDIT_PASSWORD', ''),
        )
        self.daily_count = 0

    def check_account_status(self) -> bool:
        """检查账号状态"""
        try:
            me = self.reddit.user.me()
            if me is None:
                print("[!] 认证失败，请检查凭据")
                return False

            created_days = (time.time() - me.created_utc) / 86400
            print(f"[*] 账号: u/{me.name}")
            print(f"[*] 注册天数: {created_days:.0f}")
            print(f"[*] 评论 karma: {me.comment_karma}")
            print(f"[*] 帖子 karma: {me.link_karma}")

            if created_days < 30:
                print("[!] 警告: 账号不足 30 天，发帖风险极高")

            if me.comment_karma < 100:
                print("[!] 警告: 评论 karma 不足 100，发帖风险极高")

            return True
        except Exception as e:
            print(f"[!] 账号检查失败: {e}")
            return False

    def post_to_subreddit(
        self,
        subreddit_name: str,
        title: str,
        content: str,
        flair: str = None,
        dry_run: bool = False,
    ):
        """发布到指定 subreddit"""
        if self.daily_count >= self.MAX_DAILY_POSTS:
            print(f"[!] 今天已发 {self.daily_count} 篇，达上限")
            return None

        # 检查 subreddit 是否存在
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            # 尝试获取规则
            subreddit.rules()
        except Exception as e:
            print(f"[!] subreddit r/{subreddit_name} 访问异常: {e}")
            return None

        if dry_run:
            print(f"[DRY RUN] r/{subreddit_name}")
            print(f"  标题: {title}")
            print(f"  内容: {content[:100]}...")
            return None

        # 发布前随机等待（模拟人类操作）
        wait = random.uniform(5, 15)
        print(f"[*] 等待 {wait:.1f}s 后发布...")
        time.sleep(wait)

        try:
            submission = subreddit.submit(title=title, selftext=content)
            print(f"[Reddit] ✓ 发布成功: {submission.url}")
            print(f"[*] 帖子 ID: {submission.id}")
            self.daily_count += 1
            return submission
        except Exception as e:
            print(f"[Reddit] ✗ 发布失败: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description='Reddit 安全发布器')
    parser.add_argument('--subreddit', required=True, help='目标 subreddit')
    parser.add_argument('--title', required=True, help='帖子标题')
    parser.add_argument('--content', help='帖子内容（Markdown 文本）')
    parser.add_argument('--dry-run', action='store_true', help='不实际发布')
    args = parser.parse_args()

    publisher = RedditPublisher()

    if not publisher.check_account_status():
        return 1

    content = args.content or ""
    if args.content and os.path.exists(args.content):
        content = open(args.content, encoding='utf-8').read()

    publisher.post_to_subreddit(
        subreddit_name=args.subreddit,
        title=args.title,
        content=content,
        dry_run=args.dry_run,
    )


if __name__ == '__main__':
    main()
```

---

## 四、各平台发布时机

### Reddit

| Subreddit | 最佳时间 | 帖子类型 | 频率 |
|-----------|---------|---------|------|
| r/selfhosted | 周六/日 上午 (US) | 项目公告 | 1 次 |
| r/ChatGPT | 工作日 EST 上午 | 教育+提及 | 1 次 |
| r/ClaudeAI | 工作日 | 教育+提及 | 1 次 |
| r/programming | 周二-周四 EST 上午 | 技术深度 | 1 次 |
| r/privacy | 周末上午 | 工具公告 | 1 次 |
| r/devops | 工作日 EST 上午 | DevOps 教程 | 1 次 |

**关键规则:**
- 本周已发过推广贴 > 5 篇时暂停
- 每篇帖子发布间隔至少 4 小时
- 发布后 1-2 小时内回复评论
- 不同 subreddit 的帖子内容要有差异化

### Dev.to

- 最佳: 周二/周三 EST 上午
- 频率: 每周 1 篇
- 每篇加 canonical URL 指向官网

### 掘金 / CSDN

- 最佳: 工作日 上午 10:00 或 下午 14:00 (北京时间)
- 频率: 新号每天 ≤1 篇，成熟号每天 ≤3 篇
- 发布间隔 ≥1 小时
- CSDN: 使用 SEO 友好的标题

---

## 五、百度站长 URL 提交

```python
#!/usr/bin/env python3
"""百度站长平台 URL 提交"""
import requests

def submit_baidu(urls: list[str], site: str, token: str):
    """提交 URL 到百度站长平台"""
    api_url = f'http://data.zz.baidu.com/urls?site={site}&token={token}'
    body = '\n'.join(urls)
    resp = requests.post(api_url, data=body.encode('utf-8'))
    result = resp.json()
    print(f"[百度] 提交 {result.get('success_count', 0)}/{len(urls)} 条")
    print(f"[百度] 剩余配额: {result.get('remain', 'N/A')}")
    return result

# 用法:
# submit_baidu(
#     urls=['https://privacygw.pages.dev/protect-chatgpt-privacy'],
#     site='privacygw.pages.dev',
#     token='YOUR_BAIDU_TOKEN'
# )
```

---

## 六、Docker Hub 描述更新

```bash
# 更新 Docker Hub 仓库描述
# 需要先用 docker login 登录

TOKEN=$(curl -s -X POST https://hub.docker.com/v2/users/login \
  -H "Content-Type: application/json" \
  -d '{"username":"'$DOCKER_USER'","password":"'$DOCKER_PASS'"}' | jq -r '.token')

curl -X PATCH https://hub.docker.com/v2/repositories/gunxueqiu6/ai-privacy-gateway \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"full_description": "'"$(cat docs/marketing/dockerhub-producthunt.md | jq -Rs .)"'"}'
```

---

## 七、安全发布检查清单

### 发布前

- [ ] 账号已预热（min 30 天 + 相关活动）
- [ ] 内容非 100% AI 生成（有实质性人工修改）
- [ ] 标签不超过平台限制（Dev.to: 4, Hashnode: 5, Reddit: 取决于 subreddit）
- [ ] canonical URL 已设置（指向官网）
- [ ] 发布间隔已随机化（不是固定时间）
- [ ] `--dry-run` 已通过

### 发布后

- [ ] 确认文章在平台上可见
- [ ] 1-2 小时内回复评论
- [ ] 记录发布日志: 平台、URL、时间
- [ ] 不要同时在多个平台发完全相同的内容
