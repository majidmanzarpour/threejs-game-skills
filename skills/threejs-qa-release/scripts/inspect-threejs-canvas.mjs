#!/usr/bin/env node
import { chromium, devices } from '@playwright/test';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { PNG } from 'pngjs';

// Starting-point render budgets (see threejs-aaa-graphics-builder
// references/technical-art.md). Over-budget rows are reported, not fatal.
const RENDER_BUDGETS = {
  desktop: { calls: 300, triangles: 750_000, geometries: 300, textures: 60 },
  mobile: { calls: 150, triangles: 300_000, geometries: 200, textures: 40 },
};

function parseArgs(argv) {
  const args = {
    url: 'http://127.0.0.1:5188',
    out: 'artifacts/canvas-inspection',
    mobile: false,
    wait: 750,
    state: null,
    seed: undefined,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    if (value === '--url') args.url = argv[++i];
    else if (value === '--out') args.out = argv[++i];
    else if (value === '--mobile') args.mobile = true;
    else if (value === '--wait') args.wait = Number(argv[++i]);
    else if (value === '--state') args.state = argv[++i];
    else if (value === '--seed') args.seed = Number(argv[++i]);
    else if (value === '-h' || value === '--help') {
      console.log(
        'Usage: inspect-threejs-canvas.mjs [--url URL] [--out DIR] [--mobile] [--wait MS] [--state NAME] [--seed N]\n' +
          '  --state/--seed drive window.__THREE_GAME_TEST_HOOKS__ (setState/seed) before capture\n' +
          '  so specific game states can be measured deterministically.',
      );
      process.exit(0);
    } else {
      throw new Error(`Unknown argument: ${value}`);
    }
  }

  return args;
}

const round = (value, digits) => Number(value.toFixed(digits));

// Objective pixel statistics used as "Measured Evidence" in the visual
// scorecard. Computed on a coarse luminance grid so cost stays trivial.
function computePixelMetrics(png) {
  const stepX = Math.max(1, Math.floor(png.width / 160));
  const stepY = Math.max(1, Math.floor(png.height / 90));
  const cols = Math.floor(png.width / stepX);
  const rows = Math.floor(png.height / stepY);
  const luminance = new Float64Array(cols * rows);
  const bucketCounts = new Map();
  let samples = 0;

  for (let gy = 0; gy < rows; gy += 1) {
    for (let gx = 0; gx < cols; gx += 1) {
      const offset = ((gy * stepY) * png.width + gx * stepX) * 4;
      const r = png.data[offset];
      const g = png.data[offset + 1];
      const b = png.data[offset + 2];
      luminance[gy * cols + gx] = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      const key = `${r >> 4},${g >> 4},${b >> 4}`;
      bucketCounts.set(key, (bucketCounts.get(key) ?? 0) + 1);
      samples += 1;
    }
  }

  const sorted = Array.from(luminance).sort((a, b) => a - b);
  const mean = sorted.reduce((sum, v) => sum + v, 0) / sorted.length;
  const p5 = sorted[Math.floor(sorted.length * 0.05)];
  const p95 = sorted[Math.floor(sorted.length * 0.95)];

  let entropy = 0;
  let dominant = 0;
  for (const count of bucketCounts.values()) {
    const p = count / samples;
    entropy -= p * Math.log2(p);
    dominant = Math.max(dominant, count);
  }

  let edges = 0;
  let checked = 0;
  for (let gy = 0; gy < rows - 1; gy += 1) {
    for (let gx = 0; gx < cols - 1; gx += 1) {
      const i = gy * cols + gx;
      const dx = Math.abs(luminance[i] - luminance[i + 1]);
      const dy = Math.abs(luminance[i] - luminance[i + cols]);
      if (Math.max(dx, dy) > 12) edges += 1;
      checked += 1;
    }
  }

  return {
    colorBuckets: bucketCounts.size,
    colorEntropyBits: round(entropy, 2),
    edgeDensity: round(edges / checked, 3),
    luminance: {
      mean: round(mean, 1),
      p5: round(p5, 1),
      p95: round(p95, 1),
      contrast: round(p95 - p5, 1),
    },
    dominantColorShare: round(dominant / samples, 3),
    nonBackgroundShare: round(1 - dominant / samples, 3),
  };
}

// Playwright's default headless is chromium_headless_shell, which ships no GPU
// backend and silently falls back to SwiftShader (CPU). Every frame-time and FPS
// number measured that way is software-rendered fiction. channel:'chromium' runs
// the full Chromium build in new headless mode against the real GPU.
async function launchBrowser() {
  try {
    return await chromium.launch({ channel: 'chromium' });
  } catch {
    console.error(
      'warning: channel:"chromium" is unavailable, falling back to the bundled headless shell.\n' +
        '  Rendering will be software (SwiftShader) and any FPS/frame-time evidence is invalid.\n' +
        '  Fix with: npx playwright install chromium',
    );
    return chromium.launch();
  }
}

