// Serves this folder over HTTP and renders scene.html frame by frame (WebGL via SwiftShader).
// Usage: node render.js <outDir> [fps] [duration] [t1,t2,... for preview stills]
const { chromium } = require('playwright');
const http = require('http');
const fs = require('fs');
const path = require('path');

const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.jpg': 'image/jpeg', '.png': 'image/png' };
const server = http.createServer((req, res) => {
  const p = path.join(__dirname, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(__dirname) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': TYPES[path.extname(p)] || 'application/octet-stream' });
  fs.createReadStream(p).pipe(res);
});

(async () => {
  const outDir = process.argv[2] || 'frames';
  const fps = Number(process.argv[3] || 30);
  const dur = Number(process.argv[4] || 10);
  const stills = process.argv[5] ? process.argv[5].split(',').map(Number) : null;
  fs.mkdirSync(outDir, { recursive: true });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;

  const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/scene.html`);
  await page.waitForFunction(() => window.ready && window.renderFrame, null, { timeout: 120000 });
  await page.evaluate(() => window.ready);

  const times = stills || Array.from({ length: Math.round(fps * dur) }, (_, i) => i / fps);
  const el = await page.$('#out');
  const t0 = Date.now();
  for (let i = 0; i < times.length; i++) {
    await page.evaluate(t => window.renderFrame(t), times[i]);
    const name = stills ? `still_${times[i].toFixed(2)}.png` : `f_${String(i).padStart(4, '0')}.png`;
    await el.screenshot({ path: path.join(outDir, name), type: 'png' });
    if (i % 30 === 0) console.log(`frame ${i}/${times.length} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
  }
  await browser.close();
  server.close();
})();
