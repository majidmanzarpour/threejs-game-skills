---
name: threejs-qa-release
description: "Verify and release Three.js browser games. Combines playtest QA, automated bot playtests, mobile/responsive checks, production builds, preview verification, static-hosting base paths, debug gating, bundle review, screenshots, visual test harness decisions, packaged canvas-pixel inspection with measured metrics, console checks, and release risk reports."
---

# Three.js QA Release

## Purpose

Prove the game works as a player encounters it, then prepare a shippable browser build with known risks.

## QA Workflow

Load `references/qa-release-checklists.md` as the first action before broad QA, mobile verification, bug reporting, production preview, static-hosting checks, or release preparation. Track it in a reference ledger with yes/no, path, and failure reason. Do not mark QA/release complete while this reference is skipped for QA or release work.

Load `references/checklists/visual-verification.md` for screenshot/canvas verification, `references/checklists/playtest-qa.md` for player-loop QA, and `references/checklists/release.md` for production release checks. Load `references/prompt-templates.md` only when the user asks for reusable QA/release prompts or a task template.

Load `references/visual-test-harness.md` and `references/checklists/visual-test-harness.md` when the game warrants screenshot baselines, visual regression testing, release-ready visual evidence, UI/generated-asset regression protection, or premium visual QA. If a harness is not warranted, report the skip reason.

Load `references/playtest-bot.md` and `references/checklists/bot-playtest.md` for release-ready gameplay claims, difficulty/fairness verification, or when the playable loop has never been driven by scripted input. Report the bot playtest decision as added/extended/skipped with reason.

1. Install dependencies if needed.
2. Run build/typecheck.
3. Start dev or preview server.
4. Open browser target.
5. Capture console/page/network errors.
6. Verify nonblank canvas pixels.
7. Capture desktop and mobile screenshots.
8. Trigger main input, objective progression, fail/retry, and recent risky paths.
9. Check HUD text fit, safe areas, touch targets, responsive layout.
10. Decide whether to add or extend a visual test harness. For premium/release UI or generated-asset work, prefer a harness unless determinism is a real blocker.
10b. Decide whether to run the bot playtest (`tests/bot-playtest.template.ts` in scaffold games). For release-ready gameplay claims, run it and report the metrics JSON.
11. If audio changed, verify user-gesture unlock, SFX triggers, ambience loop start/stop, pause/restart cleanup, mute/volume behavior, and decode/load errors.
12. Record artifacts and issues.

## Packaged Canvas Inspector

Use the bundled inspector when the target project does not already include one:

```bash
node <this-skill-dir>/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188
```

For mobile emulation, add `--mobile`. Add `--state <name>` (and optionally `--seed <n>`) to drive the game's `__THREE_GAME_TEST_HOOKS__` before capture, so every named state (active-play, fail, stress) can be measured deterministically without live play — outputs are suffixed per state. Generated games from the packaged scaffold also include their own `scripts/inspect-threejs-canvas.mjs` and `npm run inspect:canvas`.

The inspector JSON includes a `metrics` block (color entropy, edge density, luminance contrast, dominant-color share) and a `renderBudget` comparison against starting-point tier budgets. Cite these as the Measured Evidence in the visual scorecard (`threejs-aaa-graphics-builder/references/visual-scorecard.md`); over-budget rows need a documented tradeoff, and blank-canvas or error conditions still exit nonzero.

## Release Workflow

1. Inspect package scripts, Vite config, base path, public/assets.
2. Gate debug UI/logging/test helpers.
3. Run production build and preview/static server.
4. Verify built output desktop/mobile.
5. Review bundle and large assets.
6. Document deploy command, host assumptions, and residual risks.

## Final Response

Lead with pass/fail. Include the reference ledger, QA matrix/checklist result, commands, URL, controls, screenshots/artifacts, issues found/fixed, deployment notes, and risks.
When visual baselines are in scope, include the harness decision, states covered, update/compare commands, artifact paths, thresholds/masks, and flake risks.
When the bot playtest ran, include its metrics JSON (frames, score progression, distance, softlock windows, seed) and the added/extended/skipped decision.
