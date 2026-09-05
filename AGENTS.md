# Agent Instructions

This repo contains agent workflow assets for Three.js browser-game development. For broad requests to build, upgrade, polish, or finish a Three.js game, start from `skills/threejs-game-director/SKILL.md` — it routes work across the specialist skills (gameplay, AAA graphics, UI, debug/profile, QA/release, 3D/image/audio generation). The user should not have to name every specialist skill.

The same nine skills serve Codex and Claude Code. The user's requested scope, art style, constraints, and prior decisions take precedence over skill defaults. Use the runner's available tools; skills do not enable native async APIs or change model settings.

## Coordination

- The lead owns scope, shared interfaces, integration, and one consolidated verification pass. Delegate independent work when it improves quality or saves time, normally to at most two workers with separate file ownership and explicit outputs. One focused independent review is useful for substantial gameplay, graphics, or animation changes. Continue directly when delegation tools are unavailable.
- Complete games load the five production specialists and relevant generators; narrow changes load only affected skills and references. Read each phase's relevant references before doing that work.
- For substantial builds, keep `artifacts/game-progress.md` current with intent, constraints, completed work, pending task IDs/checkpoints, defects, and next actions. Apply user corrections to pending work and preserve completed assets.

## Default Technical Stack

- TypeScript, Vite, npm package imports, Three.js modules; `three/addons/...` for official controls, loaders, and post-processing helpers.
- Physics: custom collision for arcade triggers, Rapier as the default robust engine, `cannon-es` as a lightweight JS fallback. See `skills/threejs-gameplay-systems/references/physics-engine-selection.md` when physics is in scope.
- `lil-gui` for local tuning; a lightweight HUD or `stats.js` for frame diagnostics when performance matters.
- WebGPU is conditional: `WebGPURenderer` only when the project benefits, with a WebGL/WebGL2 fallback.

## Quality Bar

The full bar lives in `skills/threejs-game-director/SKILL.md`. In short:

- A playable loop comes first — a static scene is not done. Broad game creation starts from a design brief, core loop contract, and level plan.
- The user's own words set the scope. A small arcade game is not a request for the premium pipeline; "premium", "AAA", "polished", "release-ready", or "less basic" is, and at that bar a first playable slice is not finished.
- Premium claims use the 10-category scorecard in `skills/threejs-aaa-graphics-builder/references/visual-scorecard.md` with its anchors and the inspector's measured metrics: no category below 2, average at least 2.3.
- With keys set, premium hero surfaces get generated assets unless the user explicitly chose procedural art or restricted external generation. Run `skills/threejs-game-director/scripts/probe_asset_credentials.sh` before assuming anything about keys. Classify failures and recover accepted tasks before falling back; follow `skills/threejs-game-director/references/asset-recovery.md`.
- Establish the art direction, camera scale, and representative playable scene before expanding content. Asset counts come from the genre and design brief.
- Generic stat-card HUDs, cube obstacles, and skyline boxes are prototype placeholders unless the user asked for that style.
- Mobile input and resize belong in the first implementation path, not a final afterthought.

## Evidence

For complete games, capture active-play screenshots for the target viewports plus canvas-pixel evidence with the scaffold's `npm run inspect:canvas` and `npm run verify:visual`, or `skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs`. Animated work also needs motion evidence. Small edits receive targeted verification; do not repeat unchanged suites without a new concern.

`skills/threejs-game-director/scripts/check_evidence.py <project> --manifest <manifest.json>` verifies the declared viewport/state captures from the current run. The format lives in `skills/threejs-game-director/references/evidence-manifest.md`. Legacy `--report` checks file existence but cannot prove current-run coverage or visual quality.
