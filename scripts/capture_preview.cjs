const path = require('node:path');
const {
  attachErrorCollectors,
  ensureParent,
  loadPlaywright,
  numberArg,
  parseArgs,
  required,
  setAuditTime,
  writeJson,
} = require('./_browser_common.cjs');

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node capture_preview.cjs --url URL --output page.png --width 390 --height 844 [--full-page] [--audit-time MS] [--report report.json]');
    return 0;
  }
  const url = required(args, 'url');
  const output = path.resolve(required(args, 'output'));
  const width = numberArg(args, 'width', 390);
  const height = numberArg(args, 'height', 844);
  const errors = [];
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  let report;
  try {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    attachErrorCollectors(page, errors);
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    if (args['audit-time'] !== undefined) {
      await setAuditTime(page, numberArg(args, 'audit-time', 0));
    }
    const settleMs = numberArg(args, 'settle-ms', 0);
    if (settleMs > 0) await page.waitForTimeout(settleMs);
    ensureParent(output);
    await page.screenshot({ path: output, fullPage: Boolean(args['full-page']), animations: 'disabled' });
    report = { passed: errors.length === 0, url, output, viewport: { width, height }, errors };
  } finally {
    await browser.close();
  }
  writeJson(args.report || `${output}.json`, report);
  console.log(`${report.passed ? 'PASS' : 'FAIL'} captured ${width}x${height} -> ${output}`);
  return report.passed ? 0 : 1;
}

main().then((code) => process.exitCode = code).catch((error) => {
  console.error(`FAIL ${error.stack || error}`);
  process.exitCode = 1;
});

