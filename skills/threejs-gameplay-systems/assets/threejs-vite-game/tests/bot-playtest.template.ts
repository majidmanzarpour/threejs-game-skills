import { expect, test } from '@playwright/test';

// Copy this file to tests/bot-playtest.spec.ts to enable automated playtests.
// The bot drives the game through scripted real input and measures whether the
// game actually progresses: score/objective movement, player motion, softlock
// windows, and error-free play. Adapt `INPUT_SCRIPT` to your game's controls
// and level layout — keep the progression assertion; a bot that cannot make
// the objective move is evidence the game is unclear or broken.
//
// Requires window.__THREE_GAME_DIAGNOSTICS__ (frame/score/complete/player) and
// window.__THREE_GAME_TEST_HOOKS__ (seed/setState) — both ship in the scaffold.

type BotSnapshot = {
  frame: number;
  score: number;
  complete: boolean;
  x: number;
  z: number;
};

// Keyboard sweep tuned to the scaffold arena (22x14, pickups in two rows).
// Each step holds keys for `ms` then samples diagnostics.
const INPUT_SCRIPT: Array<{ keys: string[]; ms: number }> = [
  { keys: ['KeyW'], ms: 1000 },
  { keys: ['KeyA'], ms: 1900 },
  { keys: ['KeyD'], ms: 3400 },
  { keys: ['KeyW'], ms: 350 },
  { keys: ['KeyA'], ms: 3400 },
  { keys: ['KeyS'], ms: 1700 },
  { keys: ['KeyD'], ms: 3400 },
  { keys: ['KeyS'], ms: 350 },
  { keys: ['KeyA'], ms: 3400 },
];

test('bot playtest: scripted input drives progress without errors', async ({ page }, testInfo) => {
  test.skip(
    testInfo.project.name !== 'desktop-chrome',
    'The bot uses keyboard input; mobile touch input is exercised by visual.spec.ts.',
  );
  test.setTimeout(90_000);

  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });

  await page.goto('/');
  await page.waitForFunction(() => (window.__THREE_GAME_DIAGNOSTICS__?.frame ?? 0) > 10);
  await page.evaluate(() => {
    window.__THREE_GAME_TEST_HOOKS__?.seed(12345);
    window.__THREE_GAME_TEST_HOOKS__?.setState('active-play');
  });

  const sample = (): Promise<BotSnapshot | null> =>
    page.evaluate(() => {
      const d = window.__THREE_GAME_DIAGNOSTICS__;
      if (!d) return null;
      return {
        frame: d.frame,
        score: d.score,
        complete: d.complete,
        x: d.player.position.x,
        z: d.player.position.z,
      };
    });

  const before = await sample();
  expect(before, 'diagnostics must be published before the bot can play').not.toBeNull();

  const snapshots: BotSnapshot[] = [before as BotSnapshot];
  let softlockWindows = 0;
  let distance = 0;
  let stepOfFirstScore = -1;

  for (const [index, step] of INPUT_SCRIPT.entries()) {
    for (const key of step.keys) await page.keyboard.down(key);
    await page.waitForTimeout(step.ms);
    for (const key of step.keys) await page.keyboard.up(key);

    const snap = await sample();
    const prev = snapshots[snapshots.length - 1];
    if (snap) {
      const moved = Math.hypot(snap.x - prev.x, snap.z - prev.z);
      distance += moved;
      const progressed = snap.score > prev.score || (snap.complete && !prev.complete);
      if (progressed && stepOfFirstScore === -1) stepOfFirstScore = index;
      // Softlock signature: frames advance while held input neither moves the
      // player nor progresses the objective.
      if (snap.frame > prev.frame && moved < 0.2 && !progressed) softlockWindows += 1;
      snapshots.push(snap);
    }
  }

  const after = snapshots[snapshots.length - 1];
  const report = {
    steps: INPUT_SCRIPT.length,
    framesAdvanced: after.frame - (before as BotSnapshot).frame,
    scoreBefore: (before as BotSnapshot).score,
    scoreAfter: after.score,
    complete: after.complete,
    distanceTravelled: Number(distance.toFixed(2)),
    stepOfFirstScore,
    softlockWindows,
    consoleErrors,
    pageErrors,
  };
  await testInfo.attach('bot-playtest-report', {
    body: JSON.stringify(report, null, 2),
    contentType: 'application/json',
  });
  console.log(`bot playtest: ${JSON.stringify(report)}`);

  expect(pageErrors, 'page errors during bot play').toEqual([]);
  expect(consoleErrors, 'console errors during bot play').toEqual([]);
  expect(report.framesAdvanced, 'game loop must keep running').toBeGreaterThan(100);
  expect(report.distanceTravelled, 'player must respond to scripted input').toBeGreaterThan(5);
  expect(report.softlockWindows, 'held input repeatedly produced no motion or progress').toBeLessThanOrEqual(2);
  expect(
    report.scoreAfter,
    'scripted sweep should progress the objective — tune INPUT_SCRIPT to your level layout',
  ).toBeGreaterThan(report.scoreBefore);
});
