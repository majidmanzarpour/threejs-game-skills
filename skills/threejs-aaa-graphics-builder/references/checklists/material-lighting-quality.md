# Material and Lighting Quality Checklist

Gate the lighting/material recipes in `references/render-recipes.md` and the material kit in `references/technical-art.md`.

- Renderer color space, tone mapping, exposure, and shadow settings are intentional.
- Key, fill, rim, ambient, and environment lighting follow the lighting stack in `references/render-recipes.md` and clarify depth and gameplay roles.
- Materials avoid flat default looks through roughness/metalness/emissive/vertex-color variation.
- Important objects have readable silhouettes against background, fog, and effects.
- Shadows help ground assets without obscuring navigation or collision boundaries.
- Fog, bloom, particles, and post-processing support readability instead of hiding it.
- Procedural textures or decals are scaled, stable, and not visually noisy during movement.
- Materials reuse the shared kit in `references/technical-art.md` where possible and are disposed when obsolete.
- Desktop and mobile screenshots are checked after lighting/material changes.
- Renderer info or frame-time evidence is gathered when render cost changes.
