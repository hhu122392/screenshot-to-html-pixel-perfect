const fs = require('node:fs');
const path = require('node:path');

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) throw new Error(`Unexpected argument: ${token}`);
    const key = token.slice(2);
    const next = argv[index + 1];
    if (!next || next.startsWith('--')) {
      result[key] = true;
    } else {
      result[key] = next;
      index += 1;
    }
  }
  return result;
}

function required(args, key) {
  if (!args[key]) throw new Error(`Missing required --${key}`);
  return args[key];
}

function numberArg(args, key, fallback) {
  if (args[key] === undefined) return fallback;
  const value = Number(args[key]);
  if (!Number.isFinite(value)) throw new Error(`--${key} must be a number`);
  return value;
}

function ensureParent(file) {
  fs.mkdirSync(path.dirname(path.resolve(file)), { recursive: true });
}

function writeJson(file, value) {
  ensureParent(file);
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function loadPlaywright() {
  try {
    return require('playwright');
  } catch (error) {
    throw new Error('Playwright is required. Install it in the project or expose it through NODE_PATH.');
  }
}

function attachErrorCollectors(page, target) {
  page.on('console', (message) => {
    if (message.type() === 'error') target.push({ type: 'console', text: message.text() });
  });
  page.on('pageerror', (error) => target.push({ type: 'pageerror', text: String(error) }));
}

function contextOptions(viewport = {}) {
  return {
    viewport: {
      width: Number(viewport.width || 390),
      height: Number(viewport.height || 844),
    },
    deviceScaleFactor: Number(viewport.device_scale_factor || viewport.deviceScaleFactor || 1),
    isMobile: Boolean(viewport.is_mobile || viewport.isMobile),
    hasTouch: Boolean(viewport.has_touch || viewport.hasTouch),
  };
}

async function inspectElementVisibility(locator) {
  return locator.evaluate((node) => {
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    const colorMatch = style.color.match(/rgba?\(([^)]+)\)/i);
    const colorParts = colorMatch ? colorMatch[1].split(',').map((part) => part.trim()) : [];
    const colorAlpha = colorParts.length === 4 ? Number(colorParts[3]) : 1;
    const opacity = Number(style.opacity);
    const originalArea = Math.max(0, rect.width) * Math.max(0, rect.height);
    const visible = {
      left: Math.max(0, rect.left),
      top: Math.max(0, rect.top),
      right: Math.min(window.innerWidth, rect.right),
      bottom: Math.min(window.innerHeight, rect.bottom),
    };
    const clippedBy = [];
    const label = (element) => {
      if (element.id) return `#${element.id}`;
      if (element.classList.length) return `.${[...element.classList].join('.')}`;
      return element.tagName.toLowerCase();
    };
    for (let ancestor = node.parentElement; ancestor; ancestor = ancestor.parentElement) {
      const ancestorStyle = getComputedStyle(ancestor);
      const ancestorRect = ancestor.getBoundingClientRect();
      const clipsX = ['hidden', 'clip', 'auto', 'scroll', 'overlay'].includes(ancestorStyle.overflowX);
      const clipsY = ['hidden', 'clip', 'auto', 'scroll', 'overlay'].includes(ancestorStyle.overflowY);
      const before = { ...visible };
      if (clipsX) {
        visible.left = Math.max(visible.left, ancestorRect.left);
        visible.right = Math.min(visible.right, ancestorRect.right);
      }
      if (clipsY) {
        visible.top = Math.max(visible.top, ancestorRect.top);
        visible.bottom = Math.min(visible.bottom, ancestorRect.bottom);
      }
      if (Math.abs(before.left - visible.left) > 0.5
        || Math.abs(before.right - visible.right) > 0.5
        || Math.abs(before.top - visible.top) > 0.5
        || Math.abs(before.bottom - visible.bottom) > 0.5) clippedBy.push(label(ancestor));
    }
    const visibleWidth = Math.max(0, visible.right - visible.left);
    const visibleHeight = Math.max(0, visible.bottom - visible.top);
    const visibleArea = visibleWidth * visibleHeight;
    const intersectsViewport = rect.right > 0 && rect.bottom > 0 && rect.left < window.innerWidth && rect.top < window.innerHeight;
    const fullyInViewport = rect.left >= -0.5 && rect.top >= -0.5
      && rect.right <= window.innerWidth + 0.5 && rect.bottom <= window.innerHeight + 0.5;
    const fullyUnclipped = originalArea > 0 && Math.abs(visibleArea - originalArea) <= Math.max(1, originalArea * 0.002);
    return {
      opacity,
      color: style.color,
      color_alpha: Number.isFinite(colorAlpha) ? colorAlpha : 1,
      in_viewport: intersectsViewport,
      intersects_viewport: intersectsViewport,
      fully_in_viewport: fullyInViewport,
      fully_unclipped: fullyUnclipped,
      visible_ratio: originalArea > 0 ? visibleArea / originalArea : 0,
      clipped_by: [...new Set(clippedBy)],
      rendered_box: [rect.left, rect.top, rect.right, rect.bottom],
      visible_box: [visible.left, visible.top, visible.right, visible.bottom],
    };
  });
}