// Records which GPU actually rasterized the run, so a software fallback can never
// masquerade as performance evidence again. Reuses the game's own context when it
// is WebGL rather than allocating a second one.
async function readGpuInfo(page) {
  const info = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return null;
    let gl = null;
    try {
      gl = canvas.getContext('webgl2') ?? canvas.getContext('webgl');
    } catch {
      gl = null;
    }
    if (!gl) return null;
    const debug = gl.getExtension('WEBGL_debug_renderer_info');
    return {
      renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
      vendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR),
    };
  });

  if (!info?.renderer) {
    return { renderer: null, vendor: null, softwareRendered: null };
  }

  return {
    ...info,
    softwareRendered: /swiftshader|llvmpipe|software|basic render/i.test(info.renderer),
  };
}

function checkRenderBudget(renderer, mode) {
  if (!renderer) return null;
  const budget = RENDER_BUDGETS[mode];
  const rows = Object.entries(budget).map(([metric, limit]) => {
    const actual = renderer[metric];
    return {
      metric,
      actual: typeof actual === 'number' ? actual : null,
      limit,
      ok: typeof actual === 'number' ? actual <= limit : null,
    };
  });
  return {
    tier: mode,
    note: 'starting-point budget; adjust per game and document overrides',
    rows,
    withinBudget: rows.every((row) => row.ok !== false),
  };
}

async function sampleCanvas(page, mode) {
  const locator = page.locator('canvas').first();
  const rect = await locator.boundingBox();
  if (!rect || rect.width < 32 || rect.height < 32) {
    return { ok: false, reason: 'canvas-too-small', rect };
  }

  const buffer = await locator.screenshot();
  const png = PNG.sync.read(buffer);
  let min = 255;
  let max = 0;
  let alphaPixels = 0;
  const colors = new Set();
  const stride = Math.max(1, Math.floor((png.width * png.height) / 4096));

  for (let pixel = 0; pixel < png.width * png.height; pixel += stride) {
    const offset = pixel * 4;
    const r = png.data[offset];
    const g = png.data[offset + 1];
    const b = png.data[offset + 2];
    const a = png.data[offset + 3];
    min = Math.min(min, r, g, b);
    max = Math.max(max, r, g, b);
    if (a > 0) alphaPixels += 1;
    colors.add(`${r >> 4},${g >> 4},${b >> 4},${a >> 6}`);
  }

  const variance = max - min;
  const diagnostics = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    return {
      drawingBuffer: canvas
        ? { width: canvas.width, height: canvas.height }
        : null,
      game: window.__THREE_GAME_DIAGNOSTICS__ ?? null,
    };
  });

  const ok = alphaPixels > 256 && (variance > 8 || colors.size > 3);
  return {
    ok,
    reason: ok ? 'nonblank' : 'low-variance',
    rect,
    drawingBuffer: diagnostics.drawingBuffer,
    alphaPixels,
    variance,
    colorBuckets: colors.size,
    metrics: computePixelMetrics(png),
    renderBudget: checkRenderBudget(diagnostics.game?.renderer ?? null, mode),
    diagnostics: diagnostics.game,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  await mkdir(args.out, { recursive: true });

  const browser = await launchBrowser();
  const context = await browser.newContext(args.mobile
    ? { ...devices['iPhone 13'], userAgent: undefined }
    : { viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];

  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await page.goto(args.url, { waitUntil: 'networkidle' });
  await page.waitForSelector('canvas', { state: 'visible', timeout: 10_000 });

  if (args.state || args.seed !== undefined) {
    const applied = await page.evaluate(({ seed, state }) => {
      const hooks = window.__THREE_GAME_TEST_HOOKS__;
      if (!hooks) return false;
      if (typeof seed === 'number') hooks.seed?.(seed);
      if (state) hooks.setState?.(state);
      return true;
    }, { seed: args.seed, state: args.state });
    if (!applied) {
      console.error(
        'warning: --state/--seed requested but __THREE_GAME_TEST_HOOKS__ is not defined; capturing the current state instead',
      );
    }
  }

  await page.waitForTimeout(args.wait);

  const mode = args.mobile ? 'mobile' : 'desktop';
  const baseName = args.state ? `${mode}-${args.state}` : mode;
  const gpu = await readGpuInfo(page);
  const result = await sampleCanvas(page, mode);
  const screenshotPath = path.join(args.out, `${baseName}.png`);
  await page.screenshot({ path: screenshotPath, fullPage: true });

  if (gpu.softwareRendered) {
    console.error(
      `warning: this run rasterized on ${gpu.renderer} (software). Pixel and budget ` +
        'checks remain valid; any FPS or frame-time reading from it does not.',
    );
  }

  const report = {
    url: args.url,
    mode,
    state: args.state,
    seed: args.seed ?? null,
    screenshotPath,
    gpu,
    result,
    consoleErrors,
    pageErrors,
  };

  await writeFile(path.join(args.out, `${baseName}.json`), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();

  console.log(JSON.stringify(report, null, 2));

  if (!result.ok || consoleErrors.length > 0 || pageErrors.length > 0) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
