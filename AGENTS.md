# Agent Instructions

This repo contains agent workflow assets for Three.js browser-game development. For broad requests to build, upgrade, polish, or finish a Three.js game, route through `skills/threejs-game-director/SKILL.md` first — it orchestrates the specialist skills (gameplay, AAA graphics, UI, debug/profile, QA/release, 3D/image/audio generation) and defines the runner capability check, skill path ladder, ledgers, gates, and verification bar. The user should not have to name every specialist skill.

## Default Technical Stack

- Prefer TypeScript, Vite, npm package imports, and Three.js modules; use `three/addons/...` for official controls, loaders, and post-processing helpers.
- Physics: simple custom collision for arcade triggers; Rapier as the default robust engine; `cannon-es` only as a lightweight JS fallback. Load `skills/threejs-gameplay-systems/references/physics-engine-selection.md` before adding or changing physics-heavy gameplay.
- Use `lil-gui` for local tuning and a lightweight HUD or `stats.js` for frame diagnostics when performance is in scope.
- Treat WebGPU as conditional: use `WebGPURenderer` only when the project benefits, and keep a WebGL/WebGL2 fallback path.

## Quality Bar

The binding gates live in `skills/threejs-game-director/SKILL.md` (External Asset Sourcing Gate, Reference Gate, Premium Completion Rule, Required Verification) and `skills/threejs-game-director/references/phase-playbook.md` (phase exit evidence, ledger templates, completion gate). Non-negotiables worth restating:

- Build a playable loop first; a static scene is not done. Broad game creation starts from a game design brief, core loop contract, and level/encounter plan.
- Do not stop at a first playable slice when the user asked for premium, AAA, polished, complete, release-ready, or "less basic" quality.
- Premium/AAA/showcase claims require the filled visual scorecard from `skills/threejs-aaa-graphics-builder/references/visual-scorecard.md` with measured evidence and a fresh-eyes review pass; a build is not premium if any category is below 2.
- Load the generator skills (`threejs-3d-generator`, `threejs-image-generator`, `threejs-audio-generator`) before deciding generated assets are unnecessary for premium work; run the credential probe before claiming a key is unavailable; report the external asset sourcing ledger.
- Treat generic stat-card HUDs, cube obstacles, and skyline boxes as prototype placeholders unless the user explicitly wants that style.
- Keep mobile input and resize behavior in the first implementation path, not as a final afterthought.
- In Claude-style runners the director cannot literally invoke other skills: it loads sibling `SKILL.md` files by path and reports a skill-loading ledger. Never claim a skill was invoked when it was only loaded.

## Verification Bar

Follow Required Verification in `skills/threejs-game-director/SKILL.md`. When shell tools are available, audit the final evidence report with `skills/threejs-game-director/scripts/audit_reference_report.py --premium <report.md>` before claiming premium/complete success. Use the scaffold's `npm run verify:visual` and `npm run inspect:canvas` when available, or `skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs`.
