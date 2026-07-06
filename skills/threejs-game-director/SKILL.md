---
name: threejs-game-director
description: "Primary entrypoint for complete Three.js browser game creation, premium iteration, and automatic phase orchestration. Use by default for build-a-game, upgrade, polish, premium, AAA, high-fidelity, from-scratch, endless runner, arcade, action, release-ready, or showcase requests. For broad work, first load sibling public skill files for gameplay systems, AAA graphics, UI, debug/profile, and QA/release. For premium games with characters, vehicles, ships, weapons, buildings, signature props, skies, textures, decals, logos, icons, GUI art, audio/SFX/voice needs, or less-basic graphics, load threejs-3d-generator, threejs-image-generator, and/or threejs-audio-generator before deciding generated assets are unnecessary. Keep skill-loading, reference, asset-sourcing, and phase-execution ledgers so users do not choose skills manually."
---

# Three.js Game Director

## Purpose

Own the end-to-end game outcome. Build the playable loop, route through the right phases, verify evidence, and do not call prototype-quality work premium.

## Claude Compatibility Rule

Claude-style skill runners may invoke only this skill when the user runs `/threejs-game-director`. Do not claim other skills were invoked unless the runner actually invoked them. For broad work, you must still try to load the sibling public `SKILL.md` files with filesystem read tools before planning or editing, then load each phase's required reference files before that phase starts. If a sibling `SKILL.md` cannot be loaded, then use `references/director-phase-os.md` as the fallback for that phase and record the failure.

## Mandatory Sibling Skill Loading

For complete, premium, AAA, polished, high-fidelity, showcase, from-scratch, upgrade, or release-ready game work, load these sibling skill files before implementation:

- `threejs-gameplay-systems/SKILL.md`
- `threejs-aaa-graphics-builder/SKILL.md`
- `threejs-game-ui-designer/SKILL.md`
- `threejs-debug-profiler/SKILL.md`
- `threejs-qa-release/SKILL.md`

For premium, AAA, high-fidelity, showcase, complete, release-ready, or "less basic" game work, load this skill when the game includes or should include high-value 3D assets: generated 3D models, rigging, animation, textured imported assets, characters, creatures, bosses, buildings, vehicles, ships, weapons, signature props, complex pickups, or hero environment pieces. Do this before deciding whether procedural Three.js is enough:

- `threejs-3d-generator/SKILL.md`

For premium, AAA, high-fidelity, showcase, complete, release-ready, or "less basic" game work, load this skill when the game includes or should include concept/reference images, texture references, material references, skies/backgrounds, logos, marks, icons, decals, GUI art, title/menu art, terrain/sky plates, or 2D images for image-to-3D input. Do this before deciding those assets are not needed:

- `threejs-image-generator/SKILL.md`

For premium, AAA, high-fidelity, showcase, complete, release-ready, or "less basic" game work, load this skill when the game includes or should include SFX, ambience, UI sounds, interaction audio, vehicle/weapon/boss sounds, announcer/dialogue, scratch-performance voice conversion, or audio cleanup. Do this before deciding generated audio is not needed:

- `threejs-audio-generator/SKILL.md`

Try paths in this order:

1. Sibling installed path: `../<skill-name>/SKILL.md`
2. Claude default path: `~/.claude/skills/<skill-name>/SKILL.md`
3. Codex default path: `~/.codex/skills/<skill-name>/SKILL.md`
4. General agents path: `~/.agents/skills/<skill-name>/SKILL.md`
5. Repository source path: `skills/<skill-name>/SKILL.md`

If the file-read tool requires absolute paths, expand `~` to the user's home directory before reading.

For narrow director-invoked work, load the directly relevant sibling skill and `threejs-qa-release`. For broad game creation or premium iteration, load all five. Do not skip sibling loading just because this director contains a summarized phase OS.

## External Asset Sourcing Gate

Do not decide "3D generator not needed", "image generator not needed", or "audio generator not needed" before loading the relevant skill files when the trigger categories above are present.

