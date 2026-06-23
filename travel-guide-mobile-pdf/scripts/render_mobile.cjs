// 手机竖屏卡片 PDF 渲染：300pt×667.5pt（9:20，匹配 2670×1200 手机屏）
// 用法：NODE_PATH=/usr/local/lib/node_modules node scripts/render_mobile.cjs source.html out.pdf [标题]
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(process.argv[2]), { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts && document.fonts.ready);
  await page.waitForTimeout(300);

  const title = process.argv[4] || '';
  const footerTemplate = `
    <div style="font-size:8pt;color:#7f7f7f;width:100%;padding:0 11pt;
                display:flex;justify-content:space-between;
                font-family:'PingFang SC',sans-serif;">
      <span style="opacity:.5;">${title}</span>
      <span><span class="pageNumber"></span> / <span class="totalPages"></span></span>
    </div>`;

  await page.pdf({
    path: process.argv[3],
    width: '300pt',
    height: '667.5pt',
    printBackground: true,
    preferCSSPageSize: false,
    displayHeaderFooter: true,
    headerTemplate: '<div></div>',
    footerTemplate,
    margin: { top: '12pt', right: '11pt', bottom: '14pt', left: '11pt' },
  });

  await browser.close();
  console.log(JSON.stringify({ ok: true, size_kb: Math.round(fs.statSync(process.argv[3]).size / 1024) }));
})();
