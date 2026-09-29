#!/usr/bin/env node
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { existsSync, realpathSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

// Starting-point render budgets (see threejs-aaa-graphics-builder
// references/technical-art.md). Over-budget rows are reported, not fatal.
const RENDER_BUDGETS = {
  desktop: { calls: 300, triangles: 750_000, geometries: 300, textures: 60 },
  mobile: { calls: 150, triangles: 300_000, geometries: 200, textures: 40 },
};

// Browser errors kept per report: unique messages, truncated. Totals are always counted.
const MAX_ERRORS = 20;
const MAX_ERROR_LENGTH = 500;

const USAGE =
  'Usage: inspect-threejs-canvas.mjs [--url URL] [--out DIR] [--mobile] [--wait MS] [--state NAME] [--seed N] [--run-id ID] [--json]\n' +
  '       inspect-threejs-canvas.mjs --manifest artifacts/evidence.json [--url URL] [--seed N] [--wait MS] [--json]\n' +
  '  --manifest captures every declared viewport/state in one browser, writing each report to its declared path.\n' +
  '  Prints one summary line per capture; full reports are written to disk. --json prints the full reports instead.\n' +
  '  --wait defaults to 0ms for named states (already frozen) and 750ms for current-view captures.\n' +
  '  --state requires setState(NAME) to return or resolve {state: NAME}; unknown states must throw.\n' +
  '  Named captures also require setPausedForScreenshot: stop simulation immediately, keep rendering.\n' +
  '  --seed requires a seed(N) hook; both hooks are awaited before capture.\n' +
  '  Preparation, including --wait, hooks, fonts and render frames, has a 10000ms deadline.\n' +
  '  State names and run IDs use 1-128 letters, digits, dots, underscores or hyphens, starting with a letter or digit.';

function validateIdentifier(value, flag) {
  if (typeof value !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(value)) {
    throw new Error(`${flag} must be a safe 1-128 character identifier starting with a letter or digit`);
  }
}

export function parseArgs(argv) {
  const args = {
    url: 'http://127.0.0.1:5188',
    out: 'artifacts/canvas-inspection',
    mobile: false,
    wait: null,
    state: null,
    seed: undefined,
    runId: null,
    manifest: null,
    json: false,
    help: false,
  };
  const singleCaptureFlags = [];

  for (let i = 0; i < argv.length; i += 1) {
    const value = argv[i];
    const takeValue = () => {
      const next = argv[++i];
      if (typeof next !== 'string' || !next.trim() || next.startsWith('--')) {
        throw new Error(`Missing value for ${value}`);
      }
      return next;
    };
    if (value === '--url') args.url = takeValue();
    else if (value === '--out') { args.out = takeValue(); singleCaptureFlags.push(value); }
    else if (value === '--mobile') { args.mobile = true; singleCaptureFlags.push(value); }
    else if (value === '--wait') args.wait = Number(takeValue());
    else if (value === '--state') { args.state = takeValue(); singleCaptureFlags.push(value); }
    else if (value === '--seed') args.seed = Number(takeValue());
    else if (value === '--run-id') { args.runId = takeValue(); singleCaptureFlags.push(value); }
    else if (value === '--manifest') args.manifest = takeValue();
    else if (value === '--json') args.json = true;
    else if (value === '-h' || value === '--help') args.help = true;
    else {
      throw new Error(`Unknown argument: ${value}`);
    }
  }

  if (args.state !== null) validateIdentifier(args.state, '--state');
  if (args.runId !== null) validateIdentifier(args.runId, '--run-id');
  if (args.seed !== undefined && !Number.isSafeInteger(args.seed)) {
    throw new Error('--seed must be a safe integer');
  }
  if (args.wait !== null && (!Number.isFinite(args.wait) || args.wait < 0 || args.wait > 2_147_483_647)) {
    throw new Error('--wait must be finite non-negative milliseconds within the timer range');
  }
  if (!['http:', 'https:'].includes(new URL(args.url).protocol)) {
    throw new Error('--url must use http or https');
  }
  if (args.manifest !== null && singleCaptureFlags.length > 0) {
    throw new Error(`--manifest declares each capture; remove ${singleCaptureFlags.join(', ')}`);
  }

  return args;
}

// Named states are frozen before settling, so they need no extra wait by default.
export function settleWait(wait, state) {
  return wait ?? (state ? 0 : 750);
}

export function readManifestCaptures(manifest) {
  if (!manifest || typeof manifest !== 'object' || Array.isArray(manifest)) {
    throw new Error('manifest must be a JSON object');
  }
  if (typeof manifest.runId !== 'string' || !manifest.runId.trim()) throw new Error('manifest requires a runId');
  validateIdentifier(manifest.runId, 'manifest runId');
  if (!Array.isArray(manifest.captures) || manifest.captures.length === 0) {
    throw new Error('manifest requires a nonempty captures list');
  }
  return manifest.captures.map((capture, index) => {
    if (!capture || typeof capture !== 'object') throw new Error(`capture ${index} must be an object`);
    const { mode, state, report } = capture;
    if (mode !== 'desktop' && mode !== 'mobile') throw new Error(`capture ${index} mode must be desktop or mobile`);
    if (!('state' in capture)) throw new Error(`capture ${index} requires state (a name or null)`);
    if (state !== null) validateIdentifier(state, `capture ${index} state`);
    if (typeof report !== 'string' || !report.endsWith('.json')) {
      throw new Error(`capture ${index} report must be a .json path`);
    }
    return { mobile: mode === 'mobile', state, runId: manifest.runId, reportPath: report,
      screenshotPath: report.replace(/\.json$/, '.png') };
  });
}

export async function loadDependency(name, cwd = process.cwd()) {
  const project = path.resolve(cwd);
  const resolvers = [createRequire(import.meta.url), createRequire(path.join(project, 'package.json'))];
  let missing;
  for (const require of resolvers) {
    let resolved;
    try {
      resolved = require.resolve(name);
    } catch (error) {
      if (error.code !== 'MODULE_NOT_FOUND') throw error;
      missing = error;
      continue;
    }
    // Import outside the catch: a broken installed package is not a missing dependency.
    const dependency = await import(pathToFileURL(resolved).href);
    // createRequire can select a CommonJS entrypoint with only a default export.
    return { ...dependency.default, ...dependency };
  }
  throw new Error(
    `Missing inspector dependency "${name}". Install @playwright/test and pngjs in the game project ` +
      `(${project}), then run the inspector from that directory.`,
    { cause: missing },
  );
}

async function runPreparation(page, { state = null, seed, timeoutMs = 10_000, wait = 0 }, capture) {
  if (state !== null) validateIdentifier(state, '--state');
  if (seed !== undefined && !Number.isSafeInteger(seed)) throw new Error('--seed must be a safe integer');
  if (!Number.isFinite(timeoutMs) || timeoutMs <= 0 || timeoutMs > 2_147_483_647) {
    throw new Error('Preparation timeout must be positive milliseconds within the timer range');
  }
  if (!Number.isFinite(wait) || wait < 0 || wait > 2_147_483_647) {
    throw new Error('--wait must be finite non-negative milliseconds within the timer range');
  }
  if (!capture && state === null && seed === undefined) return { requestedState: null, appliedState: null };

  const message = `${capture ? 'Capture preparation' : 'Test hooks'} did not finish within ${timeoutMs}ms`;
  const deadline = Date.now() + timeoutMs;
  let hostTimer;
  try {
    // A host-side deadline also covers a stalled evaluate call or blocked browser event loop.
    return await Promise.race([
      new Promise((_, reject) => {
        hostTimer = setTimeout(() => reject(new Error(message)), timeoutMs);
      }),
      page.evaluate(async ({ state, seed, capture, wait, deadline, message }) => {
        const hooks = window.__THREE_GAME_TEST_HOOKS__;
        const namedCapture = capture && state !== null;
        if ((state !== null || seed !== undefined) && !hooks) {
          throw new Error('--state/--seed requires window.__THREE_GAME_TEST_HOOKS__');
        }
        if (state !== null && typeof hooks.setState !== 'function') {
          throw new Error('--state requires a setState function');
        }
        if (seed !== undefined && typeof hooks.seed !== 'function') {
          throw new Error('--seed requires a seed function');
        }
        if (namedCapture && typeof hooks.setPausedForScreenshot !== 'function') {
          throw new Error('--state capture requires a setPausedForScreenshot function that stops simulation immediately and keeps rendering');
        }

        let expired = false;
        let timer;
        let settleTimer;
        let frameId;
        const checkDeadline = () => {
          if (expired || Date.now() >= deadline) throw new Error(message);
        };
        const step = async (operation) => {
          checkDeadline();
          const result = await operation();
          checkDeadline();
          return result;
        };
        try {
          return await Promise.race([
            new Promise((_, reject) => {
              timer = setTimeout(() => {
                expired = true;
                reject(new Error(message));
              }, Math.max(0, deadline - Date.now()));
            }),
            (async () => {
              if (namedCapture) await step(() => hooks.setPausedForScreenshot(false));
              if (seed !== undefined) await step(() => hooks.seed(seed));
              if (state !== null) {
                const acknowledgement = await step(() => hooks.setState(state));
                if (!acknowledgement || typeof acknowledgement !== 'object' ||
                    Array.isArray(acknowledgement) || acknowledgement.state !== state) {
                  throw new Error(`setState(${JSON.stringify(state)}) must acknowledge {state: ${JSON.stringify(state)}}`);
                }
                // Freeze in this evaluation immediately after setup, before any settling or render wait.
                if (namedCapture) await step(() => hooks.setPausedForScreenshot(true));
              }
              if (capture) {
                if (namedCapture && typeof hooks.setReducedMotion === 'function') {
                  await step(() => hooks.setReducedMotion(true));
                }
                if (namedCapture && typeof hooks.hideDebugUi === 'function') {
                  await step(() => hooks.hideDebugUi(true));
                }
                if (wait > 0) await step(() => new Promise((resolve) => { settleTimer = setTimeout(resolve, wait); }));
                if (document.fonts) await step(() => document.fonts.ready);
                await step(() => new Promise((resolve) => {
                  frameId = requestAnimationFrame(() => {
                    if (!expired) frameId = requestAnimationFrame(resolve);
                  });
                }));
              }
              return { requestedState: state, appliedState: state };
            })(),
          ]);
        } finally {
          expired = true;
          clearTimeout(timer);
          clearTimeout(settleTimer);
          if (frameId !== undefined) cancelAnimationFrame(frameId);
        }
      }, { state, seed, capture, wait, deadline, message }),
    ]);
  } finally {
    clearTimeout(hostTimer);
  }
}

export async function applyTestHooks(page, args = {}) {
  return runPreparation(page, args, false);
}

export async function prepareCapture(page, args = {}) {
  return runPreparation(page, args, true);
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
  const { chromium } = await loadDependency('@playwright/test');
  try {
    return await chromium.launch({ channel: 'chromium' });
  } catch {
    console.error(
      'warning: channel:"chromium" is unavailable, falling back to the bundled headless shell.\n' +
        '  Rendering will be software (SwiftShader) and any FPS/frame-time evidence is invalid.\n' +
        '  Fix with: npx playwright install --no-shell chromium',
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

function cropImage(png, rect) {
  const clamp = (value, max) => Math.min(max, Math.max(0, Math.round(value)));
  const x0 = clamp(rect.x, png.width);
  const y0 = clamp(rect.y, png.height);
  const width = clamp(rect.x + rect.width, png.width) - x0;
  const height = clamp(rect.y + rect.height, png.height) - y0;
  const data = Buffer.alloc(Math.max(0, width * height * 4));
  for (let y = 0; y < height; y += 1) {
    const from = ((y0 + y) * png.width + x0) * 4;
    png.data.copy(data, y * width * 4, from, from + width * 4);
  }
  return { width, height, data };
}

// One CSS-scale full-page screenshot serves as both the review image and the
// canvas sample: a device-pixel mobile capture costs several times the image
// tokens and screenshot time for no extra evidence at this sampling density.
async function captureCanvas(page, mode, screenshotPath) {
  const { PNG } = await loadDependency('pngjs');
  const layout = await page.evaluate(() => {
    const canvas = document.querySelector('canvas');
    const box = canvas?.getBoundingClientRect();
    return {
      rect: box ? { x: box.left + window.scrollX, y: box.top + window.scrollY, width: box.width, height: box.height } : null,
      drawingBuffer: canvas ? { width: canvas.width, height: canvas.height } : null,
      game: window.__THREE_GAME_DIAGNOSTICS__ ?? null,
    };
  });
  await mkdir(path.dirname(screenshotPath), { recursive: true });
  const buffer = await page.screenshot({ path: screenshotPath, fullPage: true, scale: 'css' });
  const { rect } = layout;
  if (!rect || rect.width < 32 || rect.height < 32) {
    return { ok: false, reason: 'canvas-too-small', rect };
  }

  const png = cropImage(PNG.sync.read(buffer), rect);
  if (png.width < 32 || png.height < 32) return { ok: false, reason: 'canvas-too-small', rect };
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
  const ok = alphaPixels > 256 && (variance > 8 || colors.size > 3);
  return {
    ok,
    reason: ok ? 'nonblank' : 'low-variance',
    rect,
    drawingBuffer: layout.drawingBuffer,
    alphaPixels,
    variance,
    colorBuckets: colors.size,
    metrics: computePixelMetrics(png),
    renderBudget: checkRenderBudget(layout.game?.renderer ?? null, mode),
    diagnostics: layout.game,
  };
}

function recordError(list, report, countField, text) {
  report[countField] += 1;
  const message = text.length > MAX_ERROR_LENGTH ? `${text.slice(0, MAX_ERROR_LENGTH)}…` : text;
  if (list.length < MAX_ERRORS && !list.includes(message)) list.push(message);
}

export async function inspectPage(page, args) {
  const consoleErrors = [];
  const pageErrors = [];
  const mode = args.mobile ? 'mobile' : 'desktop';
  const baseName = args.state ? `${mode}-${args.state}` : mode;
  const report = {
    url: args.url,
    mode,
    state: null,
    requestedState: args.state ?? null,
    appliedState: null,
    runId: args.runId ?? null,
    seed: args.seed ?? null,
    screenshotPath: null,
    gpu: null,
    result: null,
    consoleErrors,
    pageErrors,
    consoleErrorCount: 0,
    pageErrorCount: 0,
  };

  page.on('console', (message) => {
    if (message.type() === 'error') recordError(consoleErrors, report, 'consoleErrorCount', message.text());
  });
  page.on('pageerror', (error) => recordError(pageErrors, report, 'pageErrorCount', error.message));

  try {
    // 'load' instead of 'networkidle': named states await their own assets, and
    // networkidle adds a fixed idle window to every capture.
    await page.goto(args.url, { waitUntil: 'load' });
    await page.waitForSelector('canvas', { state: 'visible', timeout: 10_000 });
    const applied = await prepareCapture(page, { ...args, wait: settleWait(args.wait, args.state) });
    report.state = applied.appliedState;
    report.appliedState = applied.appliedState;
    report.gpu = await readGpuInfo(page);
    const screenshotPath = args.screenshotPath ?? path.join(args.out, `${baseName}.png`);
    report.result = await captureCanvas(page, mode, screenshotPath);
    report.screenshotPath = screenshotPath;

    if (report.gpu.softwareRendered) {
      console.error(
        `warning: this run rasterized on ${report.gpu.renderer} (software). Pixel and budget ` +
          'checks remain valid; any FPS or frame-time reading from it does not.',
      );
    }
  } catch (error) {
    report.result = { ok: false, reason: 'capture-failed', error: error instanceof Error ? error.message : String(error) };
  }
  return report;
}

function contextOptions(devices, mobile) {
  return mobile
    ? { ...devices['iPhone 13'], userAgent: undefined }
    : { viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 };
}

function reportPassed(report) {
  return report.result?.ok === true && report.consoleErrorCount === 0 && report.pageErrorCount === 0;
}

// One line per capture keeps agent-visible output small; the full report is on disk.
export function summarize(report, reportPath) {
  const result = report.result ?? {};
  const parts = [reportPassed(report) ? 'PASS' : 'FAIL', report.mode, report.requestedState ?? 'current-view'];
  if (report.runId) parts.push(`run=${report.runId}`);
  if (!result.ok) {
    parts.push(`reason=${result.reason}`);
    if (result.error) parts.push(`error=${JSON.stringify(result.error.slice(0, 300))}`);
  }
  if (report.gpu?.renderer) parts.push(report.gpu.softwareRendered ? 'gpu=SOFTWARE(fps-invalid)' : 'gpu=hardware');
  const metrics = result.metrics;
  if (metrics) {
    parts.push(`entropy=${metrics.colorEntropyBits} edges=${metrics.edgeDensity} ` +
      `contrast=${metrics.luminance.contrast} dominant=${metrics.dominantColorShare}`);
  }
  if (result.renderBudget) {
    const over = result.renderBudget.rows.filter((row) => row.ok === false)
      .map((row) => `${row.metric}:${row.actual}>${row.limit}`);
    parts.push(over.length ? `over-budget=${over.join(',')}` : 'budget=ok');
  }
  for (const [field, count] of [['consoleErrors', 'consoleErrorCount'], ['pageErrors', 'pageErrorCount']]) {
    if (report[count] > 0) {
      parts.push(`${field}=${report[count]} first=${JSON.stringify(report[field][0].slice(0, 200))}`);
    }
  }
  parts.push(`report=${reportPath}`);
  if (report.screenshotPath) parts.push(`png=${report.screenshotPath}`);
  return parts.join(' ');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log(USAGE);
    return;
  }
  const mode = args.mobile ? 'mobile' : 'desktop';
  const captures = args.manifest
    ? readManifestCaptures(JSON.parse(await readFile(args.manifest, 'utf8')))
    : [{ mobile: args.mobile, state: args.state, runId: args.runId,
      reportPath: path.join(args.out, `${args.state ? `${mode}-${args.state}` : mode}.json`) }];

  const { devices } = await loadDependency('@playwright/test');
  const browser = await launchBrowser();
  const reports = [];
  try {
    for (const capture of captures) {
      const context = await browser.newContext(contextOptions(devices, capture.mobile));
      let report;
      try {
        report = await inspectPage(await context.newPage(), { ...args, ...capture });
      } finally {
        await context.close();
      }
      await mkdir(path.dirname(capture.reportPath), { recursive: true });
      await writeFile(capture.reportPath, `${JSON.stringify(report, null, 2)}\n`);
      reports.push(report);
      if (!args.json) console.log(summarize(report, capture.reportPath));
      if (!reportPassed(report)) process.exitCode = 1;
    }
  } finally {
    await browser.close();
  }
  if (args.json) console.log(JSON.stringify(args.manifest ? reports : reports[0], null, 2));
}

if (process.argv[1] && existsSync(process.argv[1]) &&
    import.meta.url === pathToFileURL(realpathSync(process.argv[1])).href) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
