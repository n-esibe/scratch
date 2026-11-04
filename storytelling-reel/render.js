// Renders reel.html frame by frame with headless Chromium.
// Usage: node render.js <outDir> [fps] [duration] [t1,t2,... for preview stills]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const outDir = process.argv[2] || 'frames';
  const fps = Number(process.argv[3] || 30);
  const dur = Number(process.argv[4] || 10);
  const stills = process.argv[5] ? process.argv[5].split(',').map(Number) : null;
  fs.mkdirSync(outDir, { recursive: true });

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(__dirname, 'reel.html'));
  await page.evaluate(() => window.ready);

  const times = stills || Array.from({ length: Math.round(fps * dur) }, (_, i) => i / fps);
  for (let i = 0; i < times.length; i++) {
    await page.evaluate(t => window.renderFrame(t), times[i]);
    const name = stills ? `still_${times[i].toFixed(2)}.png` : `f_${String(i).padStart(4, '0')}.png`;
    await page.screenshot({ path: path.join(outDir, name), type: 'png' });
  }
  await browser.close();
})();
