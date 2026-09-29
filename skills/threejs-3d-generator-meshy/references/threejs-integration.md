# Importing Meshy Output into Three.js

## Formats

Ask for `glb` (`--target-formats glb`, the default) and load with `GLTFLoader`. FBX is only
worth downloading for a DCC round-trip; `FBXLoader` output needs scale and material fixups
that the GLB does not.

Rigging returns BOTH `rigged_character_glb_url` and `rigged_character_fbx_url`; the GLB is
the one to ship. Animation tasks return one clip per file (`animation_glb_url`).

## Rigged character + clips

Meshy hands you a rigged GLB and separate one-clip GLBs. Load the character once, then pull
each clip's `AnimationClip` out of its own file and drive them all with one mixer:

```js
const loader = new GLTFLoader();
const character = await loader.loadAsync('models/hero-rig-rigged_character_glb.glb');
scene.add(character.scene);

const mixer = new THREE.AnimationMixer(character.scene);
const clips = {};
for (const [name, url] of Object.entries({
    idle: 'models/hero-000-Idle-animation_glb.glb',
    walk: 'models/hero-001-Walking_Woman-animation_glb.glb',
})) {
    const gltf = await loader.loadAsync(url);
    clips[name] = gltf.animations[0];
}
mixer.clipAction(clips.idle).play();
```

The clip files also contain a copy of the skinned mesh; only `gltf.animations` is needed, so
do not add their `scene` to your scene graph. Bone names match (`mixamorig:*`) because both
files come from the same rig task - if you ever mix rigs, retarget by bone name first.

## Root motion

Library clips are baked with root motion. When gameplay code moves the character, zero the
HORIZONTAL components of the root/hips position track and keep the vertical one (jump arcs
and gait bob live there):

```js
function stripHorizontalRootMotion(clip) {
    for (const track of clip.tracks) {
        if (!track.name.endsWith('.position')) continue;
        if (!/Hips|Root|Armature/i.test(track.name)) continue;
        for (let i = 0; i < track.values.length; i += 3) {
            track.values[i] = track.values[0];
            track.values[i + 2] = track.values[2];
        }
    }
    return clip;
}
```

## Constant scale tracks resize the clip (verified in three.js)

Library clips carry a scale track on every bone. Most are constant at the rest scale and
harmless, but a clip can be baked with a constant OFF-rest scale: the `Idle` clip (action 0)
came in with `Hips` scale `1.176`, so playing it rendered the character 17.6 % taller than
the same rig playing `walking_2` - measured head height 1.78 m vs 1.568 m in a three.js
scene. Drop the constant scale tracks at import; the varying ones (spread > 0.05) are the
only ones worth keeping, and they usually indicate a bad bake:

```js
function dropConstantScale(clip) {
    clip.tracks = clip.tracks.filter((track) => {
        if (!track.name.endsWith('.scale')) return true;
        const v = track.values;
        let spread = 0;
        for (let i = 0; i < v.length; i += 3) {
            spread = Math.max(spread, Math.abs(v[i] - v[0]), Math.abs(v[i + 1] - v[1]), Math.abs(v[i + 2] - v[2]));
        }
        return spread >= 0.05;
    });
    return clip;
}
```

`validate-animation` reports these as `constant rescale vs rest pose` instead of failing, so
check that line before wiring several clips onto one character.

## Scale and pivot

`height_meters` on the rig task (default 1.7) means the character arrives in metres; props
from text/image tasks do not, so set `--auto-size` or normalize on import. `origin_at`
(`bottom` default) controls the pivot - `bottom` is what you want for anything standing on
terrain.

## Budget checks after download

Inspect triangle count, material count, texture resolution, file size, bounds and animation
clip names before wiring the asset into the game. `--target-polycount` at generation time is
cheaper than decimating later; a second pass through `remesh --topology triangle
--target-polycount N` is the fallback for an asset that came back too dense.

## Provider-neutral guidance

The Three.js side of this (loading, mixers, LOD, budgets, prop kits around hero assets) is
the same as in the Tripo skill. See the sibling
`threejs-3d-generator/references/threejs-integration.md` for the longer version; the
Meshy-specific parts are the ones above.

## White silhouette: emissive material + a blocked texture

The rig material comes back with `emissiveFactor [1,1,1]` and both its base color AND its
emissive driven by the same embedded image. That means a failed texture decode does not
render an untextured grey model - it renders a **pure white silhouette**, because the
emissive term is left at full strength with no map to modulate it.

GLTFLoader decodes a GLB-embedded image through a `blob:` URL, which a page under a strict
CSP can refuse. Two defenses, both worth having:

```js
// 1. never let a missing texture glow white
root.traverse((o) => {
    if (!o.isMesh) return;
    for (const mat of [].concat(o.material)) {
        if (mat.emissive && mat.emissive.getHex() > 0x111111 && !mat.emissiveMap) {
            mat.emissive.setHex(0x000000);
            if (!mat.map) mat.color.setHex(0x8e9aa8);
            mat.needsUpdate = true;
        }
    }
});

// 2. on a CSP-restricted page, ship the texture beside the GLB and decode it to a bitmap,
//    which loads no resource at all (slim_glb.py rig --extract-texture splits it out)
const bitmap = await createImageBitmap(new Blob([jpegBytes], { type: 'image/jpeg' }));
const tex = new THREE.Texture(bitmap);
tex.colorSpace = THREE.SRGBColorSpace;
tex.flipY = false;
tex.needsUpdate = true;
for (const mat of materials) { mat.map = tex; mat.emissiveMap = tex; mat.needsUpdate = true; }
```

## Sizes for an inline preview

Measured on one character: each clip GLB ships a full copy of the skinned mesh (8.1 MB) even
though only the animation is needed - `slim_glb.py clip` cuts it to 37-94 KB. The rig's 4k
texture is 6.0 MB; re-encoded at 1024 px JPEG it is 181 KB, and the geometry is the
remaining 2.0 MB. A rig plus three clips fits in ~2.4 MB, which is what makes an inline,
self-contained viewer page practical.
