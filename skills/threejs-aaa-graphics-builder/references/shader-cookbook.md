# Shader And Material Cookbook

Concrete material, shader, and post-processing recipes. Use with `references/technical-art.md` (budgets, when shader work is justified) and `references/render-recipes.md` (render pipeline).

Targets three.js `^0.184`; imports use the `three/addons/*` alias (maps to `examples/jsm`). Every entry lists **When**, **Cost** (draw calls / fill rate / compile), and **Read** (the rule: effects clarify gameplay, never hide missing geometry).

## Prerequisite: Renderer And Environment Map

Metals and glossy dielectrics read as flat gray without an environment map to reflect. Set this up once before PBR materials.

```ts
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping; // simpler tone mapping for bright arcade reads
renderer.toneMappingExposure = 1.0;
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));

// 5-line env map: neutral studio IBL, no HDR file needed.
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture; // r184: RoomEnvironment() takes no args
scene.environmentIntensity = 1.0; // r184 global multiplier over per-material envMapIntensity
pmrem.dispose();
```

Needed by any scene with metal, ceramic, glass, or clearcoat. Cost is one PMREM bake at startup, near-zero per frame; it lights support surfaces so hero emissive/trim still wins attention.

## PBR Material Recipes

Copy the config; tune `color` to the palette. `envMapIntensity` values assume the env map above. Use `MeshStandardMaterial` unless a `MeshPhysicalMaterial`-only feature (clearcoat, transmission, sheen) is visible during play.

```ts
// Painted metal (car body, ship hull panel) — dielectric paint over metal read via clearcoat.
new THREE.MeshPhysicalMaterial({ color: 0x1f6feb, metalness: 0.0, roughness: 0.5,
  clearcoat: 0.9, clearcoatRoughness: 0.15, envMapIntensity: 1.0 });

// Bare brushed metal (raw steel, gun frame) — needs the env map to look metallic.
new THREE.MeshStandardMaterial({ color: 0xaeb4bd, metalness: 1.0, roughness: 0.4, envMapIntensity: 1.1 });

// Rubber / tire — near-black, no reflection, kills the env map.
new THREE.MeshStandardMaterial({ color: 0x0a0a0b, metalness: 0.0, roughness: 0.92, envMapIntensity: 0.35 });

// Matte plastic (housings, crates) — dielectric, mid roughness, muted reflection.
new THREE.MeshStandardMaterial({ color: 0xd23b3b, metalness: 0.0, roughness: 0.62, envMapIntensity: 0.6 });

// Glossy ceramic / clean hull — sharp reflection, add clearcoat for wet-look premium.
new THREE.MeshPhysicalMaterial({ color: 0xf5f5f5, metalness: 0.0, roughness: 0.12,
  clearcoat: 1.0, clearcoatRoughness: 0.05, envMapIntensity: 1.0 });

// Emissive signal (beacon, pickup core) — dark base so only the glow reads; >1 intensity feeds bloom.
new THREE.MeshStandardMaterial({ color: 0x101010, emissive: 0x18e0ff, emissiveIntensity: 2.5,
  metalness: 0.0, roughness: 0.4 });

// Cloth / fabric — high roughness + sheen for the soft edge highlight.
new THREE.MeshPhysicalMaterial({ color: 0x3a4a6b, metalness: 0.0, roughness: 0.9,
  sheen: 1.0, sheenRoughness: 0.5, sheenColor: new THREE.Color(0x8899bb), envMapIntensity: 0.5 });
```

**Read:** separate roles by roughness/metalness contrast (matte vs glossy, metal vs plastic), not hue alone.

### Glass: real vs fake

```ts
// REAL refractive glass — MeshPhysicalMaterial transmission.
new THREE.MeshPhysicalMaterial({ metalness: 0.0, roughness: 0.05, transmission: 1.0,
  thickness: 0.5, ior: 1.5, envMapIntensity: 1.0 });
```

