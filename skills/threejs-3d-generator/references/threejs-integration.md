# Three.js Integration

Use this after `threejs-3d-generator` generates or post-processes a model.

## Preferred Outputs

- Three.js runtime: GLB/PBR model first.
- Animation/game-engine interchange: FBX when needed, then convert/import carefully.
- Static web asset exchange: GLTF/GLB.
- 3D print only: STL or 3MF, not for textured game runtime.
- Apple AR: USDZ.

## Import Pattern

Use `GLTFLoader`:

```ts
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const loader = new GLTFLoader();
const gltf = await loader.loadAsync('/assets/models/asset/model.glb');
scene.add(gltf.scene);
```

For animation:

```ts
const mixer = new THREE.AnimationMixer(gltf.scene);
const action = mixer.clipAction(gltf.animations[0]);
action.play();

// in loop
mixer.update(deltaSeconds);
```

Animation intake notes (the underlying Tripo API behavior and prohibitions — NlaTrack naming, batched-vs-single retarget, `animate_in_place` corruption — are documented canonically in `api-notes.md`; this section is the engine-side fix):

- A batched retarget returns ONE GLB whose clips are named `NlaTrack`, `NlaTrack.001`, … in request order. The names carry no meaning: map clips to presets by index against the order you requested, rename them after load (`clip.name = 'walk'`), then select by your own names.
- Log `gltf.animations.map(c => `${c.name} ${c.tracks.length} tracks`)` after load. A healthy humanoid clip drives many bones; clips with only a handful of tracks mean the upstream auto-rig was degenerate — fix the rig, not the runtime.
- Do NOT strip or neutralize twist-bone tracks (`UpperarmTwist`, `ForearmTwist`, …) on v1.0 rigs: Tripo skins most of the limb mesh to the twist bones, and their baked values differ greatly from the GLB rest pose — removing the tracks collapses the limbs into the torso. Tripo's slightly open, palm-forward hands are the preset house style, not corruption.
- Never retarget with `animate_in_place=true` (see `api-notes.md` for why it corrupts the bake). Convert to in-place at import instead, and do it precisely:
  - Touch ONLY the top root bone's position track (`Root.position`). Tripo FBX clips bake position tracks on EVERY bone with values that differ from FBXLoader's rest transforms; filtering Hip/Pelvis or pattern-matching broadly collapses the skeleton into a hunch.
  - Zero the HORIZONTAL components only — keep Y. Vertical root motion IS the animation for jumps (and the bob in gaits); deleting the whole track turns a jump into grounded hand-waving.

```ts
for (const clip of clips) {
  for (const tr of clip.tracks) {
    if (tr.name !== 'Root.position') continue;
    const v = tr.values, x0 = v[0], z0 = v[2];
    for (let i = 0; i < v.length; i += 3) { v[i] = x0; v[i + 2] = z0; }
  }
}
```

FBX intake specifics (v1.0 humanoid retargets):

- `FBXLoader` lives at `three/addons/loaders/FBXLoader.js` and imports `fflate`; bundler projects get it from npm automatically, but import-map/CDN pages must map it (e.g. `"fflate": "https://cdn.jsdelivr.net/npm/fflate@0.8.2/esm/browser.js"`).
- Use ONE FBX per animation (the pipeline does this automatically) and play each file's `animations[0]` as exported. The variant order of duplicate takes differs per file — `animations[0]` is always the correct one.

- `FBXLoader` emits each take twice under different node-path prefixes (`Armature.001|walk_…` and `Armature|Armature.001|walk_…`). Keep the variant with the SHALLOWER path (fewer `|` segments); the deep variant's tracks bind incorrectly.
- Clips carry real names (`walk_normal_m_remap`, `idle_251105_remap`) — select by keyword (slash arrives as an attack/swing name), not by index.
- Play the clips otherwise untouched. Every loader-side "fix" beyond the single root-position strip has been tested and makes things worse.
- FBXLoader produces Phong materials (darker than GLB PBR). For final art parity, convert FBX→GLB offline (Blender import/export or FBX2glTF) — the corrected animation survives conversion.
- Tripo preset retargeting only works on `spec=tripo` rigs. A `spec=mixamo` rig is for external animation pipelines (Mixamo clips, custom libraries) — retarget those in a DCC tool or at runtime with `SkeletonUtils.retargetClip`, and expect to supply bone-name mappings and check bind-pose orientation when skeleton conventions differ.

## Asset Intake Checklist

Inspect before shipping:

- File size.
- Triangle count.
- Mesh count.
- Material count.
- Texture count and texture dimensions.
- PBR material behavior under the game lighting rig.
- Scale in meters and `auto_size` assumptions.
- Pivot/origin and bounds.
- Collision proxy separate from detailed mesh.
- Animation clip names, durations, root motion, and in-place behavior.
- Mobile memory/performance impact.

## Game Asset Strategy

- Use `threejs-3d-generator` for hero assets, characters, creatures, bosses, buildings, weapons, signature props, and complex pickups.
- Use procedural Three.js kits for high-volume repeated detail such as bolts, windows, track plates, rails, debris, markers, and background silhouettes.
- Use `threejs-image-generator` for concept art, texture references, decals, logos, UI icons, and backdrop images.
- Combine: image-generator concept -> 3D-generator model -> Three.js import -> procedural set dressing -> visual scorecard.

## Performance Discipline

- Use `face_limit`, `smart_low_poly`, conversion, or low-poly postprocess for browser/mobile budgets.
- Prefer one high-fidelity hero asset plus instanced/procedural supporting detail over many unique heavy models.
- Keep textures compressed or reasonably sized.
- Clone carefully. Share geometry/materials when possible.
- Dispose loaded assets when leaving scenes.
- Run renderer diagnostics after importing: calls, triangles, geometries, textures, materials, file sizes.

## Common Fixes

- Model too large/small: normalize bounds in an asset wrapper group.
- Wrong orientation: set a wrapper rotation, or use Tripo image `orientation=align_image` for image inputs.
- Animations move out of place: keep exported root motion intact, then strip only horizontal root-position components in code as shown above. Do not retarget with `animate_in_place=true`.
- Too expensive: lower `face_limit`, use `smart_low_poly`, reduce texture quality/size, or convert with a face limit.
- Materials too dark/bright: check color space, tone mapping, environment, and light exposure.
- Collision too complex: build primitive proxies in Three.js and keep Tripo mesh visual-only.

## Final Evidence

Report:

- 3D generator task IDs.
- Downloaded asset paths.
- Model version and generation options.
- Post-process tasks: texture, rig, animation, conversion.
- Three.js import files changed.
- Renderer diagnostics before/after import.
- Screenshot evidence in active gameplay.
