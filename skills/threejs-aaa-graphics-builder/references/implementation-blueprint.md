# AAA Graphics Implementation Blueprint

Use this when a Three.js game reads as basic even after it is playable. The goal is a production graphics architecture that can be iterated, scored, profiled, and reused. For premium/AAA/showcase work, also load `references/technical-art.md` and treat the technical art brief and budget as part of the graphics architecture.

## Recommended Ownership

```text
src/assets/MaterialLibrary.ts
src/assets/ProceduralTextures.ts
src/assets/DecalShapes.ts
src/assets/ModelDiagnostics.ts
src/assets/ImportedAssetRegistry.ts
src/assets/modelFactories/HeroFactory.ts
src/assets/modelFactories/ObstacleFactory.ts
src/assets/modelFactories/RewardFactory.ts
src/assets/modelFactories/WorldPropKit.ts
src/systems/LightingRig.ts
src/systems/RenderPipeline.ts
src/systems/VfxSystem.ts
src/systems/WorldArtDirector.ts
src/systems/QualityDiagnostics.ts
```

Keep these boundaries lightweight. In small projects, a single file can contain multiple factories, but the concepts must remain separate: materials, authored geometry, repeated props, effects, render settings, and diagnostics.

## Hybrid AI Asset Pipeline

Choose the asset path per surface:

- Procedural Three.js: repeated detail, simple props, rails, track parts, decals, collision proxies, VFX geometry, debug-friendly primitives.
- `threejs-image-generator`: concept sheets, T-pose/A-pose references, texture references, trim sheets, decals, icons, logos, skies, backgrounds, UI art.
- `threejs-3d-generator`: hero/player, characters, creatures, vehicles, buildings, weapons, signature props, pickups, bosses, complex terrain modules.
- Hybrid: image-generator concept/reference -> 3D-generator image-to-model -> Three.js import -> procedural collision/VFX/prop kit -> visual scorecard.

For premium/AAA/showcase/high-fidelity/less-basic games, do not decide `threejs-3d-generator` or `threejs-image-generator` is unnecessary before loading the relevant skill when the game includes characters, creatures, vehicles, ships, weapons, buildings, signature props, hero pickups, skies, textures, decals, logos, icons, or GUI art. Load first, run the credential probe, then document the tradeoff.

Use `threejs-3d-generator` when generated model fidelity will materially improve the active screenshot. Do not use generated 3D for every repeated small prop; use instancing/procedural kits for volume.

For premium hero surfaces, procedural-only is not a valid final choice unless a real blocker is recorded: missing key from the credential probe, API/network/quota error after an attempted command, user requested no external assets, or offline-only constraint. Repeated low-value props can stay procedural.

