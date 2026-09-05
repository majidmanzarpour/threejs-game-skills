---
name: threejs-game-director
description: "Entrypoint for building, upgrading, and finishing Three.js browser games. Routes work across the sibling threejs-* skills for gameplay, graphics, UI, 3D/image/audio asset generation, debugging, and release. Use for build-a-game, upgrade, polish, premium, AAA, high-fidelity, showcase, from-scratch, endless runner, arcade, action, and release-ready requests."
---

# Three.js Game Director

Own the end-to-end game outcome: a playable loop first, then the visual and interface depth the request actually asked for, then browser evidence that it works.

## Scope

The user's own words set the bar. "Make a small arcade game" is not a request for the full premium pipeline — build the good version of what was asked and stop. "Premium", "AAA", "polished", "high-fidelity", "showcase", "release-ready", or "less basic" *is* that request, and at that bar a first playable slice is not done. "Less basic" specifically means the current visual level was rejected; treat it as the premium bar.

The user's scope, art style, constraints, and prior decisions override skill defaults. A narrow edit to a premium game remains a narrow edit. Make routine implementation calls yourself and complete authorized work before seeking a decision that only affects a later step. Ask only when a missing choice materially changes the requested result; continue independent work meanwhile.

## Working style

Say in one sentence what you're about to do before your first tool call. While working, give a brief update only when you find something important or change direction. Lead the final response with the outcome.

The lead owns shared interfaces, integration, and the final verification pass. Use available delegation tools for independent work that saves time or improves quality: asset generation alongside gameplay, or isolated UI work after the intent/state interface is defined. Normally use a lead plus up to two workers. Give each worker a task, separate file ownership, input/output contract, and acceptance criteria. Keep the immediate blocking integration work with the lead.

For substantial gameplay, graphics, or animation changes, one focused independent review can catch missed defects. Supply raw captures/code and the relevant rubric; ask for concrete defects rather than endorsement of the lead's score. Resolve findings without recursive review cycles. When delegation tools are absent, work directly.

Report what you ran and what you saw. If you couldn't run something, say that instead.

## Sibling skills

Use the actual loaded skill directory as `<director-skill-dir>`. Resolve siblings through `../<skill>/SKILL.md` there. If absent, use the runner's discovered skill path, then a matching repo `skills/` directory or the active runner's install location (`~/.agents/skills` for Codex, `~/.claude/skills` for Claude Code, legacy `~/.codex/skills` last). Resolve references relative to the selected skill; avoid mixing installed versions.

| Phase | Skill |
| --- | --- |
| Design brief, core loop, levels, entities, input, camera, physics, feel | `threejs-gameplay-systems` |
| Models, materials, shaders, VFX, lighting, render budget, scorecard | `threejs-aaa-graphics-builder` |
| HUD, menus, overlays, responsive and touch UI | `threejs-game-ui-designer` |
| Blank canvas, render/runtime bugs, mobile input, profiling | `threejs-debug-profiler` |
| Browser QA, screenshots, canvas pixels, bot playtest, production build | `threejs-qa-release` |
| Characters, vehicles, weapons, buildings, rigs, animation | `threejs-3d-generator` |
| Concepts, textures, skies, logos, icons, GUI art, image-to-3D inputs | `threejs-image-generator` |
| SFX, ambience, UI sounds, announcer and dialogue | `threejs-audio-generator` |

For complete games and broad upgrades, read all five production skills before implementing, plus generators whose trigger surfaces exist. Read each phase's required references at phase entry. For narrow edits, load the affected specialists and references, preserving unrelated systems. Record actual loaded resources when reporting skill use; a phase label is not a skill invocation.

## Continuity and early quality

Start broad builds with the gameplay design brief, core-loop contract, and level plan. Define art direction, camera scale, and hero/readability targets early. Launch useful asset jobs while implementing the loop, then assess a representative playable scene with the real assets before multiplying levels, waves, or enemy variants. Inspect concepts and generated model previews before their dependent generation or rigging stages.

