---
name: threejs-qa-release
description: "Verify and release Three.js browser games: playtest QA, automated bot playtests, mobile and responsive checks, production builds, static-hosting base paths, debug gating, bundle review, screenshots, visual regression baselines, canvas-pixel inspection with measured metrics, and release risk reports."
---

# Three.js QA Release

Prove the game works the way a player will meet it, then prepare a shippable build with its known risks.

Resolve `<this-skill-dir>` and local references from the actual loaded skill file; resolve sibling skills beside it before using runner-discovered alternatives. Run the inspector from the game project with its npm dependencies installed.

## References

| File | Read it when |
| --- | --- |
| `references/release-checks.md` | mobile verification, production release, performance evidence, or release-failure traps |
| `references/visual-test-harness.md` | screenshot baselines, visual regression, UI or generated-asset regression protection |
| `references/playtest-bot.md` | release-ready gameplay claims, difficulty and fairness checks, or a loop never driven by scripted input |

## QA pass

For a complete game use the full pass below. For narrow edits select checks covering the affected behavior, states, and target viewports. Reuse valid specialist evidence from the same code revision; the lead owns one consolidated pass. Repeat only after relevant changes, failures, or unresolved concerns. An explicit desktop-only scope does not require adding mobile gameplay.

1. Install dependencies, run build and typecheck, start the dev or preview server.
2. Open the browser target and capture console, page, and network errors.
3. Confirm non-blank, visually varied canvas pixels.
4. Capture active play on each target viewport (desktop and mobile by default), not just the title screen.
5. Exercise the main input, objective progression, fail and retry, and whatever changed most recently.
6. Check HUD text fit, safe areas, touch targets, and responsive layout.
7. When audio changed: user-gesture unlock, SFX triggers, ambience loop start and stop, pause and restart cleanup, mute and volume, decode errors.
8. Decide on a visual test harness. For premium, release-ready, UI-heavy, or generated-asset work a harness is usually worth it; say so either way.
9. Run the bot playtest (`tests/bot-playtest.template.ts` in scaffold games) for release-ready gameplay claims and report its metrics JSON.
10. When animation changed, capture a short unpaused sequence and inspect locomotion, clip transitions, feet, rig deformation, and attack/contact timing using `references/visual-test-harness.md`.

Screenshots alone do not cover gameplay changes.

## Canvas inspector

```bash
node <this-skill-dir>/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --state active-play --run-id pass-1
```

`--mobile` selects mobile emulation. `--state <name>` (with optional `--seed <n>`) awaits the game's test hooks before capture. The state hook must acknowledge `{ state: name }`, and `setPausedForScreenshot` must stop simulation immediately while rendering continues. Capture freezes the acknowledged state before settling; the complete preparation phase has a timeout. Missing hooks, no-op results, unknown states, and mismatched acknowledgements fail. Reports retain `state` and add `requestedState`, `appliedState`, and `runId`. Scaffold games have their own copy plus `npm run inspect:canvas`.

Use a fresh `--run-id` for each verification pass and a separate `--out` directory. Declare expected viewport/state pairs before capture in the director's `references/evidence-manifest.md` format, then run its checker with `--manifest`. Include all requested states; do not remove a failing slot to make the manifest pass. Omitting `--state` performs only a current-view canvas check.

The JSON carries a `metrics` block (color entropy, edge density, luminance contrast, dominant-color share) and a `renderBudget` comparison against tier budgets. These are the Measured Evidence for the visual scorecard in `threejs-aaa-graphics-builder/references/visual-scorecard.md`; over-budget rows need a documented tradeoff, and blank-canvas or error conditions exit non-zero.

## Release pass

Inspect package scripts, Vite config, base path, and public assets → gate debug UI, logging, and test helpers → run the production build and preview it on a static server → check the built output on target viewports → review bundle and large assets → document the deploy command, host assumptions, and residual risks.

## Report

Lead with the result and unresolved defects. Put the detailed commands, manifest, captures, motion evidence, controls exercised, issues fixed, and deployment notes in the project's evidence report. Include the harness decision and bot metrics when in scope. Return the artifact path to the lead; passing pixels and acknowledged state hooks do not establish aesthetic quality or successful gameplay by themselves.
