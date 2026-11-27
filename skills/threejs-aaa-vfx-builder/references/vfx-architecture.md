# AAA VFX Architecture — Choreography, Topologies, and HDR 2-Pass Pipeline

Design reference for real-time Three.js VFX systems targeting `three ^0.184` (`three/addons/*`).

## 1. The 5-Beat Timing Grammar

Great game VFX is music in 3D space. Flat constant-intensity effects feel amateur even with expensive shaders; deliberate contrast between **stillness**, **compression**, and **release** makes simple geometry feel explosive.

| Beat | Typical share | Visual & Motion Purpose | Key Techniques |
| --- | --- | --- | --- |
| **1. Anticipation** | 15–25% | Signals who is acting and builds energy before release. | Bone/socket plasma core, inward suction sparks, hand/muzzle SDF sigil, rising pitch SFX. |
| **2. Telegraph** | 10–20% | Communicates *where* and *what shape* the effect covers so players can react. | Ground decal/stencil/corridor outline, converging target reticle, crisp edge rim with low interior alpha. |
| **3. Pre-Impact Hold + Climax** | 5–12% | **The AAA secret**: a 50–110ms implosion dip / silence beat immediately followed by a 1–3 frame visual peak. | Intensity curve drops toward `0` briefly, then spikes to `2.5–3.0x` HDR + 1–3 frame bespoke impact frame + radial optical shockwave + hitstop (`threejs-gameplay-systems`). |
| **4. Sustained Payload** | 30–45% | Carries the signature 3D silhouette and gameplay read (damage zone, shield, beam, swarm). | Multi-layered authored 3D geometry + 2-phase curl flowmap erosion + depth-softened contact rims + dynamic trails/lightning. |
| **5. Cooling Aftermath** | 15–25% | Grounds the event back into the world without popping out. | Eroding alpha dissolve (hot glowing edge → dark soot), charred ground scorch, drifting ember/ash glints, smooth light decay to `0`. |

### Intensity Curve Design
Drive every major effect from an analytical curve (or piecewise ease table) so lighting, bloom strength, camera punch, and audio stay locked together:
- **Fast attack, expressive settle**: use `easeOutExpo` / `easeOutBack` for bursts and `easeInCubic` for implosion pull-ins.
- **Avoid symmetric sine fades** for impacts — impacts snap open in `30–70ms` and decay asymmetrically over `400–1200ms`.
- **Scrubbable evaluation**: prefer pure functions of effect age `t` (`evaluate(t)`) over fragile frame-integrated Euler drift wherever possible. Even pooled projectile/particle bursts can evaluate parametrically (`pos(t) = p0 + v0*t + 0.5*g*t^2`), making pause, hitstop, slow-mo, and Playwright visual baselines 100% deterministic.

---

## 2. Anti-"Spinning Circle" Topology Diversity Matrix

Models default to horizontal glowing rings and spherical particle clouds. Enforce structural silhouette diversity across an ability kit or enemy roster by assigning each effect a distinct geometric family from this matrix:

