# 网站 AI 感重设计计划

> 2026-06-06 | 目标：让官网传达出 AI 数据隐私产品应有的智能感与品质感

## 差距分析

对比 Anthropic/OpenAI 官网，当前网站的不足：

| 维度 | 当前状态 | 目标效果 (Anthropic/OpenAI 风格) |
|------|---------|-------------------------------|
| 背景 | 冷黑色 `#0d0d12`，扁平无层次 | 深靛黑带暖底调，径向渐变光球营造氛围 |
| 主色 | 荧光绿 `#a3e635`，像终端命令行 | 精致翠绿 `#86efac`，克制且现代 |
| 材质 | 纯色卡片 + 细边框 | 毛玻璃卡片 (`backdrop-filter: blur`)、微弱边框光晕 |
| 排版 | 系统默认字体 | Inter 字体 + 紧凑字间距，多变字重 |
| 氛围 | 无背景装饰 | 网点纹理 + 渐变光球 + 光晕呼吸动画 |

## 改造方案

### 一、色调体系重塑

```
背景:   #0d0d12 → #06060c (深靛黑，带极微蓝/紫底调)
表面:   #12121a → #0e0e18 → #131320 (加入暖度)
主色:   #a3e635 → #86efac (翠绿，精致柔和)
辅色:   紫色 #a78bfa (AI/智能感)、琥珀 #fbbf24 (强调)
```

### 二、氛围系统

- **网点纹理** — CSS `radial-gradient` 生成全局微网点背景
- **渐变光球** — 各 section 放置 600-800px 径向渐变球体
- **光晕呼吸** — CSS `@keyframes` 20s 循环缩放/透明度变化

### 三、毛玻璃卡片

```css
.glass {
  background: rgba(255,255,255,0.02);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.06);
}
.glass:hover { border-color: rgba(255,255,255,0.12); }
```

### 四、排版升级

- 引入 Google Fonts **Inter**（标题），系统字体（正文中文）
- 标题 `letter-spacing: -0.04em ~ -0.02em`
- 字重: 600 (标题) / 500 (副标题) / 400 (正文)

### 五、首页各区域改法

1. **Hero** — 背景放大渐变光球，标题更紧凑，代码块毛玻璃化
2. **问题区** — 三列保持，加入微弱图标
3. **功能 Bento** — 全部改为毛玻璃卡片 + 边框光晕
4. **工作原理** — 三步卡片加横向连接线，增强数据流动感
5. **版本** — 推荐卡片加背景光晕
6. **CTA** — 超大型径向渐变光球做背景

## 涉及文件

- `website-astro/src/layouts/Layout.astro` — 全局样式重写
- `website-astro/src/pages/index.astro` — 首页重写

## 验证方式

```bash
cd website-astro && npx astro build
npx wrangler pages deploy dist/ --project-name privacygw --branch main
# 浏览器验证 https://privacygw.pages.dev/
```
