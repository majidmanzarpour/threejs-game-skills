# Three.js Image Generator Pairing

Use `threejs-image-generator` when a strong 2D input improves Meshy output or when the final
asset is 2D rather than 3D. The current image provider is Google's Gemini image API.

## 2D To 3D Reference Images

Generate clean reference images before image-to-3D for:

- Characters: full-body T-pose or A-pose, neutral expression, visible hands and feet, no cropped limbs.
- Creatures: side and front silhouettes, clear limb count, readable anatomy.
- Vehicles: front, side, and three-quarter concepts, clear wheels/thrusters/wings, material zones.
- Buildings: front elevation, roof silhouette, doors and windows, scale cues.
- Weapons and tools: side view, readable handle/blade/barrel proportions, material callouts.
- Props and pickups: centered object, plain background, strong silhouette, no baked-in text unless wanted.

For the actual prompt wording, use the templates in `threejs-image-generator`'s SKILL.md under
"Prompt Patterns" — that skill is the canonical source. The notes here cover only how those
references pair into the Meshy pipeline.

## Multi-View Is The Meshy-Specific Win

`multi-image` takes 1-4 views of the **same** subject and produces markedly better backs,
undersides, and silhouettes than a single view. Generate the views as one consistent set:

- Same character, same outfit, same proportions, same lighting, plain background.
- Front, side, back, and optionally a three-quarter view; no view cropped differently.
- No motion blur, no depth of field, no dramatic perspective — orthographic-looking views retopologize best.

A mismatched set is worse than a single good view: Meshy blends the views, so an outfit that
changes between them produces a blended, incoherent model.

## Handoff

1. Save concepts in the working project, usually `assets/concepts/`.
2. Pass local paths straight to `image --image <path>` or `multi-image --images a.png,b.png`.
   Local files are inlined as data URIs automatically; Meshy has no upload endpoint.
3. Keep source images well under the data-URI ceiling — the script warns above 9 MB.
4. Use `--texture-image` to steer the texture pass from a separate style reference.
5. Download generated 3D outputs immediately; links expire in about three days.

## Avoid

- Crowded scene images for single-object generation.
- Cropped limbs, hidden backs, extreme perspective, motion blur, or heavy depth of field.
- Tiny UI or logo text baked into a model texture unless text fidelity is noncritical.
- Using 3D generation for pure 2D UI assets; generate those as images.