- **When:** one or two hero surfaces (cockpit canopy, potion vial) at close range.
- **Cost:** high. Each transmissive material triggers an extra scene render into a transmission buffer every frame; fill-rate heavy and multiplies with resolution. Never use on repeated/instanced props.
- **Read:** refraction must not smear the hazard behind it into unreadability.

```ts
// CHEAP fake glass — no transmission buffer. Use for repeated windows, visors, shields.
new THREE.MeshPhysicalMaterial({ color: 0x88ccff, metalness: 0.0, roughness: 0.1,
  transparent: true, opacity: 0.25, clearcoat: 1.0, envMapIntensity: 1.5, depthWrite: false });
```

- **Cost:** one transparent draw call, no extra render target. Add the fresnel rim below for a readable edge.

## onBeforeCompile Patterns

Inject GLSL into stock materials to keep PBR lighting for free. Rules that make this safe with shared materials:

- **Cache key:** any material whose `onBeforeCompile` injects code MUST set `customProgramCacheKey` returning a string unique to that injection. Without it three can hand back a cached program compiled from a different (un-injected) material of the same type, silently dropping your code.
- **Sharing:** `onBeforeCompile` runs once per compiled program. Reuse one material instance across meshes and its uniforms update once for all. For per-object variation, use separate material instances (same cache key → program is still reused) or drive it from `instanceMatrix` / `instanceColor`.
- **Animating uniforms:** `onBeforeCompile` fires once, so stash the shader (`material.userData.shader = shader`) and write the uniform each frame: `if (m.userData.shader) m.userData.shader.uniforms.uTime.value = t;`. The snippets below use this pattern.

### (a) Fresnel rim glow

`vNormal` and `vViewPosition` (both view space) exist in the Standard/Physical fragment shader; `saturate` is defined in `<common>`.

```ts
material.onBeforeCompile = (shader) => {
  shader.uniforms.uRimColor = { value: new THREE.Color(0x33ccff) };
  shader.uniforms.uRimPower = { value: 3.0 };
  shader.uniforms.uRimStrength = { value: 1.5 };
  shader.fragmentShader =
    'uniform vec3 uRimColor;\nuniform float uRimPower;\nuniform float uRimStrength;\n' +
    shader.fragmentShader.replace(
      '#include <emissivemap_fragment>',
      `#include <emissivemap_fragment>
       float fres = pow(1.0 - saturate(dot(normalize(vNormal), normalize(vViewPosition))), uRimPower);
       totalEmissiveRadiance += uRimColor * fres * uRimStrength;`
    );
};
material.customProgramCacheKey = () => 'fresnel-rim';
```

- **When:** shields, cloak/invuln states, silhouette separation from a busy background.
- **Cost:** a few ALU ops, no extra passes.
- **Read:** the rim marks a state change; keep base color readable when the rim is off.

### (b) Scrolling emissive panels

Inject a private UV varying so it works without a map assigned.

```ts
material.onBeforeCompile = (shader) => {
  shader.uniforms.uTime = { value: 0 };
  shader.uniforms.uPanelColor = { value: new THREE.Color(0x18e0ff) };
  material.userData.shader = shader;
  shader.vertexShader = 'varying vec2 vCookUv;\n' + shader.vertexShader.replace(
    '#include <begin_vertex>', '#include <begin_vertex>\n vCookUv = uv;');
  shader.fragmentShader =
    'uniform float uTime;\nuniform vec3 uPanelColor;\nvarying vec2 vCookUv;\n' +
    shader.fragmentShader.replace(
      '#include <emissivemap_fragment>',
      `#include <emissivemap_fragment>
       float scroll = fract(vCookUv.y * 6.0 - uTime * 0.5);
       float band = smoothstep(0.46, 0.5, scroll) * smoothstep(0.54, 0.5, scroll);
       totalEmissiveRadiance += uPanelColor * band * 2.0;`
    );
};
material.customProgramCacheKey = () => 'scroll-emissive';
```

- **When:** energy conduits, reactor walls, loading/charge bars, boost lanes.
- **Cost:** one `fract`/`smoothstep`, no textures.
- **Read:** scroll direction/speed should encode state (charging up, draining down).

