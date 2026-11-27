---
name: threejs-aaa-vfx-builder
description: "Author AAA real-time Three.js game VFX: combat abilities, spells, weapon fire, melee slashes, explosions, shields, portals, boosts, and environmental FX. Covers 5-beat choreography, anti-circle 3D topology diversity, 2-pass HDR DepthTexture soft particles and contact rims, procedural noise/curl-flowmap atlases, NaN-safe stylized shaders, dynamic trails and fractal lightning, bone-anchored cast/muzzle anticipation, and optical shockwave/heat-haze/lensing/impact-frame post passes. Use when building or upgrading game VFX; not for base hero/world modeling (threejs-aaa-graphics-builder) or core gameplay/hitstop mechanics (threejs-gameplay-systems)."
---

# Three.js AAA VFX Builder

Build real-time browser VFX that read like crafted studio effects (Riot / Blizzard / UE5 Niagara craft): bold shapes, disciplined timing, depth-softened scene integration, zero-allocation updates, and selective HDR bloom.

Resolve `<this-skill-dir>` from the actual loaded skill file; resolve sibling skills beside it before runner-discovered alternatives.

## References and Starter Kit

Load only what the current VFX task needs:

| Resource | Read / copy when |
| --- | --- |
| `references/vfx-architecture.md` | designing effect choreography, selecting non-circular 3D silhouettes, wiring the 2-pass `DepthTexture` + `HalfFloatType` bloom + optical post pipeline, or setting mobile/QA budgets |
| `references/vfx-shaders-and-textures.md` | baking the shared procedural noise/flowmap/glint atlas, writing NaN-safe GLSL (`DEPTH_FADE_GLSL`, 2-phase flowmap advection, color-ramp erosion, SDF sigils/reticles), or configuring `ImpactPostPass` |
| `references/vfx-geometry-and-motion.md` | building parametric ribbons/domes/beams/shards, dynamic camera-facing lightning or weapon/hand trails, instanced burst/suction sparks, bone-anchored anticipation VFX, character rim/cloth wind coupling, or audio-VFX sync |
| `<this-skill-dir>/assets/vfx-kit/` | drop-in strict-TypeScript modules (`VfxTimeline.ts`, `ProceduralVfxTextures.ts`, `VfxGeometry.ts`, `VfxShaders.ts`, `ImpactPostPass.ts`, `index.ts`) ready to copy into `src/vfx/` and adapt |

## Six Non-Negotiable Laws

1. **Shape and value before bloom.** Every effect must read as a crisp dark-to-bright silhouette with bloom disabled. Use a `HalfFloatType` MSAA `EffectComposer` with selective `UnrealBloomPass` (`threshold >= 1.05`, tight `radius` `0.22–0.34`, restrained `strength` `0.25–0.45`) so only hot cores, impact edges, and flares bloom.
2. **5-beat timing grammar.** Signature VFX are never flat loops or instant pop-ins: *Anticipation* (socket buildup / inward suction) → *Telegraph* (readable threat/lane shape) → *Hold + Impact Climax* (brief 50–110ms stillness/implosion dip before a 1–3 frame visual punch + optical shockwave) → *Sustained Payload* → *Cooling Aftermath* (scorch, embers, settling smoke).
3. **Anti-"spinning circle" topology diversity.** Distinct abilities, weapons, or hazards must use distinct 3D geometric silhouettes (linear rails, 60° cones, 90° orthogonal cages, spline-growth tendrils, catenary chains, cresting fluid waves, flocking swarms, sculpted summons, vertical architectural drops, curved barriers, fault-line ruptures) — never recolored spinning toruses.
4. **Depth-softened scene integration.** Smoke puffs, shields, beams, and energy domes must sample an opaque pre-pass `DepthTexture` (`uHasDepth = 1.0` on WebGL2 desktop; `0.0` fallback on low-end mobile) to fade hard intersections and paint luminous contact rims where VFX touch floors, walls, and characters. Never leave depth-sampling VFX meshes visible during the opaque depth pass (causes WebGL feedback loops).
5. **Zero-alloc, NaN-safe, deterministic.** Pre-allocate all `BufferGeometry`, `InstancedMesh` matrices, ribbon vertex buffers (`DynamicDrawUsage`), and scratch `Vector3`/`Quaternion`/`Matrix4` objects at init. Guard every fractional GLSL power with `pow(max(0.0001, x), p)` and `normalize(v + vec3(1e-5))` — a single `NaN` fragment blacks out the entire `HalfFloatType` bloom framebuffer. Drive effects from accumulated effect time + seeded RNG so `setState`, `setPausedForScreenshot`, and `setReducedMotion` stay deterministic.
6. **Character, camera, and audio coupling.** Anchor anticipation VFX to real bones/sockets (hands, weapon muzzle, blade tip, thruster), drive reactive character Fresnel rim and secondary motion/cloth wind gusts, trigger gameplay hitstop/shake/FOV via `threejs-gameplay-systems`, and align phase-specific SFX via `threejs-audio-generator`.

