# Technical Art For Three.js Games

Readable authored detail that survives active gameplay, mobile viewports, and WebGL budgets — not maximum detail.

## Render budget starting points

Starting contracts, not universal limits. Measure on the target game; document every deliberate overrun as a tradeoff. The canvas inspector (`npm run inspect:canvas`) compares live diagnostics against these numbers and reports over-budget rows.

| Metric (worst active-play view) | Desktop | Mobile |
| --- | --- | --- |
| Draw calls (`info.render.calls`) | <= 300 | <= 150 |
| Triangles (`info.render.triangles`) | <= 750k | <= 300k |
| Geometries (`info.memory.geometries`) | <= 300 | <= 200 |
| Textures (`info.memory.textures`) | <= 60 | <= 40 |
| Texture memory (est.) | <= 256 MB | <= 128 MB |
| Shadow-casting lights | <= 2 | 1 |
| Shadow map size | <= 2048 | <= 1024 |
| DPR cap | 2 | 1.5-2 |
| Post passes (beyond render+output) | <= 2 | 0-1 |

Where to spend: draw calls go to instanced or material-merged repeats; triangles go to silhouettes near the camera, with LOD or impostors behind; unique material count grows faster than geometry count, so share roles aggressively; real shadows go to hero objects and grounding anchors, with blob/contact meshes for small repeated props (cheap contact-shadow recipe in `shader-cookbook.md`).

Report actual diagnostics after a graphics pass: calls, triangles, geometries, textures, materials, post passes, shadow settings, DPR cap, and the bottleneck.

## Material kit

Named shared roles, reused across every mesh that plays the same part — not one-off colors:

`bodyPrimary` (dominant shell) · `bodySecondary` (panel contrast) · `trim` (rails, bevels, edge highlights) · `hazard` (danger, damage, warning stripes) · `reward` (collectibles) · `shieldBoost` (shield/boost/status) · `glass` (cockpit, lens, visor) · `emissiveSignal` (authored glow strips, status lights) · `groundContact` (dark matte, shadow receivers) · `decalDark` / `decalLight` (panel lines, scratches, numbers).

UI signal colors and world signal colors come from the same set.

`MeshStandardMaterial` for most surfaces; `MeshPhysicalMaterial` selectively for cockpit glass, clearcoat panels, iridescent shields, hero details.

Shader and `onBeforeCompile` work earns its place through state readability (shield ripple, heat, cloak, damage pulse), surface identity (water, forcefield, hologram, energy core), cheap procedural variation replacing textures, or separating player/threat/reward from background. Use the proven values and GLSL patterns in `shader-cookbook.md` rather than improvising.

## VFX

Event-driven, tied to gameplay state, pooled, with geometries and materials reused:

- Pickup: ring contraction, shard burst, score trail, brief HUD echo.
- Hit/fail: impact ring, debris, damage flash, hit pause, camera impulse.
- Boost/speed: engine trail, lane streaks, FOV ease, side streaks, audio pitch.
- Near miss/combo: side spark, line snap, badge pulse, streak counter.
- Shield: refractive shell, rim pulse, absorbed-impact ripple, material swap.
- Spawn/despawn: anticipation pulse, telegraph, dissolve or scale snap.

Each effect should point at the player, a threat, a reward, or an impact, and clear the collision volume, the HUD, and the next decision. Heavy shake and strobe need a reduced-motion fallback.

Threats read differently from rewards by shape and motion, not only hue; interactables separate from background by silhouette, value, and material. Anything conveyed by color alone needs a shape, icon, or motion backup.

## Instancing, LOD, culling

Instance many copies sharing geometry and material with varying transforms: windows, bolts, lane markers, city lights, debris, stars, crowd cards, track panels, repeated pickups, background modules.

- Set `instanceMatrix.needsUpdate` / `instanceColor.needsUpdate` once after a batch of changes, not per instance.
- Recompute bounds for instanced groups when transforms move materially.
- Different materials or constantly changing transforms erase the win — instancing is not free.
- Collision stays separate from instanced visual detail.

LOD earns its place when an object spans large distance ranges, when the silhouette only matters near camera, or when an imported model is heavier than a background role needs. Add hysteresis or distance gaps so transitions do not pop, and check them under gameplay camera motion rather than static orbit.

## Imported and generated asset cleanup

For every imported GLB/FBX hero asset: confirm scale, pivot, forward/up orientation, bounds, and active-play silhouette; build a collision proxy independent of the visual mesh; inspect file size, triangles, mesh/material/texture counts, and animation clips; simplify excessive materials and textures; add an LOD or simplified variant when reused many times; check PBR readability under the game's own lighting rather than a model viewer.

API keys and temporary download URLs stay out of client code and out of checked-in files.

## Surface detail

Reusable systems beat one-off geometry: canvas-generated trim sheets for panel lines, markings, arrows and numbers; thin offset decal meshes for hazard marks, faction symbols, lane glyphs, scuffs; shared small noise/wear textures instead of unique full-size images; procedural UV-independent detail for repeated hard-surface props.

Surface detail reinforces scale, function, faction, route, or state.
