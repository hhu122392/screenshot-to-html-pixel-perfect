const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const outputDir = path.join(root, "evidence", "responsive-audit");
fs.mkdirSync(outputDir, { recursive: true });

const cases = [
  { id: "mobile-360", width: 360, height: 780 },
  { id: "mobile-390", width: 390, height: 846 },
  { id: "mobile-430", width: 430, height: 932 },
];

(async () => {
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    for (const item of cases) {
      const page = await browser.newPage({ viewport: { width: item.width, height: item.height }, deviceScaleFactor: 1 });
      const errors = [];
      page.on("console", (message) => {
        if (message.type() === "error") errors.push(`console:${message.text()}`);
      });
      page.on("pageerror", (error) => errors.push(`page:${error.message}`));
      await page.goto("http://127.0.0.1:4198/", { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      const facts = await page.evaluate(() => {
        const box = (selector) => {
          const rect = document.querySelector(selector).getBoundingClientRect();
          return { left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom, width: rect.width, height: rect.height };
        };
        return {
          header: box(".promo-header"),
          body: box(".dialog-body"),
          close: box(".close-button"),
          rewardCount: document.querySelectorAll(".reward-card").length,
          scrollWidth: document.documentElement.scrollWidth,
          scrollHeight: document.documentElement.scrollHeight,
        };
      });
      const inViewport = [facts.header, facts.body, facts.close].every((rect) => (
        rect.left >= -0.5 && rect.top >= -0.5 && rect.right <= item.width + 0.5 && rect.bottom <= item.height + 0.5
      ));
      const passed = inViewport && facts.rewardCount === 7 && facts.scrollWidth === item.width && facts.scrollHeight === item.height && errors.length === 0;
      const screenshot = path.join(outputDir, `${item.id}.png`);
      await page.screenshot({ path: screenshot, animations: "disabled" });
      results.push({ ...item, passed, inViewport, errors, ...facts, screenshot });
      await page.close();
    }
  } finally {
    await browser.close();
  }
  const report = {
    passed: results.every((item) => item.passed),
    case_count: results.length,
    failed_case_count: results.filter((item) => !item.passed).length,
    cases: results,
  };
  fs.writeFileSync(path.join(outputDir, "responsive-audit.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(`${report.passed ? "PASS" : "FAIL"} responsive cases=${report.case_count} failed=${report.failed_case_count}`);
  process.exitCode = report.passed ? 0 : 1;
})().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