### (c) Wind sway (foliage / flags)

`transformed` is object space and displaced before `<project_vertex>` applies `instanceMatrix`, so read the instance translation column for per-instance phase. Assumes model origin at the base, up = +Y.

```ts
material.onBeforeCompile = (shader) => {
  shader.uniforms.uTime = { value: 0 };
  material.userData.shader = shader;
  shader.vertexShader = 'uniform float uTime;\n' + shader.vertexShader.replace(
    '#include <begin_vertex>',
    `#include <begin_vertex>
     #ifdef USE_INSTANCING
       float phase = instanceMatrix[3].x + instanceMatrix[3].z; // instance world offset
     #else
       float phase = 0.0;
     #endif
     float h = max(position.y, 0.0); // base stays planted, tips move most
     transformed.x += sin(uTime * 1.5 + phase) * 0.08 * h;
     transformed.z += cos(uTime * 1.1 + phase) * 0.05 * h;`
  );
};
material.customProgramCacheKey = () => 'wind-sway';
```

- **When:** grass cards, banners, antennae, kelp — background life, not gameplay geometry.
- **Cost:** two trig ops per vertex; free on an `InstancedMesh`.
- **Read:** sway is ambient motion; never move collidable/interactable geometry with it.

### (d) Dissolve / spawn

Threshold-discard with a glowing edge. Inject a local-position varying and a hash; drive `uProgress` 0→1 to despawn, 1→0 to spawn.

