# Director Phase Playbook

The canonical phase specification for `threejs-game-director`. Load this file at planning time for broad work. When a sibling skill file is loaded, that sibling owns its phase's workflow and this file supplies phase entry/exit evidence, ledger templates, and gate details. When a sibling `SKILL.md` cannot be loaded, the matching phase section here is the fallback procedure — record the missing path and reason in the ledger; the fallback is never a reason to skip attempting sibling loading first.

Path resolution for every file named here uses the Skill Path Ladder in `threejs-game-director/SKILL.md`.

## Non-Negotiable Rules

- Do not claim another skill was invoked unless the runner actually invoked it; "loaded" means its file was read into context.
- Broad game builds start with a compact game design brief, core loop contract, and level/encounter plan before implementation.
- Load each phase's required reference files at phase entry, not at final judgment. A phase cannot be `done` if its required references were skipped.
- Record an external asset sourcing ledger before the graphics phase; run the credential probe before claiming any generator key is unavailable.
- Premium graphics phases include a technical-art budget and readability pass, not only visual polish.
- QA phases decide whether a visual test harness is warranted and report added/extended/skipped evidence.
- A broad request is not complete at first playable slice when the user asked for premium, AAA, polished, showcase, complete, release-ready, or "less basic".
- Prefer a small authored vertical slice over a larger placeholder scene. Treat primitive-dominant models, box skylines, flat arenas, generic stat-card HUDs, and glow/fog-only detail as prototype placeholders.
- Verify through browser evidence before calling the game done.

## Ledger Templates

Compaction rule (from `SKILL.md`): report every row with meaningful state; collapse consecutive `not-needed` rows into one line naming them.

```text
Skill-loading ledger:
- Director: active
- Gameplay systems: yes/no, path or reason:
- AAA graphics: yes/no, path or reason:
- UI: yes/no, path or reason:
- Debug/profile: yes/no, path or reason:
- QA/release: yes/no, path or reason:
- 3D generator: yes/no/not-needed, path or reason:
- Image generator: yes/no/not-needed, path or reason:
- Audio generator: yes/no/not-needed, path or reason:

External asset sourcing ledger:
- Credential probe output:
- Hero/player source:
- Enemies/vehicles/weapons source:
- Signature props/pickups source:
- World/sky/background source:
- Materials/textures/decals source:
- Logos/icons/GUI art source:
- Audio/SFX/voice source:
- Chosen sources per surface: procedural / threejs-image-generator / threejs-3d-generator / threejs-audio-generator / hybrid
- External assets generated: yes/no, outputs (task IDs / file paths) or skip reason:
- Audio assets generated: yes/no/not-needed, outputs or skip reason:

Reference ledger: one yes/no/not-needed row with path or reason per required
reference that applies to the task (see Required References below).

Phase ledger:
- Gameplay systems: pending/running/done/skipped - evidence:
- External asset sourcing: pending/running/done/skipped - evidence:
- AAA graphics: pending/running/done/skipped - evidence:
- UI: pending/running/done/skipped - evidence:
- Debug/profile: pending/running/done/skipped - evidence:
- QA/release: pending/running/done/skipped - evidence:
```

Mark a phase `done` only after implementation plus verification evidence. If a phase is skipped, state why it is out of scope or blocked.

## Allowed External-Generation Skip Reasons

After the relevant generator skills are loaded, actual external generation may be skipped only when:

- The user explicitly requested no external AI/assets or offline-only output.
- Credential probe output shows the relevant key is `MISSING`.
- A real API/network/quota error occurs after an attempted generation command; include the command and error summary.
- The surface is a repeated low-value prop better handled by instancing/procedural kits.
- A non-hero repeated/support surface already scores 2+ and the ledger explains why external generation would not improve the active screenshot.

Do not write `not-needed` for a generator skill before loading it when trigger surfaces are present. The hero-surface evidence rule is in `threejs-game-director/SKILL.md` (External Asset Sourcing Gate).

## Required References

Load these files before the matching phase starts:

- Gameplay systems: `threejs-gameplay-systems/references/gameplay-workflows.md`
- Game design and level design, for broad new-game creation, major gameplay upgrades, level/arena/track/wave/hole/puzzle work, encounter design, progression/difficulty work, or premium gameplay claims: `threejs-gameplay-systems/references/game-design-level-design.md`
- Game feel, for feel/juice/impact tuning or any premium/polished gameplay claim: `threejs-gameplay-systems/references/game-feel.md`
- Physics selection, when physics/collision-heavy gameplay is in scope: `threejs-gameplay-systems/references/physics-engine-selection.md`
- New-game checklist, when creating a game or first playable slice: `threejs-gameplay-systems/references/checklists/new-game-definition-of-done.md`
- Game design and level design checklist, when creating a game, upgrading major gameplay, designing levels/encounters, or claiming premium gameplay: `threejs-gameplay-systems/references/checklists/game-design-level-design.md`
- Game feel checklist, when tuning feel or claiming premium gameplay: `threejs-gameplay-systems/references/checklists/game-feel.md`
- Endless runner checklist, when building or upgrading an endless runner: `threejs-gameplay-systems/references/checklists/endless-runner-premium-quality.md`
- AAA graphics, for any graphics phase: `threejs-aaa-graphics-builder/references/visual-scorecard.md`, `threejs-aaa-graphics-builder/references/implementation-blueprint.md`, `threejs-aaa-graphics-builder/references/model-recipes.md`, and `threejs-aaa-graphics-builder/references/render-recipes.md`
- Shader and material cookbook, for premium/AAA/showcase graphics or custom shader/material/post-processing work: `threejs-aaa-graphics-builder/references/shader-cookbook.md`
- Technical art, for premium/AAA/showcase graphics, shaders/material systems, VFX systems, generated/imported asset cleanup, LOD/instancing, or visual performance work: `threejs-aaa-graphics-builder/references/technical-art.md`
- AAA graphics checklists, for premium/AAA/showcase claims: `threejs-aaa-graphics-builder/references/checklists/aaa-game-quality-gate.md` and `threejs-aaa-graphics-builder/references/checklists/aaa-visual-scorecard.md`
- Technical art checklist, for premium/AAA/showcase graphics or visual performance claims: `threejs-aaa-graphics-builder/references/checklists/technical-art-quality.md`
- UI: `threejs-game-ui-designer/references/ui-patterns.md`
- UI checklists, when UI/HUD/menu/touch layout is in scope: `threejs-game-ui-designer/references/checklists/game-ui-quality.md`, `threejs-game-ui-designer/references/checklists/hud-readability.md`, and `threejs-game-ui-designer/references/checklists/responsive-ui-fit.md`
- Debug/profile: `threejs-debug-profiler/references/debug-profile-checklists.md`, plus `threejs-debug-profiler/references/checklists/scene-debugging.md` or `threejs-debug-profiler/references/checklists/performance-profile.md` when debugging or profiling
- QA/release: `threejs-qa-release/references/qa-release-checklists.md`, plus for final verification `threejs-qa-release/references/checklists/visual-verification.md`, `threejs-qa-release/references/checklists/playtest-qa.md`, and `threejs-qa-release/references/checklists/release.md`
- Visual test harness, when premium/release-ready visual QA, generated asset visibility, UI regression protection, or screenshot baselines are warranted: `threejs-qa-release/references/visual-test-harness.md` and `threejs-qa-release/references/checklists/visual-test-harness.md`
- Bot playtest, for release-ready gameplay claims or difficulty/fairness verification: `threejs-qa-release/references/playtest-bot.md` and `threejs-qa-release/references/checklists/bot-playtest.md`
- 3D generator, when loaded by the external asset sourcing gate: `threejs-3d-generator/references/api-notes.md` and `threejs-3d-generator/references/threejs-integration.md`
- 3D plus image generator, when both are loaded: `threejs-3d-generator/references/image-generator-workflows.md`
- Audio generator, when loaded for a game: `threejs-audio-generator/references/audio-workflows.md`

Prompt templates are packaged in `references/prompt-templates.md` under the director and relevant sibling skills. Load them only when the user asks for a reusable prompt or task template.

## Phase 1: Discovery And Playable Contract

