---
name: threejs-game-director
description: "Primary entrypoint for complete Three.js browser game creation and premium iteration. Use by default for build-a-game, upgrade, polish, premium, AAA, high-fidelity, showcase, from-scratch, endless runner, arcade, action, or release-ready requests. Orchestrates sibling skills for gameplay, AAA graphics, UI, debug/profile, and QA/release, plus 3D/image/audio generators for characters, vehicles, weapons, buildings, props, skies, textures, logos, icons, GUI art, and SFX/voice. Keeps skill-loading, reference, asset-sourcing, and phase ledgers so users never choose skills manually."
---

# Three.js Game Director

## Purpose

Own the end-to-end game outcome. Build the playable loop, route through the right phases, verify evidence, and do not call prototype-quality work premium. "Less basic" from the user means the current visual level is rejected: treat it as the premium bar.

## Runner Capability Check

Before planning, note what this runner can do and adapt:

1. **Invoke sibling skills directly?** Usually not — the runner invokes only this skill. Load sibling `SKILL.md` files with file-read tools instead. Never claim a skill was "invoked" when it was only loaded/read.
2. **Read files by path?** Resolve every skill and reference path through the path ladder below. If a required file cannot be read anywhere on the ladder, record the failure in the ledger and use `references/phase-playbook.md` as the fallback procedure for that phase.
3. **Run shell commands (node + python3)?** If yes, use the packaged scripts (scaffold creator, credential probe, canvas inspector, report audit). If not, ask the user to run each command and paste the output; never fabricate script output.
4. **Drive a browser / run Playwright?** If yes, capture screenshots and canvas inspection yourself. If not, ask the user to run `npm run verify:visual` and `npm run inspect:canvas` and paste the results; report unverified visuals as a residual risk, never as verified.

### Skill Path Ladder

Try in order, expanding `~` to the user's home directory when the read tool requires absolute paths:

1. `../<skill-name>/SKILL.md` relative to this skill's directory
2. `~/.claude/skills/<skill-name>/SKILL.md`
3. `~/.codex/skills/<skill-name>/SKILL.md`
4. `~/.agents/skills/<skill-name>/SKILL.md`
5. `skills/<skill-name>/SKILL.md` in the repository source

Reference files resolve the same way: `<skill-dir>/references/<file>.md`. Sibling skills point back to this ladder instead of restating it.

## Sibling Skill Loading

For broad work (complete, premium, AAA, polished, high-fidelity, showcase, from-scratch, upgrade, release-ready), load all five phase skills before implementation: `threejs-gameplay-systems`, `threejs-aaa-graphics-builder`, `threejs-game-ui-designer`, `threejs-debug-profiler`, `threejs-qa-release`. For narrow director-invoked work, load the directly relevant sibling plus `threejs-qa-release`. Do not skip sibling loading because this director bundles a phase playbook.

Load generator skills before deciding generated assets are unnecessary, whenever their trigger surfaces exist in premium/AAA/showcase/complete/release-ready/"less basic" work:

- `threejs-3d-generator/SKILL.md` — characters, creatures, bosses, vehicles, ships, weapons, buildings, signature props, complex pickups, hero environment pieces, rigging/animation, textured imports.
- `threejs-image-generator/SKILL.md` — concept/reference sheets, texture and material references, skies/backgrounds, logos, icons, decals, GUI/title/menu art, terrain/sky plates, image-to-3D inputs.
- `threejs-audio-generator/SKILL.md` — SFX, ambience, UI sounds, vehicle/weapon/boss audio, announcer/dialogue, voice conversion, audio cleanup.

## External Asset Sourcing Gate

- Never record "not-needed" for a generator before loading its `SKILL.md` when trigger surfaces exist.
- Before claiming an API key is unavailable, run the credential probe and paste its literal `KEY=SET|MISSING` output into the report. Each generator script also has its own `probe` subcommand.

```bash
bash <director-skill-dir>/scripts/probe_asset_credentials.sh
```

- For premium hero surfaces (player, enemy, boss, creature, vehicle, ship, weapon, building, signature prop), procedural-only is not an allowed final answer without real blocker evidence: a `MISSING` probe line, or an attempted generation command plus its API/network/quota error. Otherwise at least one high-value surface must show a 3D generator task ID, downloaded GLB/GLTF/FBX path, image generator output path, or documented hybrid chain.
- For premium active gameplay, missing audio is a reported gap unless the user asked for silent/offline output or the audio key/API is blocked.
- Fill the external asset sourcing ledger before the graphics phase. The ledger template and the allowed skip reasons live in `references/phase-playbook.md`.

## Reference Gate

References are phase-entry gates, not optional enrichment. The canonical per-phase Required References list lives in `references/phase-playbook.md`; load that file at planning time for broad work and at phase entry otherwise.

