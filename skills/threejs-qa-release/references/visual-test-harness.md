# Visual Test Harness

Screenshot baselines are worth adding when the visual state is valuable enough to protect and deterministic enough to compare — not for every prototype.

**Add or extend** when the user asked for premium/AAA/showcase/release-ready quality, when HUD or responsive text fit has regressed before, when imported assets must be proven visible in-game, when a signature scene is worth protecting, or when every release needs desktop/mobile active-play evidence. For a narrow fix, protect the affected state; do not re-run unrelated release coverage just because the existing game is premium.

**Defer** for exploratory prototypes, intentionally random scenes that cannot be seeded quickly, and images dominated by particles or noise where masking would hide the actual assertion. If the only question is "is the canvas non-blank", the canvas inspector already answers it. Say which way you went and why.

## States worth capturing

Two to five high-value states: `active-play-desktop` (player, objective, threat, reward, HUD all visible), `active-play-mobile` (same under mobile viewport and touch controls), `pause-or-settings` (layout, safe areas, text fit), `fail-or-retry`, and `hero-asset` (imported or generated asset in real lighting at real camera distance).

Title-only screenshots are only useful when title/menu work is the change.

## Determinism contract

Scaffold games ship a working implementation in `src/game/Game.ts` (`installTestHooks`), typed in `src/vite-env.d.ts`, with a seeded RNG in `src/utils/random.ts`. Keep the hooks real as the game evolves — the template fails loudly when the hooks object is missing, because silent no-op hooks capture a live animating scene and then every rerun diffs. Non-scaffold games implement the same contract:

```ts
window.__THREE_GAME_TEST_HOOKS__ = {
  seed: setGameSeed,
  async setState(name: string) {
    if (!supportedStates.has(name)) throw new Error(`Unknown test state: ${name}`);
    await loadAssetsForState(name);
    await enterGameState(name);
    return { state: name };
  },
  setPausedForScreenshot: setSimulationPaused,
  setReducedMotion: setReducedMotion,
  hideDebugUi: hideDebugUi,
};
```

The example's helpers are project-owned implementations, not placeholders to copy as no-ops. `setState` returns `{ state: name }` synchronously or through a Promise only after applying the requested state. Unknown states throw. Await `seed()` and `setState()`, and assert the acknowledgment. Named captures also require `setPausedForScreenshot` to stop simulation/state transitions immediately while rendering continues. The inspector fails explicit state captures when this contract is missing or broken.

Before a baseline: unpause a previously frozen scene, seed randomness, apply and await the state, then immediately freeze simulation so it cannot advance to a different state during capture setup. Stabilize particles and noise, disable camera shake / hitstop / time-dependent post, hide debug overlays and FPS meters, and wait for fonts and rendered frames. These visual hooks must apply their changes while paused, without needing a gameplay tick. The entire preparation phase is bounded, including hooks, fonts, and frames. Use fixed viewport profiles and mask dynamic UI only where the masked area is not part of the acceptance criteria.

## Playwright

Generated games include `tests/visual-regression.template.ts`. Copy it to `tests/visual-regression.spec.ts` when the project is ready:

```bash
npx playwright test tests/visual-regression.spec.ts --update-snapshots
npx playwright test tests/visual-regression.spec.ts
```

Thresholds: low `maxDiffPixelRatio` for stable UI and menu states, slightly higher for WebGL antialiasing and post-processing variation, never so high that a real layout or asset failure slips through.

Run WebGL suites with `workers: 1` and the full `chromium` channel — see `playtest-bot.md`, both matter more than they look.

## Asset visibility

For generated or imported assets, assert the path is loaded or present in diagnostics, screenshot it in active gameplay rather than a showroom, and check scale, orientation, bounds, material readability, and collision proxy. Provider URLs and API keys stay out of baseline paths and client code.

## Motion Evidence

For substantial animated gameplay, rig, or clip changes, capture a short unpaused sequence at the real gameplay camera. Cover at least a complete relevant motion cycle, locomotion start/stop and clip crossfades, plus attack/impact/recovery when combat is present. Record Playwright video (`recordVideo` on the context, close the context to finalize it), the runner's video tool, or a timed frame sequence with animation diagnostics. Do not use the paused screenshot hook for this pass.

Inspect for frozen rigs, collapsing or stretching limbs, foot sliding relative to world displacement, root-motion double application, snapping transitions, looping attacks, and hit/contact events that disagree with the visible motion. Note clip names, durations, mixer action changes, and event times alongside observed defects. Test active movement and interruption through real input, not only a forced pose. Rigid-body-only games need checks of their actual physics/motion, not an invented skeleton audit.

Declare motion files with the current-run capture manifest described in the director's `references/evidence-manifest.md`. File existence alone cannot establish good motion. Keep the detailed visual decision, states covered, commands, paths, thresholds, masks, motion findings, and flake risks in the lead's consolidated evidence artifact.
