---
name: travel-guide-mobile-pdf
description: >-
  生成适合手机竖屏阅读、可分享的旅游攻略 PDF（HTML→Chromium→PDF）。
  支持两种设计单元：.page（默认，一段一物理页，自然流动）+ .screen（opt-in，固定一屏的硬卡）。
  当用户要「旅游/citywalk/周末出游/行程攻略」且要「手机看的 PDF / 可分享卡片」时使用。
  不适用于桌面打印 A4 报告、纯文本回答。
---

# 旅游攻略手机 PDF Skill

把旅游攻略渲染成**手机竖屏、可分享**的 PDF。本文件管**流程、工具链、机械契约、验证门**；**视觉样式不在这里约束，留给模型自由发挥**——调性、配色、版式按场景自己定，**不要照搬模板**。（`docs/style-reference.md` 是配色 / 密度数值 / 组件的**菜单**，没思路或要密度锚点时翻一下，**别照抄**——照规定式参考做容易出模板化死板的产物。）

## 两类设计单元（按需选，不冲突）

本 skill 渲染任意外层标签名为 `.page` 或 `.screen` 的 `<section>`，**两种类名混用也支持**。什么时候用哪个：

| 类名 | 行为 | 用在 |
|---|---|---|
| **`.page`**（默认） | 一段一物理页，自然流动分页；内容不够高就用 `min-height: 1 page` + flex center 撑起 + 垂直居中 | 90% 的内容页：行程总览 / 某天路线 / 预算表 / 实用贴士 / 时间轴… |
| **`.screen`**（opt-in） | `height: 1 page` 固定 + 渲染时溢出检测；强制 1 卡 = 1 物理页，不许内容溢出 | 满版封面图（要正好填满一屏）、单张可分享的「卡」（截图发出去独立成立）、缩略图列表 |

**判断口诀**：
- "这一页放的是一整段内容" → `.page`
- "这一页必须正好一屏高，少了空、多了切" → `.screen`

两者**不互斥**：一份文档可以混用——比如封面用 `.screen`（满版图），其余内容用 `.page`（自然流动）。renderer 两种都校验。

## When to use
- 旅游攻略 / citywalk / 周末出游 / 多日行程，出口是**手机**、要 **PDF 或可分享卡片**
- **不适用**：纯文本回答、桌面 A4 报告、数据驱动可复现文档（那走 reportlab）

## 技术栈
HTML → Chromium(Playwright) → PDF。强视觉攻略用 HTML+Chrome 最顺手；**不要**走 LaTeX/reportlab。

## 工作流程
1. **需求拆解**：人数 / 天数 / 出发地 / 预算 / 节奏 / 必去点 / 硬性要求（如「两套路线」「机酒价」）。
2. **信息核查**：`web_search` 查真实店名 / 民宿 / 景点 / 价格区间，**禁编造**；无 live 价标「估算 + 时间」。配图同理——只用**验证过能打开**的 URL（见机械契约「图片真实可达」）。
3. **分页（先定页数）**：先决定**这份攻略分几页、每页放哪个小标题 + 哪些内容块**。`.page` 走自然分页（内容不够高就居中），`.screen` 必须 1 卡 = 1 页。**先把页数定下来再写 HTML，别一上来就写满**。
4. **每页定密度档 + 适配排版**：估这页内容量 → 挑密度档，按档调字号 / 行距 / 间距 / 布局（**数值锚点查 `style-reference.md` 密度菜单**）：
   - **稀疏**（封面 / 章节卡 / 单点 hero）：少元素 → 大字、大留白、居中焦点、一个视觉主角。
   - **均衡**（标准点位卡 / 2–3 块）：中字号、舒适间距、卡片化。
   - **密集**（路线时间轴 / 长清单 / 对照表）：紧凑字号行距（但守可读下限）、小间距、必要时分栏。
   - **同一页内容多就上密集档、少就上稀疏档——参数跟着内容量走，别一套参数套全程。**
5. **写 HTML**：每段一个 `<section class="page">`（默认）。需要硬卡（满版封面 / 独立可分享单卡）才改用 `<section class="screen">`。renderer 靠类名做护栏，**务必用 `.page` 或 `.screen` 这两个类名之一**，别用别的。
6. **渲染 PDF**：`node scripts/render_mobile.cjs source.html out.pdf`（需 `NODE_PATH` 指向装了 playwright 的 node_modules）。读它输出的**逐页报告**。
7. **自检 → 重修闭环（不过不交付）**：跑 `python3 scripts/check_edges.py out.pdf --expect-pages <设计页数>` 测页边距 + 居中；再 `pdftoppm -r 96 -png out.pdf /tmp/pg` **逐页 Read 看图**核对脚本测不到的（孤立标题、破图、卡片切断、贴边）。**任一不过 → 写清哪页哪元素什么问题 → 改 HTML → 重渲染 → 重跑。循环到全过。**
8. **交付（必须附自检证据，否则不算完成）**：**逐页列证据表**——每页：`check_edges` 留白% / 居中 / 贴边 / 有无孤立标题/破图/切断。**没有这张表 = 没做自检 = 不准交付**。

