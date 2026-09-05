import assert from 'node:assert/strict';
import { copyFile, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { runInNewContext } from 'node:vm';
import test from 'node:test';
import {
  applyTestHooks,
  inspectPage,
  parseArgs,
  prepareCapture,
} from '../../skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs';

const inspectorUrl = new URL('../../skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs', import.meta.url);
const scaffoldInspectorUrl = new URL('../../skills/threejs-gameplay-systems/assets/threejs-vite-game/scripts/inspect-threejs-canvas.mjs', import.meta.url);

// Evaluate the actual browser callback in an isolated window, with browser-like
// serialization on return. Tests need neither Playwright nor a running browser.
function mockPage(hooks, events = [], fontsReady = Promise.resolve(), browserOverrides = {}) {
  return {
    on() {},
    async goto() { events.push('navigate'); },
    async waitForSelector() { events.push('canvas-visible'); },
    async waitForTimeout() { assert.fail('capture preparation must not yield back to the host between setup and freezing'); },
    async screenshot() { events.push('screenshot'); },
    async evaluate(callback, args) {
      const value = await runInNewContext(`(${callback.toString()})(args)`, {
        args,
        window: { __THREE_GAME_TEST_HOOKS__: hooks },
        document: { fonts: { ready: fontsReady } },
        requestAnimationFrame: (fn) => setImmediate(() => { events.push('frame'); fn(0); }),
        cancelAnimationFrame: clearImmediate,
        setTimeout,
        clearTimeout,
        ...browserOverrides,
      });
      return structuredClone(value);
    },
  };
}

async function isolatedInspector(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'threejs-inspector-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const installed = path.join(root, 'installed skill');
  const game = path.join(root, 'game project');
  await mkdir(installed);
  await mkdir(game);
  const script = path.join(installed, 'inspect.mjs');
  await copyFile(inspectorUrl, script);
  return { root, installed, game, script, inspector: await import(pathToFileURL(script).href) };
}

async function fixturePackage(root, name, source) {
  const directory = path.join(root, 'node_modules', name);
  await mkdir(directory, { recursive: true });
  await writeFile(path.join(directory, 'package.json'), JSON.stringify({ name, version: '1.0.0', main: 'index.cjs' }));
  await writeFile(path.join(directory, 'index.cjs'), source);
}

test('imports without executing the CLI or loading browser dependencies', () => {
  const result = spawnSync(process.execPath, ['--input-type=module', '-e',
    `await import(${JSON.stringify(inspectorUrl.href)}); console.log('imported');`],
  { encoding: 'utf8', timeout: 5000 });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, 'imported\n');
  assert.equal(result.stderr, '');
});

test('CLI help works without browser dependencies', () => {
  const result = spawnSync(process.execPath, [fileURLToPath(inspectorUrl), '--help'],
    { encoding: 'utf8', timeout: 5000 });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /--run-id ID/);
  assert.match(result.stdout, /unknown states must throw/);
  assert.match(result.stdout, /setPausedForScreenshot/);
});

test('CLI help preserves the realpath entrypoint when invoked through a symlink', async (t) => {
  const { root, script, game } = await isolatedInspector(t);
  const linked = path.join(root, 'linked inspector.mjs');
  await symlink(script, linked);
  const result = spawnSync(process.execPath, [linked, '--help'], { cwd: game, encoding: 'utf8', timeout: 5000 });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Usage: inspect-threejs-canvas/);
});

test('installed inspector resolves both dependencies from the game cwd fallback', async (t) => {
  const { game, inspector } = await isolatedInspector(t);
  await writeFile(path.join(game, 'package.json'), JSON.stringify({ name: 'fixture-game', private: true }));
  for (const name of ['@playwright/test', 'pngjs']) {
    await fixturePackage(game, name, `exports.origin = 'game'; exports.name = ${JSON.stringify(name)};`);
    const dependency = await inspector.loadDependency(name, game);
    assert.equal(dependency.origin, 'game');
    assert.equal(dependency.name, name);
  }
});

test('dependency lookup keeps the inspector-local package when available', async (t) => {
  const { installed, game, inspector } = await isolatedInspector(t);
  await fixturePackage(installed, 'pngjs', "exports.origin = 'installed';");
  await fixturePackage(game, 'pngjs', "exports.origin = 'game';");
  assert.equal((await inspector.loadDependency('pngjs', game)).origin, 'installed');
});

