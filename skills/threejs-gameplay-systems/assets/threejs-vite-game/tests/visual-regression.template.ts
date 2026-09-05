import { expect, test, type Page } from '@playwright/test';

// Copy this file to tests/visual-regression.spec.ts when the game is stable
// enough for screenshot baselines. First run:
//   npx playwright test tests/visual-regression.spec.ts --update-snapshots
// Then compare:
//   npx playwright test tests/visual-regression.spec.ts
//
// REQUIREMENT: the game must implement window.__THREE_GAME_TEST_HOOKS__
// (see src/game/Game.ts installTestHooks and src/vite-env.d.ts). Without real
// hooks, baselines capture a live animating scene and every rerun diffs.
// prepareDeterministicScreenshot fails loudly if the hooks object is missing.

async function prepareDeterministicScreenshot(page: Page, stateName: string) {
  await page.goto('/');
  await page.waitForFunction(() => (window.__THREE_GAME_DIAGNOSTICS__?.frame ?? 0) > 10);

  const acknowledgement = await page.evaluate(async (name) => {
    const hooks = window.__THREE_GAME_TEST_HOOKS__;
    if (!hooks) throw new Error('__THREE_GAME_TEST_HOOKS__ is required for visual baselines');
    for (const key of ['seed', 'setState', 'setPausedForScreenshot', 'setReducedMotion', 'hideDebugUi'] as const) {
      if (typeof hooks[key] !== 'function') throw new Error(`Visual baselines require the ${key} hook`);
    }
    await hooks.setPausedForScreenshot(false);
    await hooks.seed(12345);
    const applied = await hooks.setState(name);
    if (!applied || applied.state !== name) throw new Error(`setState must acknowledge {state: ${JSON.stringify(name)}}`);
    // Preserve the acknowledged state while optional hooks, fonts and rendering settle.
    await hooks.setPausedForScreenshot(true);
    await hooks.setReducedMotion(true);
    await hooks.hideDebugUi(true);
    await document.fonts.ready;
    const renderFrames = () => new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
    await renderFrames();
    return applied;
  }, stateName);
  expect(acknowledgement.state, 'requested visual state must be applied').toBe(stateName);
}

// State names must match the game's setState implementation. The scaffold
// supports 'active-play' and 'complete'; add baselines for your game's own
// states (fail/retry, menus, boss phases) as you implement them.

test('active play visual baseline', async ({ page }, testInfo) => {
  await prepareDeterministicScreenshot(page, 'active-play');
  await expect(page).toHaveScreenshot(`active-play-${testInfo.project.name}.png`, {
    fullPage: true,
    maxDiffPixelRatio: 0.015,
  });
});

test('complete state visual baseline', async ({ page }, testInfo) => {
  await prepareDeterministicScreenshot(page, 'complete');
  await expect(page).toHaveScreenshot(`complete-${testInfo.project.name}.png`, {
    fullPage: true,
    maxDiffPixelRatio: 0.015,
  });
});
