---
name: threejs-aaa-graphics-builder
description: "Upgrade Three.js games from basic/prototype visuals to premium AAA-inspired browser graphics. Combines art-direction critique, procedural model building, technical art, mandatory external asset sourcing decisions, threejs-3d-generator assets, threejs-image-generator concept/texture workflows, scene visual polish, material/texture libraries, world prop kits, shaders, VFX readability, render budgets, LOD/instancing, render pipeline, and visual scorecard gates. For premium games with characters, vehicles, ships, weapons, buildings, signature props, skies, textures, decals, logos, icons, or GUI art, load the relevant generator skills before deciding procedural assets are enough."
---

# Three.js AAA Graphics Builder

## Purpose

Own the production graphics pass. Convert basic screenshots into authored, high-density, performance-aware visual experiences.

## Use When

Screenshots still look basic, models look primitive, worlds are sparse, UI/world art feels generic, or the user asks for premium, AAA, high-fidelity, showcase, or less-basic graphics.

## Required References

These references are required phase-entry gates, not optional reading:

- Load `references/visual-scorecard.md` before scoring, judging completion, or making any premium/AAA/showcase claim.
- Load `references/implementation-blueprint.md` before changing graphics architecture, materials, VFX, rendering, diagnostics, or broad visual systems.
- Load `references/model-recipes.md` before building or upgrading hero/player, obstacle, enemy, pickup, world-kit, material, or prop models.
- Load `references/render-recipes.md` before changing lighting, tone mapping, shadows, fog, post-processing, materials, or render composition.
- Load `references/technical-art.md` before premium/AAA/showcase graphics work, shaders/material systems, VFX systems, generated/imported asset cleanup, LOD/instancing work, or visual changes that could affect browser performance.
- Load `references/shader-cookbook.md` before writing any custom shader, `onBeforeCompile` injection, material recipe, sky, or post-processing chain — use its proven values and GLSL patterns instead of improvising.
- Load `references/checklists/aaa-game-quality-gate.md` and `references/checklists/aaa-visual-scorecard.md` before declaring a game premium, AAA, showcase, complete, release-ready, or less basic.
- Load the relevant checklist before focused work: `references/checklists/procedural-model-quality.md`, `references/checklists/material-lighting-quality.md`, `references/checklists/performance-safe-visual-detail.md`, or `references/checklists/technical-art-quality.md`.
- Load `references/prompt-templates.md` only when the user asks for reusable prompts, a graphics-pass prompt, or a task template.

For broad "still looks basic", premium, AAA, high-fidelity, showcase, or less-basic graphics work, load all five references as the first action in the phase. Track them in a reference ledger with yes/no, path, and failure reason. Do not mark the graphics phase complete while any required reference is skipped.

External asset sourcing gate:

- For premium/AAA/showcase/high-fidelity/less-basic graphics with a hero/player, character, creature, boss, vehicle, ship, building, weapon, signature prop, complex pickup, or hero environment piece, load `threejs-3d-generator` before deciding procedural geometry is enough.
- For premium/AAA/showcase/high-fidelity/less-basic graphics with concept needs, texture/material references, decals, logos, faction marks, icons, GUI art, skies, backgrounds, title/menu art, or image-to-3D inputs, load `threejs-image-generator` before deciding 2D external assets are not needed.
- Run the director credential probe before using `key unavailable` as a skip reason and paste the SET/MISSING output.
- Create an asset sourcing ledger for each high-value surface: procedural / threejs-image-generator / threejs-3d-generator / hybrid, plus outputs or skip reason.
- `not-needed` is valid only after the relevant skill was loaded and the ledger explains why external generation would not improve a non-hero support surface, or why the credential probe or attempted generation shows a real blocker.
- For premium hero surfaces, procedural-only is not an allowed final answer unless there is real blocker evidence. At least one high-value surface must show a 3D generator task ID, downloaded GLB/GLTF/FBX path, image generator output path, or documented hybrid chain.

## Workflow

1. Capture or inspect active desktop/mobile screenshots.
2. Score visuals across art direction, hero/player, obstacles, rewards, world, materials, render, VFX, UI, and performance evidence.
3. Add missing graphics architecture: material library, procedural textures/decals, model factories, world prop kit, technical-art budget, VFX system, render pipeline, diagnostics.
4. Run the credential probe, then fill the external asset sourcing ledger per surface: procedural Three.js factory, `threejs-image-generator` 2D reference/texture, `threejs-3d-generator` 3D generation, or a hybrid.
5. Upgrade every weak visible surface, not only one hero object.
6. Add lighting/render/material polish after authored forms exist.
7. Add event-driven VFX tied to gameplay state.
8. Re-score screenshots against the calibration anchors, citing the inspector's measured metrics. Continue until every premium category is at least 2/3 or report exact blockers.
9. Run the fresh-eyes review per `references/visual-scorecard.md` before finalizing premium/AAA/showcase claims.
10. Verify renderer diagnostics against the render budget table, technical-art budget, desktop/mobile screenshots, console/page errors, canvas pixels, imported asset budgets, and playability.

## Core Rule

Do not make primitives look AAA by adding glow. First build authored forms, then materials, then lighting, then effects.

## Final Response

Report the reference ledger, credential probe output, external asset sourcing ledger, technical art brief, score before/after, production surfaces upgraded, files changed, screenshots/artifacts, renderer diagnostics, imported asset diagnostics when relevant, VFX readability and render-budget tradeoffs, and remaining blockers. For premium/AAA/showcase claims, include the filled visual scorecard exactly as defined in `references/visual-scorecard.md`, including average and automatic failures remaining.
