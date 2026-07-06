# Three.js AAA Graphics Prompt Templates

Reusable prompt templates packaged with this skill. Use only templates relevant to the current request, and adapt placeholders to the game/project context.

---

# AAA Graphics Production Pass Prompt

Use `threejs-aaa-graphics-builder` to upgrade this Three.js game from basic prototype visuals to premium browser-game graphics.

Current screenshot blockers:
- 

Target art direction:
- 

Required pass:
- Score current screenshots with `threejs-aaa-graphics-builder/references/visual-scorecard.md`.
- Add or improve the graphics architecture from `references/implementation-blueprint.md`.
- Add the technical art brief from `references/technical-art.md`: material kit, shader/VFX purpose, instancing/LOD/culling, imported asset cleanup, renderer budget, mobile tradeoffs.
- Build material library, procedural texture/decal helpers, model factories, world prop kit, VFX system, lighting/render pipeline, and diagnostics.
- Use `threejs-3d-generator` for high-value hero/player, character, creature, vehicle, building, weapon, pickup, boss, rigging, animation, texture, or conversion needs when procedural code is not enough.
- Use `threejs-image-generator` for 2D concepts, T-pose/A-pose references, texture references, decals, logos, icons, GUI art, skies, backgrounds, or image-to-3D inputs.
- Upgrade hero/player, obstacles/enemies, rewards/interactables, world kit, HUD cohesion, lighting, effects, and renderer metrics.

Do not count as completion:
- Recolored boxes/cones/spheres.
- Glow, fog, or darkness hiding missing detail.
- One improved object while world/obstacles/UI remain placeholders.
- Idle/showroom screenshots only.
- Missing renderer diagnostics after visual density changes.

Verification:
- Capture active gameplay desktop and mobile screenshots.
- Report visual score before/after.
- Report draw calls, triangles, geometries, textures, material count, DPR cap, shadow/post settings, and instancing/LOD/culling decisions when available.
- Run build, browser, console/page error, nonblank canvas, interaction, and responsive checks.
- Continue until every scorecard category is at least 2, or report exactly why the target was not reached.

---

# Before/After Visual Critique Prompt

Use `threejs-aaa-graphics-builder` to critique this Three.js game's current screenshots with the visual scorecard and produce a prioritized graphics plan.

Evidence to gather:
- Desktop screenshot.
- Mobile screenshot.
- Optional before/after screenshots if a pass was already completed.
- Renderer diagnostics if available.
- Notes on the game genre, core verb, and target mood.

Critique dimensions:
- Gameplay readability.
- UI hierarchy and text fit.
- Procedural model silhouette and fidelity.
- Material, lighting, shadows, color, and contrast.
- Camera composition and motion clarity.
- Mobile framing and touch/control readability.
- Performance risk from proposed upgrades.

Output:
- Pass/fail on whether the game looks polished enough for the current milestone.
- Top five blockers ordered by player impact.
- Recommended next skill/phase: `threejs-aaa-graphics-builder`, `threejs-game-ui-designer`, `threejs-debug-profiler`, or `threejs-qa-release`.
- Concrete acceptance criteria for the next pass.

---

# Material, Lighting, and Render Quality Pass Prompt

Use `threejs-aaa-graphics-builder` for scene-level render quality, material libraries, model materials, geometry factories, and visual scoring.

Current problem:
- 

Target look:
- 

Work areas:
- Renderer color space, tone mapping, exposure, shadow settings, DPR cap.
- Key/fill/rim/environment lighting.
- Material roughness, metalness, emissive accents, vertex colors, generated textures, and decals.
- Fog, background, post-processing, and feedback effects only where they improve readability.
- Camera composition and gameplay-distance readability.

Constraints:
- Improve lighting and materials before adding heavy post-processing.
- Keep threats, pickups, player, and objective readable during motion.
- Avoid excessive bloom, low-contrast fog, and particle clutter.
- Re-measure renderer info if visual complexity changes.

Verification:
- Capture desktop and mobile screenshots.
- Check console/page errors and nonblank canvas pixels.
- Compare renderer calls/triangles/textures before and after when practical.
- Play the core loop and confirm effects do not hide gameplay information.

---

# Technical Art Pass Prompt

Use `threejs-aaa-graphics-builder` for a technical-art pass on this Three.js game.

Current visual/performance risk:
- 

Target art direction:
- 

Required pass:
- Load `references/technical-art.md`.
- Write a technical art brief: hero surfaces, support surfaces, material kit, VFX language, lighting stack, render budget, asset strategy, mobile constraint.
- Convert art direction into renderable systems: materials, decals/trim, shaders, VFX, LOD, instancing, culling, imported asset cleanup.
- Make threats, rewards, player state, and objectives readable by shape/motion/value, not color alone.
- Keep API/generated asset calls out of browser runtime.

