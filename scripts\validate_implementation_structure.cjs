const path = require('node:path');
const {
  attachErrorCollectors,
  ensureParent,
  inspectElementVisibility,
  loadPlaywright,
  parseArgs,
  readJson,
  required,
  writeJson,
} = require('./_browser_common.cjs');

function matchesText(actual, expected, mode) {
  const normalized = String(actual || '').replace(/\s+/g, ' ').trim();
  const target = String(expected || '').replace(/\s+/g, ' ').trim();
  return mode === 'contains' ? normalized.includes(target) : normalized === target;
}

function visibilityPass(presentation, mode = 'intersects') {
  if (!presentation) return false;
  const painted = presentation.opacity > 0.05 && presentation.color_alpha > 0.05;
  if (mode === 'dom') return painted;
  if (mode === 'fully-visible') {
    return painted && presentation.fully_in_viewport && presentation.fully_unclipped;
  }
  return painted && presentation.intersects_viewport && presentation.visible_ratio > 0;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node validate_implementation_structure.cjs --spec STRUCTURE_AUDIT.json --output-dir evidence/structure-audit');
    return 0;
  }

  const spec = readJson(path.resolve(required(args, 'spec')));
  const outputDir = path.resolve(required(args, 'output-dir'));
  const viewport = spec.viewport || { width: 390, height: 844 };
  const browserErrors = [];
  const failures = [];
  const liveTextResults = [];
  const collectionResults = [];
  const rasterResults = [];
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });

  try {
    const page = await browser.newPage({ viewport, deviceScaleFactor: 1 });
    attachErrorCollectors(page, browserErrors);
    await page.goto(spec.url, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts && document.fonts.ready);

    for (const item of spec.live_text || []) {
      const locator = page.locator(item.selector);
      const count = await locator.count();
      const visible = count === 1 && await locator.isVisible();
      const tagName = count === 1 ? await locator.evaluate((node) => node.tagName) : null;
      const text = count === 1 ? await locator.textContent() : null;
      const presentation = count === 1 ? await inspectElementVisibility(locator) : null;
      const nonRasterElement = !['IMG', 'PICTURE', 'CANVAS', 'SVG'].includes(tagName);
      const textMatches = count === 1 && matchesText(text, item.text, item.mode || 'exact');
      const visiblyPainted = visibilityPass(presentation, item.visibility || 'intersects');
      const passed = count === 1 && visible && visiblyPainted && nonRasterElement && textMatches;
      const result = { ...item, count, visible, tag_name: tagName, actual_text: text, presentation, passed };
      liveTextResults.push(result);
      if (!passed) failures.push(`live_text:${item.id || item.selector}`);
    }

    for (const item of spec.collections || []) {
      const collection = page.locator(item.selector);
      const count = await collection.count();
      const countPassed = item.expected_count === undefined
        ? count >= Number(item.min_count || 1)
        : count === Number(item.expected_count);
      const children = [];
      for (let index = 0; index < count; index += 1) {
        const row = collection.nth(index);
        const rowResult = { index, visible: await row.isVisible(), children: [] };
        for (const childSpec of item.required_children || []) {
          const child = row.locator(childSpec.selector);
          const childCount = await child.count();
          const childVisible = childCount === 1 && await child.isVisible();
          const tagName = childCount === 1 ? await child.evaluate((node) => node.tagName) : null;
          const presentation = childCount === 1 ? await inspectElementVisibility(child) : null;
          const visiblyPainted = visibilityPass(
            presentation,
            childSpec.visibility || item.visibility || 'intersects',
          );
          const passed = childCount === 1 && childVisible && visiblyPainted && !['IMG', 'PICTURE', 'CANVAS'].includes(tagName);
          rowResult.children.push({ selector: childSpec.selector, count: childCount, visible: childVisible, tag_name: tagName, presentation, passed });
        }
        rowResult.passed = rowResult.visible && rowResult.children.every((child) => child.passed);
        children.push(rowResult);
      }
      const passed = countPassed && children.every((row) => row.passed);
      collectionResults.push({ ...item, count, count_passed: countPassed, rows: children, passed });
      if (!passed) failures.push(`collection:${item.id || item.selector}`);
    }

    const rasterPolicy = spec.raster_policy || {};
    const rasterData = await page.evaluate(({ maximum, allowedSelectors, forbiddenPatterns }) => {
      const viewportArea = window.innerWidth * window.innerHeight;
      const isVisible = (node, style, rect) =>
        style.display !== 'none' && style.visibility !== 'hidden' && Number(style.opacity) > 0 && rect.width > 0 && rect.height > 0;
      const isAllowed = (node) => allowedSelectors.some((selector) => {
        try { return node.matches(selector); } catch { return false; }
      });
      const patternMatch = (source) => forbiddenPatterns.find((pattern) => new RegExp(pattern, 'i').test(source)) || null;
      const found = [];

      for (const image of document.querySelectorAll('img')) {
        const style = getComputedStyle(image);
        const rect = image.getBoundingClientRect();
        if (!isVisible(image, style, rect)) continue;
        const source = image.currentSrc || image.src || '';
        const areaRatio = (rect.width * rect.height) / viewportArea;
        const allowed = isAllowed(image);
        const forbiddenPattern = patternMatch(source);
        found.push({
          kind: 'img',
          selector_hint: image.className || image.id || image.tagName,
          source,
          rendered_box: [rect.left, rect.top, rect.right, rect.bottom],
          rendered_area_ratio: areaRatio,
          allowed,
          forbidden_pattern: forbiddenPattern,
          passed: !forbiddenPattern && (allowed || areaRatio <= maximum),
        });
      }

      for (const node of document.querySelectorAll('body *')) {
        const style = getComputedStyle(node);
        if (!style.backgroundImage || style.backgroundImage === 'none' || !style.backgroundImage.includes('url(')) continue;
        const rect = node.getBoundingClientRect();
        if (!isVisible(node, style, rect)) continue;
        const source = style.backgroundImage;
        const areaRatio = (rect.width * rect.height) / viewportArea;
        const allowed = isAllowed(node);
        const forbiddenPattern = patternMatch(source);
        found.push({
          kind: 'css-background',
          selector_hint: node.className || node.id || node.tagName,
          source,
          rendered_box: [rect.left, rect.top, rect.right, rect.bottom],
          rendered_area_ratio: areaRatio,
          allowed,
          forbidden_pattern: forbiddenPattern,
          passed: !forbiddenPattern && (allowed || areaRatio <= maximum),
        });
      }
      return found;
    }, {
      maximum: Number(rasterPolicy.max_rendered_area_ratio ?? 0.08),
      allowedSelectors: rasterPolicy.allow_selectors || [],
      forbiddenPatterns: rasterPolicy.forbidden_source_patterns || [],
    });

    rasterResults.push(...rasterData);
    const rejectOverlap = rasterPolicy.reject_overlap_with_live_text !== false;
    const allowedOverlapSelectors = rasterPolicy.allow_overlap_selectors || [];
    if (rejectOverlap) {
      for (const raster of rasterResults) {
        const overlapAllowed = allowedOverlapSelectors.some((selector) => raster.selector_hint.split(/\s+/).includes(selector.replace(/^\./, '')));
        if (overlapAllowed) continue;
        const [left, top, right, bottom] = raster.rendered_box;
        const overlaps = liveTextResults.filter((textResult) => {
          const box = textResult.presentation && textResult.presentation.rendered_box;
          if (!box) return false;
          return Math.min(right, box[2]) > Math.max(left, box[0])
            && Math.min(bottom, box[3]) > Math.max(top, box[1]);
        }).map((textResult) => textResult.id || textResult.selector);
        raster.overlaps_live_text = overlaps;
        if (overlaps.length) raster.passed = false;
      }
    }
    for (const item of rasterResults.filter((entry) => !entry.passed)) {
      failures.push(`raster:${item.selector_hint}`);
    }
    if (browserErrors.length) failures.push('browser_errors');

    const screenshotPath = path.join(outputDir, 'structure-audit.png');
    ensureParent(screenshotPath);
    await page.screenshot({ path: screenshotPath, fullPage: false, animations: 'disabled' });
    await page.close();
  } finally {
    await browser.close();
  }

  const passed = failures.length === 0;
  const report = {
    passed,
    url: spec.url,
    viewport,
    failure_count: failures.length,
    failures,
    browser_errors: browserErrors,
    live_text: liveTextResults,
    collections: collectionResults,
    rasters: rasterResults,
  };
  writeJson(path.join(outputDir, 'structure-audit.json'), report);
  console.log(`${passed ? 'PASS' : 'FAIL'} live_text=${liveTextResults.length} collections=${collectionResults.length} rasters=${rasterResults.length} failures=${failures.length}`);
  return passed ? 0 : 1;
}

main().then((code) => { process.exitCode = code; }).catch((error) => {
  console.error(`FAIL ${error.stack || error}`);
  process.exitCode = 1;
});