test('dependency fallback exposes dynamically assigned CommonJS exports', async (t) => {
  const { game, inspector } = await isolatedInspector(t);
  await fixturePackage(game, '@playwright/test', `
    const api = function test() {};
    Object.assign(api, { chromium: { launch() {} }, devices: { 'iPhone 13': { viewport: { width: 390 } } } });
    module.exports = api;
  `);
  const dependency = await inspector.loadDependency('@playwright/test', game);
  assert.equal(typeof dependency.chromium.launch, 'function');
  assert.equal(dependency.devices['iPhone 13'].viewport.width, 390);
});

test('missing dependencies name the package, project directory and install requirements', async (t) => {
  const { game, inspector } = await isolatedInspector(t);
  await assert.rejects(inspector.loadDependency('@threejs-inspector-fixture/missing', game), (error) => {
    assert.match(error.message, /Missing inspector dependency "@threejs-inspector-fixture\/missing"/);
    assert.match(error.message, /Install @playwright\/test and pngjs/);
    assert.ok(error.message.includes(game));
    return true;
  });
});

test('installed dependency errors are preserved instead of reported as absent packages', async (t) => {
  const { installed, game, inspector } = await isolatedInspector(t);
  await fixturePackage(installed, 'pngjs', "require('@threejs-inspector-fixture/missing-transitive');");
  await fixturePackage(game, 'pngjs', "exports.origin = 'game';");
  await assert.rejects(inspector.loadDependency('pngjs', game), (error) => {
    assert.equal(error.code, 'MODULE_NOT_FOUND');
    assert.match(error.message, /missing-transitive/);
    assert.doesNotMatch(error.message, /Missing inspector dependency/);
    return true;
  });
});

test('both packaged inspector copies are identical', async () => {
  assert.equal(await readFile(inspectorUrl, 'utf8'), await readFile(scaffoldInspectorUrl, 'utf8'));
});

test('parses run IDs while preserving legacy null defaults', () => {
  const legacy = parseArgs([]);
  assert.equal(legacy.runId, null);
  assert.equal(legacy.state, null);
  assert.equal(legacy.seed, undefined);
  const args = parseArgs(['--state', 'boss.phase-2', '--seed', '0', '--run-id', 'run_2026-09', '--mobile', '--wait', '0']);
  assert.equal(args.state, 'boss.phase-2');
  assert.equal(args.seed, 0);
  assert.equal(args.runId, 'run_2026-09');
  assert.equal(args.mobile, true);
  assert.equal(args.wait, 0);
  assert.equal(parseArgs(['--out', '/tmp/capture evidence']).out, '/tmp/capture evidence');
});

test('rejects missing argument values and unsafe state/run identifiers', () => {
  for (const option of ['--state', '--seed', '--run-id', '--wait', '--url', '--out']) {
    assert.throws(() => parseArgs([option]), /Missing value/);
    assert.throws(() => parseArgs([option, '--mobile']), /Missing value/);
    assert.throws(() => parseArgs([option, '']), /Missing value/);
  }
  for (const option of ['--state', '--run-id']) {
    for (const value of ['../boss', '/tmp/boss', '..', 'a/b', 'a\\b', 'boss phase', 'boss\nstate', 'x'.repeat(129)]) {
      assert.throws(() => parseArgs([option, value]), /safe.*identifier/);
    }
  }
  assert.throws(() => parseArgs(['--unknown']), /Unknown argument/);
});

test('rejects invalid seeds, waits and URLs', () => {
  for (const value of ['NaN', 'Infinity', '1.5', '9007199254740992']) {
    assert.throws(() => parseArgs(['--seed', value]), /safe integer/);
  }
  for (const value of ['NaN', 'Infinity', '-1', '2147483648']) {
    assert.throws(() => parseArgs(['--wait', value]), /milliseconds/);
  }
  assert.throws(() => parseArgs(['--url', 'file:///tmp/game.html']), /http or https/);
});

test('legacy capture without explicit state or seed does not require hooks', async () => {
  const page = { evaluate() { assert.fail('hooks must not be consulted'); } };
  assert.deepEqual(await applyTestHooks(page), { requestedState: null, appliedState: null });
});

test('synchronous acknowledgement confirms the requested state', async () => {
  const page = mockPage({ setState(name) { return { state: name }; } });
  assert.deepEqual(await applyTestHooks(page, { state: 'boss' }), { requestedState: 'boss', appliedState: 'boss' });
});

