---
name: travel-guide-mobile-pdf
description: >-
  生成适合手机竖屏阅读、可分享的旅游攻略 PDF（HTML→Chromium→PDF）。
  当用户要「旅游/citywalk/周末出游/行程攻略」且要「手机看的 PDF / 可分享」时使用。
  不适用于桌面打印 A4 报告、纯文本回答。
---

# 旅游攻略手机 PDF Skill

把旅游攻略渲染成**手机竖屏、可分享**的 PDF。本文件管**流程、工具链、机械契约、验证门**；具体**视觉样式不在这里硬约束**——风格方向、配色、卡片/emoji 用法、依据参数都在 [`docs/style-reference.md`](docs/style-reference.md)，那是**菜单和参考，不是规则**，样式自由度留给模型。

## When to use
- 旅游攻略 / citywalk / 周末出游 / 多日行程，出口是**手机**、要 **PDF 或可分享卡片**
- **不适用**：纯文本回答、桌面 A4 报告、数据驱动可复现文档（那走 reportlab）

## 技术栈
HTML → Chromium(Playwright) → PDF。强视觉攻略用 HTML+Chrome 最顺手；**不要**走 LaTeX/reportlab。

## 工作流程
1. **需求拆解**：人数 / 天数 / 出发地 / 预算 / 节奏 / 必去点 / 硬性要求（如「两套路线」「机酒价」）。
2. **信息核查**：`web_search` 查真实店名 / 民宿 / 景点 / 价格区间，**禁编造**；无 live 价时标「估算 + 时间」。配图同理——只用**验证过能打开**的 URL（见机械契约「图片真实可达」）。
3. **写 HTML 源**：分节、每节唯一 `id`、TOC/行程速览用 `<a href="#id">`。样式自由发挥，方向见 `docs/style-reference.md`。
4. **渲染 PDF**：`node scripts/render_mobile.cjs source.html out.pdf`（需 `NODE_PATH` 指向装了 playwright 的 node_modules）。
5. **自检**：过下方验证门。
6. **交付**。

## 机械契约（HTML→PDF 的"对/错"，非样式偏好）
这些是渲染正确性问题，不照做会出坏产物——和审美无关，必须遵守：

- **页面尺寸**：目标设备 2670×1200（≈9:20 竖屏，DPR3 → 逻辑视口 ≈400×890 CSS px）。
  渲染器用 `width:'400px' height:'890px'`（= 300pt×667.5pt；**Playwright `page.pdf` 不收 `pt` 单位**，必须用 px/in）。
- **满版无白边**：渲染 `margin:0`、`displayHeaderFooter:false`；页边距/留白全靠 **CSS 内边距**控制，别靠渲染器 margin。
- **背景跨页连续**：背景色铺到 `html, body`；多页时翻页处**不能出现白条/断裂**。
- **不要每节强行分页**：`page-break-before` 滥用是 #1 amateurish 信号；只在卡片上 `break-inside:avoid` 防标题被切。
- **别用固定高度模拟"一屏一页"**：渲染器按 890px 页高**自动分页**，HTML 内容必须**自然流动**。给 `.page`/section 设 `height:890px; overflow:hidden`（或任何写死的满屏高）会把超出内容**裁掉**，多页内容塌成 **1 页**（step3.7 实测：12 页被压成 1 页，被迫手写拆页脚本兜底）。要主动断页用 `break-before/after`，**不靠固定高度**。
- **链接必须真可点**：地图/订房/参考用真实 `<a href>`（渲染成 PDF `/Link`），**禁假链接 div**。
- **图片真实可达**：配图只用**验证过能打开**的 URL，别凭记忆编文件名（step3.7 实测：5 张编造的 Wikimedia 文件名全 404 留白）。Wikimedia 走 Commons API 搜真实文件名 → `imageinfo` 取 `thumburl`；任意图床嵌入前 `curl -sI <url>` 确认 200。**宁可少图，不留 404 空块**。
- **不横向滚动**：内容宽 ≤ 内容区宽；长 URL/表格换行或缩短。
- **CJK 字体回退** `SC→JP→KR→Latin`（日文在前会让简体用日文字形）；webfont 截图前 `await document.fonts.ready`。
- **颜色保真**：`print-color-adjust: exact` 挂 `*`（挂 body 无效）。

> 详细机械说明（字体栈、Chart.js settle 等）见 [`docs/style-reference.md`](docs/style-reference.md) 末节。

## 渲染器（scripts/render_mobile.cjs）
满版无白边，margin 0，留白交给 CSS，背景跨页连续。用法：
```bash
NODE_PATH=<装了 playwright 的 node_modules> node scripts/render_mobile.cjs source.html out.pdf
```

## 验证门（流程纪律，缺一不可）
| 检查 | 命令 / 方法 | 通过标准 |
|---|---|---|
| 页面尺寸 | `pdfinfo out.pdf \| grep "Page size"` | ≈300×667.5pt（9:20） |
| 页数合理 | `pdfinfo out.pdf \| grep Pages` | 与内容量相称；**=1 页几乎必是固定高度塌页** |
| 图片未丢 | `pdfimages -list out.pdf \| tail -n +3 \| wc -l` | ≥ 预期数（404 会使计数 < 预期 → 漏图） |
| 链接可点 | `pypdf` 数 `/Link` + spot-click ≥3 | 命中、能跳转 |
| 文字可读 | `pdftotext -layout` | 无乱码、无残留占位符 |
| 翻页连续 | 看图（见下） | 背景跨页连续、无白条断裂 |
| 内容不贴边/不空 | 看图（见下） | 内容不贴边、无大片留白凑页、尾页 ≥1/2 满 |

> **看图是主验证手段**：渲染后必跑 `pdftoppm -r 96 -png out.pdf /tmp/pg`，用 **Read 逐页看图**核对分页/溢出/贴边/尾页空——claude & m3 实测都印证：版面问题**只有看图能发现**，`pdfinfo`/`pdftotext` 全部静默放行（上面两行"看图"就靠这步落地）。
>
> `pdftotext` 看不到图像，单独用会**静默放行无图 PDF**——必须配 `pdfimages`。任何步骤 **MUST NOT** `2>/dev/null`（丢掉唯一的失败信号）。

## 样式（不在本文件约束）
风格方向（小红书/公众号编辑风）、配色菜单、卡片/标签/callout/emoji 用法、字号行距的人类经验参数、避免的"AI 默认观感"——全在 [`docs/style-reference.md`](docs/style-reference.md)。**那是参考与菜单，不是硬约束**：模型按场景自由取舍，只要过上面的机械契约和验证门即可。
