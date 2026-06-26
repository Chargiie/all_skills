// 手机竖屏「屏卡」PDF 渲染：每页 = 一屏（400×890 CSS px ≈ 300×667.5pt，9:20，匹配 2670×1200 手机屏）
// 满版无白边：margin 0，留白靠 CSS 内边距，背景色跨页连续。
// 屏卡护栏：渲染前遍历所有 .screen，测内容是否溢出一屏 / 填充是否过空，逐卡报告；
//   有任一卡溢出（内容 > 890px，会被裁切 / 出血）→ 退出码 1（这是把固定高度变安全的关键）。
//   无 .screen 元素时回退旧行为（仅渲染 + 报体积），向后兼容。
// 用法：NODE_PATH=~/.npm-global/lib/node_modules node scripts/render_mobile.cjs source.html out.pdf

const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');

const SCREEN_H = 890;          // 一屏逻辑高（CSS px）
const OVERFLOW_TOL = 2;        // 容差，避免 1px 取整误报
const UNDERFILL = 0.55;        // 低于此填充比给 warn（不致命，交给「看图」终判）

(async () => {
  const src = process.argv[2], out = process.argv[3];
  if (!src || !out) { console.error('用法: render_mobile.cjs <source.html> <out.pdf>'); process.exit(2); }

  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(src), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.waitForTimeout(300);

  // —— 屏卡测量：每张 .screen 的盒高、内容高、是否溢出、填充比 ——
  const cards = await page.evaluate(() => {
    const screens = Array.from(document.querySelectorAll('.screen'));
    return screens.map((el, i) => {
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      // 内容真实高度：取所有「非绝对/固定定位」后代相对卡顶的最大下沿（绝对定位多为装饰出血，排除以免误报）
      let contentBottom = 0;
      el.querySelectorAll('*').forEach(c => {
        const pos = getComputedStyle(c).position;
        if (pos === 'absolute' || pos === 'fixed') return;
        const b = c.getBoundingClientRect().bottom - r.top;
        if (b > contentBottom) contentBottom = b;
      });
      const padBottom = parseFloat(cs.paddingBottom) || 0;
      return {
        i: i + 1,
        boxH: Math.round(r.height),
        clientH: el.clientHeight,
        scrollH: el.scrollHeight,           // 仅供参考；含绝对定位出血元素，不用于判定（见下方报告）
        contentH: Math.round(contentBottom + padBottom),
      };
    });
  });

  await page.pdf({
    path: out,
    width: '400px',                        // = 300pt（96dpi：pt×4/3），Playwright page.pdf 不收 pt 单位
    height: '890px',                       // = 667.5pt，物理尺寸等价，9:20
    printBackground: true,
    preferCSSPageSize: false,
    displayHeaderFooter: false,            // 满版编辑风：不注入页眉页脚，避免与满版色块冲突
    margin: { top: '0', right: '0', bottom: '0', left: '0' },  // 满版无白边，留白靠 CSS 内边距
  });

  await browser.close();

  const size_kb = Math.round(fs.statSync(out).size / 1024);

  // —— 无 .screen：回退旧行为 ——
  if (cards.length === 0) {
    console.log(JSON.stringify({ ok: true, size_kb, screens: 0,
      note: '未发现 .screen 屏卡元素，按普通流动模式渲染；屏卡护栏未生效' }));
    return;
  }

  // —— 屏卡报告 ——
  // 判溢出只看「在流内容」高度 contentH（测量时已排除绝对/固定定位元素）。
  // 不能用 scrollHeight：它含绝对定位的出血装饰（满版 SVG、贴边页脚等），会把本该通过的卡误报溢出。
  // 颐和园式真实事故（流动页脚被超量正文顶出屏）是「在流」内容，contentH 能准确逮到。
  const report = cards.map(c => {
    const overflow = c.contentH > SCREEN_H + OVERFLOW_TOL;
    const fill = +(c.contentH / SCREEN_H).toFixed(2);
    return { card: c.i, contentH: c.contentH, scrollH: c.scrollH, fill,
      overflow, underfill: !overflow && fill < UNDERFILL };
  });
  const overflowed = report.filter(r => r.overflow);
  const underfilled = report.filter(r => r.underfill);

  console.log(JSON.stringify({
    ok: overflowed.length === 0,
    size_kb,
    screens: cards.length,
    screen_h: SCREEN_H,
    cards: report,
    overflow_cards: overflowed.map(r => r.card),
    underfill_cards: underfilled.map(r => r.card),
  }, null, 2));

  if (overflowed.length) {
    console.error(`\n✗ 溢出：第 ${overflowed.map(r => r.card).join(', ')} 张卡内容超过一屏(${SCREEN_H}px)，会被裁切/出血。`);
    console.error('  → 拆成多张卡，或降一档密度（缩小字号/行距/间距、精简文案）。');
    process.exit(1);
  }
  if (underfilled.length) {
    console.error(`\n⚠ 偏空：第 ${underfilled.map(r => r.card).join(', ')} 张卡填充 < ${UNDERFILL}，可能显空。`
      + '请看图确认是否「有意的 hero 留白」，否则放大字号/加内容/合并卡。');
  }
})();