```ts
material.onBeforeCompile = (shader) => {
  shader.uniforms.uProgress = { value: 0 };
  shader.uniforms.uEdgeColor = { value: new THREE.Color(0xff6a00) };
  material.userData.shader = shader;
  shader.vertexShader = 'varying vec3 vDisPos;\n' + shader.vertexShader.replace(
    '#include <begin_vertex>', '#include <begin_vertex>\n vDisPos = position;');
  shader.fragmentShader =
    `uniform float uProgress;\nuniform vec3 uEdgeColor;\nvarying vec3 vDisPos;
     float hash13(vec3 p){ p = fract(p * 0.1031); p += dot(p, p.yzx + 33.33); return fract((p.x + p.y) * p.z); }\n` +
    shader.fragmentShader.replace(
      '#include <dithering_fragment>',
      `float n = hash13(floor(vDisPos * 12.0));
       if (n < uProgress) discard;
       float edge = smoothstep(uProgress, uProgress + 0.08, n);
       gl_FragColor.rgb += uEdgeColor * (1.0 - edge) * 3.0; // post-tonemap add feeds bloom
       #include <dithering_fragment>`
    );
};
material.customProgramCacheKey = () => 'dissolve';
```

- **When:** enemy death, teleport-in, pickup spawn, object streaming.
- **Cost:** one hash + `discard` (discard disables early-Z; keep it to spawning objects, not the whole scene).
- **Read:** the edge color/direction telegraphs the event — spawn vs destroy must look different.

## Gradient Sky Dome

Cheaper than a cubemap for stylized scenes: a `BackSide` sphere with a top/horizon lerp plus a sun disc and halo.

```ts
const skyUniforms = {
  uTop:      { value: new THREE.Color(0x3a6fb0) },
  uHorizon:  { value: new THREE.Color(0xcfe4f5) },
  uSunColor: { value: new THREE.Color(0xfff2cc) },
  uSunDir:   { value: new THREE.Vector3(0.4, 0.28, 0.6).normalize() },
};
const sky = new THREE.Mesh(
  new THREE.SphereGeometry(500, 32, 16),
  new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, uniforms: skyUniforms,
    vertexShader: `varying vec3 vDir;
      void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `varying vec3 vDir;
      uniform vec3 uTop, uHorizon, uSunColor, uSunDir;
      void main(){
        float h = clamp(vDir.y * 0.5 + 0.5, 0.0, 1.0);
        vec3 col = mix(uHorizon, uTop, pow(h, 0.6));
        float d = clamp(dot(normalize(vDir), normalize(uSunDir)), 0.0, 1.0);
        col += uSunColor * (pow(d, 800.0) + pow(d, 8.0) * 0.25); // disc + halo
        gl_FragColor = vec4(col, 1.0);
      }`,
  })
);
sky.frustumCulled = false;
scene.add(sky);
```

- **When:** any stylized outdoor scene without a photographic backdrop.
- **Cost:** one draw call, no cubemap textures, no mips.
- **Read:** a raw `ShaderMaterial` bypasses tone mapping and sRGB conversion — author colors in display space; if the scene runs ACES, nudge them brighter. Keep horizon value distinct from hazards silhouetted against it.

## Post-Processing Chain

Finishing pass only. Move tone mapping/sRGB to `OutputPass`; keep `renderer.toneMapping` set so it reads it.

```ts
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));

// UnrealBloomPass(resolution, strength, radius, threshold)
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight),
  0.45,  // strength: 0.35-0.6
  0.3,   // radius: 0.2-0.4
  0.85); // threshold: only pixels brighter than this bloom
composer.addPass(bloom);

const VignetteShader = {
  uniforms: { tDiffuse: { value: null }, uStrength: { value: 0.85 }, uSize: { value: 0.72 } },
  vertexShader: `varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uStrength, uSize; varying vec2 vUv;
    void main(){
      vec4 c = texture2D(tDiffuse, vUv);
      float d = distance(vUv, vec2(0.5));
      c.rgb *= mix(1.0, smoothstep(uSize, uSize - 0.45, d), uStrength);
      gl_FragColor = c;
    }`,
};
composer.addPass(new ShaderPass(VignetteShader));
composer.addPass(new OutputPass()); // ALWAYS last: tone mapping + sRGB

// loop: composer.render() instead of renderer.render()
// resize: composer.setSize(w, h); composer.setPixelRatio(Math.min(devicePixelRatio, 2));
```

- **Bloom rule:** bloom sells authored emissive (threshold 0.85 keeps mid-bright materials out). It must never be the main source of detail — if a shape only reads because it glows, the geometry is missing.
- **Vignette cost:** one full-screen ShaderPass; keep `uStrength` subtle, never darken the play path.
- **Mobile:** the composer allocates full-resolution HDR targets, so cost scales with DPR². Cap DPR before adding passes. On low-end, skip the composer (call `renderer.render`) or run bloom-only via `composer.setPixelRatio(Math.min(devicePixelRatio, 1.25))`. Compare screenshots with post on/off and profile.

## Cheap Tricks

- **Vertex-color AO** — bake occlusion into the mesh: `geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))`, material `{ vertexColors: true }`, darken cavities/creases. **When:** static props/terrain. **Cost:** one attribute, zero draw calls. **Read:** ground shapes with contact darkness; don't tint gameplay-critical surfaces.
- **Polygon-offset decals** — coplanar decal mesh with `{ polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1, transparent: true }` to kill z-fighting. **When:** panel lines, numbers, faction glyphs. **Cost:** +1 draw call each — instance repeats. **Read:** decals imply function/scale, not random surface noise.
- **Fake contact shadow** — flat `PlaneGeometry` with a radial-gradient `CanvasTexture`, `{ transparent: true, depthWrite: false }`, under the object; scale/fade alpha with height. **When:** hovering or moving props that don't warrant a shadow map. **Cost:** one draw call, no shadow pass. **Read:** anchors floating objects so position reads.
- **Emissive LOD signals** — swap `emissiveIntensity` or material by distance so far pickups/beacons still read, add geometry detail only up close. **When:** dense repeated signals. **Cost:** a material/uniform swap. **Read:** keep the signal color constant across LOD so identity survives the transition.
- **Matcap props** — `new THREE.MeshMatcapMaterial({ matcap })` bakes lighting into one texture; no lights or env needed. **When:** background/stylized props. **Cost:** the cheapest lit-looking material, one texture. **Read:** matcap ignores scene lights, so never use it where a dynamic light or state glow must show on the surface.
