# Technical Art For Three.js Games

Use this reference before premium/AAA/showcase graphics work, shader/material/post-processing changes, VFX systems, generated/imported asset cleanup, LOD/instancing work, or any visual pass that could affect browser performance.

Technical art is the bridge between art direction and real-time constraints. The goal is not maximum detail; it is readable authored detail that survives active gameplay, mobile viewports, and WebGL budgets.

Research basis: Three.js exposes renderer diagnostics through `WebGLRenderer.info`; `InstancedMesh` is designed for many objects sharing geometry/materials; `LOD` switches objects by distance; `KTX2Loader` supports Basis Universal GPU texture workflows; MDN WebGL best practices emphasize eliminating errors, understanding system limits, eager deletion, batching draw calls, per-pixel VRAM budgets, smaller back buffers, mipmaps, compressed textures, and high-DPI discipline.

## Technical Art Brief

Before implementation, write:

- Art direction in renderable terms: shapes, materials, lighting, VFX, camera, UI/world motifs.
- Hero surfaces: what must look authored at active-play distance.
- Support surfaces: what can be procedural, instanced, simplified, or culled.
- Material kit: named roles, not one-off colors.
- VFX language: event-driven effects and state readability.
- Lighting stack: key/fill/rim/practical/contact/depth.
- Render budget target: draw calls, triangles, textures, materials, DPR, shadow/post cost.
- Asset strategy: procedural / generated 2D / generated 3D / hybrid / imported.
- Mobile constraint: what changes first if performance or readability fails.

## Render Budget Starting Points

These are not universal limits. Use them as a starting contract, then measure on the target game:

- Draw calls: keep active-play calls low; repeated world/detail pieces should be instanced or merged by material.
- Triangles: spend on silhouettes near the camera; reduce background detail through LOD, impostors, or simplified meshes.
- Materials: share material roles aggressively. Unique material count often grows faster than geometry count.
- Textures: keep opaque large images compressed or small; avoid unique 2K+ textures for tiny repeated props.
- DPR: cap for mobile/high-density displays before deleting all art.
- Shadows: reserve real shadows for hero objects and grounding anchors; use blob/contact meshes for small repeated props.
- Post: every pass must earn its cost and preserve gameplay clarity.

Always report actual renderer diagnostics after the graphics pass: calls, triangles, geometries, textures, material count if available, post passes, shadow settings, DPR cap, and bottlenecks.

## Material And Shader System

Use a material kit:

- Body primary/secondary.
- Trim and edge highlights.
- Hazard/damage.
- Reward/value.
- Shield/boost/status.
- Glass/lens/cockpit.
- Ground/contact.
- Decal dark/light.
- UI/world shared signal colors.

Shader or `onBeforeCompile` work must have a reason:

- State readability: shield ripple, heat, cloak, damage pulse.
- Surface identity: water, forcefield, hologram, scanline, energy core.
- Performance: cheap procedural variation instead of many textures.
- Composition: separating player/threat/reward from background.

Reject shader work that only adds noise, bloom bait, or hidden cost without improving active-play decisions.

## VFX Readability

Every VFX effect must answer:

- What event or state triggers it?
- What does it tell the player?
- Does it point to player, threat, reward, objective, or impact?
- How long does it last?
- Is it pooled or cheap to recreate?
- Does it obscure collision, HUD, or the next decision?
- Is there a reduced-motion fallback for heavy shake/strobe?

Use event-driven VFX over permanent particle clutter:

- Pickup: short burst, collection line, HUD echo.
- Hit/fail: impact ring, debris, short camera impulse, state flash.
- Boost: trail, FOV ease, speed lines, audio pitch hook.
- Spawn: anticipation pulse and telegraph.
- Shield: rim pulse and absorbed-impact ripple.

## Instancing, LOD, And Culling

Use instancing for many copies with the same geometry/material and different transforms: windows, bolts, lane markers, city lights, debris, foliage-like props, stars, crowd cards, track panels, repeated pickups, background modules.

Rules:

- Update `instanceMatrix.needsUpdate` and `instanceColor.needsUpdate` only after batched changes.
- Compute or update bounds for instanced groups when transforms change materially.
- Do not instance everything blindly. Different materials or constantly changing transforms can erase the win.
- Keep collision separate from instanced visual detail.

Use LOD when:

- A hero/background object spans large distance ranges.
- The silhouette matters near camera but not far away.
- Imported/generated models are heavier than needed for background use.

Rules:

- Add hysteresis or distance gaps to reduce visible popping.
- Use impostor cards or simplified silhouettes for far layers when appropriate.
- Verify LOD transitions during gameplay camera motion, not only static orbit.

## Generated And Imported Asset Cleanup

For every Tripo/imported GLB/FBX hero asset:

- Confirm scale, pivot, forward/up orientation, bounds, and active-play silhouette.
- Create a simple collision proxy independent from the visual mesh.
- Inspect file size, approximate triangles, mesh count, material count, texture count, and animation clips when available.
- Replace or simplify excessive materials and textures.
- Add LOD or simplified background variant when reused many times.
- Verify PBR material readability under the game's lighting, not only in a model viewer.
- Keep API keys and temporary URLs out of client code and checked-in files.

## Decals, Trim, And Surface Detail

Prefer reusable surface systems:

- Canvas-generated trim sheets for panel lines, markings, arrows, numbers.
- Thin offset decal meshes for hazard marks, faction symbols, lane glyphs, scuffs.
- Shared small textures for noise/wear rather than unique full-size images.
- Procedural UV-independent detail for repeated hard-surface props.

Surface detail must reinforce scale, function, faction, route, or state. Do not add random lines everywhere.

## Color And Readability

Readability beats palette consistency:

- Threats differ from rewards by shape and motion, not only hue.
- Interactables differ from background by silhouette/value/material.
- UI signal colors match world signal colors.
- Bloom/fog/darkness cannot be the primary separator.
- Colorblind-risk information has shape/icon/motion backup.

## Technical Art Report

Report:

- Technical art brief.
- Material kit and shader/VFX decisions.
- Instancing/LOD/culling strategy.
- Render budget target and actual diagnostics.
- Imported/generated asset cleanup evidence.
- VFX readability checks.
- Mobile/DPR/post/shadow tradeoffs.
- Remaining visual performance risks.