- Inspect package scripts, dependencies, app structure, renderer setup, loop ownership, input, camera, UI, diagnostics, and existing screenshots.
- Define the design brief: player promise, target feeling, primary verb, objective, pressure, reward/progression, fail/retry, skill expression, and non-goals.
- Define the core loop contract: player verb, objective, pressure, reward, fail state, restart.
- Define the first level/encounter plan: spatial format, player start, first decision, first threat, first reward, landmarks, escalation, recovery beats, and readability.
- Define target devices and performance budget. If absent, assume desktop plus mobile browser, WebGL/WebGL2 fallback, and capped DPR.
- Identify the highest-risk surfaces: blank/broken canvas, no playable loop, weak controls, basic graphics, unreadable UI, or unverified release.

Exit evidence: current scripts/dependencies known; game design brief, core loop contract, and level/encounter plan stated; phase ledger initialized.

For a new project, use the gameplay skill's packaged scaffold creator:

```bash
python3 <threejs-gameplay-systems-skill-dir>/scripts/create_threejs_game.py ./my-game
```

## Phase 2: Gameplay Systems

Build or repair the playable loop before visual depth.

- Add renderer, scene, camera, resize, update loop, input intents, state machine, entities, collision or physics, scoring/progression, fail/retry, HUD state, audio/VFX hooks, and diagnostics.
- Implement from the design brief and level/encounter plan. Do not bolt mechanics onto a static scene after the fact. If the level/arena/track is decorative rather than decision-shaping, return to the plan before adding art.
- If the game is physics-heavy, load the physics selection reference, choose an engine explicitly, and prefer Rapier unless the task fits custom collision or a small cannon-es fallback.
- Keep ownership boundaries clear: `core`, `game`, `entities`, `systems`, `assets`, `ui`, `tests`.
- Tune movement, camera follow, FOV, acceleration, cooldowns, difficulty, and restart through short play loops. Apply the game-feel reference (hitstop, screenshake, easing, impact feedback) for premium/polished gameplay claims.
- Keep collision proxies simpler than detailed meshes; avoid multiple animation loops, duplicated state, and per-frame allocations in hot paths.
- Route all gameplay randomness through the scaffold's seeded RNG so the deterministic test hooks keep working.

Exit evidence: build/typecheck passes; browser opens with nonblank canvas; main control path changes state; objective or score progresses; fail/retry path exists when relevant; game design/level checklist outcome reported for broad builds; game-feel checklist outcome reported for premium gameplay claims; physics engine choice, timestep, collider strategy, and diagnostics reported when physics is in scope; new-game checklist outcome reported for new games.

## Phase 3: External Asset Sourcing

Run before the premium graphics pass when trigger surfaces exist.

- Run the credential probe and paste output.
- Load `threejs-3d-generator`, `threejs-image-generator`, and/or `threejs-audio-generator` when their trigger surfaces exist, plus their required references.
- Decide source per high-value surface: procedural / threejs-image-generator / threejs-3d-generator / threejs-audio-generator / hybrid.
- Generate at least one high-value external output for premium hero surfaces unless the probe or an attempted generation shows a real blocker.
- Record task IDs, downloaded GLB/GLTF/FBX paths, image/audio output paths, or blocker evidence.

Exit evidence: credential probe output; generator rows in the skill-loading and reference ledgers; filled asset sourcing ledger; external outputs or blocker evidence.

## Phase 4: AAA Graphics

Use when screenshots look basic or the user asks for premium quality.

- Score active-play screenshots across the ten scorecard categories before and after.
- Add production graphics architecture: material library, procedural textures, decals, model factories, world prop kit, VFX system, lighting/render pipeline, diagnostics.
- Add technical art architecture: material kit, shader/VFX purpose, instancing/LOD/culling strategy, imported asset cleanup plan, render budget with numeric targets, and mobile DPR/shadow/post tradeoffs.
- Use the shader cookbook for custom material/shader/post work instead of improvising unproven effects.
- Upgrade all visible surfaces, not only the player: hero, hazards, rewards, ground/track/arena, foreground props, background layers, interactable telegraphs, material variation, and state VFX.
- Use the generator skills per the asset sourcing ledger; complete Phase 3 before deciding procedural code is enough.
- Build authored forms (bevels, extrusions, curves, tubes, lathes, custom geometry, decals, trim, panel lines, instanced repeats, collision proxies) before adding lighting, tone mapping, shadows, fog, and post-processing.