## 机械契约（渲染正确性，非样式偏好）
不照做会出坏产物，和审美无关，必须遵守：

**页面结构**
- **页面尺寸**：目标设备 2670×1200（≈9:20 竖屏，DPR3 → 逻辑视口 ≈400×890 CSS px）。渲染器用 `width:'400px' height:'890px'`（= 300pt×667.5pt；**Playwright `page.pdf` 不收 `pt` 单位**，必须用 px/in）。
- **满版无白边**：渲染 `margin:0`、`displayHeaderFooter:false`；页边距 / 留白全靠 **CSS 内边距**，别靠渲染器 margin。
- **背景跨页连续**：背景色铺到 `html, body`；多页时翻页处**不能出现白条 / 断裂**。
- **`.page` 排版**（默认范式）：每个设计页 = 一个 `<section class="page">`；**用 `min-height: 1 page` + `flex center` 垂直居中**（居中后留白被分到上下两端，物理页数==`.page` 段数，验证门会同时核对）。**不设 `height`，不设 `overflow:hidden`**——高度由内容自然撑开，超出才会被物理分页、`check_edges --expect-pages` 抓到。
- **`.screen` 排版**（opt-in）：每个硬卡 = 一个 `<section class="screen">`；`height:890px` 写死 + `overflow:hidden` 兜底；**`render_mobile.cjs` 渲染时逐卡测内容高，超一屏 → 退出码 1 + 指出卡号**。**只在必须"1 卡=1 屏"时用**（满版封面、独立分享卡）。
- **居中机制（`.page`）**：`.page:not(.cover){ min-height:890px; display:flex; flex-direction:column; justify-content:center; }`——`min-height` 允许内容撑高溢出（`check_edges` 能抓到），不像 `height+overflow:hidden` 那样静默裁掉。
- **兜底（不被切断）**：`.page` / `.screen` 都给**叶子卡片**（`.tip-card` / `.place-card` / `.timeline-item` 等）`break-inside: avoid`、给**所有标题 / 小标题**（`.day-header` / `.sec-title` / `.label` / `.section-title` 等）`break-after: avoid`——`check_edges` 测不到的卡片切断 / 标题孤立靠这个兜底。
- **不横向滚动**：内容宽 ≤ 内容区宽；长 URL / 表格换行或缩短。

**内容真实**
- **链接必须真可点**：地图 / 订房 / 参考用真实 `<a href>`（渲染成 PDF `/Link`），**禁假链接 div**。
- **图片真实可达**：配图只用**验证过能打开**的 URL，别凭记忆编文件名（实测：编造的 Wikimedia 文件名全 404 留白）。Wikimedia 走 Commons API 搜真实文件名 → `imageinfo` 取 `thumburl`；任意图床嵌入前 `curl -sI <url>` 确认 200。**宁可少图 / 用内联 SVG，不留 404 空块**。
- **`<img>` 别乱加 `crossorigin="anonymous"`**（实测踩坑）：除非要 canvas 读像素，**一律不要加**。它会把图片改成 CORS 请求，而很多图床（amap `aos-comment.amap.com` / `store.is.autonavi.com`、部分 Wikimedia 镜像）**不返回 `Access-Control-Allow-Origin` 头 → CORS 失败 → 静默破图**。**`curl -sI` 仍是 200（CORS 是浏览器层，curl 查不到）**——所以「curl 200」是必要不充分，**图片是否真显示最终以渲染后逐页看图为准**。
- **唤端链接用 web URI**（PDF 链接点击最稳）：地图 / 导航 / 订房用 **`https://uri.amap.com/...`** web URI；**别用** `amapuri://...` 唤端 scheme——PDF 阅读器未必识别，点不动还以为是死链。

**渲染细节**
- **CJK 字体栈 / 回退**：`-apple-system, "PingFang SC", "STSong", "Helvetica Neue", Arial, sans-serif`，回退顺序 `SC→JP→KR→Latin`（日文在前会让简体用日文字形），字型最多两种；webfont 截图前 `await document.fonts.ready`。
- **颜色保真**：`print-color-adjust: exact` 挂 `*`（挂 body 无效）。
- **图表少用**：攻略一般不用图表；万一用 Chart.js，必须 `animation:false` 且等渲染完再截。

