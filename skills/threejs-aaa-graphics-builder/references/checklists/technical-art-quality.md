# Technical Art Quality Checklist

Use before claiming premium, AAA, showcase, high-fidelity, or less-basic visual quality after graphics changes. Each item gates the guidance in `references/technical-art.md`.

- Technical art brief converts art direction into shapes, material roles, lighting, VFX, camera, UI/world motifs, and budgets.
- Hero surfaces and support surfaces are identified separately.
- Material kit uses the named shared roles from `references/technical-art.md`, not scattered one-off colors/materials.
- Shader/post-processing choices have player-facing purpose and measured or bounded cost.
- VFX follow the event-driven language in `references/technical-art.md`: readable, short-lived, and not hiding collision, threats, rewards, or UI.
- Instancing is used for large repeated same-geometry/same-material detail where appropriate.
- LOD, culling, or simplified far variants are planned for heavy background/imported assets.
- Imported/generated models have scale, pivot/orientation, bounds, file size, triangle/material/texture counts when available, and collision proxies checked.
- Decals/trim/detail systems reinforce function, route, faction, scale, or state.
- Threats, rewards, interactables, and player state are not communicated by color alone.
- DPR cap, shadow settings, post-processing passes, and mobile tradeoffs are reported.
- Renderer diagnostics match the render budget reporting in `references/technical-art.md`: calls, triangles, geometries, textures, and material count when available.
- Final visual scorecard performance evidence category includes budget and technical-art evidence, not only screenshots.
