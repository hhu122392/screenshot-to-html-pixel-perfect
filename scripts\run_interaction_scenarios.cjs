const path = require('node:path');
const {
  attachErrorCollectors,
  contextOptions,
  inspectElementVisibility,
  loadPlaywright,
  parseArgs,
  readJson,
  required,
  setAuditTime,
  swipeLocator,
  writeJson,
} = require('./_browser_common.cjs');

async function performStep(page, step) {
  const locator = step.selector ? page.locator(step.selector) : null;
  switch (step.action) {
    case 'click': await locator.click(); break;
    case 'tap': await locator.tap(); break;
    case 'hover': await locator.hover(); break;
    case 'fill': await locator.fill(String(step.value ?? '')); break;
    case 'press': await locator.press(String(step.key)); break;
    case 'scroll': await page.evaluate(({ x, y }) => window.scrollTo(x, y), { x: Number(step.x || 0), y: Number(step.y || 0) }); break;
    case 'scrollSelector': {
      await locator.evaluate((node, value) => {
        const top = value.position === 'end'
          ? node.scrollHeight
          : value.position === 'start'
            ? 0
            : Number(value.top || 0);
        node.scrollTo({ top, left: Number(value.left || 0), behavior: 'instant' });
      }, step);
      await page.waitForTimeout(Number(step.settle_ms || 50));
      break;
    }
    case 'wheel': {
      if (locator) await locator.hover();
      else if (step.x !== undefined && step.y !== undefined) await page.mouse.move(Number(step.x), Number(step.y));
      await page.mouse.wheel(Number(step.delta_x || 0), Number(step.delta_y || step.delta || 0));
      await page.waitForTimeout(Number(step.settle_ms || 80));
      break;
    }
    case 'swipe': await swipeLocator(page, locator, { ...step, selector: step.selector }); break;
    case 'wait': await page.waitForTimeout(Number(step.ms || 0)); break;
    case 'auditTime': await setAuditTime(page, Number(step.time_ms || 0)); break;
    default: throw new Error(`Unsupported interaction action: ${step.action}`);
  }
}

async function assertState(page, assertion) {
  const locator = assertion.selector ? page.locator(assertion.selector) : null;
  switch (assertion.type) {
    case 'visible': if (!(await locator.isVisible())) throw new Error(`${assertion.selector} is not visible`); break;
    case 'hidden': if (await locator.isVisible()) throw new Error(`${assertion.selector} is visible`); break;
    case 'text': {
      const actual = await locator.textContent();
      if (actual !== String(assertion.value)) throw new Error(`text mismatch for ${assertion.selector}: ${actual}`);
      break;
    }
    case 'attribute': {
      const actual = await locator.getAttribute(assertion.name);
      if (actual !== String(assertion.value)) throw new Error(`attribute mismatch for ${assertion.selector}: ${actual}`);
      break;
    }
    case 'count': {
      const actual = await locator.count();
      if (actual !== Number(assertion.value)) throw new Error(`count mismatch for ${assertion.selector}: ${actual}`);
      break;
    }
    case 'url': if (page.url() !== String(assertion.value)) throw new Error(`URL mismatch: ${page.url()}`); break;
    case 'scrollTop': {
      const actual = await locator.evaluate((node) => node.scrollTop);
      if (assertion.value !== undefined && Math.abs(actual - Number(assertion.value)) > Number(assertion.tolerance || 1)) {
        throw new Error(`scrollTop mismatch for ${assertion.selector}: ${actual}`);
      }
      if (assertion.min !== undefined && actual < Number(assertion.min)) {
        throw new Error(`scrollTop below minimum for ${assertion.selector}: ${actual}`);
      }
      if (assertion.max !== undefined && actual > Number(assertion.max)) {
        throw new Error(`scrollTop above maximum for ${assertion.selector}: ${actual}`);
      }
      break;
    }
    case 'fullyVisible': {
      const presentation = await inspectElementVisibility(locator);
      if (!presentation.fully_in_viewport || !presentation.fully_unclipped) {
        throw new Error(`${assertion.selector} is not fully visible: ${JSON.stringify(presentation)}`);
      }
      break;
    }
    default: throw new Error(`Unsupported assertion type: ${assertion.type}`);
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('Usage: node run_interaction_scenarios.cjs --spec INTERACTION_SCENARIOS.json --output-dir evidence/interaction-audit');
    return 0;
  }
  const specPath = path.resolve(required(args, 'spec'));
  const outputDir = path.resolve(required(args, 'output-dir'));
  const spec = readJson(specPath);
  const viewport = spec.viewport || { width: 390, height: 844 };
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const results = [];
  try {
    for (const scenario of spec.scenarios || []) {
      const errors = [];
      const viewportSpec = { ...viewport, ...(scenario.viewport || {}) };
      const context = await browser.newContext(contextOptions(viewportSpec));
      const page = await context.newPage();
      attachErrorCollectors(page, errors);
      let failure = null;
      try {
        await page.goto(scenario.url || spec.url, { waitUntil: 'networkidle' });
        await page.evaluate(() => document.fonts && document.fonts.ready);
        for (const step of scenario.steps || []) await performStep(page, step);
        for (const assertion of scenario.assertions || []) await assertState(page, assertion);
      } catch (error) {
        failure = String(error.message || error);
      }
      const screenshot = path.join(outputDir, `${scenario.id}.png`);
      await page.screenshot({ path: screenshot, fullPage: false, animations: 'disabled' });
      await context.close();
      results.push({ id: scenario.id, passed: !failure && errors.length === 0, failure, errors, screenshot });
    }
  } finally {
    await browser.close();
  }
  const passed = results.length > 0 && results.every((result) => result.passed);
  const report = { passed, scenario_count: results.length, failed_scenario_count: results.filter((item) => !item.passed).length, scenarios: results };
  writeJson(path.join(outputDir, 'interaction-audit.json'), report);
  console.log(`${passed ? 'PASS' : 'FAIL'} scenarios=${results.length} failed=${report.failed_scenario_count}`);
  return passed ? 0 : 1;
}

main().then((code) => process.exitCode = code).catch((error) => {
  console.error(`FAIL ${error.stack || error}`);
  process.exitCode = 1;
});
