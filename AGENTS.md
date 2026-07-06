# Agent Instructions

This repo contains Codex workflow assets for Three.js browser-game development.

## Default Technical Stack

- Prefer TypeScript, Vite, npm package imports, and Three.js modules.
- Use `three/addons/...` for official controls, loaders, and post-processing helpers.
- Use simple custom collision for arcade triggers and prototype-scale interactions.
- Use Rapier as the default robust physics engine for serious Three.js browser games with rigid bodies, sensors, balls, ramps, moving platforms, many contacts, or high-speed collisions.
- Use `cannon-es` only as a lightweight JavaScript fallback for small/simple rigid-body scenes when avoiding WASM matters.
- Load `threejs-gameplay-systems/references/physics-engine-selection.md` before adding or changing physics-heavy gameplay.
- Use `lil-gui` for local tuning when it materially speeds iteration.
- Use a lightweight HUD or `stats.js` for frame diagnostics when performance is in scope.
- Treat WebGPU as conditional. Use Three.js `WebGPURenderer` only when the project benefits from it and keep a WebGL/WebGL2 fallback path.

## Game Quality Bar

- For broad requests to build, upgrade, polish, or finish a Three.js game, route through `threejs-game-director` first. The user should not have to name every specialist skill.
- Public Three.js skills are consolidated around the director plus specialist systems: gameplay, AAA graphics, UI, debug/profile, QA/release, 3D generation, image generation, and audio generation.
- In Claude-style skill runners, do not assume a director skill can literally invoke other skills. The director must attempt to load sibling public `SKILL.md` files first, report a skill-loading ledger, and use the bundled phase OS only for files that cannot be loaded.
- For broad/premium director work, the director must load each phase's required `references/*.md` files at phase entry and report a reference ledger. A phase is not done if its required references were skipped.
- Premium/AAA/showcase claims must include the filled visual scorecard from `threejs-aaa-graphics-builder/references/visual-scorecard.md`, including average score and automatic failures remaining. Do not substitute an improvised rubric.
- When shell tools are available, run `skills/threejs-game-director/scripts/audit_reference_report.py --premium <report.md>` against the final evidence report before claiming premium, AAA, showcase, complete, release-ready, or "less basic" success.
- Build a playable loop first. A static scene is not done.
- For broad game creation or major gameplay upgrades, require a compact game design brief, core loop contract, and level/encounter plan before implementation.
- Load `threejs-gameplay-systems/references/game-design-level-design.md` before broad new-game creation, level/arena/track/wave/hole/puzzle design, combat/encounter design, progression/difficulty work, or premium gameplay claims.
- Do not stop at first playable slice when the user asked for premium, AAA, polished, complete, release-ready, or showcase quality.
- Keep scene setup, loop, input, systems, entities, UI, assets, and debug tools separated once the prototype grows beyond a single simple file.
- Tune movement, camera, collisions, feedback, and HUD through short playtest loops.
- For physics-heavy games, report engine choice, fixed timestep, collider strategy, sensors, CCD use, body/collider counts, and restart cleanup evidence.
- Avoid decorative-only UI, generic purple gradients, particle clutter, and unchecked post-processing.
- Keep mobile input and resize behavior in the first implementation path, not as a final afterthought.
- Use screenshot-based art-direction critique when visual priorities are unclear.
- Use `threejs-aaa-graphics-builder` when screenshots still look basic across multiple visual surfaces. Do not split that broad graphics problem into isolated small polish tasks.
- For premium graphics work, include technical art: material kit, shader/VFX purpose, instancing/LOD/culling strategy, render budget, imported asset cleanup, and mobile DPR/post/shadow tradeoffs.
- Load `threejs-aaa-graphics-builder/references/technical-art.md` before premium/AAA/showcase graphics, shaders/material systems, VFX systems, generated/imported asset cleanup, LOD/instancing, or visual performance work.
- Use focused UI passes for HUDs, menus, text fit, icon controls, and safe-area layout instead of treating interface craft as generic polish.
- Use focused procedural-model passes for scratch-built assets, prop kits, material variation, instancing, LOD, and renderer-count-aware detail.
- For premium/AAA/showcase/high-fidelity/less-basic work with characters, vehicles, ships, weapons, buildings, signature props, skies, textures, decals, logos, icons, GUI art, SFX, ambience, or voice, load `threejs-3d-generator`, `threejs-image-generator`, and/or `threejs-audio-generator` before deciding procedural/generated assets are unnecessary.
- Run the director credential probe before claiming 3D/image/audio generation credentials are unavailable. A missing key is not a valid blocker unless the SET/MISSING probe output is reported.
- Report an external asset sourcing ledger for premium graphics work: procedural / threejs-image-generator / threejs-3d-generator / hybrid per high-value surface, plus task IDs/output paths or real blocker evidence.
- For premium hero surfaces, procedural-only is not a valid final answer unless credential probe output or attempted generation shows a real blocker.
- Use `threejs-3d-generator` for high-value external AI-generated 3D assets, auto-rigging, animation, texture, conversion, and GLB/FBX game asset workflows.
- Use `threejs-image-generator` before `threejs-3d-generator` when 2D concept/reference images, T-pose/A-pose character sheets, texture references, decals, logos, icons, skies, backgrounds, or GUI art would improve the result.
- Use `threejs-audio-generator` for game SFX, ambience loops, UI sounds, announcer/dialogue, voice conversion, and audio cleanup.
- Treat generic stat-card HUDs, cube obstacles, and skyline boxes as prototype placeholders unless the user explicitly wants that style.
- Require active-play screenshot scoring for premium/AAA claims. A build is not premium if the visual scorecard has any category below 2.
- For premium/release-ready visual QA, generated asset visibility, or UI regression risk, load `threejs-qa-release/references/visual-test-harness.md` and report whether a Playwright screenshot harness was added, extended, or skipped.

## Verification Bar

For meaningful Three.js changes, gather evidence before claiming success:

- `npm run build`
- a local dev or preview server opened in a browser
- browser console and page error check
- Playwright screenshot
- canvas nonblank pixel check
- visual test harness decision when premium/release-ready visual QA, generated assets, or UI regression risk are in scope
- at least one desktop and one mobile viewport
- interaction check for the main control path
- performance snapshot when draw calls, asset counts, shaders, or post-processing changed
- UI text-fit, overlap, safe-area, and touch-target evidence when interface layout changed
- renderer diagnostics when procedural model fidelity, material count, or repeated props changed
- technical art budget/readability evidence when premium graphics changed
- external asset sourcing ledger when premium graphics include high-value 3D or 2D asset categories
- credential probe output plus real external asset outputs or blocker evidence for premium asset-category claims
- visual scorecard before/after when the user asks for premium, AAA, showcase, or "less basic" graphics

Use the scaffold's `npm run verify:visual` and `npm run inspect:canvas` when available, or `skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs` from this repo.