Before claiming an API key is unavailable, run the credential probe and paste its literal output in the report:

```bash
bash <director-skill-dir>/scripts/probe_asset_credentials.sh
```

Expected output shape:

```text
TRIPO_API_KEY=SET|MISSING
GEMINI_API_KEY=SET|MISSING
ELEVENLABS_API_KEY=SET|MISSING
```

The probe sources the user's shell profiles and prints only SET/MISSING markers, never secret values. `key unavailable` is not a valid skip reason unless this probe output is shown.

For broad or premium game work, create an asset sourcing ledger before the graphics phase:

```text
External asset sourcing:
- Credential probe output:
- Hero/player:
- Enemies/vehicles/weapons:
- Signature props/pickups:
- World/sky/background:
- Materials/textures/decals:
- Logos/icons/GUI art:
- Chosen sources per surface: procedural / threejs-image-generator / threejs-3d-generator / hybrid
- 3D generator loaded: yes/no, path or blocker:
- Image generator loaded: yes/no, path or blocker:
- Audio generator loaded: yes/no/not-needed, path or blocker:
- External assets generated: yes/no, outputs or reason:
- Audio assets generated: yes/no/not-needed, outputs or reason:
```

Allowed reasons to skip actual external generation after loading the skills:

- The user explicitly requested no external AI/assets or offline-only output.
- Credential probe output shows the relevant key is `MISSING`.
- A real API/network/quota error occurs after an attempted generation command; include the command and error summary.
- The surface is a repeated low-value prop better handled by instancing/procedural kits.
- A non-hero repeated/support surface is already scoring 2+ in the visual scorecard and the asset sourcing ledger explains why external generation would not improve the active screenshot.

If the game includes vehicles, ships, characters, creatures, weapons, buildings, sky/background art, logos/icons, decals, GUI art, or audio/SFX/voice needs, `not-needed` is not a valid ledger entry until the relevant generator skill has been loaded and the asset sourcing ledger explains the tradeoff. For premium claims, at least one high-value visual asset surface should use `threejs-image-generator`, `threejs-3d-generator`, or a documented hybrid unless an allowed skip reason blocks it.

For premium claims with hero surfaces such as player, enemy, boss, creature, vehicle, ship, weapon, building, or signature prop, procedural-only is not an allowed final answer unless the credential probe or attempted generation shows a real blocker. At least one hero/high-value asset must have real external evidence: a 3D generator task ID, downloaded GLB/GLTF/FBX path, image generator output path, or documented hybrid chain. For premium claims that include active gameplay, audio-only omission must be reported as a remaining gap unless the user explicitly asked for silent/offline output or `ELEVENLABS_API_KEY` is blocked.

## Mandatory Reference Gate

References are not optional enrichment. They are phase-entry gates. For broad game creation, premium/AAA/showcase/polish requests, release-ready work, or any task that claims high visual quality, load the applicable reference files before implementation in that phase.

Required phase references:

- Gameplay systems: `threejs-gameplay-systems/references/gameplay-workflows.md`
- Game design and level design, for broad new-game creation, major gameplay upgrades, level/arena/track/wave/hole/puzzle work, encounter design, progression/difficulty work, or premium gameplay claims: `threejs-gameplay-systems/references/game-design-level-design.md`
- Physics selection, when physics/collision-heavy gameplay is in scope: `threejs-gameplay-systems/references/physics-engine-selection.md`
- New game completion checklist, when creating a game or first playable slice: `threejs-gameplay-systems/references/checklists/new-game-definition-of-done.md`
- Game design and level design checklist, when creating a game, upgrading major gameplay, designing levels/encounters, or claiming premium gameplay: `threejs-gameplay-systems/references/checklists/game-design-level-design.md`
- Endless runner checklist, when building or upgrading an endless runner: `threejs-gameplay-systems/references/checklists/endless-runner-premium-quality.md`
- AAA graphics: `threejs-aaa-graphics-builder/references/visual-scorecard.md`
- AAA graphics: `threejs-aaa-graphics-builder/references/implementation-blueprint.md`
- AAA graphics: `threejs-aaa-graphics-builder/references/model-recipes.md`
- AAA graphics: `threejs-aaa-graphics-builder/references/render-recipes.md`
- Technical art, for premium/AAA/showcase graphics, shaders/material systems, VFX systems, generated/imported asset cleanup, LOD/instancing, or visual performance work: `threejs-aaa-graphics-builder/references/technical-art.md`
- AAA graphics checklists, for premium/AAA/showcase claims: `threejs-aaa-graphics-builder/references/checklists/aaa-game-quality-gate.md` and `threejs-aaa-graphics-builder/references/checklists/aaa-visual-scorecard.md`
- Technical art checklist, for premium/AAA/showcase graphics or visual performance claims: `threejs-aaa-graphics-builder/references/checklists/technical-art-quality.md`
- UI: `threejs-game-ui-designer/references/ui-patterns.md`
- UI checklists, when UI/HUD/menu/touch layout is in scope: `threejs-game-ui-designer/references/checklists/game-ui-quality.md`, `threejs-game-ui-designer/references/checklists/hud-readability.md`, and `threejs-game-ui-designer/references/checklists/responsive-ui-fit.md`
- Debug/profile: `threejs-debug-profiler/references/debug-profile-checklists.md`
- Debug/profile checklists, when debugging or profiling: `threejs-debug-profiler/references/checklists/scene-debugging.md` or `threejs-debug-profiler/references/checklists/performance-profile.md`
- QA/release: `threejs-qa-release/references/qa-release-checklists.md`
- QA/release checklists, for final verification: `threejs-qa-release/references/checklists/visual-verification.md`, `threejs-qa-release/references/checklists/playtest-qa.md`, and `threejs-qa-release/references/checklists/release.md`
- Visual test harness, when premium/release-ready visual QA, generated asset visibility, UI regression protection, or screenshot baselines are warranted: `threejs-qa-release/references/visual-test-harness.md` and `threejs-qa-release/references/checklists/visual-test-harness.md`
- 3D generator, when loaded by the external asset sourcing gate: `threejs-3d-generator/references/api-notes.md`
- 3D generator, when loaded for a game: `threejs-3d-generator/references/threejs-integration.md`
- 3D plus image generator, when both are loaded: `threejs-3d-generator/references/image-generator-workflows.md`
- Audio generator, when loaded for a game: `threejs-audio-generator/references/audio-workflows.md`

Prompt templates are packaged in `references/prompt-templates.md` under the director and relevant sibling skills. Load them only when the user asks for a reusable prompt or task template.

Try reference paths in this order:

1. Relative to the loaded skill path: `<loaded-skill-dir>/references/<file>.md`
2. Claude default path: `~/.claude/skills/<skill-name>/references/<file>.md`
3. Codex default path: `~/.codex/skills/<skill-name>/references/<file>.md`
4. General agents path: `~/.agents/skills/<skill-name>/references/<file>.md`
5. Repository source path: `skills/<skill-name>/references/<file>.md`

Rules:

- Load references at phase entry, not at the end.
- Track every required reference in the reference ledger with yes/no, path, and failure reason.
- A phase cannot be marked `done` until its required references are loaded or the final answer explicitly reports the reference as unavailable and the phase as blocked/fallback.
- For premium/AAA/showcase claims, the final response must include the filled 10-category visual scorecard from `visual-scorecard.md`, including average and automatic failures remaining.
- For broad work, include the phase checklist outputs from each relevant reference, not just a summary that the game works.
- Thorough mode is the default for broad, premium, AAA, showcase, complete, and release-ready requests. Economy mode is allowed only for narrow fixes that do not claim premium quality.

If Task/subagent/workflow tools are available, delegate each major phase to a focused worker with the phase `SKILL.md` plus its required references explicitly loaded. If those tools are unavailable, execute serially after the same reference files have been loaded.

## Ledgers

Track both skill loading and phase execution:

