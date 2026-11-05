import puppeteer from 'puppeteer';

(async () => {
  const browser = await puppeteer.launch({
    headless: "new",
    executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.goto('http://localhost:5678', { waitUntil: 'networkidle2' });
  const title = await page.title();
  const url = page.url();
  await page.screenshot({ path: 'utils/n8n_preview.png' });
  await browser.close();
  console.log("SUCCESS:", title, url);
})();