async function swipeLocator(page, locator, options = {}) {
  const box = await locator.boundingBox();
  if (!box) throw new Error(`Cannot swipe invisible selector: ${options.selector || '<unknown>'}`);
  const direction = String(options.direction || 'up');
  const distance = Math.max(1, Number(options.distance || Math.round(box.height * 0.72)));
  const steps = Math.max(3, Number(options.steps || 12));
  const centerX = box.x + box.width / 2;
  const centerY = box.y + box.height / 2;
  const margin = Math.min(24, Math.max(4, box.height * 0.08));
  let startX = centerX;
  let startY = centerY;
  let endX = centerX;
  let endY = centerY;
  if (direction === 'up') {
    startY = box.y + box.height - margin;
    endY = Math.max(box.y + margin, startY - distance);
  } else if (direction === 'down') {
    startY = box.y + margin;
    endY = Math.min(box.y + box.height - margin, startY + distance);
  } else if (direction === 'left') {
    startX = box.x + box.width - margin;
    endX = Math.max(box.x + margin, startX - distance);
  } else if (direction === 'right') {
    startX = box.x + margin;
    endX = Math.min(box.x + box.width - margin, startX + distance);
  } else {
    throw new Error(`Unsupported swipe direction: ${direction}`);
  }
  const session = await page.context().newCDPSession(page);
  await session.send('Input.dispatchTouchEvent', {
    type: 'touchStart',
    touchPoints: [{ x: startX, y: startY, radiusX: 5, radiusY: 5, force: 1, id: 1 }],
  });
  for (let index = 1; index <= steps; index += 1) {
    const ratio = index / steps;
    await session.send('Input.dispatchTouchEvent', {
      type: 'touchMove',
      touchPoints: [{
        x: startX + ((endX - startX) * ratio),
        y: startY + ((endY - startY) * ratio),
        radiusX: 5,
        radiusY: 5,
        force: 1,
        id: 1,
      }],
    });
    await page.waitForTimeout(16);
  }
  await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
  await page.waitForTimeout(Number(options.settle_ms || 120));
}

async function setAuditTime(page, milliseconds, requiredHook = true) {
  const found = await page.evaluate(async (time) => {
    if (typeof window.__setAuditTime !== 'function') return false;
    await window.__setAuditTime(time);
    await new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    return true;
  }, milliseconds);
  if (!found && requiredHook) throw new Error('window.__setAuditTime(milliseconds) is not defined');
  return found;
}

module.exports = {
  attachErrorCollectors,
  contextOptions,
  ensureParent,
  inspectElementVisibility,
  loadPlaywright,
  numberArg,
  parseArgs,
  readJson,
  required,
  setAuditTime,
  swipeLocator,
  writeJson,
};
