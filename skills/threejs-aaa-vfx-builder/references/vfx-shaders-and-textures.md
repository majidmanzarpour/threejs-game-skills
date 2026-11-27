# AAA VFX Shaders, Procedural Texture Atlas, and Optical Post-Pass

Battle-tested GLSL ES 3.0 and startup-baked `DataTexture` recipes. Strict TypeScript implementations of all patterns below live in `<this-skill-dir>/assets/vfx-kit/` (`ProceduralVfxTextures.ts`, `VfxShaders.ts`, `ImpactPostPass.ts`).

---

## 1. HDR NaN-Safety Rules (Mandatory for All Custom Shaders)

Under a `HalfFloatType` `EffectComposer` + `UnrealBloomPass`, **a single `NaN` or `Inf` fragment spreads through the Gaussian blur mip chain and blacks out the entire screen**. Enforce these four rules in every VFX shader:

1. **Guard every `pow()` (including `pow(x, 2.0)`):** `pow(x, y)` is undefined in GLSL ES 3.0 whenever `x < 0.0` (or `x == 0.0 && y <= 0.0`), even for integer exponent `2.0` on Metal/ANGLE! Use `x * x` for squares and `pow(max(0.0001, x), y)` for fractional exponents (e.g. `pow(max(0.0001, 1.0 - ndotv), 2.2)`).
2. **Guard every `normalize()`:** When normalizing a view/position/tangent vector that could collapse to zero, write `normalize(v + vec3(1e-5))` or check `length(v) > 1e-4`.
3. **Guard every division and `smoothstep(e0, e1, x)`:** Never divide by a uniform/radius without `max(denom, 1e-4)`; ensure `e0 < e1` in `smoothstep`.
4. **Clamp HDR output ceilings:** Keep peak emissive multipliers bounded (`<= 4.0–6.0`) so bloom halos stay crisp instead of blowing out into solid white rectangles.

---

## 2. Shared Startup-Baked Procedural Texture Atlas (Zero Network Cost)

Bake four compact, seamless textures **once** at startup and share them across every ability/effect (`4` textures total, `< 1.5 MB` GPU memory):

| Texture | Resolution | Channel Packing | Primary Uses |
| --- | --- | --- | --- |
| **4-Channel VFX Noise Atlas** (`RepeatWrapping`) | `320×320` (desktop) / `256×256` (mobile) | **R**: domain-warped organic FBM<br>**G**: 4:1 anisotropic painterly streaks<br>**B**: 8:1 crisp calligraphy shreds<br>**A**: seamless Voronoi caustic ridges | Ground vortices, slash ribbons, domes, plasma dissolution, ice/magma cracks, shield energy. |
| **2D Curl-Noise Flowmap** (`RepeatWrapping`) | `256×256` | **RG**: divergence-free velocity `(dPsi/dy, -dPsi/dx)` mapped to `[0..1]`<br>**B**: curl magnitude<br>**A**: fine eddy scalar | 2-phase ping-pong UV advection — organic swirling fluid/smoke/fire motion with **zero rigid scrolling or loop pop**. |
| **Stylized Smoke Puff** (`ClampToEdge`) | `256×256` | **R**: directional top-lit shading<br>**G**: coarse billow FBM<br>**B**: fine erosion mask<br>**A**: soft silhouette shape | Cel-shaded dust bursts, explosions, steam, shockwave clouds. |
| **4-Point Star Glint** (`ClampToEdge`) | `128×128` | **RGBA**: incandescent core + concave 4-point cross needles + radial fade | Sparks, embers, frost motes, hit sparkles, nebula dust — kills square point-sprite clipping. |

### Seamless Periodic Noise Guarantee
Standard value noise leaves visible UV seams on polar rings, cylinders, and hemispherical domes. Always wrap lattice coordinates modulo period `(px, py)` at every octave (`((fx % px) + px) % px`, doubling `px, py` per octave) so every texture tiles invisibly across `U ∈ [0, 1]` and `V ∈ [0, 1]`.

---

## 3. Core GLSL Building Blocks

### A. Depth-Softened Particles & Glowing Scene-Intersection Contact Rims (`DEPTH_FADE_GLSL`)

Sample the opaque pre-pass `DepthTexture` to both **soften hard plane intersections** (smoke/beams meeting floors) and **paint luminous contact rims** (shields/domes/beams cutting through terrain or characters):

```glsl
uniform sampler2D tDepth;
uniform vec2 uResolution;
uniform float uCameraNear;
uniform float uCameraFar;
uniform float uHasDepth;

float linearizeSceneDepth(float z) {
  float ndc = z * 2.0 - 1.0;
  return (2.0 * uCameraNear * uCameraFar) /
         max(0.0001, uCameraFar + uCameraNear - ndc * (uCameraFar - uCameraNear));
}

float getSceneDepthDiff() {
  if (uHasDepth < 0.5) return 99.0; // graceful fallback when depth pre-pass is disabled
  vec2 suv = gl_FragCoord.xy / max(uResolution, vec2(1.0));
  float sceneZ = linearizeSceneDepth(texture2D(tDepth, suv).r);
  float fragZ  = linearizeSceneDepth(gl_FragCoord.z);
  return max(0.0, sceneZ - fragZ);
}

// Usage 1 — Soft smoke / billboard fade near solid surfaces:
// float softFade = smoothstep(0.0, 0.85, getSceneDepthDiff());
// alpha *= softFade;

// Usage 2 — Glowing intersection rim on shields / domes / forcefields:
// float depthDiff = getSceneDepthDiff();
// float contactRim = (1.0 - smoothstep(0.0, 0.55, depthDiff)) * step(0.5, uHasDepth);
// col += uHotColor * contactRim * 2.2;
```

