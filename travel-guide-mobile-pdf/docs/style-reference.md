# 样式参考 · 旅游攻略手机 PDF

> **这是菜单和参考，不是硬约束。** SKILL.md 只管流程/工具链/机械契约/验证门；样式自由度留给模型。下面的方向、数值、示例都可按场景取舍、覆盖、混搭——只要产物过得了 SKILL.md 的机械契约和验证门即可。
>
> 唯一的"别做"是少数真正廉价的观感（见最后「避免」节），其余一切鼓励发挥。

## 风格方向（一个推荐基调，非唯一）
目标观感参考**小红书 / 公众号编辑风**：暖色调、信息密、有视觉重点、卡片化、emoji 引导视线。好的攻略让人想逛、想存、想分享。
"极简白底报告"不是这个场景的好选择——素、空、无重点通常会让攻略显得没做完。但具体走暖色编辑风、杂志风、还是清爽 ins 风，**模型自己定**。

## 配色（菜单，挑一套或自创）
思路：**一个主色 + 2–3 个由主色派生的低饱和浅色填充**，底色用浅米/浅灰，卡片纯白浮其上。正文深灰非纯黑（如 `#333`/`#3F3F3F`）。
几组现成暖色搭配可直接用或改：

| 基调 | 主色 | 浅色填充示例 | 底色 |
|---|---|---|---|
| 赤陶橙（citywalk 实测好用） | `#C85A3C` | `#F5DDD5` 浅橙 / `#DCE6D5` 浅绿 / `#FBEFE7` 米 | `#FAF6EC` |
| 墨绿 | `#3F6B52` | `#DCE6D5` / `#EAE3D2` | `#F7F4EC` |
| 藏蓝 | `#2F4A6B` | `#DCE3EE` / `#F0E9DC` | `#F6F4EF` |

色数不必死守——协调即可。

## 字号 / 行距（人类经验参数，作锚点不作铁律）
来自小红书/公众号实测 px，按 `pt = px × 0.75` 换算到 300pt 宽页：
- 正文 ≈ 14–15px → **10.5–11pt**，行距 1.5–1.75
- 标题 16–18px → H2 **13–15pt**；大标题可 18–24pt 粗体
- 图注/页脚 12–13px → **8–9pt** 灰
- 两侧边距 8–16px，段间距 10–15px
这些是"看着舒服"的经验区间，不是验收线；模型可按版面调。

## 页面密度分档（数值菜单 · 锚点非铁律）
> SKILL.md 定「分档原则」（内容多/少跟随调整）；这里给**数值区间**当锚点。**可覆盖、可混搭**，只要过机械契约（不溢出、填充合理、单页自洽）。**一页选一档，别全程一套参数。**

| 档 | 用在 | 一页块数 | 大标题 | 正文 | 行距 | 块间距 | 边距 | 手法 |
|---|---|---|---|---|---|---|---|---|
| **稀疏** | 封面 / 章节卡 / 单点 hero | 1–3 | 40–64px 粗 | 18–22px | 1.6–1.8 | 20–32px | 28–40px | 居中焦点、大留白、一个视觉主角；可整页 `justify-content:center` |
| **均衡** | 标准点位页 / 2–3 块 | 3–5 | 28–36px | 16–19px | 1.5–1.7 | 12–18px | 18–24px | 卡片化、标题+卡列流、舒适呼吸 |
| **密集** | 路线时间轴 / 长清单 / 对照表 | 5–9 | 22–28px | 15–17px | 1.35–1.5 | 6–11px | 14–18px | 紧凑、虚线分隔、必要时两栏；**正文别低于 15px、行距别低于 1.35**（可读下限） |

判档：先把要放的内容堆进页，**溢出就降一档**（或拆段），**填不满就升一档**（放大/加留白），直到 `check_edges.py` 报留白/居中/贴边全过 + `render_mobile.cjs` 报物理页数==设计页数。

## 骨架（两套：`.page` 默认 + `.screen` opt-in）

### `.page` 骨架（默认 · 自然流动分页）
```css
* { margin:0; padding:0; box-sizing:border-box; print-color-adjust:exact; -webkit-print-color-adjust:exact; }
html, body { background:#FAF6EC; }                         /* 满版底色，跨页连续 */
.page {                                                    /* 一段一物理页（默认范式） */
  width:400px;                                             /* 不设 height——内容自然撑高 */
  min-height:890px;                                        /* 撑到一屏高 + 配合 flex center 居中 */
  display:flex; flex-direction:column;
  justify-content:center;                                  /* 上下居中：内容少时分到上下两端 */
  padding:28px 20px; position:relative;
  break-before:page;                                       /* 每段独占一物理页 */
  break-after:page;
  background:#FAF6EC;
}
.page:first-child { break-before:avoid; }                  /* 首页不被推空白页 */
.page:last-child  { break-after:auto; }                    /* 末段不拖空白页 */
.page .grow { flex:1; }                                    /* 把页脚顶到底（不需要时删） */
```
**关键**：用 `min-height` 不是 `height`，配合 `flex center`——内容超了会自然溢出被 `check_edges --expect-pages` 抓到，不会静默裁切。

