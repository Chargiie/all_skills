---
name: travel-guide-mobile-pdf
description: >-
  生成适合手机竖屏阅读、可分享的旅游攻略 PDF（HTML→Chromium→PDF），小红书/公众号编辑风。
  当用户要「旅游/citywalk/周末出游/行程攻略」且要「手机看的 PDF / 可分享」时使用。
  不适用于桌面打印 A4 报告、纯文本回答。
---

# 旅游攻略手机 PDF Skill

生成适合手机竖屏阅读、可分享的旅游攻略 PDF。**目标观感 = 小红书/公众号编辑风**：暖色调、信息密、有视觉重点、卡片化、emoji 引导视线。参数来自真实排版经验（px），按 `pt = px × 0.75` 换算到 PDF。

> ⚠️ 这不是"极简白底报告"。攻略要好看、好逛、想分享。素、空、无重点 = 失败。

## When to use
- 旅游攻略 / citywalk / 周末出游 / 多日行程，出口是**手机**、要 **PDF 或可分享卡片**
- **不适用**：纯文本回答、桌面 A4 报告、数据驱动可复现文档（那走 reportlab）

## 技术栈
HTML → Chromium(Playwright) → PDF。强视觉攻略用 HTML+Chrome 最顺手；不要走 LaTeX/reportlab。

## 工作流程
1. **需求拆解**：人数 / 天数 / 出发地 / 预算 / 节奏 / 必去点 / 硬性要求（如「两套路线」「机酒价」）。
2. **信息核查**：`web_search` 查真实店名 / 民宿 / 景点 / 价格区间，**禁编造**；无 live 价时标「估算 + 时间」。
3. **写 HTML 源**：选暖色主题 → 全屏封面 → 编号点位卡 → 交通/Tips → 收尾。遵守下方 Operational Rules。
4. **渲染 PDF**：`node scripts/render_mobile.cjs source.html out.pdf`（300pt×667.5pt，满版无白边）。
5. **自检**：双门（pdfinfo + pdfimages）+ 链接 spot-click + 目视密度/重点/配色。
6. **交付**。

## 页面尺寸（锁定）
目标设备 2670×1200（≈9:20 竖屏，高分屏 DPR3 → 逻辑视口 ≈400×890 CSS px）。

- **MUST** `@page { size: 300pt 667.5pt; margin: 0 }`（≈106×235mm，9:20，满屏无黑边）。
- **MUST** 显式物理尺寸；**MUST NOT** 用 `100vh/100vw`、**MUST NOT** 横屏。
- **MUST** 背景色满版铺到 `html, body`，跨页连续——内容自然流式分页，**翻页处不能出现白条/断裂**。
- **MUST NOT** 给每段强行 `page-break-before`（#1 amateurish 标志）；只在 `.section-card` / `.place-card` 上加 `break-inside: avoid` 避免标题被切。
- 自洽：正文 11pt 在 300pt 宽页 ≈ 手机 14.7px，落在人类经验 14–15px 区间。

## 版面骨架（必须照搭）
内容**满版**，留白靠内边距而非页边距。所有横向内边距在 CSS 控制，**不要**靠 Playwright 页边距。

```css
* { margin:0; padding:0; box-sizing:border-box; print-color-adjust:exact; -webkit-print-color-adjust:exact; }
html, body { background:#FAF6EC; }              /* 满版米色，跨页连续 */
.cover  { background:#C85A3C; color:#fff; padding:30pt 20pt 22pt; }  /* 封面满版色块 */
.body   { padding:18pt 16pt 0; }                /* 正文区横向内边距，内容不贴边 */
.place-card  { background:#fff; border-radius:12pt; padding:16pt; margin-bottom:14pt; break-inside:avoid; }
.callout { background:#FBEFE7; border-left:3pt solid #5A7052; border-radius:8pt; padding:11pt 13pt; }
```

封面套路（最稳）：小字母间距 eyebrow（如 `SHANGHAI · CITY WALK`）→ 大号粗体标题 → 一排 emoji 信息胶囊（`👫 2人` / `🕛 中午出发` / `🍡 逛吃为主`）。

## Operational Rules（生成时硬约束，非建议）

### 字号与行距
1. 正文 **10.5–11pt**，行距 **1.5–1.7**。
2. 标题 H1 **18–24pt** / H2 **13–15pt** / H3 **11.5–12pt**，行距 1.1–1.3，粗体。
3. 图注/页脚 **8–9pt**，灰色。
4. **MUST NOT** 用 px 做版面/字号单位（统一 pt）。

### 配色（暖色编辑风，不是单色）
5. **一个暖色主色**（如赤陶橙 `#C85A3C`、墨绿、藏蓝皆可）+ **2–3 个由主色派生的低饱和浅色填充**（如 `#F5DDD5` 浅橙、`#DCE6D5` 浅绿、`#FBEFE7` 米）。主色用于封面/标题/强调，填充用于标签/卡片底。
6. 底色满版米/浅色（`#FAF6EC` 系），卡片纯白浮在其上 = 编辑风核心观感。
7. 正文深灰非纯黑（`#333`/`#3F3F3F`）；标题可用主色或近黑。
8. `print-color-adjust: exact` **MUST** 挂 `*`（挂 body 无效）。