- Director: active
- Sibling skills loaded:
  - Gameplay systems: yes/no, path or reason:
  - AAA graphics: yes/no, path or reason:
  - UI: yes/no, path or reason:
  - Debug/profile: yes/no, path or reason:
  - QA/release: yes/no, path or reason:
  - 3D generator: yes/no/not-needed, path or reason:
  - Image generator: yes/no/not-needed, path or reason:
  - Audio generator: yes/no/not-needed, path or reason:
- External asset sourcing:
  - Credential probe output:
  - Hero/player source:
  - Enemies/vehicles/weapons source:
  - Signature props/pickups source:
  - World/sky/background source:
  - Materials/textures/decals source:
  - Logos/icons/GUI art source:
  - Audio/SFX/voice source:
  - External assets generated or skip reason:
  - Audio assets generated or skip reason:
- Required references loaded:
  - Gameplay workflows: yes/no/not-needed, path or reason:
  - Game design and level design: yes/no/not-needed, path or reason:
  - Physics engine selection: yes/no/not-needed, path or reason:
  - Gameplay/new-game checklists: yes/no/not-needed, path or reason:
  - Gameplay design/level checklist: yes/no/not-needed, path or reason:
  - Visual scorecard: yes/no/not-needed, path or reason:
  - Graphics implementation blueprint: yes/no/not-needed, path or reason:
  - Model recipes: yes/no/not-needed, path or reason:
  - Render recipes: yes/no/not-needed, path or reason:
  - Technical art: yes/no/not-needed, path or reason:
  - Graphics checklists: yes/no/not-needed, path or reason:
  - Technical art checklist: yes/no/not-needed, path or reason:
  - UI patterns: yes/no/not-needed, path or reason:
  - UI checklists: yes/no/not-needed, path or reason:
  - Debug/profile checklists: yes/no/not-needed, path or reason:
  - QA/release checklists: yes/no/not-needed, path or reason:
  - Visual test harness: yes/no/not-needed, path or reason:
  - 3D generator API notes: yes/no/not-needed, path or reason:
  - 3D generator Three.js integration: yes/no/not-needed, path or reason:
  - 3D/image generator workflows: yes/no/not-needed, path or reason:
  - Audio workflows: yes/no/not-needed, path or reason:
- Gameplay systems: pending/running/done/skipped, evidence:
- External asset sourcing: pending/running/done/skipped, evidence:
- AAA graphics: pending/running/done/skipped, evidence:
- UI: pending/running/done/skipped, evidence:
- Debug/profile: pending/running/done/skipped, evidence:
- QA/release: pending/running/done/skipped, evidence:

A phase is done only with implementation plus verification evidence.

## Phase Routing

- `threejs-gameplay-systems`: first playable slice, architecture, mechanics, entities, input, camera, controls, game feel.
- Game design and level design: design brief, player promise, core loop contract, level/arena/track/wave/hole/puzzle plan, encounter pacing, difficulty curve, tuning constants, and fun-factor rejection tests. This runs before implementation for broad game builds.
- Physics selection: engine choice, fixed timestep, collider strategy, sensors, collision proxies, CCD, diagnostics, and QA for physics-heavy games.
- External asset sourcing: credential probe, generator skill loading, asset source decision, task IDs/output files or blocker evidence. This phase must be done before `threejs-aaa-graphics-builder` can be marked done for premium graphics work.
- `threejs-aaa-graphics-builder`: basic-looking screenshots, asset architecture, models, materials, technical art, VFX, lighting/render, visual scorecard.
- `threejs-game-ui-designer`: HUDs, menus, overlays, responsive UI, icons, safe areas, UI states.
- `threejs-debug-profiler`: blank canvas, render/runtime bugs, loading, resize, mobile input/render bugs, performance profiling.
- `threejs-qa-release`: browser QA, screenshots, canvas pixels, responsive checks, visual test harness decision, production build, preview, release notes.
- `threejs-3d-generator`: external AI-generated models, GLB/FBX outputs, text/image-to-3D, texturing, auto-rigging, animation, conversion.
- `threejs-image-generator`: 2D concept/reference images, image-to-model inputs, textures, sky/backgrounds, logos, icons, GUI elements, decals.
- `threejs-audio-generator`: generated SFX, looping ambience, UI sounds, voice/TTS, voice conversion, cleanup/isolation, and game audio runtime planning.

