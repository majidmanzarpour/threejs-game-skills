# AAA VFX Geometry, Dynamic Trails, Character Coupling & Audio Sync

Procedural VFX geometry, zero-allocation dynamic motion strips, bone-anchored anticipation VFX, character reactions, and timeline-synced SFX. Ready-to-use strict-TS builders live in `<this-skill-dir>/assets/vfx-kit/VfxGeometry.ts`.

---

## 1. Parametric VFX Geometry Primitives

Build VFX meshes with UVs aligned to motion flow (`U` = along length/angle, `V` = across width/radius) so every shader scrolls cleanly without distortion:

| Builder | UV Layout | Best Uses |
| --- | --- | --- |
| **Polar Ring / Cupped Disc** | `U = angle [0..1]` (seamless), `V = radius [0..1]` | Ground telegraphs, swirling vortices, shockwave rings, blast scorches, launch pads. Slight quadratic `cupHeight` lifts edges off uneven terrain. |
| **Tapered Banking Arc Ribbon** | `U = arc length [0..1]`, `V = width [0..1]` | Melee sword slashes, spiral energy arcs, projectile wakes, drift streaks. Taper width at head/tail (`widthTaper`) and bank/twist along `U` for calligraphic 3D volume. |
| **Muzzle Crescent Ring** | Perpendicular to `+Z` with conical forward flare | Gun/cannon/staff muzzle blasts, thruster shock diamonds, speed-boost rings. |
| **Open Cupola Energy Dome** | `U = azimuth [0..1]`, `V = base→apex [0..1]` | Forcefields, stasis bubbles, barrier domes. Subtle bell-flare at base creates strong contact read with `DEPTH_FADE_GLSL`. |
| **Tapered Beam + Helical Wrap** | `U = along +Z [0..1]` | Lasers, railguns, healing tethers, tractor beams. Pair a hot opaque-core cylinder with 1–2 additive twisting helix ribbons so the beam reads 3D from any angle. |
| **Flat-Shaded Shards / Spires / Debris** | Non-indexed crisp facet normals | Ice prisons, shattered shields, rock eruptions, orbiting chunks. Always call `.toNonIndexed()` + `.computeVertexNormals()` for razor-sharp specular facets. |

---

## 2. Dynamic Camera-Facing Strips (Zero Allocation)

Static cylinder lightning and `THREE.Line` trails look thin and break in WebGL (where `linewidth` is locked to `1px`). Use pre-allocated 2-vertex-per-segment triangle strips (`BufferAttribute.setUsage(THREE.DynamicDrawUsage)`) oriented perpendicular to `(segmentTangent × toCamera)` every frame:

### A. 24fps Stepped Fractal Lightning Strip
- Quantize time to `Math.floor(t * 24)` as the seeded RNG frame key — authentic crunchy animation snap without jittering at 120Hz.
- Displace interior spine points perpendicular to the `(start → end)` orthonormal basis with a sine envelope `sin(u * PI)` so endpoints stay locked cleanly onto sockets/targets.
- Extrude each spine vertex left/right by `normalize(cross(tangent, toCamera)) * halfWidth`, tapering `widthStart → widthEnd`.
- Set `mesh.frustumCulled = false` on dynamic vertex-updated strips so Three.js never culls them using stale init bounds.

### B. Ring-Buffer Weapon / Hand / Thruster Ribbon Trail
- Maintain a fixed circular buffer of `N` (typically `16–32`) world-space sample positions (`Vector3[]`, pre-allocated).
- On `update(anchorPos, dt)`: append only when moved `> minStep` (or interpolate smoothly); on reset/teleport/pause-scrub, clear the ring to `anchorPos` so trails never stretch across the arena!
- Taper strip width smoothly from head (`1.0`) to tail (`0.0`) and fade alpha in the fragment shader along `vUv.x`.

---

## 3. Instanced Burst & Inward Suction Particles

Use one `InstancedMesh` (billboarded star-glint quads or faceted shards) per particle family instead of hundreds of individual `Mesh` objects:

- **Pre-allocate** per-particle deterministic parameters (`seedAngle`, `radius`, `speed`, `phaseOffset`, `scale`, `spin`) once using `createSeededRng(seed)`.
- **Inward Suction (Anticipation Beat)**: map local cycle `p = fract(t * rate + phaseOffset)` so particles spiral *inward* from outer radius `R` toward the emitter socket `(1 - p)^1.6`, scaling up as they converge and vanishing cleanly at the core.
- **Outward Burst (Impact Beat)**: evaluate ballistic arcs parametrically (`pos = origin + dir * speed * age + 0.5 * gravity * age * age`) with ground bounce clamping (`y = max(0.05, y)`) and squash-stretch along velocity.
- Set `instancedMesh.instanceMatrix.needsUpdate = true` **once** per frame after writing all active instances (hide inactive slots via zero-scale matrix).

---

## 4. Character & Socket Coupling (Bone-Anchored Anticipation)

Standalone world VFX floating in front of a rigid character feels disconnected. Couple effects directly to the actor:

### Multi-Layer Socket Anticipation Pattern (Hands / Muzzles / Thrusters / Blades)
For casting hands, charging cannons, or primed melee weapons, combine up to 6 lightweight layers anchored via `bone.getWorldPosition(tmpPos)` (refreshing `skeletonRoot.updateMatrixWorld(true)` once before reading sockets):

1. **Displaced Fresnel Plasma Core** (small icosahedron per socket with vertex ripple + Fresnel/void shader).
2. **Rotating Procedural SDF Sigil / Reticle** (billboarded or palm/muzzle-plane quad matched to the ability's style).
3. **Sweeping Socket Trails** (ring-buffer ribbon trails following hand/blade/wingtip motion during wind-up).
4. **Inter-Socket Arc** (for dual-hand/twin-emitter casts: a single dynamic camera-facing plasma helix or 24fps lightning strip bridging Left → Right socket while distance is within charge range).
5. **Inward Suction Motes** (`InstancedMesh` of 32–64 star glints spiraling into the socket).
6. **Release Star-Flare + Pooled Socket `PointLight`** (snaps bright on release frame, decays smoothly to `0` so no light leaks into idle states).

### Reactive Character Lighting & Secondary Motion
- **Reactive Fresnel Rim**: inject or modulate a Fresnel rim uniform on caster and target materials synced to the active ability's primary HDR color — immediately seats characters into bright VFX illumination without adding extra lights.
- **Secondary Motion / Cloth Wind Gust**: expose a simple scalar/vector `windImpulse` from active VFX (`anticipation` = gentle inward pull, `climax` = sharp radial blast wave) to drive cape/cloth/hair/antenna spring simulations.
- **Hit Reaction Alignment**: keep target recoil/knockback/stasis tilt aligned with the impact vector and verify skeleton bind-pose axes (see `threejs-3d-generator/references/threejs-integration.md` for Blender Z-up / Mixamo Hips bind compensation).

---

## 5. VFX ↔ Audio Synchronization

Pair with `threejs-audio-generator` using explicit timeline cue markers instead of guessing delays with `setTimeout`:

```ts
interface VfxAudioCue {
  id: string;
  at: number; // seconds from effect start
  volume?: number;
  pitchJitter?: number;
}
```
- Trigger cue `c` when `prevTime < c.at && currTime >= c.at` (one-shot crossing test).
- On pause, reset, or timeline scrub jump (`currTime < prevTime` or `dt > 0.25`), stop active one-shots and reset the cue cursor cleanly so scrubbing never stacks overlapping audio.
- Match `threejs-gameplay-systems/references/game-feel.md` ducking + `playbackRate` pitch modulation during hitstop or slow-motion beats.