| Topology Family | Structural Silhouette | Best Game Uses | Signature Layer Stack |
| --- | --- | --- | --- |
| **Linear Rail / Corridor** | Long ground lane + collimated lance + chevron accelerator gates | Railguns, sniper beams, dash lanes, piercers | Tapered beam cylinder + helical wrap + muzzle crescent rings + scorched lane decal |
| **Angular Cone / Wedge (45°–75°)** | Sweeping volumetric fan anchored at emitter | Flamethrowers, dragon breath, shotgun blasts, shock cones | Layered crescent fire/plasma ribbons + depth-softened smoke puffs + drifting ember glints |
| **90° Orthogonal Cage / Grid** | Hard-edged rectilinear pillars, scan planes, wireframe prisms | Sci-fi traps, cyber hacks, stasis cells, shield walls | Sharp box/frame `InstancedMesh` + scrolling scanline shader + digital glitch impact frame |
| **Spline-Growth Organic Tendrils** | Rising/snaking tapered tubes with thorns or leaves | Roots, corruption, lightning-vines, tentacle snares | Progressive `TubeGeometry` (`drawRange` growth) + instanced petal/thorn burst + ground crack |
| **Catenary Chains / Tethers** | Sagging physical links binding caster/anchor to target | Grappling hooks, soul shackles, energy tethers, tow beams | Instanced chain links sampled along sagging catenary curve + tension flash at lock |
| **Cresting Fluid Wave & Crown** | Sweeping asymmetric curl crest + upward splash crown | Water/lava/acid surges, tsunami slams, slime bursts | Custom bent-wave buffer mesh + 2-phase flowmap foam + radial splash crown + foam rings |
| **Flocking / Murmuration Swarm** | 40–180 coherent instanced bodies orbiting or diving in streams | Homing missiles, insect/bird flocks, blade storms, nanites | Single `InstancedMesh` (folded origami/darts/blades) + curled Boid/spline paths + ribbon wisps |
| **Sculpted Architectural Drop** | Monolithic geometric form descending vertically onto target | Meteor/anvil slams, guillotine blades, orbital strikes, turrets | High-contrast hero VFX mesh + vertical descent trail + radial dust/debris ring + fracture cracks |
| **Curved Refractive Wall / Dome** | Asymmetric faceted shield or cupped hemisphere with glowing base seam | Forcefields, time bubbles, ward barriers, cloak fields | Open cupola / curved panel mesh + `DEPTH_FADE_GLSL` floor seam + Fresnel rim + spherical lens warp |
| **Gravitational Singularity** | Dark absorbing center + warped accretion disc + infalling debris | Black holes, void rifts, emp implosions, vortex pulls | Pitch-black core + bright photon ring + orbiting `InstancedMesh` debris + Einstein-ring post lensing |
| **Zigzag Fault-Line Rupture** | Jagged segmented ground fissure + erupting magma/shard slabs | Earthquakes, tectonic slams, mine chains, ice spikes | Multi-segment jagged path + raised beveled basalt/crystal slabs + localized heat-haze shimmer |
| **Stepped Fractal Arcs** | 24fps crisp camera-facing lightning bolts jumping between nodes | Chain lightning, tesla coils, plasma overloads, short-circuits | Dynamic camera-facing strips (`DynamicDrawUsage`) + node sparks + stepped chromatic pulse |

---

## 3. 2-Pass HDR DepthTexture + Selective Bloom + Optical Post Pipeline

A single-pass `EffectComposer(renderer)` breaks AAA VFX in two fatal ways:
1. Default `EffectComposer` allocates an **8-bit `UnsignedByteType`** target, clamping HDR values (`> 1.0`) before `UnrealBloomPass` ever runs.
2. Transparent meshes have no access to scene depth, producing harsh straight-line intersections where smoke, domes, and beams clip the floor or characters.

### Scene Graph Split (Prevents WebGL Feedback Loops)

Split the scene into two top-level groups:
- **`opaqueGroup`**: terrain, arena, buildings, characters, props — everything that writes to depth.
- **`vfxRootGroup`**: transparent VFX, soft smoke, domes, ribbons, beams, particles — everything that reads `tDepth`.

> **Critical WebGL2 rule:** Hide `vfxRootGroup` (`vfxRootGroup.visible = false`) during the opaque depth pre-pass, then restore it before `composer.render()`. If a shader samples `tDepth` while rendering into `depthTarget`, WebGL triggers `GL_INVALID_OPERATION: Feedback loop` and renders black.

### Complete Pipeline Wiring