Verification:
- Capture active desktop and mobile screenshots.
- Report renderer diagnostics: calls, triangles, geometries, textures, material count when available, DPR cap, shadow/post settings.
- Report imported/generated asset diagnostics when relevant: file size, bounds, scale, orientation, collision proxy, triangles/materials/textures/clips when available.
- Report VFX readability: trigger, duration, player-facing meaning, and reduced-motion concern if applicable.
- State what was optimized, what was intentionally left rich, and remaining performance risks.

---

# Procedural Hero Asset Pass Prompt

Use `threejs-aaa-graphics-builder` to create or upgrade a high-fidelity scratch-built Three.js hero asset.

Asset brief:
- Role:
- Silhouette:
- Scale:
- Camera distance:
- Style references:
- Performance budget:

Requirements:
- Build a reusable model factory that returns a named `THREE.Group`.
- Establish a recognizable silhouette before adding small detail.
- Add secondary and tertiary detail through bevels, trims, panels, ridges, tubes, decals, emissive elements, and material contrast.
- Add visible subassemblies, not just a few primitives: shell/body, core/cockpit, trims/rails, engines/emitters, decals/surface marks, and state feedback when relevant.
- Use shared geometries/materials where possible.
- Use PBR-style materials, shadows, color management, and lighting intentionally.
- Keep collision or gameplay proxies simpler than the visual mesh.

Avoid:
- Placeholder stacks of primitives.
- Detail visible only from a showroom camera.
- Excessive segment counts, unique materials, or draw calls without gameplay value.
- Glow-only upgrades that leave the silhouette primitive.

Verification:
- Build and run locally.
- Capture gameplay-camera screenshot and one inspection screenshot if useful.
- Report renderer info before/after when available.
- Verify the asset reads clearly at desktop and mobile gameplay distances.

---

# Visual Polish Prompt

Use `threejs-aaa-graphics-builder` to improve the game's visual clarity and identity.

Use focused prompts instead when the main problem is narrower:
- Use `threejs-game-ui-designer/references/prompt-templates.md` for HUD/menu/interface quality prompts.
- Use the procedural hero asset or world prop kit sections in this file for scratch-built model fidelity inside the AAA graphics phase.
- Use the before/after visual critique section in this file when priorities are unclear.

Target feel:
- 

Constraints:
- Keep the game readable during motion.
- Avoid generic purple gradients, excessive bloom, particle clutter, and static showroom composition.
- Prefer purposeful lighting, color contrast, silhouettes, material variation, and procedural geometry that supports gameplay.
- Hand off substantial UI craft to `threejs-game-ui-designer`; keep model/world/render construction under `threejs-aaa-graphics-builder`.
- Keep performance visible while polishing.

Verification:
- Capture before/after screenshots where possible.
- Check desktop and mobile framing.
- Confirm the game remains interactive and no console errors were introduced.

---

# World Prop Detail Kit Pass Prompt

Use `threejs-aaa-graphics-builder` to create a reusable procedural prop/detail kit for this Three.js game's world.

World role:
- 

Kit requirements:
- Define 4-8 reusable prop factories with shared materials.
- Include scale variants, color/material variants, and clear placement rules.
- Use instancing or shared geometry/materials for repeated details.
- Add visual detail that supports navigation, danger, reward, or atmosphere.
- Keep the kit coherent with the existing game UI and world lighting.
- For city/runner worlds, include skyline modules with setbacks/window bands/roof details, foreground speed props, track hardware, signage/cables/supports, and distant parallax layers.

Performance constraints:
- Avoid unique material explosions.
- Keep repeated props instanced or pooled when practical.
- Track draw calls, triangles, geometries, textures, and frame impact.

Verification:
- Capture before/after screenshots from gameplay camera.
- Check desktop and mobile readability.
- Report renderer diagnostics.
- Confirm no console/page errors and no obvious collision/occlusion issues.
- If the world is still dominated by stretched boxes, continue the prop-kit pass.

---

# Fresh-Eyes Scorecard Review Prompt

Use for the independent review pass required by `references/visual-scorecard.md` for premium/AAA/showcase claims. Give the reviewer ONLY the inputs below — no build history, no prior scores, no description of the work performed.

Inputs:
- The COMPLETE screenshot capture set — every captured state, desktop and mobile, never a hand-picked subset: <paths>
- Scorecard rubric: `threejs-aaa-graphics-builder/references/visual-scorecard.md`
- Calibration anchors: `threejs-aaa-graphics-builder/assets/scorecard-anchors/`
- Inspector metrics JSON: <paths>

Task:
- Score all ten scorecard categories from the screenshots alone, using the 0-3 anchors and calibration images.
- Cross-check scores against the metrics (colorEntropyBits, edgeDensity, luminance.contrast, dominantColorShare, renderBudget) and flag any score the numbers contradict.
- List every automatic failure you can see in the screenshots.
- Do not give benefit of the doubt: if a surface could be a 1 or a 2, score it 1 and say what visible change would earn the 2.

Report:
- Ten category scores with one-sentence visual evidence each.
- Automatic failures observed.
- The three highest-impact changes to raise the lowest scores.
