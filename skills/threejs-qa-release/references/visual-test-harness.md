# Visual Test Harness

Use this reference when a Three.js game warrants visual regression testing, baseline screenshots, repeated release checks, generated asset verification, or UI overlap/text-fit regression protection.

Do not add screenshot baselines for every prototype. Use a harness when the visual state is valuable enough to protect and deterministic enough to compare.

Research basis: Playwright supports `expect(page).toHaveScreenshot()` for visual comparisons, device emulation for desktop/mobile projects, screenshot thresholds such as max diff pixels/ratio, and test artifacts/traces. Three.js exposes renderer diagnostics through `WebGLRenderer.info`. Existing canvas pixel checks are good smoke tests, but they do not replace screenshot baselines for polished screens.

## When To Add A Visual Harness

Add or extend a visual harness when:

- The user asks for premium, AAA, showcase, release-ready, or "less basic" quality.
- HUD/menu layout or responsive text fit has regressed before.
- Imported/generated assets must be proven visible in-game.
- A visual style, level, vehicle, table, arena, or boss scene is important enough to protect.
- You need desktop/mobile active-play evidence on every release.
- The game has deterministic states or can expose test hooks to freeze randomness, camera, time, and particles.

Skip or defer baseline screenshots when:

- The game is still an exploratory prototype.
- The scene is intentionally random and cannot be seeded quickly.
- Particles/camera/noise dominate the image and masking would hide the useful assertion.
- The only need is "is the canvas nonblank"; use the canvas inspector instead.

Even when skipped, report the skip reason.

## Harness States

Prefer 2-5 high-value states:

- `active-play-desktop`: player, objective, threat, reward, HUD visible.
- `active-play-mobile`: same as above under mobile viewport/touch controls.
- `pause-or-settings`: menu layout, safe areas, text fit.
- `fail-or-retry`: failure feedback and restart affordance.
- `hero-asset-or-generated-asset`: imported/generated asset in real lighting and camera distance.

Avoid title-only screenshots unless title/menu work is the actual change.

## Determinism Requirements

Scaffold-generated games ship a working implementation of these hooks (`src/game/Game.ts` `installTestHooks`, typed in `src/vite-env.d.ts`) plus a seeded RNG in `src/utils/random.ts`. Keep the hooks real as the game evolves — the template fails loudly if the hooks object is missing, because silent no-op hooks capture live animating scenes and every rerun diffs. For non-scaffold games, implement the same contract:

```ts
window.__THREE_GAME_TEST_HOOKS__ = {
  seed(value: number) {},
  setState(name: string) {},
  setPausedForScreenshot(paused: boolean) {},
  setReducedMotion(enabled: boolean) {},
  hideDebugUi(hidden: boolean) {},
};
```

Before taking baselines:

- Seed random generation.
- Pause or stabilize particle/noise systems.
- Freeze camera shake, hit stop, and time-dependent post effects.
- Hide debug overlays and FPS meters unless the test covers diagnostics.
- Wait for fonts, GLTFs, textures, audio decode blockers, and first frames.
- Use fixed viewport/device profiles.
- Mask known dynamic UI only if the masked area is not part of the acceptance criteria.

## Playwright Pattern

Use the project's existing Playwright setup. Generated games include `tests/visual-regression.template.ts` as an optional starting point. Copy it to `tests/visual-regression.spec.ts` when the project is ready for baselines.

Suggested commands after copying:

```bash
npx playwright test tests/visual-regression.spec.ts --update-snapshots
npx playwright test tests/visual-regression.spec.ts
```

Use thresholds carefully:

- Prefer low `maxDiffPixelRatio` for stable UI/menu states.
- Allow slightly higher thresholds for WebGL antialiasing/post-processing differences.
- Do not set thresholds so high that real layout or asset failures pass.

## Asset Visibility Checks

For generated/imported assets:

- Assert the asset path is loaded or listed in diagnostics.
- Capture screenshot with the asset in active gameplay, not isolated in a showroom.
- Check scale, orientation, bounds, material readability, and collision proxy through diagnostics or visible state.
- Keep temporary provider URLs and API keys out of baseline paths and client code.

## Report Requirements

Report:

- Visual harness decision: added / extended / skipped.
- States covered.
- Determinism hooks used.
- Desktop/mobile projects covered.
- Screenshot update command and compare command.
- Baseline artifact paths.
- Thresholds/masks and why they are safe.
- Remaining flake risks.
