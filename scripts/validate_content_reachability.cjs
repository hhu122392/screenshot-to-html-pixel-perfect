const path = require('node:path');
const {
  attachErrorCollectors,
  contextOptions,
  inspectElementVisibility,
  loadPlaywright,
  parseArgs,
  readJson,
  required,
  swipeLocator,
  writeJson,
} = require('./_browser_common.cjs');

async function scrollContract(page, locator, method) {
  const metrics = await locator.evaluate((node) => ({ clientHeight: node.clientHeight, scrollHeight: node.scrollHeight }));
  const delta = Math.max(320, Math.round(metrics.clientHeight * 0.82));
  let previous = await locator.evaluate((node) => node.scrollTop);
  for (let attempt = 0; attempt < 8; attempt += 1) {
    if (method === 'wheel') {
      await locator.hover();
      await page.mouse.wheel(0, delta);
      await page.waitForTimeout(80);
    } else if (method === 'touch') {
      await swipeLocator(page, locator, { direction: 'up', distance: delta, settle_ms: 80 });
    } else if (method === 'programmatic') {
      await locator.evaluate((node) => node.scrollTo({ top: node.scrollHeight, behavior: 'instant' }));
      await page.waitForTimeout(40);
    } else {
      throw new Error(`Unsupported reachability method: ${method}`);
    }
    const current = await locator.evaluate((node) => node.scrollTop);
    if (current >= metrics.scrollHeight - metrics.clientHeight - 1 || current === previous) break;
    previous = current;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node validate_content_reachability.cjs --spec CONTENT_REACHABILITY.json --output-dir evidence/content-reachability');
    return 0;
  }
  const spec = readJson(path.resolve(required(args, 'spec')));
  const outputDir = path.resolve(required(args, 'output-dir'));
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const cases = [];
  const failures = [];
  try {
    for (const viewport of spec.viewports || []) {
      const context = await browser.newContext(contextOptions(viewport));
      const page = await context.newPage();
      const errors = [];
      attachErrorCollectors(page, errors);
      await page.goto(viewport.url || spec.url, { waitUntil: 'networkidle' });
      await page.evaluate(() => document.fonts && document.fonts.ready);
      for (const contract of spec.contracts || []) {
        const prefix = `${viewport.id || 'viewport'}:${contract.id || contract.scroll_selector}`;
        const scrollOwner = page.locator(contract.scroll_selector);
        const ownerCount = await scrollOwner.count();
        if (ownerCount !== 1) {
          failures.push(`${prefix}:scroll-owner-count`);
          cases.push({ viewport, contract: contract.id, passed: false, error: 'scroll-owner-count' });
          continue;
        }
        const items = scrollOwner.locator(contract.item_selector);
        const itemCount = await items.count();
        const children = [];
        let childrenPassed = true;
        for (let index = 0; index < itemCount; index += 1) {
          const row = items.nth(index);
          const childResult = { index, selectors: [] };
          for (const selector of contract.required_children || []) {
            const count = await row.locator(selector).count();
            const passed = count === 1;
            childResult.selectors.push({ selector, count, passed });
            if (!passed) childrenPassed = false;
          }
          children.push(childResult);
        }
        const ownerBefore = await scrollOwner.evaluate((node) => {
          const style = getComputedStyle(node);
          return {
            scrollTop: node.scrollTop,
            clientHeight: node.clientHeight,
            scrollHeight: node.scrollHeight,
            overflowY: style.overflowY,
          };
        });
        const firstVisibility = itemCount ? await inspectElementVisibility(items.first()) : null;
        const fixedBefore = {};
        for (const selector of contract.fixed_selectors || []) {
          fixedBefore[selector] = await page.locator(selector).evaluate((node) => {
            const rect = node.getBoundingClientRect();
            return { left: rect.left, top: rect.top };
          });
        }
        await scrollContract(page, scrollOwner, viewport.method || 'wheel');
        const scrollAfter = await scrollOwner.evaluate((node) => node.scrollTop);
        const lastVisibility = itemCount ? await inspectElementVisibility(items.last()) : null;
        const lastRequiredChildren = [];
        let lastRequiredChildrenFullyVisible = itemCount > 0;
        for (const selector of contract.required_children || []) {
          const child = items.last().locator(selector);
          const count = await child.count();
          const presentation = count === 1 ? await inspectElementVisibility(child) : null;
          const fullyVisible = count === 1
            && presentation.fully_in_viewport
            && presentation.fully_unclipped;
          lastRequiredChildren.push({ selector, count, presentation, fully_visible: fullyVisible });
          if (!fullyVisible) lastRequiredChildrenFullyVisible = false;
        }
        let fixedStable = true;
        const fixedAfter = {};
        for (const selector of contract.fixed_selectors || []) {
          fixedAfter[selector] = await page.locator(selector).evaluate((node) => {
            const rect = node.getBoundingClientRect();
            return { left: rect.left, top: rect.top };
          });
          if (Math.abs(fixedAfter[selector].left - fixedBefore[selector].left) > 1
            || Math.abs(fixedAfter[selector].top - fixedBefore[selector].top) > 1) fixedStable = false;
        }
        const countPassed = contract.expected_count === undefined || itemCount === Number(contract.expected_count);
        const scrollRange = ownerBefore.scrollHeight - ownerBefore.clientHeight;
        const explicitScrollableStyle = ['auto', 'scroll', 'overlay'].includes(ownerBefore.overflowY);
        const firstItemFullyVisible = Boolean(firstVisibility && firstVisibility.fully_in_viewport && firstVisibility.fully_unclipped);
        const lastItemFullyVisible = Boolean(lastVisibility && lastVisibility.fully_in_viewport && lastVisibility.fully_unclipped);
        const inputMoved = scrollAfter > ownerBefore.scrollTop;
        const rangePassed = scrollRange >= Number(contract.min_scroll_range || 1);
        const passed = countPassed && childrenPassed && explicitScrollableStyle && rangePassed
          && firstItemFullyVisible && inputMoved && lastItemFullyVisible
          && lastRequiredChildrenFullyVisible && fixedStable && errors.length === 0;
        const result = {
          viewport,
          contract: contract.id,
          passed,
          item_count: itemCount,
          expected_count: contract.expected_count,
          children,
          overflow_y: ownerBefore.overflowY,
          scroll_range: scrollRange,
          scroll_before: ownerBefore.scrollTop,
          scroll_after: scrollAfter,
          first_item_fully_visible: firstItemFullyVisible,
          last_item_fully_visible: lastItemFullyVisible,
          last_required_children: lastRequiredChildren,
          last_required_children_fully_visible: lastRequiredChildrenFullyVisible,
          fixed_stable: fixedStable,
          fixed_before: fixedBefore,
          fixed_after: fixedAfter,
          errors,
        };
        cases.push(result);
        if (!countPassed) failures.push(`${prefix}:item-count`);
        if (!childrenPassed) failures.push(`${prefix}:required-children`);
        if (!explicitScrollableStyle) failures.push(`${prefix}:scroll-style`);
        if (!rangePassed) failures.push(`${prefix}:scroll-range`);
        if (!firstItemFullyVisible) failures.push(`${prefix}:first-item-unreachable`);
        if (!inputMoved) failures.push(`${prefix}:input-did-not-scroll`);
        if (!lastItemFullyVisible) failures.push(`${prefix}:last-item-unreachable`);
        if (!lastRequiredChildrenFullyVisible) failures.push(`${prefix}:last-required-child-unreachable`);
        if (!fixedStable) failures.push(`${prefix}:fixed-content-shifted`);
        if (errors.length) failures.push(`${prefix}:browser-errors`);
        await page.screenshot({ path: path.join(outputDir, `${prefix.replace(/[^a-z0-9_-]+/gi, '-')}.png`) });
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
  const passed = failures.length === 0 && cases.length > 0;
  writeJson(path.join(outputDir, 'content-reachability.json'), {
    passed,
    cases,
    failures,
    p0_count: passed ? 0 : 1,
  });
  console.log(`${passed ? 'PASS' : 'FAIL'} cases=${cases.length} failures=${failures.length}`);
  return passed ? 0 : 1;
}

main().then((code) => { process.exitCode = code; }).catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