### 视觉重点（必须有，否则太素）
9. 每个点位/段落 **MUST** 至少一处强调：把"卖点短语"用**主色粗体**标出（如「泳池边喝咖啡、孙科别墅拍照」），每页 3–6 次。
10. 关键属性做成**填色圆角标签**：分类标签（浅色底 + 主色字）+ 状态标签（如「停留 1.5h」浅绿底）。
11. 推荐/提示用 **callout 块**：浅色填充 + 左侧 3pt 主色边框 + 起首 emoji。
12. 编号点位用**实心圆形 badge**（主色底白字数字）。

### emoji / 图标（用，别滥用）
13. emoji 作**视线引导**：信息胶囊、分类图标、callout 起首、交通方式（🚶🚇🍽🎁🍷🛍🎯）。一套语义一致的，**别随机堆**。
14. **MUST NOT** 用 🙏。
15. 渲染在 macOS Chromium，emoji 正常；若目标是 Linux 无字体环境，改用 `noto-color-emoji` 或退化为 SVG/几何图形（不要因此弃用视觉引导）。

### 卡片 / 圆角 / 填色（编辑风骨架，鼓励用）
16. 点位/推荐/Tips/对比 **用卡片**：白卡浮于浅底，圆角 **10–14pt**，padding 14–16pt。
17. 标签/callout 圆角 6–10pt。**鼓励**填色，别怕"花"——协调暖色系内即可。
18. 阴影克制：白卡可 `0 1px 4px rgba(0,0,0,.05)`；**MUST NOT** 浓重投影/拟物。

### 版面与留白（密 > 空）
19. 内容**不贴边**（靠 `.body` / 卡片 padding）；段间距 7.5–11pt。
20. **内容要密**：每个点位卡含 标签 + 正文 + 推荐 callout，信息饱满。**MUST NOT** 大片留白凑页数。
21. 末页 **MUST ≥1/2 满**，不足就并入上一页或补 Tips/收尾卡，**MUST NOT** 留半空尾页。
22. **MUST NOT** 用 `<br>`/spacer 撑版面。

### 图片
23. 满版内容宽、清晰、尺寸一致；正文图源宽 ≥1080px；图注灰 8–9pt。
24. 旅游攻略**一般不用图表**；如用 Chart.js 必须 `animation=false` + `--wait`。

### 可用性（手机）
25. 不横向滚动：内容宽 ≤ 内容区宽，长 URL/表格 **MUST** 换行或缩短。
26. **链接要让人知道能点**：关键链接（地图/订房/参考）**MUST** 是真实 `<a href>`（渲染为 PDF /Link），且**MUST** 有可点提示——下划线 + 链接色（`#576B95` 或主色），或做成带箭头的胶囊按钮（如 `📍 高德地图导航 ›`）。**MUST NOT** 假链接 div、**MUST NOT** 裸蓝链无提示也不算（要明显可点）。
27. 关键页信息单屏完整（可截屏分享）。
28. 多页 **MUST** 有可点击 TOC / 行程速览（每节唯一 id）。

## 禁止项（反"AI 味"黑名单——只禁真正廉价的，不禁视觉丰富）
- 禁默认 iOS 蓝 `#007AFF`、紫→白渐变 hero、海军蓝+金"企业报告"配色
- 禁 generic 仪表板 KPI 瓷砖 + 浓重投影、拟物高光
- 禁白底居中标题 + 细横线"极简"封面（最没记忆点的 AI 默认封面）
- 禁随机 emoji 堆砌、禁 🙏
- 禁 `100vh` 当页高、px 做版面单位
- 禁 `<br>`/spacer 撑版面、缩页边距塞内容、半空尾页
- 禁每段 `page-break-before`
> 注意：emoji、填色卡片、圆角、暖色多 tint **不在**黑名单——它们是编辑风的必需品。要禁的是"廉价 AI 默认观感"，不是"视觉丰富"。

## 生成后自检（双门，缺一不可）
| 检查 | 命令 / 方法 | 通过标准 |
|---|---|---|
| 页面尺寸 | `pdfinfo out.pdf \| grep "Page size"` | ≈300×667.5pt（9:20） |
| 图片未丢 | `pdfimages -list out.pdf \| tail -n +3 \| wc -l` | ≥ 预期数 |
| 链接可点 | `pypdf` 数 /Link + spot-click ≥3 | 命中、能跳转，且视觉上明显可点 |
| 文字可读 | `pdftotext -layout` | 无乱码、无残留占位符 |
| 内容密度 | 目视 | 卡片信息饱满、无大片留白、尾页 ≥1/2 满 |
| 视觉重点 | 目视 | 每页有强调高亮 + 填色标签/callout，非纯灰素排 |
| 翻页连续 | 目视 | 背景色跨页连续、无白条断裂 |
| 配色 | 目视 | 暖色主题成立、非默认蓝/紫渐变 |

> `pdftotext` 看不到图像，单独用会**静默放行无图 PDF**——必须配 `pdfimages`。任何步骤 **MUST NOT** `2>/dev/null`。
