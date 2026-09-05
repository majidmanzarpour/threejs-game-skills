---
name: threejs-aaa-graphics-builder
description: "Upgrade Three.js games from prototype visuals to premium browser graphics: art-direction critique, procedural model building, material and texture libraries, world prop kits, shaders, VFX, lighting and render pipeline, LOD and instancing, render budgets, and a 10-category visual scorecard. Use when screenshots still look basic or the user asks for premium, AAA, high-fidelity, showcase, or less-basic graphics."
---

# Three.js AAA Graphics Builder

Own the production graphics pass: turn basic screenshots into authored, high-density, performance-aware visuals.

## References

| File | Read it when |
| --- | --- |
| `references/visual-scorecard.md` | scoring visuals or making any premium/AAA/showcase claim |
| `references/authoring-recipes.md` | building hero, obstacle, reward, world-kit, or prop models; changing lighting, tone mapping, shadows, fog, post, or graphics architecture |
| `references/technical-art.md` | render budgets, material kits, VFX systems, instancing/LOD, imported asset cleanup, anything that could affect browser performance |
| `references/shader-cookbook.md` | custom shaders, `onBeforeCompile`, skies, or post-processing; use recipes as tested starting points and verify them against the project's Three.js version |

For a broad "still looks basic" or premium pass, read all four before implementing. A narrow graphics edit loads only its relevant references and checks; the requested style and scope override recipe defaults.

## Core rule

Glow does not make primitives look AAA. Build authored forms first, then materials, then lighting, then effects — in that order.

## Workflow

1. Capture or inspect active-play screenshots on the target viewports when a playable scene exists.
2. For an existing game, score the affected views and pick the weakest surfaces. For a new game, establish art direction, camera scale, material roles, and the hero target first; do not invent a before screenshot.
3. Add the graphics architecture the game is missing: material library, procedural textures and decals, model factories, world prop kit, VFX system, render pipeline, diagnostics.
4. Choose a source per high-value surface: procedural Three.js, a `threejs-image-generator` reference or texture, a user-generated `threejs-3d-generator` model, or an image-to-3D hybrid chain. Use Codex's built-in imagegen path when available. For Tripo, prepare the prompt, settings, destination, acceptance checks, and user-run command or Studio checklist.
   Inspect the concept/model before dependent generation or rigging. Finish one representative playable scene with actual assets and feedback before expanding the content kit.
5. Upgrade every weak visible surface, not only the hero: hazards, rewards, ground and track, foreground props, background layers, telegraphs, material variation, state VFX.
6. Add lighting, tone mapping, and render polish once authored forms exist.
7. Add event-driven VFX tied to gameplay state.
8. Re-score against the calibration anchors, citing the inspector's measured metrics. Keep going until every premium category is at least 2, or name the exact blocker.

## Asset sourcing

When keyed agent-executed generation is in scope, run `threejs-game-director/scripts/probe_asset_credentials.sh` before assuming anything about keys. Codex's built-in imagegen path needs no project credential or probe. Tripo generation is user-executed and does not depend on the agent process inheriting a Tripo key. No probe or paid submission is needed for explicitly procedural art.

Generated assets belong on the hero surfaces — player, character, creature, boss, vehicle, ship, building, weapon, signature prop, hero environment piece — and on high-value 2D: skies, backgrounds, texture and trim references, decals, faction marks, icons, GUI and title art, image-to-3D inputs. Use native image tools directly when available; make Tripo a concrete user-executed handoff. Respect explicit procedural-only art or external-generation restrictions. Procedural Three.js handles repeated props, kits, collision proxies, VFX geometry, and instanced volume.

Use the director's `references/asset-recovery.md`: recover transient failures and accepted tasks before fallback. Missing keys, exhausted credits, or exhausted bounded recovery permit a local replacement with the remaining quality gap reported. A single timeout is not evidence that generation is unavailable.

For animated assets inspect motion as well as silhouettes: locomotion, blend transitions, foot contacts, hit timing, and secondary motion in real gameplay. A focused independent critique may identify defects after a substantial pass; the lead remains responsible for the final score and integration.

## Report

Score before and after with one line of evidence per category, the surfaces you upgraded, files changed, screenshots, renderer diagnostics against the budget table, generated asset paths and task IDs, and what is still weak. Include imported-asset diagnostics (scale, bounds, collision proxy, clips) when generated 3D was used.