For substantial tasks maintain `artifacts/game-progress.md`: current intent and constraints, decisions, completed work, pending jobs with task IDs/checkpoint paths, remaining defects, and next actions. Re-read it after an interruption. A correction updates affected work; a status question does not replace the build objective. Preserve completed assets and mark obsolete pending outputs instead of accidentally spending again.

Use available background tool sessions to keep independent local work moving. Tripo generation is a user-executed boundary: prepare the prompt, settings, destination, and copy-paste command, then continue work that does not depend on the asset until the user supplies it. Native API async calling, steering, and reasoning configuration are host capabilities, not settings enabled by this skill.

## The bar for premium work

Every visible surface that exists in the design is authored, not just the hero: player, obstacles and enemies, interactables, ground and world kit, HUD and menu states, lighting and materials, feel, and target-device performance. Unrefined primitives, empty arenas, box skylines, generic stat-card HUDs, and glow-or-fog-only detail are prototype placeholders unless the user explicitly chose that style. Interpret the scorecard through the genre rather than adding unrelated content.

Score the result with the 10-category scorecard in `threejs-aaa-graphics-builder/references/visual-scorecard.md`, using its anchors and the inspector's measured metrics rather than a personal rubric. Premium means no category below 2 and an average of at least 2.3.

## Asset sourcing

```bash
bash <director-skill-dir>/scripts/probe_asset_credentials.sh
```

When keyed agent-executed generation is in scope, run it before assuming anything about keys. It sources the user's shell profile, which the agent process usually does not inherit, and prints `KEY=SET|MISSING` for the packaged providers. Codex's built-in imagegen path uses the active Codex subscription and needs no project key or credential probe. Tripo generation remains user-executed, so its missing process key is not a reason to downgrade the planned asset. Explicitly procedural or no-external-service work does not need a credential probe.

Premium hero surfaces should use generated assets when the design benefits. The `threejs-image-generator` skill chooses Codex imagegen first on Codex and its Gemini helper on runners without native image generation. For Tripo, prepare the exact user handoff described by `threejs-3d-generator`; never submit or retry a paid Tripo task on the user's behalf. Respect an explicit procedural-only style or external-generation restriction. Procedural kits handle repeated props, decals, collision proxies, and instanced volume. Premium active gameplay includes event-driven audio.

Read `references/asset-recovery.md` when sourcing external assets or recovering a job. Missing credentials or exhausted credits permit a documented local fallback. A transient error calls for bounded recovery of the existing job; invalid parameters need correction. An uncertain paid submission must be reconciled before replacement. Continue independent work and identify any quality requirement still unmet after fallback.

## Verification ownership

The lead consolidates specialist results into one check set appropriate to the change. Full games need production build, real-input progression and retry, target-viewport captures, renderer diagnostics, and the premium scorecard when requested. Small edits need affected behavior/layout checks. Repeat checks only after relevant changes, failures, or unresolved concerns. For animated work include motion captures covering locomotion, transitions, and contact timing, not only stills.

## Getting started and checking output

```bash
python3 <threejs-gameplay-systems-skill-dir>/scripts/create_threejs_game.py ./my-game
node <threejs-qa-release-skill-dir>/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --state active-play --run-id pass-1
python3 <director-skill-dir>/scripts/check_evidence.py ./my-game --manifest artifacts/evidence.json
```

Generated games carry their own `npm run inspect:canvas` and `npm run verify:visual`. Before capturing, read `references/evidence-manifest.md` and declare the expected viewport/state pairs for this pass. The checker verifies only that set and its run ID. Its result establishes artifact coverage, not aesthetic quality or gameplay correctness. When maintaining the pack itself, use `references/workflow-evaluations.md` for behavioral comparisons.

## Final response

Lead with what was built, whether it works, the local URL and controls, and remaining limitations. For substantial builds put the design artifacts, asset task IDs/paths, captures and motion evidence, renderer/physics metrics, tests, and scorecard in `artifacts/final-evidence.md` and link it. For narrow edits report only affected behavior and checks. Describe what ran and was observed; do not substitute a completion claim for missing evidence.
