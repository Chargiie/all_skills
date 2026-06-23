// 手机竖屏卡片 PDF 渲染：300pt×667.5pt（9:20，匹配 2670×1200 手机屏）
// 满版无白边：margin 0，所有内边距在 CSS 控制，背景色跨页连续。
// 用法：NODE_PATH=/usr/local/lib/node_modules node scripts/render_mobile.cjs source.html out.pdf
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(process.argv[2]), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.waitForTimeout(300);

  await page.pdf({
    path: process.argv[3],
    width: '300pt',
    height: '667.5pt',
    printBackground: true,
    preferCSSPageSize: false,
    displayHeaderFooter: false,            // 满版编辑风：不注入页眉页脚，避免与满版色块冲突
    margin: { top: '0', right: '0', bottom: '0', left: '0' },  // 满版无白边，留白靠 CSS 内边距
  });

  await browser.close();
  console.log(JSON.stringify({ ok: true, size_kb: Math.round(fs.statSync(process.argv[3]).size / 1024) }));
})();
