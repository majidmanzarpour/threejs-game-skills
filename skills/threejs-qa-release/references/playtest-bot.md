# Bot Playtest

Automated playtests drive the game through scripted real input and measure whether it actually plays: objective progression, player responsiveness, softlock windows, and error-free runtime. A game that renders beautifully but cannot be progressed by a scripted sweep is not release-ready. Use this for release-ready gameplay claims and difficulty/fairness verification; the canvas inspector proves the game renders, the bot proves it plays.

## Prerequisites

- `window.__THREE_GAME_DIAGNOSTICS__` publishing frame, score/objective, complete/fail state, and player position every update.
- `window.__THREE_GAME_TEST_HOOKS__` with at least `seed()` and `setState()` so runs are reproducible (scaffold games ship both).
- All gameplay randomness routed through the seeded RNG — otherwise bot metrics are noise.

## Setup

Copy the packaged template and adapt it:

```bash
cp tests/bot-playtest.template.ts tests/bot-playtest.spec.ts
npx playwright test tests/bot-playtest.spec.ts
```

Adapt `INPUT_SCRIPT` to the game's controls and level layout: an endless runner bot holds forward and switches lanes on a cadence; an arena game sweeps the play space; a tower defense bot places affordable towers via test hooks and starts waves. Game-specific hooks (e.g. `forceWave()`, `buildFirstOpenPad()`) are encouraged for genres where raw keyboard input cannot express the core verb.

## Metrics And What They Mean

- `framesAdvanced` — the loop survived the whole run; a stall here is a crash or frozen loop.
- `distanceTravelled` — input responsiveness; near-zero under held keys means broken input mapping.
- `scoreAfter - scoreBefore` and `stepOfFirstScore` — objective progression and how quickly a naive player finds it. If a scripted sweep never scores, the objective is unreachable, unreadable, or broken.
- `softlockWindows` — sampling windows where frames advanced but held input produced neither motion nor progress. Repeated windows indicate stuck-on-geometry, dead input states, or unrecovered fail states.
- Time-to-first-fail (games with fail states) — add a scripted "reckless" run that seeks hazards and assert the fail state triggers and the retry path restores play; a game that cannot be failed has no pressure, and a fail state that cannot be retried is a release blocker.
- Console/page errors — must be empty for the full run.

## Headless WebGL Caveats

- Always launch Chromium with `channel: 'chromium'` (the scaffold config and `inspect-threejs-canvas.mjs` do). Playwright's default headless is `chromium_headless_shell`, which ships no GPU backend and silently falls back to SwiftShader (CPU). This is a launch-config bug, not a headless limitation: on the same 1024x1024 scene the shell reports `ANGLE (Google, ... SwiftShader driver)` and renders at 32 fps, while `channel: 'chromium'` reports `ANGLE (Apple, ANGLE Metal Renderer: Apple M3 Pro)` and renders at 127 fps — ~4x, from one line of config.
- Verify the GPU before reporting any FPS; never assume it. `inspect-threejs-canvas.mjs` records a `gpu` block (`renderer`, `vendor`, `softwareRendered`) in its JSON report — check it. If `softwareRendered` is true, the run fell back to CPU and its FPS/frame-time numbers are not performance evidence; pixel, budget, and functional checks are still valid. Fix the fallback with `npx playwright install chromium` rather than caveating the number.
- Run Playwright suites with `workers: 1` for WebGL games (the scaffold config does). Parallel contexts still contend for the GPU, and the frame-time collapse makes game time drift from wall time, flaking timed phases and screenshot baselines.
- Headless FPS on a verified real GPU is still not a phone. Treat it as a desktop-GPU signal and validate mobile targets on real hardware.

## Difficulty And Fairness Signals

For games with fail states, run the bot at two skill levels (e.g. reaction delay 0ms vs 300ms between script steps) and compare survival time and score. If the delayed bot survives as long as the fast one, difficulty pressure is decorative; if even the fast script cannot survive the first threat, the opening is unfair. Report both runs when difficulty tuning is in scope.

## Reporting

Include in the QA evidence: the JSON report attachment (steps, frames, score progression, distance, softlock windows, errors), the seed used, and pass/fail per assertion. Report the bot playtest decision like the visual harness decision: added / extended / skipped with reason.