## Workflow

1. **Audit the game context.** Check active camera distance/angle, renderer/composer setup, art direction palette, and the gameplay events that need VFX.
2. **Author a VFX brief per effect.** Assign each effect a unique 3D topology, 3-value palette (dark rim, mid body, hot HDR core), duration, 5-beat timing markers, socket anchors, and gameplay-clarity clearance (must never hide hitboxes, telegraphs, or the next player decision).
3. **Stand up shared infrastructure once.** Copy or adapt `<this-skill-dir>/assets/vfx-kit/` into `src/vfx/`: one shared procedural texture atlas (`noise`, `flowmap`, `smokePuff`, `starGlint`), optional opaque `DepthTexture` pre-pass (`opaqueGroup` vs `vfxRootGroup`), `HalfFloatType` MSAA composer, and unified `ImpactPostPass`.
4. **Build layered effects, not single meshes.** Combine 3–5 complementary layers per signature effect (e.g., dark contrast backing + carved shader ribbon/shell + instanced debris/glints + socket anticipation + brief pooled `PointLight` + optical shockwave) sharing geometry/materials and respecting the budget below.
5. **Wire deterministic hooks & disposal.** Expose clean `trigger(event)`, `update(dt, elapsed, camera)`, `evaluateAt(t)` (for scrubbable abilities/cutscenes), `setReducedMotion(on)`, and `dispose()` freeing every geometry, material, texture, and render target.
6. **Verify in motion.** Capture unpaused motion sequences (not only paused stills) through `threejs-qa-release` covering anticipation, impact frame/climax, sustain, and cool-off; inspect with bloom on/off and check desktop + mobile renderer diagnostics.

## VFX Budget Guardrails

Stay inside the game's render budget (`threejs-aaa-graphics-builder/references/technical-art.md`):

| Budget item (peak combat) | Desktop target | Mobile target |
| --- | --- | --- |
| Additional VFX draw calls | `<= 45` | `<= 20` |
| Shared procedural VFX textures | `4` (`<= 384px`, baked once) | `4` (`<= 256px`) |
| Dynamic `PointLight`s for VFX | `<= 3` (pooled, intensity `0` at rest) | `0–1` (prefer fake floor light cards) |
| Transparent full-screen overdraw layers | `<= 3` stacked | `<= 1–2` stacked |
| Opaque `DepthTexture` pre-pass | Enabled (opaque group only) | Optional (`uHasDepth = 0.0` fallback) |
| Optical post pass (`ImpactPostPass`) | Enabled (dormant fast-path when idle) | Shockwave/wash only or bypassed on low-end |

## Anti-Patterns

- Spinning glowing toruses + raw `Points` sphere bursts standing in for authored VFX.
- `new EffectComposer(renderer)` without `HalfFloatType` (clamps HDR before bloom) or `bloom.threshold < 0.9` washing out the whole scene.
- Unguarded `pow(x, frac)` or `normalize(vec3(0.0))` in custom shaders causing intermittent full-screen bloom blackouts.
- Hard planar clipping where smoke, domes, or beams intersect the floor.
- Per-frame `new THREE.Vector3()`, `new THREE.BufferGeometry()`, or `new THREE.ShaderMaterial()` allocations inside `update()`.
- Calling `Math.random()` inside VFX trajectories (breaks visual-regression hooks and scrub reproducibility).
- Blocking player visibility or leaving `PointLight`/post-distortion uniforms stuck non-zero after an effect ends or restarts.

## Report

Return the VFX inventory (topologies, palettes, beat timings), shared pipeline changes (depth pre-pass, HDR bloom, `ImpactPostPass`, mobile fallback), active-play + motion evidence covering anticipation/impact/aftermath, peak vs idle renderer diagnostics, and any reduced-motion or budget tradeoffs to the lead for the consolidated verification pass.
