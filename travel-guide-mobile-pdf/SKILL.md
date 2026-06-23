---
name: travel-guide-mobile-pdf
description: >-
  生成适合手机竖屏阅读、可分享的旅游攻略 PDF（HTML→Chromium→PDF）。
  当用户要「旅游/citywalk/周末出游/行程攻略」且要「手机看的 PDF / 可分享」时使用。
  不适用于桌面打印 A4 报告、纯文本回答。
---

# 旅游攻略手机 PDF Skill

生成适合手机竖屏阅读、可分享的旅游攻略 PDF。参数依据来自小红书/公众号真实排版经验（px），按 `pt = px × 0.75` 换算到 PDF。

## When to use
- 旅游攻略 / citywalk / 周末出游 / 多日行程，出口是**手机**、要 **PDF 或可分享卡片**
- **不适用**：纯文本回答、桌面 A4 报告、数据驱动可复现文档（那走 reportlab）

## 技术栈
HTML → Chromium(Playwright) → PDF。强视觉攻略用 HTML+Chrome 最顺手；不要走 LaTeX/reportlab。

## 工作流程
1. **需求拆解**：人数 / 天数 / 出发地 / 预算 / 节奏 / 必去点 / 硬性要求（如「两套路线」「机酒价」）。
2. **信息核查**：`web_search` 查真实店名 / 民宿 / 景点 / 价格区间，**禁编造**；无 live 价时标「估算 + 时间」。
3. **写 HTML 源**：分节、每节唯一 `id`、TOC 用 `<a href="#id">`，遵守下方 Operational Rules。
4. **渲染 PDF**：`node scripts/render_mobile.cjs source.html out.pdf`（300pt×667.5pt 卡片式）。
5. **自检**：双门（pdfinfo + pdfimages）+ 链接 spot-click + 目视圆角/emoji/配色。
6. **交付**。

## 页面尺寸（锁定）
目标设备 2670×1200（≈9:20 竖屏，高分屏 DPR3 → 逻辑视口 ≈400×890 CSS px）。

- **MUST** `@page { size: 300pt 667.5pt; margin: 0 }`（≈106×235mm，9:20，手机满屏无黑边，一页=一屏）。
- **MUST** 显式物理尺寸；**MUST NOT** 用 `100vh/100vw`、**MUST NOT** 横屏。
- 长内容分页（每节一页或多页），**MUST NOT** 超长单页。
- 自洽：正文 11pt 在 300pt 宽页 ≈ 手机 14.7px，落在人类经验 14–15px 区间。

## Operational Rules（生成时硬约束，非建议）

### 字号与行距
1. 正文 **10.5–11pt**，行距 **1.5–1.65**。
2. 标题 H1 **16–20pt** / H2 **13–15pt** / H3 **11.5–12pt**，行距 1.1–1.3。
3. 图注 **8.5–9pt**、页脚 **8pt**，灰色。
4. 字距可选 0.5–1pt；**MUST NOT** 用 px 做版面/字号单位（统一 pt）。

### 配色
5. 全文 **≤3 色**；正文深灰非纯黑（`#333`/`#3F3F3F`）。
6. **单一强调色**，不用于正文文字，每页 <8 次。
7. `print-color-adjust: exact` **MUST** 挂 `*`（挂 body 无效）。

### 字体（CJK）
8. 系统字体栈：`-apple-system, "PingFang SC", "STSong", "Helvetica Neue", Arial, sans-serif`。
9. CJK 回退 **MUST** SC→JP→KR→Latin（日文在前会让简体字用日文字形）。
10. webfont 截图前 **MUST** `await document.fonts.ready`；字型最多两种。

### 版面与留白
11. 内容区不贴边；段间距 7.5–11pt。
12. 末页 **MUST ≥1/3 满**，不足扩内容，**MUST NOT** 缩页边距塞内容。
13. **MUST NOT** 用 `<br>`/spacer 撑版面。
14. **MUST NOT** 给每个 H2 加 page-break-before（#1 amateurish 标志），只在真正分节处分页。

### 卡片 / 圆角 / 阴影（最易翻车）
15. 卡片**仅限** KPI / 推荐块 / 对比框 / 结论块；**正文 MUST NOT 带边框卡片**。
16. 圆角仅 callout / KPI 卡片，**最大 9pt**；其他 **MUST NOT** 圆角。
17. **MUST NOT** 阴影（图表卡片最多 `0 1px 3px rgba(0,0,0,0.04)`）。

### 图片
18. 满版内容宽、清晰、尺寸一致；正文图源宽 ≥1080px；图注灰 8.5–9pt。
19. 旅游攻略**一般不用图表**；如用 Chart.js 必须 `animation=false` + `--wait`。

### 可用性（手机）
20. 不横向滚动：内容宽 ≤ 内容区宽，长 URL/表格 **MUST** 换行或缩短。
21. 关键链接（地图/订房/参考）**MUST** 是真实 `<a href>`（渲染为 PDF /Link）；**MUST NOT** 假链接 div。
22. 关键页信息单屏完整（可截屏分享）。
23. 多页 **MUST** 有可点击 TOC（每节唯一 id）。

## 禁止项（反 AI 美学黑名单）
- 禁默认蓝 `#007AFF`、紫渐变白底、海军蓝+金色
- 禁卡片仪表板风、滥用圆角、阴影
- 禁 **emoji / 图标字体**（Linux 缺字体渲染失败 + 不专业）
- 禁 100vh 当页高、px 做版面单位
- 禁 `<br>`/spacer 撑版面、缩页边距塞内容
- 禁每个 H2 都 page-break-before、禁白底居中标题+细横线封面

## 生成后自检（双门，缺一不可）
| 检查 | 命令 / 方法 | 通过标准 |
|---|---|---|
| 页面尺寸 | `pdfinfo out.pdf \| grep "Page size"` | ≈300×667.5pt（9:20） |
| 图片未丢 | `pdfimages -list out.pdf \| tail -n +3 \| wc -l` | ≥ 预期数 |
| 链接可点 | `pypdf` 数 /Link + spot-click ≥3 | 命中、能跳转 |
| 文字可读 | `pdftotext -layout` | 无乱码、无残留占位符 |
| 末页 | 目视 | ≥1/3 满 |
| 配色/圆角/emoji | 目视 | 非默认蓝、单强调色、无滥用圆角、无 emoji |

> `pdftotext` 看不到图像，单独用会**静默放行无图 PDF**——必须配 `pdfimages`。任何步骤 **MUST NOT** `2>/dev/null`。