test('awaits seed and asynchronous state acknowledgement in order, preserving hook receiver', async () => {
  const events = [];
  const hooks = {
    seeded: false,
    async seed(value) {
      assert.equal(value, 0);
      events.push('seed-start');
      await new Promise((resolve) => setImmediate(resolve));
      this.seeded = true;
      events.push('seed-ready');
    },
    async setState(name) {
      assert.equal(this.seeded, true);
      events.push('state-start');
      await new Promise((resolve) => setImmediate(resolve));
      events.push('state-ready');
      return { state: name };
    },
  };
  const applied = await applyTestHooks(mockPage(hooks), { state: 'late-wave', seed: 0 });
  assert.deepEqual(events, ['seed-start', 'seed-ready', 'state-start', 'state-ready']);
  assert.deepEqual(applied, { requestedState: 'late-wave', appliedState: 'late-wave' });
});

test('explicit state and seed require the hooks object', async () => {
  await assert.rejects(applyTestHooks(mockPage(undefined), { state: 'boss' }), /requires window.__THREE_GAME_TEST_HOOKS__/);
  await assert.rejects(applyTestHooks(mockPage(undefined), { seed: 1 }), /requires window.__THREE_GAME_TEST_HOOKS__/);
});

test('requires hook functions before any setup mutation', async () => {
  for (const setState of [undefined, null, true, 'boss', {}]) {
    await assert.rejects(applyTestHooks(mockPage({ setState }), { state: 'boss' }), /requires a setState function/);
  }
  for (const seed of [undefined, null, 1, {}]) {
    await assert.rejects(applyTestHooks(mockPage({ seed }), { seed: 1 }), /requires a seed function/);
  }
  let seeded = false;
  await assert.rejects(applyTestHooks(mockPage({ seed() { seeded = true; } }), { seed: 1, state: 'boss' }), /setState function/);
  assert.equal(seeded, false);
});

test('rejects no-op, missing, malformed and mismatched acknowledgements', async () => {
  for (const acknowledgement of [undefined, null, false, true, 'boss', {}, [], { state: 'active-play' }, { state: null }]) {
    const page = mockPage({ setState() { return acknowledgement; } });
    await assert.rejects(applyTestHooks(page, { state: 'boss' }), /must acknowledge/);
  }
  await assert.rejects(applyTestHooks(mockPage({ async setState() {} }), { state: 'boss' }), /must acknowledge/);
});

test('unknown states and rejected asynchronous setup propagate as failures', async () => {
  await assert.rejects(applyTestHooks(mockPage({ setState(name) { throw new Error(`Unknown test state: ${name}`); } }),
    { state: 'unknown' }), /Unknown test state: unknown/);
  await assert.rejects(applyTestHooks(mockPage({ async setState() { throw new Error('Model failed to load'); } }),
    { state: 'boss' }), /Model failed to load/);
});

test('seed-only requests await seeding without claiming a verified state', async () => {
  let seeded = false;
  const page = mockPage({ async seed() { await Promise.resolve(); seeded = true; } });
  assert.deepEqual(await applyTestHooks(page, { seed: 123 }), { requestedState: null, appliedState: null });
  assert.equal(seeded, true);
});

test('a failed seed prevents state setup', async () => {
  let stateCalled = false;
  const page = mockPage({
    async seed() { throw new Error('Seed failed'); },
    setState(name) { stateCalled = true; return { state: name }; },
  });
  await assert.rejects(applyTestHooks(page, { state: 'boss', seed: 123 }), /Seed failed/);
  assert.equal(stateCalled, false);
});

test('non-settling hooks time out rather than allowing an unverified capture', async () => {
  await assert.rejects(applyTestHooks(mockPage({ setState() { return new Promise(() => {}); } }),
    { state: 'boss', timeoutMs: 10 }), /did not finish within 10ms/);
  await assert.rejects(applyTestHooks(mockPage({ seed() { return new Promise(() => {}); } }),
    { seed: 1, timeoutMs: 10 }), /did not finish within 10ms/);
});

