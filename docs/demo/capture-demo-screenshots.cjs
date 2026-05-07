const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");

const reportPath = path.resolve(__dirname, "renders/demo-report.html");
const outDir = path.resolve(__dirname, "screenshots");
const readmeDir = path.resolve(__dirname, "../screenshots");
const storageKey = "tgcs-report-theme";

async function ensureVisible(page, selector, scrollOffset = -80) {
  const handle = await page.$(selector);
  if (!handle) {
    return false;
  }
  await handle.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  if (scrollOffset) {
    await page.evaluate((offset) => window.scrollBy(0, offset), scrollOffset);
    await page.waitForTimeout(200);
  }
  return true;
}

async function screenshotViewport(page, fileName, height = 900) {
  await page.screenshot({
    path: path.join(outDir, fileName),
    clip: { x: 0, y: 0, width: 1440, height },
  });
}

async function main() {
  if (!fs.existsSync(reportPath)) {
    console.error(`Report not found: ${reportPath}`);
    process.exit(1);
  }

  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(readmeDir, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    colorScheme: "dark",
  });

  await context.addInitScript((key) => {
    window.localStorage.setItem(key, "dark");
  }, storageKey);

  const page = await context.newPage();
  await page.goto(`file:///${reportPath.replace(/\\/g, "/")}`, { waitUntil: "networkidle" });
  await page.evaluate((key) => {
    window.localStorage.setItem(key, "dark");
    document.documentElement.setAttribute("data-theme", "dark");
    document.documentElement.style.colorScheme = "dark";
  }, storageKey);
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(800);

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await screenshotViewport(page, "01-header-stats.png");

  await ensureVisible(page, ".section-heading.high");
  await screenshotViewport(page, "02-cards-high.png");

  await ensureVisible(page, ".section-heading.medium");
  await screenshotViewport(page, "03-cards-medium.png");

  await ensureVisible(page, ".section-heading.low");
  await screenshotViewport(page, "03b-cards-low.png");

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await ensureVisible(page, ".section-heading.high");
  const toggle = await page.$(".raw-toggle");
  if (toggle) {
    await toggle.click();
    await page.waitForTimeout(350);
    await page.evaluate(() => {
      const raw = document.querySelector(".raw-content");
      if (raw) raw.scrollIntoView({ block: "center" });
    });
    await page.waitForTimeout(250);
  }
  await screenshotViewport(page, "04-expand-view.png");

  const tgLink = await page.$('a[href*="t.me/"]');
  if (tgLink) {
    await tgLink.scrollIntoViewIfNeeded();
    await tgLink.hover();
    await page.waitForTimeout(250);
  }
  await screenshotViewport(page, "06-telegram-link.png");
  await screenshotViewport(page, "05-telegram-link.png");

  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(200);
  await screenshotViewport(page, "07-full-page.png");

  await page.screenshot({
    path: path.join(readmeDir, "report-header.png"),
    clip: { x: 0, y: 0, width: 1440, height: 700 },
  });

  await ensureVisible(page, ".section-heading.high", -60);
  await page.screenshot({
    path: path.join(readmeDir, "report-cards.png"),
    clip: { x: 0, y: 0, width: 1440, height: 900 },
  });

  await browser.close();
  console.log("Dark demo screenshots captured.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
