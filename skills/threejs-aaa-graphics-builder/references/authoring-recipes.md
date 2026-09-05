# Authoring Recipes — Models, World, Render

Concrete recipes for building premium browser-game art in Three.js: what to model, how to lay the graphics code out, and how to set up the renderer behind it.

## Contents

- Modeling principles
- Minimum premium asset pass
- Hero vehicle / hero character / obstacle families / rewards / world prop kit
- Procedural geometry techniques
- Graphics architecture and factory contract
- Renderer, camera, lighting, shadows
- Fog, background, post-processing

## Modeling principles

- Silhouette first. A model should be recognizable as a dark shape before materials or glow.
- Combine primitive bases with authored geometry: extrusions, bevels, curves, tubes, lathes, custom buffers, decals, trim, instanced micro-detail.
- Asymmetry and functional parts: hinges, fins, vents, handles, rails, brackets, sensors, cables, panels, bolts.
- Detail goes where the camera looks — player-facing surfaces, not hidden undersides.
- State variants come from material swaps, animated child parts, emissive strips, and VFX sockets.
- Collision proxy stays separate from the detailed visual group.
- Shared geometries/materials and instancing for repeated bolts, panels, lights, windows, spikes, rocks, rail segments.
- Name important child meshes: `cockpitGlass`, `leftEngine`, `hazardTeeth`, `pickupCore`, `collisionProxy`.

## Minimum premium asset pass

A game asking for premium/AAA/showcase quality needs a design-derived asset pass:

- Its focal subject at actual camera scale, with the state cues the core loop needs. This may be a player model, a table and cue, or a set of puzzle pieces.
- Distinct forms and telegraphs for gameplay roles that players must distinguish. A wave game may need several enemies; pool does not need enemies at all.
- Authored interactables and feedback for the actions that exist, without inventing pickups or reward systems to satisfy a quota.
- A reusable world kit sized to the level plan, with enough variation to avoid accidental repetition at the playable camera distance.
- A coherent material kit appropriate to the art direction: trim, decals, roughness variation, or emissive masks where they serve the design.
- Collision proxies where needed and renderer diagnostics for the integrated scene.

Prove one representative playable scene before expanding the kit. The recipes below are options for their genres, not a required shopping list for every game.

## Hero vehicle

Runners, racers, hovercraft, spaceships, drones, arcade vehicles.

- Core hull: `ExtrudeGeometry` or a custom tapered `BufferGeometry`.
- Nose: wedge, intake, sensor strip, bumper, or blade.
- Cockpit: glass dome from sphere/lathe segments, beveled capsule, or faceted canopy.
- Engines: cylinders/cones/tubes with nozzle rings, inner emissive discs, heat fins, trail sockets.
- Wings/fins: extruded triangular or curved plates with bevel and trim lines.
- Undercarriage: skids, landing pads, rail clamps, suspension arms, thruster pods.
- Decals: panel lines, numeric marks, faction glyph, hazard ticks, bolts.
- State cues: boost flares, shield shell, damage scorch, pickup glow, overheat red.
- Collision proxy: one capsule/box/sphere group matching the gameplay footprint.

A box with two cylinders and a glow is a placeholder, not a hero.

## Hero character

Arena fighters, brawlers, platformers, stylized third-person.

- Body mass: torso, pelvis, head/helmet, limbs from tapered capsules and cylinders at custom scales.
- Rig illusion: separate shoulders, elbows, knees, wrists, ankles, belt, backpack, armor plates.
- Identity: visor, mask, hair or helmet crest, color-blocked silhouette, weapon or tool.
- Animation-ready pivots: group limbs under named joints even when animation is procedural.
- Material zones: skin, fabric, armor, metal, glass, emissive accents.
- State cues: hit flash material, shield ring, attack trail socket, stamina/charge glow.
- Collision proxy: capsule or cylinder independent of mesh detail.

Stacked spheres with no costume, joints, or silhouette is a placeholder.

## Obstacle and enemy families

Distinct gameplay reads, each with a unique silhouette, a danger material cue, a telegraph visible from distance, an animation or state change, a collision proxy, and low-cost repeated detail:

- Low barrier: ground-hugging slab, spikes, rails, caution panels, animated warning light.
- Gate/arch: overhead frame, side posts, pulsing pass/avoid lane, moving shutters.
- Moving hazard: rotating arm, sweeper beam, drone, crusher, sliding block, orbiting mines.
- Trap/zone: laser grid, electric puddle, collapsing tile, gravity well, proximity mine.
- Enemy: body core, sensor/head, weapon, shield, locomotion or hover base, attack telegraph.

Recolored cubes and cones are one variant, not a family.

## Rewards and interactables

Readable and desirable while the player is moving.

- Token: outer ring, inner core, value icon, shimmer cards, collect burst socket.
- Shard: faceted crystal, metal bracket, orbiting chips, emissive seam.
- Capsule: glass shell, suspended item, end caps, rotating label strip.
- Power-up: icon silhouette matched to its effect; color and shape differ from score pickups.
- Objective item: larger scale, unique motion, UI echo, stronger lighting and VFX.