test('capture freezes immediately after async setup, before optional hooks and render frames', async () => {
  const events = [];
  let paused = false;
  const hooks = {
    async setState(name) {
      events.push('state-start');
      await new Promise((resolve) => setImmediate(resolve));
      events.push('state-ready');
      return { state: name };
    },
    async setReducedMotion(enabled) { assert.equal(enabled, true); assert.equal(paused, true); events.push('reduce-motion'); },
    async hideDebugUi(hidden) { assert.equal(hidden, true); assert.equal(paused, true); events.push('hide-debug'); },
    async setPausedForScreenshot(value) {
      paused = value;
      events.push(value ? 'pause' : 'unpause');
      await new Promise((resolve) => setImmediate(resolve));
      events.push(value ? 'pause-ready' : 'unpause-ready');
    },
  };
  const applied = await prepareCapture(mockPage(hooks, events), { state: 'boss', wait: 15 });
  assert.deepEqual(applied, { requestedState: 'boss', appliedState: 'boss' });
  assert.deepEqual(events, ['unpause', 'unpause-ready', 'state-start', 'state-ready', 'pause', 'pause-ready', 'reduce-motion', 'hide-debug', 'frame', 'frame']);
});

test('named captures prevent state drift during settling and keep frozen frames rendering', async () => {
  let state = 'initial';
  let paused = false;
  let transitionAttempted = false;
  let frames = 0;
  const hooks = {
    async setState(name) {
      await new Promise((resolve) => setImmediate(resolve));
      state = name;
      setTimeout(() => {
        transitionAttempted = true;
        if (!paused) state = 'complete';
      }, 0);
      return { state: name };
    },
    setPausedForScreenshot(value) { paused = value; },
  };
  const page = mockPage(hooks, [], Promise.resolve(), {
    requestAnimationFrame(fn) {
      return setImmediate(() => {
        assert.equal(paused, true);
        assert.equal(state, 'active-play');
        frames += 1;
        fn(0);
      });
    },
  });
  const applied = await prepareCapture(page, { state: 'active-play', wait: 20 });
  assert.equal(transitionAttempted, true, 'the settling interval must exercise the potential transition');
  assert.equal(applied.appliedState, state);
  assert.equal(frames, 2);
  assert.equal(paused, true, 'state stays frozen for pixel inspection and screenshots');
});

test('named captures require a pause function before mutating seed or state', async () => {
  for (const pause of [undefined, null, false, 'pause', {}]) {
    const hooks = {
      seed() { assert.fail('seed must not run without a pause hook'); },
      setState() { assert.fail('state must not run without a pause hook'); },
      setPausedForScreenshot: pause,
    };
    await assert.rejects(prepareCapture(mockPage(hooks), { state: 'active-play', seed: 1, wait: 0 }), /requires a setPausedForScreenshot function/);
  }
});

test('bot setup does not call pause or optional screenshot hooks', async () => {
  const hooks = {
    setState(name) { return { state: name }; },
    setPausedForScreenshot() { assert.fail('bot setup must remain unpaused'); },
    setReducedMotion() { assert.fail('bot setup must not change animation'); },
    hideDebugUi() { assert.fail('bot setup must not change UI'); },
  };
  assert.deepEqual(await applyTestHooks(mockPage(hooks), { state: 'active-play' }),
    { requestedState: 'active-play', appliedState: 'active-play' });
});

test('all post-setup readiness operations share a bounded preparation deadline', async (t) => {
  for (const stage of ['unpause', 'pause', 'reduced-motion', 'debug-ui', 'fonts', 'first-frame', 'second-frame', 'settle']) {
    await t.test(stage, async () => {
      const never = () => new Promise(() => {});
      const hooks = {
        setState(name) { return { state: name }; },
        setPausedForScreenshot(paused) {
          if (stage === (paused ? 'pause' : 'unpause')) return never();
        },
        setReducedMotion() { if (stage === 'reduced-motion') return never(); },
        hideDebugUi() { if (stage === 'debug-ui') return never(); },
      };
      let frames = 0;
      const page = mockPage(hooks, [], stage === 'fonts' ? never() : Promise.resolve(), {
        requestAnimationFrame(fn) {
          frames += 1;
          if (stage === 'first-frame' || stage === 'second-frame' && frames === 2) return undefined;
          return setImmediate(fn);
        },
      });
      await assert.rejects(prepareCapture(page, { state: 'active-play', wait: stage === 'settle' ? 100 : 0, timeoutMs: 15 }),
        /Capture preparation did not finish within 15ms/);
    });
  }
});

test('fonts and render frames are bounded for captures without a named state too', async () => {
  await assert.rejects(prepareCapture(mockPage(undefined, [], new Promise(() => {})), { timeoutMs: 10 }),
    /Capture preparation did not finish within 10ms/);
});