Asset sourcing ledger:

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
- External assets generated: yes/no, task IDs/paths or allowed skip reason:
```

## Production Surfaces

A premium pass must touch every weak visible surface:

- Hero/player: authored silhouette, state feedback, decals/trim, readable front/up/side, collision proxy.
- Hazards/enemies: at least three distinct silhouettes with telegraphs and material cues.
- Rewards/interactables: at least two forms with collection states and motion/VFX hooks.
- World kit: foreground, playable lane/arena, midground, background/parallax, set dressing, scale cues.
- Materials/textures: shared PBR/stylized material library, procedural panel lines, noise, trim, wear, emissive masks.
- Lighting/render: color space, tone mapping, exposure, shadows/contact, fog/depth, post-processing discipline.
- VFX/motion: event-driven bursts, trails, impact rings, speed lines, shield/boost states, pickup/fail feedback.
- UI/world cohesion: UI colors, icons, alerts, and meters echo gameplay materials and status colors.
- Diagnostics: renderer counts, material/geometry/texture counts, screenshots, scorecard.

For imported generated 3D assets, also require downloaded GLB/PBR output, import wrappers with scale/pivot/bounds, simple collision proxies, animation clips when relevant, and triangle/material/texture/file-size diagnostics.

## Technical Art Contract

Before broad implementation, define:

- Hero surfaces that deserve the highest detail.
- Support surfaces that should be procedural, instanced, culled, or simplified.
- Render budget target: draw calls, triangles, textures, materials, DPR cap, shadow/post budget.
- Material kit roles and shader/VFX purpose.
- Instancing/LOD/culling plan.
- Imported/generated asset cleanup plan.

Do not add costly effects until this contract exists. A technical-art pass should make the scene more authored and more measurable at the same time.

## Material Library

Create named material roles instead of one-off colors:

- `bodyPrimary`: dominant player/world shell.
- `bodySecondary`: panel contrast.
- `trim`: rails, bevel highlights, borders.
- `hazard`: danger surfaces, damage cues, warning stripes.
- `reward`: collectible surfaces with readable value.
- `glass`: cockpit, shield, lens, visor.
- `emissiveSignal`: authored glow strips, status lights, beacon cores.
- `groundContact`: dark matte surfaces and shadow receivers.
- `decalDark` and `decalLight`: panel lines, scratches, numbers, icons.

Use `MeshStandardMaterial` for most surfaces. Use `MeshPhysicalMaterial` selectively for cockpit glass, clearcoat panels, iridescent shields, or premium hero details. Share materials across repeated meshes.

## Procedural Texture And Decal Kit

Use canvas textures, shape geometry, or thin offset meshes for detail that would otherwise require external assets:

- Panel lines and access hatches.
- Trim sheets and edge bands.
- Window strips, city light grids, arena markings.
- Hazard stripes, arrows, target indicators, lane glyphs.
- Scratches, wear, noise, dirt, heat tint, scorch marks.
- UI/world icon motifs reused in HUD and diegetic markers.

Set texture filtering, mipmaps, repeat/wrap, color space, and anisotropy intentionally. Avoid unique full-size textures for tiny repeated marks.

Use `threejs-image-generator` for high-value 2D source art: terrain/rock/asphalt/snow/moss texture references, sci-fi trim sheets, signs, hazard stripes, cockpit decals, sky/background plates, menu/loading art, faction logos, pickup icons, ability icons, and GUI glyphs. Use the resulting images either as actual 2D assets or as image-to-3D inputs.

## Model Factories

Factories should return a grouped object plus metadata:

```ts
type ModelFactoryResult = {
  root: THREE.Group;
  collision?: THREE.Object3D;
  lod?: THREE.LOD;
  bounds?: THREE.Box3;
  diagnostics?: {
    meshes: number;
    materials: number;
    geometries: number;
    triangles?: number;
  };
};
```

Use named child meshes for readable debugging. Separate visual detail from collision proxies. Keep repeated detail instanced where practical.

For imported generated 3D models, create an `ImportedAssetRegistry` or loader wrapper that returns similar metadata: root group, bounds, collision proxy, animation clips, and diagnostics. Never put 3D/image/audio generation API calls in browser runtime code.

## World Art Director

Build the world as layers:

- Play layer: ground, lanes, rails, objective path, hazards, pickups.
- Near layer: speed props, signs, arches, barriers, debris, foreground occluders used carefully.
- Mid layer: buildings, cliffs, hangars, pillars, platforms, arena machinery.
- Far layer: skyline, terrain silhouettes, nebula/cloud/fog cards, parallax planes.
- Motion layer: speed lines, particles, trail strips, dust, sparks, screen-space UI feedback.

Every layer should support gameplay readability. Do not obscure threats or the next decision.

## Render Pipeline

Own renderer setup in one place:

- `outputColorSpace = THREE.SRGBColorSpace`.
- Tone mapping and exposure selected for the art direction.
- DPR capped for mobile and high-density displays.
- Shadows enabled only for objects that benefit from grounding.
- Post-processing is limited and measured: bloom, vignette, chromatic aberration, film grain, or color grade only when they improve authored forms.
- Resize updates canvas, renderer, camera, composer, and UI CSS variables.

## VFX System

Effects should be event-driven, pooled, and readable:

- Pickup: ring contraction, shard burst, score trail, brief HUD echo.
- Hit/fail: impact flash, debris, camera impulse, temporary slow/hit pause.
- Boost/speed: engine trail, lane streaks, FOV ease, audio pitch.
- Near miss/combo: side spark, line snap, badge pulse.
- Shield/invulnerable: refractive shell, rim pulse, material swap.

Avoid permanent particle clutter. Effects must clarify state.

## Diagnostics

Expose or log:

- Renderer calls, triangles, geometries, textures.
- Scene mesh count, instanced mesh count, unique materials/geometries/textures.
- Approximate visible prop counts by layer.
- Screenshot paths and visual scorecard.
- Performance notes after post-processing, shadows, or many repeated props.

## Browser Game Budgets

Budgets vary by game and device, but start with explicit targets:

- Keep draw calls low through instancing and shared materials.
- Prefer many small details through instanced meshes over many unique mesh/material pairs.
- Cap DPR before removing all visual detail.
- Use LOD or distance culling for background props.
- Measure after every major graphics pass.

## Implementation Order

1. Score active screenshots and identify the weakest three categories.
2. Add material and diagnostic foundations.
3. Decide which weak surfaces need procedural, `threejs-image-generator`, `threejs-3d-generator`, or hybrid treatment.
4. Build/import hero/player and one complete obstacle/reward family.
5. Add world prop kit and layered composition.
6. Add lighting/render polish.
7. Add event-driven VFX.
8. Re-score desktop/mobile active screenshots.
9. Optimize measured bottlenecks.