For moving collectibles, useful states are idle (rotation, pulse, bob), attract (when attraction is a real mechanic), and collect (vanish, burst, score trail, HUD update). Other interactables use their own transitions, such as aim/contact/settle for a ball or hover/place/upgrade for a tower.

## World prop kit

Modular, instanceable, recombinable:

- Track/road: lane plates, seams, arrows, side rails, guard segments, repair panels.
- Arena: boundary rings, floor tiles, spawn pads, cover blocks, goal markers.
- City/sci-fi: window strips, antennas, rooftop units, bridge trusses, pylons, billboards.
- Nature: rocks from custom faceted buffers, cliffs, roots, crystals, grass cards.
- Industrial: pipes, vents, cables, tanks, crates, gantries, lights, warning signs.
- Space/air: debris panels, satellites, buoys, asteroid chunks, parallax dust.

Layer it: near props create speed and scale, mid props define the playable corridor, far props create depth without stealing draw calls. Build the world as play / near / mid / far / motion layers, and keep every layer clear of threats and the next decision.

## Procedural geometry techniques

| Class | Use for |
| --- | --- |
| `ExtrudeGeometry` | panels, fins, wings, badges, glyphs, signs |
| `LatheGeometry` | capsules, domes, engines, pipes, turret bases |
| `TubeGeometry` | cables, rails, trails, conduits, curved weapons |
| custom `BufferGeometry` | tapered hulls, rocks, shards, wedges, low-poly terrain |
| `ShapeGeometry` | decals, flat icons, trim strips, hazard markers |
| `InstancedMesh` | windows, bolts, lane markers, debris, grass, lights |
| `LOD` | hero/background variants, dense prop reductions |

When real bevel geometry is too expensive, fake it: duplicate thin trim meshes, edge strips, or slightly offset darker panels.

Use roughness/metalness contrast rather than hue contrast alone; emissive for authored signals rather than whole objects; glass and clearcoat sparingly on hero details; a darker contact material under important objects; decals to imply scale and function; UI icon shapes reused as world decals for cohesion.

## Graphics architecture

Keep these concepts separate even when a small project puts several in one file: materials, authored geometry, repeated props, effects, render settings, diagnostics.

```text
src/assets/MaterialLibrary.ts          src/assets/ProceduralTextures.ts
src/assets/DecalShapes.ts              src/assets/ImportedAssetRegistry.ts
src/assets/modelFactories/{Hero,Obstacle,Reward}Factory.ts
src/assets/modelFactories/WorldPropKit.ts
src/systems/LightingRig.ts             src/systems/RenderPipeline.ts
src/systems/VfxSystem.ts               src/systems/QualityDiagnostics.ts
```

Factories return a group plus metadata:

```ts
type ModelFactoryResult = {
  root: THREE.Group;
  collision?: THREE.Object3D;
  lod?: THREE.LOD;
  bounds?: THREE.Box3;
  diagnostics?: { meshes: number; materials: number; geometries: number; triangles?: number };
};
```

Imported GLB/FBX models get a loader wrapper returning the same shape plus animation clips. Generation API calls never appear in browser runtime code.

Procedural texture and decal kit — canvas textures, shape geometry, or thin offset meshes for panel lines and hatches, trim sheets and edge bands, window strips and city light grids, hazard stripes and arrows and lane glyphs, scratches and wear and scorch. Set filtering, mipmaps, repeat/wrap, color space, and anisotropy deliberately; avoid unique full-size textures for tiny repeated marks.

## Renderer and camera

- `renderer.outputColorSpace = THREE.SRGBColorSpace`.
- Tone mapping chosen deliberately: `ACESFilmicToneMapping` suits cinematic stylized scenes; simpler tone mapping can read better for bright arcade games.
- Tune exposure against active gameplay, not a static title view.
- Cap DPR: start at `Math.min(devicePixelRatio, 1.5)` on mobile, `2` on desktop, then profile.
- Resize updates canvas, renderer, camera, composer, and UI CSS variables together.
- Camera keeps the next decision visible — player, immediate threat or reward, and route — with foreground speed elements, playable midground, and background scale cues. Check mobile framing separately; narrow layouts usually need different offsets.

## Lighting and shadows

A small readable stack: key (defines form), fill (keeps gameplay objects legible), rim/back (separates player and hazards from background), practical/emissive (beacons, engines, pickups, arena markers), and contact shadows or blobs (grounding).

Real shadows go to hero, major hazards, and large world anchors. Use smaller shadow maps and fewer casters when profiling shows cost; cheap contact discs or transparent planes for pickups and hovering objects; tune bias against acne and peter-panning. Prefer baked-looking emissive cues, light cards, and small unlit decals over many unmeasured dynamic lights.

## Fog, background, post

Fog reveals depth and mood; it does not stand in for an empty world. Layer background silhouettes at varied scales and heights, add parallax for motion-heavy games, and keep hazards and rewards readable against fog values.

Post is a finishing pass: bloom on authored emissive elements only, subtle vignette, low-opacity grain, chromatic aberration only for brief event-driven impacts, and geometry trails in preference to motion blur. Compare screenshots with post on and off, and profile the cost — concrete chain settings are in `shader-cookbook.md`.

When performance drops, cut post and shadow cost first, then cull/LOD/instance, then reduce asset density where it is least visible.