- Load required references at phase entry, not at the end.
- Track every required reference in the reference ledger with yes/no/not-needed, path, and failure reason.
- A phase cannot be marked `done` until its required references are loaded, or the final answer reports the reference as unavailable and the phase as blocked/fallback.
- For premium/AAA/showcase claims, the final response must include the filled 10-category visual scorecard from `threejs-aaa-graphics-builder/references/visual-scorecard.md`, including measured evidence, average, and automatic failures remaining. Do not substitute a personal rubric.
- Thorough mode is the default for broad, premium, AAA, showcase, complete, and release-ready requests. Economy mode is allowed only for narrow fixes that do not claim premium quality.

If Task/subagent/workflow tools are available, delegate each major phase to a focused worker with the phase `SKILL.md` plus its required references explicitly loaded. If unavailable, execute serially after loading the same files.

## Ledgers

Keep four ledgers: skill-loading, reference, external asset sourcing, and phase execution. Templates live in `references/phase-playbook.md`.

Compaction rule: report every row that has meaningful state (yes/no/blocked/done/skipped plus path or evidence), and collapse consecutive `not-needed` rows into a single line naming them. Never omit or compress rows that carry real state.

## Phase Routing

- `threejs-gameplay-systems`: design brief, core loop contract, level/encounter plan, first playable slice, architecture, mechanics, entities, input, camera, physics selection, game feel.
- External asset sourcing: credential probe, generator skill loading, source decision per surface, task IDs/output files or blocker evidence. Must complete before the graphics phase is `done` for premium work.
- `threejs-aaa-graphics-builder`: basic-looking screenshots, asset architecture, models, materials, technical art, shaders, VFX, lighting/render, visual scorecard.
- `threejs-game-ui-designer`: HUDs, menus, overlays, responsive UI, icons, safe areas, UI states.
- `threejs-debug-profiler`: blank canvas, render/runtime bugs, loading, resize, mobile input/render bugs, performance profiling.
- `threejs-qa-release`: browser QA, screenshots, canvas pixels, responsive checks, visual test harness decision, bot playtest, production build, preview, release notes.
- `threejs-3d-generator` / `threejs-image-generator` / `threejs-audio-generator`: external AI-generated 3D models and rigs, 2D concepts/textures/logos/GUI art, and SFX/ambience/voice.

When a sibling skill file is loaded, follow its workflow for that phase. Phase entry/exit evidence, ledger templates, and the fallback procedure for unloadable siblings all live in `references/phase-playbook.md`.

## Packaged Runtime Resources

New projects use the gameplay skill's scaffold creator; canvas verification uses the generated game's `npm run inspect:canvas` or the QA skill's packaged inspector:

```bash
python3 <threejs-gameplay-systems-skill-dir>/scripts/create_threejs_game.py ./my-game
node <threejs-qa-release-skill-dir>/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188
```

## Premium Completion Rule

Premium, AAA, polished, complete, release-ready, and showcase requests require visible quality across gameplay, hero/player, obstacles/enemies, rewards/interactables, world kit, HUD/menu states, render/lighting/materials, feel, performance/mobile, and QA. If screenshots are dominated by primitives, flat roads/arenas, generic stat cards, sparse worlds, or glow-only detail, the task is not done. The full completion gate is in `references/phase-playbook.md`.

## Required Verification

- Build/typecheck; local browser run; console/page error check.
- Game design brief, core loop contract, and level/encounter plan for broad game creation or major gameplay changes.
- Active desktop and mobile screenshots plus nonblank canvas pixel evidence.
- Main input/objective/fail-or-restart path exercised.
- Visual scorecard with measured evidence for premium/AAA claims, plus a fresh-eyes review pass per `threejs-aaa-graphics-builder/references/visual-scorecard.md`.
- External asset sourcing ledger, credential probe output, and real external outputs or blocker evidence for premium asset-category claims.
- Audio evidence or a reported blocker for premium active-gameplay claims.
- Renderer diagnostics when graphics changed; technical art budget and VFX/readability evidence when premium graphics changed.
- Visual test harness decision, and bot playtest evidence when release-ready gameplay is claimed.
- Final ledgers with evidence and remaining blockers.

## Report Audit

When shell tools are available, draft the final evidence report to a markdown file and audit it before finalizing broad or premium work:

```bash
python3 <director-skill-dir>/scripts/audit_reference_report.py --premium /path/to/final-report.md
```

Use `--premium` for premium/AAA/showcase/high-fidelity/polished/complete/release-ready/"less basic" claims; add `--physics` for physics-heavy games; add `--audio` when generated or integrated audio is in scope; add `--no-design` only for debug/perf/QA-only reports with no gameplay claims. If the audit fails, fix the missing sections or state the exact blocker instead of claiming completion. If the script is unavailable, manually enforce the same sections listed in Required Verification.

## Final Response

Report the ledgers (compacted per the rule above), game design brief, core loop contract, level/encounter plan, files changed, run URL, controls, verification commands, screenshots/artifacts, renderer/performance notes, technical art budget, visual test harness decision, quality gates passed, skipped phases, and remaining risks. For premium/AAA/showcase claims, include the filled visual scorecard with measured evidence and automatic failures remaining. Be precise: "invoked" means a slash/tool skill invocation; "loaded" means the file was read into context; "executed phase" means the work was performed under loaded skill guidance or the phase playbook.