test('host deadline handles a browser evaluate that never responds', async () => {
  const page = { evaluate() { return new Promise(() => {}); } };
  await assert.rejects(prepareCapture(page, { state: 'active-play', timeoutMs: 10 }), /Capture preparation did not finish within 10ms/);
  await assert.rejects(applyTestHooks(page, { seed: 1, timeoutMs: 10 }), /Test hooks did not finish within 10ms/);
});

test('preparation uses one total deadline instead of restarting it for each hook', async () => {
  const delay = () => new Promise((resolve) => setTimeout(resolve, 30));
  const hooks = {
    async setState(name) { await delay(); return { state: name }; },
    setPausedForScreenshot() {},
    setReducedMotion: delay,
  };
  await assert.rejects(prepareCapture(mockPage(hooks), { state: 'active-play', timeoutMs: 45 }),
    /Capture preparation did not finish within 45ms/);
});

test('a timed-out hook cannot resume later preparation steps', async () => {
  let finishHook;
  let nextStepCalled = false;
  const hooks = {
    setState(name) { return { state: name }; },
    setPausedForScreenshot() {},
    setReducedMotion() { return new Promise((resolve) => { finishHook = resolve; }); },
    hideDebugUi() { nextStepCalled = true; },
  };
  await assert.rejects(prepareCapture(mockPage(hooks), { state: 'active-play', timeoutMs: 15 }), /did not finish within 15ms/);
  finishHook();
  await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(nextStepCalled, false);
});

test('legacy and seed-only capture do not silently enable optional screenshot controls', async () => {
  const events = [];
  const hooks = {
    seed() { events.push('seed'); },
    setReducedMotion() { assert.fail('not a named-state capture'); },
    setPausedForScreenshot() { assert.fail('not a named-state capture'); },
  };
  const applied = await prepareCapture(mockPage(hooks, events), { seed: 1, wait: 0 });
  assert.deepEqual(applied, { requestedState: null, appliedState: null });
  assert.deepEqual(events, ['seed', 'frame', 'frame']);
  assert.deepEqual(await prepareCapture(mockPage(undefined), { wait: 0 }), { requestedState: null, appliedState: null });
});

test('failed state capture reports requested state and run ID without claiming or taking a screenshot', async () => {
  const events = [];
  const args = parseArgs(['--state', 'boss', '--run-id', 'current-run', '--mobile']);
  const report = await inspectPage(mockPage({ setState() {}, setPausedForScreenshot() {} }, events), args);
  assert.equal(report.url, args.url);
  assert.equal(report.mode, 'mobile');
  assert.equal(report.requestedState, 'boss');
  assert.equal(report.appliedState, null);
  assert.equal(report.state, null);
  assert.equal(report.runId, 'current-run');
  assert.equal(report.screenshotPath, null);
  assert.equal(report.seed, null);
  assert.equal(report.gpu, null);
  assert.equal(report.result.ok, false);
  assert.equal(report.result.reason, 'capture-failed');
  assert.match(report.result.error, /must acknowledge/);
  assert.deepEqual(report.consoleErrors, []);
  assert.deepEqual(report.pageErrors, []);
  assert.deepEqual(events, ['navigate', 'canvas-visible']);
});

test('post-setup failure reports no applied state or screenshot', async () => {
  const events = [];
  const hooks = {
    setState(name) { return { state: name }; },
    setPausedForScreenshot() {},
    setReducedMotion() { return new Promise(() => {}); },
  };
  const args = { ...parseArgs(['--state', 'boss', '--run-id', 'current-run']), timeoutMs: 15 };
  const report = await inspectPage(mockPage(hooks, events), args);
  assert.equal(report.requestedState, 'boss');
  assert.equal(report.appliedState, null);
  assert.equal(report.state, null);
  assert.equal(report.screenshotPath, null);
  assert.equal(report.result.ok, false);
  assert.match(report.result.error, /Capture preparation did not finish within 15ms/);
  assert.deepEqual(events, ['navigate', 'canvas-visible']);
});

test('failed seed-only capture retains the legacy null run ID and no state', async () => {
  const report = await inspectPage(mockPage({}), parseArgs(['--seed', '0']));
  assert.equal(report.requestedState, null);
  assert.equal(report.appliedState, null);
  assert.equal(report.state, null);
  assert.equal(report.runId, null);
  assert.equal(report.seed, 0);
  assert.equal(report.result.ok, false);
  assert.equal(report.screenshotPath, null);
});
