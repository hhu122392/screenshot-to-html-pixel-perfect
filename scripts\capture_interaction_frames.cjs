const fs = require('node:fs');
const path = require('node:path');
const {
  attachErrorCollectors,
  loadPlaywright,
  numberArg,
  parseArgs,
  readJson,
  required,
  setAuditTime,
  writeJson,
} = require('./_browser_common.cjs');

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node capture_interaction_frames.cjs --url URL --timeline frames.json --output-dir frames --width 390 --height 844');
    return 0;
  }
  const url = required(args, 'url');
  const timeline = readJson(path.resolve(required(args, 'timeline')));
  const outputDir = path.resolve(required(args, 'output-dir'));
  const width = numberArg(args, 'width', 390);
  const height = numberArg(args, 'height', 844);
  const frames = timeline.frames || [];
  if (!frames.length) throw new Error('timeline contains no frames');
  fs.mkdirSync(outputDir, { recursive: true });
  const errors = [];
  const captured = [];
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
    attachErrorCollectors(page, errors);
    await page.goto(url, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts && document.fonts.ready);
    for (let index = 0; index < frames.length; index += 1) {
      const timeMs = Number(frames[index].time_ms);
      await setAuditTime(page, timeMs);
      const file = `frame-${String(index).padStart(6, '0')}.png`;
      await page.screenshot({ path: path.join(outputDir, file), fullPage: false, animations: 'allow' });
      captured.push({ index, time_ms: timeMs, file });
    }
  } finally {
    await browser.close();
  }
  const passed = errors.length === 0 && captured.length === frames.length;
  const manifest = {
    passed,
    url,
    viewport: { width, height },
    declared_frame_count: frames.length,
    decoded_frame_count: captured.length,
    errors,
    frames: captured,
  };
  writeJson(path.join(outputDir, 'frames.json'), manifest);
  console.log(`${passed ? 'PASS' : 'FAIL'} captured=${captured.length} declared=${frames.length}`);
  return passed ? 0 : 1;
}

main().then((code) => process.exitCode = code).catch((error) => {
  console.error(`FAIL ${error.stack || error}`);
  process.exitCode = 1;
});

