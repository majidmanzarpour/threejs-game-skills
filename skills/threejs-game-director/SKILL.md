---
name: threejs-game-director
description: "Entrypoint for building, upgrading, and finishing Three.js browser games. Routes work across the nine sibling threejs-* skills for gameplay, graphics, AAA VFX, UI, 3D/image/audio generation, debugging, and release. Use for any request to build, upgrade, polish, or ship a Three.js game as a whole, from a small arcade prototype to a premium release."
---

# Three.js Game Director

Own the end-to-end game outcome: a playable loop first, then the visual and interface depth the request actually asked for, then browser evidence that it works.

## Scope

The user's own words set the bar. "Make a small arcade game" is not a request for the full premium pipeline — build the good version of what was asked and stop. "Premium", "AAA", "polished", "high-fidelity", "showcase", "release-ready", or "less basic" *is* that request, and at that bar a first playable slice is not done. "Less basic" specifically means the current visual level was rejected; treat it as the premium bar.

The user's scope, art style, constraints, and prior decisions override skill defaults. A narrow edit to a premium game remains a narrow edit. Make routine implementation calls yourself and complete authorized work before seeking a decision that only affects a later step. Ask only when a missing choice materially changes the requested result; continue independent work meanwhile. Until the requested bar is met, don't end a turn with a summary that announces the next step, an offer to continue, or a list of decisions that don't block the work; take the next step instead. End the turn when the work is done, or when only the user can unblock it.

## Working style

Say in one sentence what you're about to do before your first tool call. While working, give a short update when you finish a phase, find something important, or change direction. Lead the final response with the outcome.

The lead owns shared interfaces, integration, and the final verification pass. Use available delegation tools for independent work that saves time or improves quality: asset generation alongside gameplay, or isolated UI work after the intent/state interface is defined. Normally use a lead plus up to two workers. Give each worker a task, separate file ownership, input/output contract, and acceptance criteria. Keep the immediate blocking integration work with the lead.

For substantial gameplay, graphics, or animation changes, one focused independent review can catch missed defects. Supply raw captures/code and the relevant rubric; ask for concrete defects rather than endorsement of the lead's score. Resolve findings without recursive review cycles. When delegation tools are absent, work directly.

Report what you ran and what you saw. If you couldn't run something, say that instead.

## Sibling skills

Use the actual loaded skill directory as `<director-skill-dir>`. Resolve siblings through `../<skill>/SKILL.md` there. If absent, use the runner's discovered skill path, then a matching repo `skills/` directory or the active runner's install location (`~/.agents/skills` for Codex, `~/.claude/skills` for Claude Code, `~/.gemini/config/skills` for Antigravity, legacy `~/.codex/skills` last). Resolve references relative to the selected skill; avoid mixing installed versions.

| Phase | Owns | Skill |
| --- | --- | --- |
| 1. Loop & feel | Design brief, core loop, levels, entities, input, camera, physics, hitstop/shake | `threejs-gameplay-systems` |
| 2. World & look | Hero/world models, PBR material kits, lighting, surface shaders, budgets, scorecard | `threejs-aaa-graphics-builder` |
| 3. Signature VFX | Combat/ability/weapon/explosion/shield VFX, soft particles, trails, optical impact post | `threejs-aaa-vfx-builder` |
| 4. Interface | HUD, menus, overlays, responsive and touch UI | `threejs-game-ui-designer` |
| 5. Triage & perf | Blank canvas, render/shader/NaN/runtime bugs, mobile input, profiling | `threejs-debug-profiler` |
| 6. QA & ship | Browser QA, screenshots, canvas pixels, motion captures, bot playtest, production build | `threejs-qa-release` |
| Asset: 3D | Generated characters, vehicles, weapons, buildings, rigs, animation | `threejs-3d-generator` |
| Asset: 2D | Concepts, textures, skies, logos, icons, GUI art, image-to-3D inputs | `threejs-image-generator` |
| Asset: Audio | SFX, music, ambience, UI sounds, announcer and dialogue | `threejs-audio-generator` |