### `.screen` 骨架（opt-in · 强制 1 卡 = 1 屏）
```css
.screen {                                                  /* 一卡一屏一页（opt-in） */
  width:400px; height:890px; overflow:hidden;              /* 固定一屏；溢出由渲染器检测 */
  display:flex; flex-direction:column;
  padding:28px 20px; position:relative;
  break-after:page;
  background:#FAF6EC;
}
.screen:last-child { break-after:auto; }
.screen.hero { justify-content:center; text-align:center; }/* 稀疏 hero：垂直居中焦点 */
```
**用在**：满版封面图（要正好填满一屏）、单张可分享的「卡」（截图发出去独立成立）、缩略图列表等。**不**用在普通内容页——那用 `.page` 让它自然流动。
卡内模块（封面 eyebrow+大标题+emoji 胶囊、编号点位卡、callout、交通 pill 等）见下「编辑风组件」，按密度档取用。

## 单卡自洽要素（让任一页单独截图也成立）
每张卡是可独立分享的单元，给它一个轻量身份：
- **顶部**：eyebrow 小字（`上海 · CITY WALK`）或卡标题，让人一眼知道这是什么。
- **底部**：极简页脚标识（攻略名 / `2/6` 卡序 / 一句 slogan），灰色小字，别和满版色块打架。
- **定位**：点位卡带城市/区域；路线卡带「第X天」或时段。
- 测试：把这张卡单独发出去，对方不看其他页能不能读懂？读不懂就补上下文。

## 编辑风组件（可选骨架示例）
照搭省事，不想用就换。满版骨架：
```css
* { margin:0; padding:0; box-sizing:border-box; print-color-adjust:exact; -webkit-print-color-adjust:exact; }
html, body { background:#FAF6EC; }                 /* 满版底色，跨页连续 */
.cover  { background:#C85A3C; color:#fff; padding:30pt 20pt 22pt; }   /* 封面满版色块 */
.body   { padding:18pt 16pt 0; }                   /* 正文横向内边距 → 不贴边 */
.place-card { background:#fff; border-radius:12pt; padding:16pt; margin-bottom:14pt; break-inside:avoid; }
.callout { background:#FBEFE7; border-left:3pt solid #5A7052; border-radius:8pt; padding:11pt 13pt; }
```
常见模块（按需取用）：
- **封面**：小字母间距 eyebrow（`SHANGHAI · CITY WALK`）→ 大号粗体标题 → 一排 emoji 信息胶囊（`👫 2人` / `🕛 中午出发`）。
- **编号点位卡**：实心圆 badge（主色底白字）+ 点位名 + 时间·区域 + 填色标签（分类 + 停留时长）+ 正文 + 推荐 callout。
- **视觉重点**：把每个点位的"卖点短语"用**主色粗体**标出（如「泳池边喝咖啡、孙科别墅拍照」），让人一眼抓到亮点。
- **推荐/Tips**：callout 块（浅色填充 + 左侧主色边框 + 起首 emoji）。
- **链接**：做成带箭头胶囊更明显可点（`📍 高德地图导航 ›`），下划线+链接色也行——关键是让人知道能点。
- **交通**：方式 emoji（🚶🚇）+ 线路 pill + 虚线分隔。

## emoji / 图标
作**视线引导**很合适：信息胶囊、分类、callout 起首、交通方式（🚶🚇🍽🎁🍷🛍🎯）。建议一套语义一致的，别随机堆。
- macOS Chromium 下 emoji 正常渲染。
- 目标若是 Linux 无字体环境，改挂 `noto-color-emoji` 或退化为 SVG/几何图形——别因此放弃视觉引导。
- **不用 🙏**。

## 避免（少数真正廉价的"AI 默认观感"）
不是禁止视觉丰富，禁的是一眼假的廉价感：
- 默认 iOS 蓝 `#007AFF`、紫→白渐变 hero、海军蓝+金"企业报告"配色
- generic 仪表板 KPI 瓷砖 + 浓重投影、拟物高光
- 白底居中标题 + 细横线"极简"封面（最没记忆点的默认封面）
- 随机 emoji 堆砌
- `<br>`/spacer 撑版面、缩页边距硬塞、半空尾页凑数
> emoji、填色卡片、圆角、暖色多 tint 都**不在**避免之列——它们是编辑风的常用料。

## 机械细节补充（与 SKILL.md 机械契约配合）
- **字体栈**：`-apple-system, "PingFang SC", "STSong", "Helvetica Neue", Arial, sans-serif`；字型最多两种。
- **图片**：满版宽、清晰、尺寸一致；正文图源宽 ≥1080px。
- **图表**：旅游攻略一般不用；如用 Chart.js 必须 `animation=false` + 等渲染完再截。
- 阴影克制：白卡可 `0 1px 4px rgba(0,0,0,.05)`，别浓重投影。
