const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const {
  attachErrorCollectors,
  loadPlaywright,
  numberArg,
  parseArgs,
  required,
  setAuditTime,
  writeJson,
} = require('./_browser_common.cjs');

function colorSlug(color, index) {
  const cleaned = color.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  return cleaned || `background-${index + 1}`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node capture_transparency_matrix.cjs --url URL --output-dir DIR --background-selector SELECTOR --component-selector SELECTOR [--backgrounds "#fff,#081226,#595959"] [--width 390 --height 844] [--audit-time MS] [--report report.json]');
    return 0;
  }
  const url = required(args, 'url');
  const outputDir = path.resolve(required(args, 'output-dir'));
  const backgroundSelector = required(args, 'background-selector');
  const componentSelector = required(args, 'component-selector');
  const width = numberArg(args, 'width', 390);
  const height = numberArg(args, 'height', 844);
  const backgrounds = String(args.backgrounds || '#ffffff,#081226,#595959')
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
  if (backgrounds.length < 2) throw new Error('--backgrounds must contain at least two colors');

  fs.mkdirSync(outputDir, { recursive: true });
  const errors = [];
  const cases = [];
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    attachErrorCollectors(page, errors);
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    const auditTime = args['audit-time'] === undefined ? null : numberArg(args, 'audit-time', 0);
    if (auditTime !== null) await setAuditTime(page, auditTime);
    const background = page.locator(backgroundSelector);
    const component = page.locator(componentSelector);
    if (await background.count() !== 1) throw new Error(`Expected one background selector match: ${backgroundSelector}`);
    if (await component.count() !== 1) throw new Error(`Expected one component selector match: ${componentSelector}`);

    for (let index = 0; index < backgrounds.length; index += 1) {
      const color = backgrounds[index];
      if (auditTime !== null) await setAuditTime(page, auditTime);
      await background.evaluate((node, value) => {
        node.style.setProperty('background', value, 'important');
        node.style.setProperty('background-color', value, 'important');
        node.style.setProperty('background-image', 'none', 'important');
      }, color);
      await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
      const file = path.join(outputDir, `${String(index + 1).padStart(2, '0')}-${colorSlug(color, index)}.png`);
      await component.screenshot({ path: file, animations: 'disabled' });
      const buffer = fs.readFileSync(file);
      cases.push({
        background: color,
        screenshot: file,
        sha256: crypto.createHash('sha256').update(buffer).digest('hex'),
      });
    }
  } finally {
    await browser.close();
  }

  const distinctScreenshotCount = new Set(cases.map((item) => item.sha256)).size;
  const passed = errors.length === 0 && cases.length === backgrounds.length && distinctScreenshotCount > 1;
  const report = {
    passed,
    url,
    viewport: { width, height },
    background_selector: backgroundSelector,
    component_selector: componentSelector,
    audit_time_ms: args['audit-time'] === undefined ? null : numberArg(args, 'audit-time', 0),
    cases,
    distinct_screenshot_count: distinctScreenshotCount,
    errors,
    note: 'Distinct composites prove background response in the rendered candidate; they do not recover unknown source Alpha.',
  };
  writeJson(args.report || path.join(outputDir, 'transparency-matrix.json'), report);
  console.log(`${passed ? 'PASS' : 'FAIL'} backgrounds=${cases.length} distinct=${distinctScreenshotCount} errors=${errors.length}`);
  return passed ? 0 : 1;
}

main().then((code) => { process.exitCode = code; }).catch((error) => {
  console.error(`FAIL ${error.stack || error}`);
  process.exitCode = 1;
});