**Phase-gated loading (do not dump every skill into context upfront):**
- **Complete games / broad upgrades:** Load `threejs-gameplay-systems` first to establish the design brief and playable loop (kick off async 3D/image/audio generation early when external assets are in scope). Load `threejs-aaa-graphics-builder` at Phase 2, `threejs-aaa-vfx-builder` when combat/ability/impact/environmental VFX enter scope, `threejs-game-ui-designer` once game state is stable, `threejs-debug-profiler` on defects or bottlenecks, and `threejs-qa-release` for browser/release verification. Read each skill's reference files only when that task begins.
- **Narrow edits:** Load only the affected specialist(s) and exact reference row(s), preserving unrelated systems.
- Record actual loaded resources when reporting skill use; a phase label is not a skill invocation.

## Continuity and early quality

Start broad builds with the gameplay design brief, core-loop contract, and level plan. Define art direction, camera scale, and hero/readability targets early. Launch useful asset jobs while implementing the loop, then assess a representative playable scene with the real assets before multiplying levels, waves, or enemy variants. Inspect concepts and generated model previews before their dependent generation or rigging stages.

For substantial tasks maintain `artifacts/game-progress.md`: current intent and constraints, decisions, completed work, pending jobs with task IDs/checkpoint paths, remaining defects, and next actions. Re-read it after an interruption. A correction updates affected work; a status question does not replace the build objective. Preserve completed assets and mark obsolete pending outputs instead of accidentally spending again.

Use available background tool sessions or submit/status/download commands to keep independent work moving.

## The bar for premium work

Every visible surface that exists in the design is authored, not just the hero: player, obstacles and enemies, interactables, ground and world kit, HUD and menu states, lighting and materials, feel, and target-device performance. Unrefined primitives, empty arenas, box skylines, generic stat-card HUDs, and glow-or-fog-only detail are prototype placeholders unless the user explicitly chose that style. Interpret the scorecard through the genre rather than adding unrelated content.

Score the result with the 10-category scorecard in `threejs-aaa-graphics-builder/references/visual-scorecard.md`, using its anchors and the inspector's measured metrics rather than a personal rubric. Premium means no category below 2 and an average of at least 2.3.

## Asset sourcing

```bash
bash <director-skill-dir>/scripts/probe_asset_credentials.sh
```

When external generation is in scope, run it before assuming anything about keys. It sources the user's shell profile, which the agent process usually does not inherit, and prints `KEY=SET|MISSING` for all three providers. Explicitly procedural or no-external-service work does not need a credential probe.

With keys set, premium hero surfaces get generated assets: player, boss, creature, vehicle, ship, weapon, signature building. Respect an explicit procedural-only style or external-generation restriction. Procedural kits handle repeated props, decals, collision proxies, and instanced volume. Premium active gameplay includes event-driven audio.

Read `references/asset-recovery.md` when sourcing external assets or recovering a job; it classifies each failure and says when a local fallback is allowed. Continue independent work meanwhile.

## Verification ownership

The lead consolidates specialist results into one check set appropriate to the change. Full games need production build, real-input progression and retry, target-viewport captures, renderer diagnostics, and the premium scorecard when requested. Small edits need affected behavior/layout checks. Repeat checks only after relevant changes, failures, or unresolved concerns. For animated models or signature multi-phase VFX, include unpaused motion captures covering anticipation, transitions, impact/contact timing, and aftermath — not only stills.

## Getting started and checking output

```bash
python3 <threejs-gameplay-systems-skill-dir>/scripts/create_threejs_game.py ./my-game
node <threejs-qa-release-skill-dir>/scripts/inspect-threejs-canvas.mjs --manifest artifacts/evidence.json --url http://127.0.0.1:5188
python3 <director-skill-dir>/scripts/check_evidence.py ./my-game --manifest artifacts/evidence.json
```

Generated games carry their own `npm run inspect:canvas` and `npm run verify:visual`. Before capturing, read `references/evidence-manifest.md` and declare the expected viewport/state pairs for this pass. The checker verifies only that set and its run ID. Its result establishes artifact coverage, not aesthetic quality or gameplay correctness. When maintaining the pack itself, use `references/workflow-evaluations.md` for behavioral comparisons.

## Final response

Lead with what was built, whether it works, the local URL and controls, and remaining limitations. For substantial builds put the design artifacts, asset task IDs/paths, captures and motion evidence, renderer/physics metrics, tests, and scorecard in `artifacts/final-evidence.md` and link it. For narrow edits report only affected behavior and checks. Describe what ran and was observed; do not substitute a completion claim for missing evidence.
