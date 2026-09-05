# Debug And Profile Playbook

Ordered triage for blank canvases, runtime errors, asset and audio loading, animation/collision/input failures, mobile bugs, and performance work.

## Contents

- Triage order · Blank or bad canvas · Asset loading · Audio · Loop and physics · Input and mobile · Profiling order · Optimizations · Diagnostics object

## Triage order

Reproduce with the same command and URL the user used → capture console, page, and network errors → confirm the expected build is serving on that port (not another local server) → identify the owner (renderer, scene, camera, loop, assets, audio, input, physics, UI, CSS, base path, performance) → fix in the owning module → retest the exact broken path.

## Blank or bad canvas — check in this order

Canvas exists in the DOM → CSS size is non-zero and visible → drawing-buffer size is non-zero and matches expected DPR → WebGL context creation succeeded → exactly one active render loop → camera aspect, projection matrix, near/far, and aim → scene has visible objects at expected transforms and scale → material visibility (opacity, `transparent`, `side`, depth, color space, fog interaction) → lights exist for lit materials → background/fog is not the same value as the objects → resize updates renderer, camera, composer, and CSS → no CSS overlay covering the canvas → render target or composer output is actually displayed.

## Asset loading

URLs and Vite base path · files in `public/` or imported paths · loader type and `three/addons/...` imports · CORS and MIME errors · glTF external buffers and textures · texture color space and flipY · async load state, loading UI, error fallback · disposal of replaced assets.

For generated/imported GLB: file size, URL casing, Draco/Meshopt requirements, scene scale, pivot and origin, bounds, texture dimensions, material count, animation clip names — and whether the generated download URLs were saved before they expired.

## Audio

Files exist at their runtime URLs with compatible MIME types · `AudioContext` resumed from a user gesture before playback · decode and load promises reject visibly rather than silently · SFX triggers are event-driven, not per-frame · ambience and music loops stop on pause, restart, and teardown · mute and volume reach every group · visibility pause/resume does not stack duplicate sources · mobile unlock tested when mobile is in scope.

## Loop, animation, physics

Delta units (seconds vs milliseconds) · delta clamping for tab sleep and frame spikes · fixed-step accumulator when timing matters · physics initialized before bodies are created or the world is stepped · one owner for body creation and disposal · timestep not tied to variable render delta · mixer updates and clip actions · only one `requestAnimationFrame` loop · state transitions that stop updates or restart timers · collision proxies vs visual meshes · collider scale, rotation, offset · high-speed tunneling and spawn overlap · CCD only where needed · sensors have active events or explicit overlap checks · kinematic platforms move the body, not just the mesh · restart cleans up entities, listeners, timers, effects, and bodies · imported model clips bound to the correct root with intentional root motion.

## Input and mobile

Keyboard focus, and `preventDefault` only where needed · pointer listeners on the right element · pointer capture, release, and cancel · `touch-action` CSS and viewport meta · page scroll stealing gestures · DPR making controls tiny or the GPU hot · safe-area insets · orientation and resize after rotation · desktop input still working after touch controls were added · UI controls emit intents rather than duplicating simulation rules.

## Profiling order

Measure in production preview when user-facing performance matters.

1. Fix the scenario: viewport, DPR, route, gameplay state, camera view, device tier.
2. Baseline: FPS/frame time, renderer calls, triangles, geometries, materials, textures, render targets and post passes, JS heap, bundle and large assets. Add imported model sizes, clips, and texture dimensions when generated 3D was added; body/collider/sensor/CCD counts and step cost when physics changed.
3. Classify the bottleneck — CPU (simulation, allocation, physics, mixers, UI layout) · GPU draw (draw calls, material switches, too many unique meshes) · GPU fragment (overdraw, post, high DPR, transparent particles) · GPU vertex (triangles, dense shadows) · memory (textures, render targets, undisposed resources) · network/bundle.
4. Apply one optimization, re-measure the same scenario, then check for visual and playability regression.

## Optimizations, roughly in order of payoff

`InstancedMesh` for repeated detail · shared geometries/materials/textures · object pools for effects, bullets, pickups, debris · frustum and distance culling · LOD for background props and world kits · DPR cap or adaptive quality · cheaper shadows (fewer casters, smaller maps, contact alternatives) · fewer post passes · texture atlases, compression, mipmaps · no per-frame allocations or layout reads · simpler colliders, sleeping, collision groups, pooled bodies · explicit disposal of geometries, materials, textures, render targets, audio.

Before deleting hero readability, try `threejs-3d-generator` face limits, `smart_low_poly`, conversion, or a lower texture quality variant.

## Diagnostics object

```ts
window.__THREE_GAME_DIAGNOSTICS__ = {
  renderer: renderer.info,
  get state() {
    return game.getDebugState();
  },
};
```

Useful fields: `renderer.info.render.calls`, `.triangles`, `.points`, `.lines`, `.memory.geometries`, `.memory.textures`.

Physics-heavy games add:

```ts
physics: { engine: 'rapier', timestep: 1 / 60, bodies, colliders, sensors, ccdBodies }
```

## Recurring mistakes

Guessing without reproducing · optimizing the dev server instead of the production preview · stripping visual detail before checking DPR, post, shadows, instancing, culling · patching CSS when renderer or camera sizing is the real bug · adding mobile controls without testing pointer cancel and safe areas · ignoring console errors because the canvas looks fine · shipping an imported model without checking scale, pivot, collision, clips, texture memory, or mobile cost.