```ts
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { createImpactPostPass, type DepthSharedUniforms } from './vfx-kit';

// 1. Opaque Depth Pre-Pass target (WebGL2 FloatType DepthTexture)
const drawBuf = new THREE.Vector2();
renderer.getDrawingBufferSize(drawBuf);

const depthTarget = new THREE.WebGLRenderTarget(drawBuf.x, drawBuf.y, {
  minFilter: THREE.NearestFilter,
  magFilter: THREE.NearestFilter,
});
depthTarget.depthTexture = new THREE.DepthTexture(drawBuf.x, drawBuf.y, THREE.FloatType);
depthTarget.depthTexture.format = THREE.DepthFormat;

export const depthShared: DepthSharedUniforms = {
  tDepth: { value: depthTarget.depthTexture },
  uResolution: { value: drawBuf.clone() },
  uCameraNear: { value: camera.near },
  uCameraFar: { value: camera.far },
  uHasDepth: { value: renderer.capabilities.isWebGL2 ? 1.0 : 0.0 },
};

// 2. HDR MSAA EffectComposer (HalfFloatType preserves > 1.0 HDR values for selective bloom!)
const hdrTarget = new THREE.WebGLRenderTarget(width, height, {
  type: THREE.HalfFloatType,
  samples: renderer.capabilities.isWebGL2 ? 4 : 0,
});
const composer = new EffectComposer(renderer, hdrTarget);
composer.addPass(new RenderPass(scene, camera));

// Selective bloom: only HDR pixels > 1.05 bloom; tight radius keeps graphic edges sharp.
const bloomPass = new UnrealBloomPass(
  new THREE.Vector2(width, height),
  0.32, // strength (modulate dynamically up to ~0.55 on climax peaks)
  0.28, // radius (tight halo, never muddy fog)
  1.06, // threshold (> 1.0 keeps non-HDR lit surfaces completely crisp!)
);
composer.addPass(bloomPass);

// Tone mapping + sRGB BEFORE display-space optical impact overlays
composer.addPass(new OutputPass());

// Unified optical refraction / heat-haze / lensing / impact-frame pass
const impactPass: ShaderPass = createImpactPostPass(width / height);
composer.addPass(impactPass);
```

### Per-Frame Render Order & Resize Sync

```ts
function renderFrame(enableDepthPass: boolean): void {
  if (enableDepthPass && depthShared.uHasDepth.value > 0.5) {
    vfxRootGroup.visible = false;
    renderer.setRenderTarget(depthTarget);
    renderer.clear();
    renderer.render(scene, camera);
    renderer.setRenderTarget(null);
    vfxRootGroup.visible = true;
  }
  composer.render();
}

function resizePipeline(w: number, h: number, maxDpr: number): void {
  const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
  renderer.setPixelRatio(dpr);
  renderer.setSize(w, h, false);
  composer.setPixelRatio(dpr);
  composer.setSize(w, h);
  bloomPass.resolution.set(w, h);

  renderer.getDrawingBufferSize(drawBuf);
  depthTarget.setSize(drawBuf.x, drawBuf.y);
  depthShared.uResolution.value.copy(drawBuf);
  depthShared.uCameraNear.value = camera.near;
  depthShared.uCameraFar.value = camera.far;
  impactPass.uniforms.uAspect.value = w / Math.max(1, h);
}
```

> **Note on Three.js r184 shadows:** Prefer `renderer.shadowMap.type = THREE.PCFShadowMap` (matches the scaffold; `PCFSoftShadowMap` is deprecated in modern Three.js).

---

## 4. Mobile & Low-End Tiering

Degrade gracefully without rewriting shaders:

| Quality Tier | DPR Cap | Depth Pre-Pass | MSAA Samples | Bloom | Optical `ImpactPostPass` |
| --- | --- | --- | --- | --- | --- |
| **Desktop / High** | `2.0` | On (`uHasDepth = 1.0`) | `4` | On (`threshold 1.06`) | Full (shockwave, heat-haze, lensing, impact frames) |
| **Mobile / Mid** | `1.5` | Off (`uHasDepth = 0.0`) | `0` | On (half-res or lower DPR) | Shockwave & color wash only (disable heavy Voronoi/lensing loops) |
| **Low-End Fallback** | `1.25` | Off (`uHasDepth = 0.0`) | `0` | Off (direct `renderer.render`) | Bypassed (brief CSS flash for heavy impacts) |

---

## 5. Deterministic Testing & Reduced-Motion Contract

Every VFX system integrated into a game with `threejs-qa-release` must honor the scaffold hooks:
- **`seed(n)`**: seed all VFX trajectory/lightning/shard generators via `createSeededRng(n)` — never `Math.random()`.
- **`setPausedForScreenshot(true)`**: freeze effect age `t` immediately; keep `composer.render()` active so paused screenshots capture crisp mid-climax frames.
- **`setReducedMotion(true)`**: clamp or disable full-screen strobing impact frames (`uImpactFrame = 0`), rapid chromatic aberration, and heavy camera shake while preserving readable 3D shapes, telegraphs, and color washes.
- **Named VFX states**: expose representative combat states (e.g., `vfx-anticipation`, `vfx-climax`) in `setState(name)` so visual baselines can assert both silhouettes and post-pass integration.
