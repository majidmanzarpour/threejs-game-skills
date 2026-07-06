import { expect, test, type Page } from '@playwright/test';

declare global {
  interface Window {
    __THREE_GAME_TEST_HOOKS__?: {
      seed?: (value: number) => void;
      setState?: (name: string) => void;
      setPausedForScreenshot?: (paused: boolean) => void;
      setReducedMotion?: (enabled: boolean) => void;
      hideDebugUi?: (hidden: boolean) => void;
    };
  }
}

async function prepareDeterministicScreenshot(page: Page, stateName: string) {
  await page.goto('/');
  await page.waitForFunction(() => (window.__THREE_GAME_DIAGNOSTICS__?.frame ?? 0) > 10);

  await page.evaluate((name) => {
    window.__THREE_GAME_TEST_HOOKS__?.seed?.(12345);
    window.__THREE_GAME_TEST_HOOKS__?.setReducedMotion?.(true);
    window.__THREE_GAME_TEST_HOOKS__?.hideDebugUi?.(true);
    window.__THREE_GAME_TEST_HOOKS__?.setState?.(name);
    window.__THREE_GAME_TEST_HOOKS__?.setPausedForScreenshot?.(true);
  }, stateName);

  await page.waitForTimeout(150);
}

// Copy this file to tests/visual-regression.spec.ts when the game is stable
// enough for screenshot baselines. First run:
//   npx playwright test tests/visual-regression.spec.ts --update-snapshots
// Then compare:
//   npx playwright test tests/visual-regression.spec.ts

test('active play visual baseline', async ({ page }, testInfo) => {
  await prepareDeterministicScreenshot(page, 'active-play');
  await expect(page).toHaveScreenshot(`active-play-${testInfo.project.name}.png`, {
    fullPage: true,
    maxDiffPixelRatio: 0.015,
  });
});

test('fail retry visual baseline', async ({ page }, testInfo) => {
  await prepareDeterministicScreenshot(page, 'fail-retry');
  await expect(page).toHaveScreenshot(`fail-retry-${testInfo.project.name}.png`, {
    fullPage: true,
    maxDiffPixelRatio: 0.015,
  });
});