Exit evidence: before/after scorecard with all ten categories, average, and automatic failures remaining; measured evidence from canvas-inspector metrics (draw calls, triangles, pixel statistics) cited for the categories they support; active desktop and mobile screenshots; renderer diagnostics; technical art budget target vs actuals; imported asset diagnostics (task IDs, file paths, scale/bounds, collision proxy, animation clips) when generated 3D was used; no scorecard category below 2 for premium claims.

## Phase 5: UI

Use when HUD/menu/interface craft affects quality or readability.

- Inventory gameplay, pause, settings, fail/retry, milestone/win, loading/error, and touch states.
- Replace utility stat-card grids with game-specific meters, compact clusters, icons, badges, alerts, cooldown rings, reticles, diegetic labels, and stateful overlays.
- Use stable dimensions, safe-area padding, fixed-width numeric fields, text fit, and responsive constraints.
- Wire UI to game state; avoid duplicated game rules inside UI code. UI must never block the player, threats, pickups, next decision, or critical touch controls.

Exit evidence: desktop and mobile screenshots for relevant states; text-fit and overlap check; touch target and safe-area check when mobile is in scope; UI checklist outcomes.

## Phase 6: Debug And Profile

Use whenever the canvas is blank/broken, interaction fails, mobile behavior breaks, or visual changes add cost.

- Reproduce locally and read console/page/network errors.
- Check canvas CSS size and drawing-buffer size, renderer/context, loop ownership, camera, near/far, lights, fog, transforms, materials, loaders, asset paths, and resize behavior.
- For performance, measure production preview where possible: FPS/frame time, draw calls, triangles, geometries, materials, textures, memory, bundle, and expensive post/shadows.
- Optimize one bottleneck at a time using instancing, shared resources, culling, LOD, pooling, adaptive DPR, cheaper shadows/post, and explicit disposal.

Exit evidence: root cause or measured bottleneck stated; baseline/post metrics when optimizing; broken path retested.

## Phase 7: QA And Release

Use before calling broad work complete.

- Run build/typecheck; start dev or preview server; check console/page/network errors.
- Capture active desktop and mobile screenshots; sample canvas pixels for nonblank and varied output using the generated game's `npm run inspect:canvas` or:

```bash
node <threejs-qa-release-skill-dir>/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188
```

- Trigger main input, objective progression, fail/retry, and recent risky paths.
- Verify HUD text fit, safe areas, touch targets, resize, and mobile input.
- Decide whether to add or extend a visual test harness (Playwright screenshot baselines with deterministic test hooks); report added/extended/skipped.
- Run the bot playtest for release-ready gameplay claims; report time-to-first-fail, progression, and softlock evidence.
- For premium/AAA claims, run the fresh-eyes scorecard review per `threejs-aaa-graphics-builder/references/visual-scorecard.md`.
- For release, verify production preview, base path, static assets, debug gating, bundle/large assets, and deployment assumptions.

Exit evidence: commands run with pass/fail; URL used; screenshot/artifact paths; inspector metrics JSON; visual test harness decision with states covered, thresholds, and flake risks; bot playtest results when run; issues fixed or listed with owners; residual risks.

## Completion Gate

For premium/AAA/showcase claims, all of these must be true:

- Skill-loading, reference, and external asset sourcing ledgers are present.
- Credential probe output plus external output evidence or blocker evidence is present for premium asset-category claims.
- Playable loop works through real input; game design brief, core loop contract, and level/encounter plan are reported for broad builds.
- Active-play screenshots exist for desktop and mobile.
- Visual scorecard uses the authored rubric, cites measured evidence, has no category below 2, and averages at least 2.3.
- A fresh-eyes review pass confirmed or corrected the scorecard (subagent review, or the adversarial self-review fallback).
- HUD/menu states are readable and responsive.
- Renderer diagnostics and technical art budget target-vs-actuals exist after graphics changes.
- Visual test harness decision is reported; bot playtest evidence exists for release-ready gameplay claims.
- Build and browser QA passed or blockers are clearly reported.
- Physics-heavy games include engine choice, timestep, collider strategy, sensors, CCD use, and body/collider diagnostics.

If any gate fails, continue iterating or report the exact blocker instead of calling the game premium.
