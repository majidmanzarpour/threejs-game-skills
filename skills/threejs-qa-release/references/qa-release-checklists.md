# QA And Release Checklists

Use this before calling a Three.js browser game complete, premium, release-ready, or fixed.

## Browser QA Matrix

Minimum meaningful QA:

- Dependencies installed or known.
- Build/typecheck passes.
- Dev or preview server opened at the correct URL.
- Console/page/network errors captured.
- Canvas nonblank and visually varied through pixel sampling.
- Desktop active-play screenshot.
- Mobile active-play screenshot when mobile is in scope.
- Main input path changes game state.
- Objective/progress path works.
- Fail/retry or pause/resume path works when relevant.
- Recent or risky code paths triggered.
- Physics-heavy games: engine choice, fixed timestep, body/collider count, collision/trigger path, high-speed tunneling check, and restart body cleanup verified.
- HUD text fit, overlap, safe areas, and touch targets checked when UI changed.
- Renderer diagnostics captured when graphics complexity changed.
- Imported/generated asset paths, file sizes, and runtime load behavior checked when external assets changed.
- Audio unlock, decode/load, loop cleanup, mute/volume, and main SFX triggers checked when audio changed.
- Visual test harness decision recorded when work is premium, release-ready, UI-heavy, generated-asset-heavy, or likely to regress visually.

## Interaction QA

Test what a player actually does:

- Start or resume.
- Move/aim/steer/jump/attack/boost as appropriate.
- Collect or score.
- Avoid or hit a hazard.
- Trigger a state change: combo, wave, checkpoint, damage, shield, fail, win.
- Pause and resume.
- Restart after fail.
- For physics games, verify bodies reset cleanly after restart and no stale bodies keep simulating.
- For audio, verify user-gesture unlock, main SFX triggers, ambience loop start/stop, pause/resume, restart cleanup, and mute/volume controls.
- Resize or rotate when responsive/mobile is in scope.

Do not rely only on screenshots for gameplay changes.

## Visual QA

For premium/AAA/showcase or "less basic" requests:

- Capture active-play screenshot before and after when possible.
- Use the visual scorecard.
- Check for automatic failures:
  - primitive-dominant active screenshot
  - flat plane/box skyline world
  - generic stat-card HUD
  - one repeated obstacle/reward silhouette
  - fog/glow/darkness hiding missing geometry
  - no renderer diagnostics
- Confirm UI and VFX do not obscure threats, rewards, player, or next decision.
- Confirm desktop and mobile framing both show the playable path.
- For generated 3D assets, confirm imported models have correct scale, orientation, material readability, collision proxies, and animation clips in active gameplay.
- Decide whether to add/extend visual regression baselines. If skipped, record why the scene is not deterministic, not valuable enough yet, or covered by smoke checks only.

## Visual Test Harness QA

When a visual harness is warranted:

- Add deterministic hooks or test setup for random seed, camera shake, particles, time, debug UI, and active state.
- Cover active desktop and active mobile screenshots when mobile is in scope.
- Cover changed HUD/menu/fail/generated-asset states.
- Use Playwright screenshot comparisons with deliberate thresholds.
- Keep canvas-pixel smoke and interaction tests; visual baselines are additional evidence.
- Report baseline update command, compare command, snapshot paths, masks, thresholds, and flake risks.

## Mobile QA

- Touch controls emit game intents.
- Pointer release/cancel/blur cannot leave controls stuck.
- Safe areas respected.
- Touch targets reachable and separated.
- Page scroll does not steal gameplay input.
- Orientation/resize preserves canvas and HUD.
- DPR/performance acceptable.
- Desktop input still works unless intentionally removed.
- UI remains readable on narrow screens.

## Performance QA

When draw calls, asset counts, shaders, shadows, or post-processing changed:

- Record renderer calls, triangles, geometries, textures.
- Record FPS/frame time if available.
- Record physics engine, timestep, body count, collider count, active sensors, CCD bodies, and known expensive colliders when physics changed.
- Note DPR cap and post/shadow settings.
- Check active gameplay, not only idle view.
- Compare before/after if performance work was requested.
- Report any unmeasured risk honestly.

## Release Checks

Before release-ready:

- Production build passes.
- Production preview/static server tested.
- Vite `base` and asset URLs match target host.
- Debug GUI, diagnostics overlays, verbose logs, and test shortcuts are gated or removed from player-facing release.
- Bundle and large assets reviewed.
- API keys are not present in client-side code, checked-in files, built assets, or browser-visible environment.
- Public assets load under static hosting assumptions.
- Browser support assumptions documented.
- Deployment command or static artifact location reported.
- Residual risks listed.

## Evidence Format

```text
QA result: pass/fail
Commands:
URL:
Controls tested:
Screenshots/artifacts:
Console/page/network errors:
Canvas pixel check:
Desktop/mobile viewports:
Renderer/performance diagnostics:
Visual test harness:
Physics diagnostics:
External asset evidence:
Audio evidence:
Issues found/fixed:
Residual risks:
```

## Bug Report Format

```text
Title:
Severity:
Reproduction steps:
Expected:
Actual:
Browser/viewport/device:
Console/page errors:
Screenshot/artifact:
Likely owner:
Suggested fix:
```

## Common Release Failures

- Testing dev server but shipping untested production build.
- Static host base path breaks assets.
- Debug UI visible to players.
- Mobile UI passes screenshot but controls do not work.
- Canvas is nonblank but wrong app is running on the port.
- Physics gameplay looks right visually but collision proxies, sensors, or restart cleanup were not tested.
- Screenshots are title/idle views instead of active play.
- Premium claim has no visual scorecard or renderer diagnostics.
- 3D/image/audio generation API key or generated temporary URLs accidentally exposed in client code.
