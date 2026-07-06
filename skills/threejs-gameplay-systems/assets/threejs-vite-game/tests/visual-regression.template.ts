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

  const hasHooks = await page.evaluate(() => Boolean(window.__THREE_GAME_TEST_HOOKS__));
  if (!hasHooks) {
    throw new Error(
      '__THREE_GAME_TEST_HOOKS__ is not defined. Implement the deterministic test hooks ' +
        '(seed/setState/setPausedForScreenshot/setReducedMotion/hideDebugUi) before ' +
        'enabling visual baselines — see threejs-qa-release references/visual-test-harness.md.',
    );
  }

  await page.evaluate((name) => {
    const hooks = window.__THREE_GAME_TEST_HOOKS__;
    hooks?.seed(12345);
    hooks?.setReducedMotion(true);
    hooks?.hideDebugUi(true);
    hooks?.setState(name);
    hooks?.setPausedForScreenshot(true);
  }, stateName);

  await page.waitForTimeout(150);
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
