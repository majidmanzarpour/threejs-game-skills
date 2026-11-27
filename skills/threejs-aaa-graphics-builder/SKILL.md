---
name: threejs-aaa-graphics-builder
description: "Upgrade Three.js games from prototype visuals to premium browser graphics: art-direction critique, procedural hero/world model kits, PBR material and texture libraries, lighting and shadows, surface shaders (onBeforeCompile, skies, HDR bloom), LOD/instancing, render budgets, and the 10-category visual scorecard. Use when scenes look basic or need authored geometry, materials, lighting, or scoring; delegate complex combat, ability, spell, explosion, trail, and optical impact VFX to threejs-aaa-vfx-builder."
---

# Three.js AAA Graphics Builder

Own the production graphics pass: turn basic screenshots into authored, high-density, performance-aware visuals.

Resolve `<this-skill-dir>` from the actual loaded skill file; resolve sibling skills beside it before runner-discovered alternatives.

## References

Load each reference when entering that sub-task — do not load all four before forms exist:

| File | Read it when |
| --- | --- |
| `references/authoring-recipes.md` | building hero, obstacle, reward, world-kit, or prop models; setting up lighting, tone mapping, shadows, fog, or graphics architecture |
| `references/technical-art.md` | setting render budgets, shared material kits, instancing/LOD, or cleaning up imported GLB/FBX assets |
| `references/shader-cookbook.md` | writing PBR materials, `onBeforeCompile` surface shaders, skies, or `HalfFloatType` bloom post-processing (`three ^0.184`) |
| `references/visual-scorecard.md` | scoring active-play screenshots or making any premium/AAA/showcase claim |

For a broad graphics pass, start with `authoring-recipes.md` + `technical-art.md`, load `shader-cookbook.md` during material/post authoring, and load `visual-scorecard.md` when scoring. A narrow edit loads only its relevant reference; user style and scope always override recipe defaults.

## Core rule

Glow does not make primitives look AAA. Build authored forms first, then materials, then lighting, then effects — in that order.

## Workflow

1. Capture or inspect active-play screenshots on the target viewports when a playable scene exists.
2. For an existing game, score the affected views and pick the weakest surfaces. For a new game, establish art direction, camera scale, material roles, and the hero target first; do not invent a before screenshot.
3. Add the graphics architecture the game is missing: material library, procedural textures and decals, model factories, world prop kit, render pipeline, diagnostics.
4. Choose a source per high-value surface: procedural Three.js, a `threejs-image-generator` reference or texture, a `threejs-3d-generator` model, or an image-to-3D hybrid chain. Run the credential probe when external generation is in scope.
   Inspect the concept/model before dependent generation or rigging. Finish one representative playable scene with actual assets and feedback before expanding the content kit.
5. Upgrade every weak visible surface, not only the hero: hazards, rewards, ground and track, foreground props, background layers, telegraphs, material variation.
6. Add lighting, `RoomEnvironment` IBL, tone mapping, and selective `HalfFloatType` HDR render polish once authored forms exist.
7. Delegate event-driven combat, ability, spell, weapon, shield, explosion, trail, and optical impact VFX to `threejs-aaa-vfx-builder` (keep lightweight pickup/state cues within budget for small arcade games).
8. Re-score against the calibration anchors, citing the inspector's measured metrics. Keep going until every premium category is at least 2, or name the exact blocker.

## Asset sourcing

When external generation is in scope, run `threejs-game-director/scripts/probe_asset_credentials.sh` first; explicitly procedural art needs no probe. With keys set, generate the hero surfaces (player, character, creature, boss, vehicle, ship, building, weapon, signature prop, hero environment piece) and high-value 2D (skies, backgrounds, texture and trim references, decals, faction marks, icons, GUI and title art, image-to-3D inputs), unless the user restricted art to procedural or ruled out external services. Procedural Three.js handles repeated props, kits, collision proxies, VFX geometry, and instanced volume. Handle failures with `threejs-game-director/references/asset-recovery.md`; a single timeout is not evidence that generation is unavailable.

For animated assets inspect motion as well as silhouettes: locomotion, blend transitions, foot contacts, hit timing, and secondary motion in real gameplay. A focused independent critique may identify defects after a substantial pass; the lead remains responsible for the final score and integration.

## Report

Score before and after with one line of evidence per category, the surfaces you upgraded, files changed, screenshots, renderer diagnostics against the budget table, generated asset paths and task IDs, and what is still weak. Include imported-asset diagnostics (scale, bounds, collision proxy, clips) when generated 3D was used.