### B. 2-Phase Curl-Flowmap Advection (Zero Looping Pop)

Advects noise UVs continuously along the curl velocity field while crossfading two half-cycle phases (`p0`, `p1`) so the distortion never stretches to infinity or snaps on reset:

```glsl
vec2 flowVec = (texture2D(uFlow, flowUV).rg * 2.0 - 1.0) * uFlowStrength;
float fTime = uTime * 0.65;
float p0 = fract(fTime);
float p1 = fract(fTime + 0.5);
float blend = abs(p0 * 2.0 - 1.0); // triangle wave: 0 at p0=0.5, 1 at p0=0/1
vec4 advected = mix(
  texture2D(uNoise, baseUV + flowVec * p0),
  texture2D(uNoise, baseUV + flowVec * p1),
  blend
);
```

### C. 4-Stop Stylized Color Ramp + Hot Dissolve Erosion

Avoid single-color monochrome glow. Map normalized energy (`0 → 1`) through **dark backing → saturated mid → bright inner → incandescent HDR core**, and push a crisp glowing edge right along the `uDissolve` erosion threshold:

```glsl
// Soft-to-sharp stylized erosion
float mask = smoothstep(uDissolve, uDissolve + 0.14, energySample);
float erodeEdge = smoothstep(uDissolve, uDissolve + 0.04, energySample) *
                  (1.0 - smoothstep(uDissolve + 0.04, uDissolve + 0.16, energySample));

vec3 col = mix(uColorOuter, uColorMid, smoothstep(0.15, 0.52, energySample));
col = mix(col, uColorInner, smoothstep(0.52, 0.82, energySample));
col = mix(col, uColorHot * uHdrBoost, smoothstep(0.82, 0.98, energySample));
col += uColorHot * erodeEdge * uHdrBoost * 0.9; // hot burning edge as effect dissolves
```

### D. Procedural SDF Emitter Sigils & Targeting Reticles (Zero Textures)

Render razor-sharp geometric circles, hex rings, clockwork dials, runes, waveforms, dark-core void coronas, or 90° cyber reticles on a single camera-facing or ground-aligned quad using signed distance functions:

```glsl
float sdPolygon(vec2 p, float r, float n) {
  float a = atan(p.y, p.x);
  float seg = 6.2831853 / n;
  return cos(floor(0.5 + a / seg) * seg - a) * length(p) - r;
}

// Sharp anti-aliased glowing line from any SDF distance d:
float glowLine(float d, float sharpness) {
  float x = d * sharpness;
  return exp(-(x * x));
}
```
Notice `x * x` instead of `pow(abs(d), 2.0)` — faster and immune to `pow(0.0, ...)` NaNs!

---

## 4. Unified Optical `ImpactPostPass` (Single Pass, Dormant Fast-Path)

Combine all full-screen event-driven optical VFX into **one** `ShaderPass` placed after `OutputPass`, with an early-out fast-path when all effect uniforms are `<= 0.001` (near-zero cost during calm gameplay):

| Optical Mode | Uniform Drivers | Best Game Uses | Math Core |
| --- | --- | --- | --- |
| **Radial Shockwave Refraction** | `uShockwaveProgress` (`0→1`), `uShockwaveStrength`, `uTargetUV` | Explosions, boss slams, ability detonations, sonic booms | Expanding Gaussian ring band (`exp(-((r - waveR)/0.065)^2)`) offsetting `uv` along radial direction + brief chromatic ring fringe. |
| **Localized Thermal Heat-Haze** | `uHeatHaze`, `uTargetUV`, `uTime` | Magma craters, jet exhaust, flamethrowers, burn zones | Radial Gaussian mask (`exp(-r*r*5.2)`) modulating rising sinusoidal UV shimmer. |
| **Spherical Bubble Refraction** | `uBubbleDistort`, `uBubbleRadius`, `uTargetUV` | Forcefields, stasis domes, water/ice shields | Smooth sine-squared radial lens profile warping background UVs inward at dome edges. |
| **Einstein-Ring Gravitational Lensing** | `uBlackHoleMass`, `uBlackHoleRadius`, `uTargetUV` | Black holes, void implosions, gravity grenades | Inverse-distance deflection outside Schwarzschild radius + pitch-black event horizon + bright photon-ring rim. |
| **1–3 Frame Bespoke Impact Frame** | `uImpactFrame` (`0→1`), `uImpactMode` (`0..4`), `uImpactAngle` | Critical hits, ultimates, parries, boss phase transitions | High-contrast monochrome/duotone luminance inversion + radial speed lines + mode-specific motif (slash cut, shattered Voronoi ice, voltage RGB glitch, eclipse corona, clockwork dial). Automatically suppressed under `setReducedMotion(true)`. |

### Projecting World Targets to `uTargetUV`
Update `uTargetUV` each frame before `composer.render()` so screen-space refraction tracks the 3D explosion/dome accurately from any camera orbit:

```ts
projTmp.copy(worldAnchor).project(camera);
impactPass.uniforms.uTargetUV.value.set(projTmp.x * 0.5 + 0.5, projTmp.y * 0.5 + 0.5);
```
Clamp or fade effect strength when `projTmp.z > 1.0` (target behind the camera) so offscreen explosions never invert behind-camera UV coordinates.