## 渲染器（scripts/render_mobile.cjs）
满版无白边（margin 0，留白交给 CSS），并**对 `.page` 段数 == 物理页数** + **`.screen` 卡内容高 ≤ 一屏**做护栏：
- `.page` 段数与物理页数不符 → 退出码 1（说明有段超一页被拆 / 塌页）。
- 任一 `.screen` 内容超 890px → 退出码 1 + 指出卡号。
- `.screen` 填充 < 55% 给 warn。
- 无 `.page` / `.screen` 时回退普通流动渲染（向后兼容，护栏不生效）。
用法：
```bash
NODE_PATH=<装了 playwright 的 node_modules> node scripts/render_mobile.cjs source.html out.pdf
```
输出 JSON 含 `pages`（.page 段数）、`screens`（.screen 卡数）、物理页数 `pdf_pages`、逐卡 `contentH/fill/overflow`、违例清单 `overflow_screens` / `page_count_mismatch` / `underfill_screens`。**任一非空必须改到空再交付。**

## 页边距 + 居中硬闸（scripts/check_edges.py）
把验证门的「留白不过量」+「未居中」+「贴边」从主观目测变成**硬数字**：
- **页底留白%**（非尾页 ≤10% / 尾页 ≤15%，封面默认跳过）
- **顶部 vs 底部留白**差 ≤5%（居中）
- **左右边距**到内容边距离 ≥8px（不贴边）
- 失败 → `exit 1` + 指明页号 + 现象

```bash
python3 scripts/check_edges.py out.pdf --expect-pages <设计页数>  # 页数 != 设计 → FAIL
python3 scripts/check_edges.py out.pdf --max-bottom 12 --max-center-delta 8 --min-edge 10
```

**它只管页边距 + 居中 + 贴边；孤立标题 / 破图 / 卡片切断测不到，仍须逐页看图。**

## 验证门（流程纪律，缺一不可 — 不过就重修，循环到过）
**这是一个闭环，不是一次性勾选**：任一项 ✗ → 写清问题（页号+元素+现象）→ 改 HTML → 重渲染 → 重跑全部检查。**全 ✓ 才算完成。**

| 检查 | 命令 / 方法 | 通过标准 | 不过怎么修 |
|---|---|---|---|
| 页面尺寸 | `pdfinfo out.pdf \| grep "Page size"` | ≈300×667.5pt（9:20） | 改 `@page`/渲染器尺寸 |
| **页数 == 设计页数** | `check_edges.py --expect-pages <N>` | 物理页数 == `.page` 段数 | 有段超一页被拆 → 拆段 / 降密度；塌页 → 查固定高度+overflow:hidden |
| **页边距 + 居中** | `check_edges.py` | 页底留白 ≤10% / 尾页 ≤15%；上下差 ≤5%；左右 ≥8px | 补内容 / 上提后文 / 调 CSS 内边距；偏 → 调 `flex center` |
| 无 `.screen` 溢出 | `render_mobile.cjs` 报告 | `overflow_screens` 为空、退出码 0 | 拆卡 / 降密度 / 缩字号 |
| `.screen` 填充合理 | 渲染报告 `fill` + 看图 | 各卡 ≥55%；<55% 确认是有意 hero 否则补 | 加大字号 / 补内容 / 合并卡 |
| 图片未丢 | `pdfimages -list out.pdf \| tail -n +3 \| wc -l` | ≥ 预期数（404/CORS 失败都会漏图） | 换**验证过 200 + CORS 干净**的图 URL；破图必换 |
| 链接可点 | `pypdf` 数 `/Link` + spot-click ≥3 | 命中、能跳转；**不含 `amapuri://` 唤端 scheme** | 补真实 `<a href>`；唤端链接换 web URI |
| 文字可读 | `pdftotext -layout` | 无乱码、无残留占位符 | 修字体栈 / 占位符 |
| 翻页连续 | 看图 | 背景跨页连续、无白条断裂 | 背景铺 `html, body` |
| 块不被切断 | 看图 | 卡片 / 行程项 / 标题都不跨页断裂；标题不孤立页底 | 叶子卡片 `break-inside:avoid` + 标题 `break-after:avoid`（兜底） |

> **看图是主验证手段**：渲染后必跑 `pdftoppm -r 96 -png out.pdf /tmp/pg`，用 **Read 逐页看图**核对分页/溢出/贴边/居中——`pdfinfo` / `pdftotext` / `check_edges` 全部测不到图片是否真显示（CORS 破图 / 字体丢字 / 截图被装饰挡住）。**页底留白是反复出现的头号缺陷，看图时逐页量一眼留白比例。**
>
> `pdftotext` 看不到图像，单独用会**静默放行无图 PDF**——必须配 `pdfimages`。任何步骤 **MUST NOT** `2>/dev/null`（丢掉唯一的失败信号）。

## 样式（自由发挥，不在本文件约束）
调性、配色、卡片 / 标签 / callout / emoji、字号行距——**模型按场景与每页密度档自由发挥，不要照搬任何模板**。只要过上面的机械契约和验证门即可。
`docs/style-reference.md` 有配色菜单、**密度分档数值区间**、`.page` / `.screen` 两套组件骨架、单卡自洽要素、要避免的「AI 默认观感」。需要数值锚点或没思路时翻一下，**翻了也别照抄**。