If a sibling skill file is loaded, follow its workflow for that phase. If it is unavailable, record the missing path/reason and use `references/director-phase-os.md` for that phase.

## Packaged Runtime Resources

For new projects, use the gameplay skill's packaged scaffold creator:

```bash
python3 <threejs-gameplay-systems-skill-dir>/scripts/create_threejs_game.py ./my-game
```

For canvas inspection, use the generated game's `npm run inspect:canvas` when available, or the QA skill's packaged inspector:

```bash
node <threejs-qa-release-skill-dir>/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188
```

## Premium Completion Rule

For premium, AAA, polished, complete, release-ready, or showcase requests, completion requires visible quality across gameplay, hero/player, obstacles/enemies, rewards/interactables, world kit, HUD/menu states, render/lighting/materials, feel, performance/mobile, and QA.

If screenshots are dominated by primitives, flat roads/arenas, generic stat cards, sparse worlds, or glow-only detail, the task is not done.

The scorecard must use the exact categories from `threejs-aaa-graphics-builder/references/visual-scorecard.md`: Art direction, Hero/player, Obstacles/enemies, Rewards/interactables, World/environment, Materials/textures, Lighting/render, VFX/motion, UI/HUD, and Performance evidence. Do not substitute a personal rubric.

## Required Verification

- Build/typecheck.
- Local browser run.
- Console/page error check.
- Game design brief and level/encounter plan for broad game creation or major gameplay changes.
- Active desktop and mobile screenshots.
- Nonblank canvas pixel evidence.
- Main input/objective/fail or restart path.
- Visual scorecard for premium/AAA claims.
- External asset sourcing ledger for premium/AAA or less-basic graphics claims.
- Credential probe output and real external asset outputs or blocker evidence for premium/AAA asset-category claims.
- Audio matrix/generated audio evidence or a reported blocker for premium active gameplay claims.
- Renderer diagnostics when graphics changed.
- Technical art budget and VFX/readability evidence when premium graphics changed.
- Visual test harness decision for premium/release-ready UI, generated asset, or visual regression risk.
- Final ledger with evidence and remaining blockers.

## Report Audit

When shell tools are available, draft the final evidence report to a temporary markdown file and run the director audit before finalizing broad or premium work:

```bash
python3 <director-skill-dir>/scripts/audit_reference_report.py --premium /path/to/final-report.md
```

Use `--premium` for premium, AAA, showcase, high-fidelity, polished, complete, release-ready, or "less basic" claims. Add `--physics` for physics-heavy games such as pool/snooker, mini-golf, pinball, marble racers, physics puzzles, rigid-body games, or games with many sensors/colliders. Add `--audio` when generated or integrated audio is in scope, and for premium active-gameplay claims unless the user requested silent/offline-only output. If the audit fails, fix the missing report sections or state the exact blocker instead of claiming completion. If the script is unavailable, manually enforce the same required sections: skill-loading ledger, reference ledger, game design brief, core loop contract, level/encounter plan, external asset/audio sourcing ledger, technical art budget, visual harness decision, phase checklist, visual scorecard, physics/audio diagnostics when relevant, verification evidence, and remaining risks.

## Final Response

Report the skill-loading ledger, reference ledger, game design brief, core loop contract, level/encounter plan, external asset sourcing ledger, phase ledger, files changed, run URL, controls, verification commands, screenshots/artifacts, renderer/performance notes, technical art budget, visual test harness decision, quality gates passed, skipped phases, and remaining risks. For premium/AAA/showcase claims, include the filled visual scorecard and automatic failures remaining. Be precise: "invoked" means a slash/tool skill invocation; "loaded" means the `SKILL.md` or reference file was read into context; "executed phase" means the work was performed under either loaded skill guidance or the director fallback.
