# Performance-Safe Visual Detail Checklist

Gate the render budget and instancing/LOD guidance in `references/technical-art.md`.

- Baseline renderer info is captured when increasing fidelity.
- Draw calls, triangles, geometries, materials, textures, and frame time are reviewed against the render budget in `references/technical-art.md` after changes.
- Repeated details use the instancing/LOD approach in `references/technical-art.md`: instancing, shared resources, atlases, or generated texture reuse where practical.
- High segment counts are limited to silhouette-critical forms.
- Shadows are scoped by light count, shadow map size, casters/receivers, and camera distance.
- Post-processing is justified by gameplay readability or strong art direction.
- DPR caps or adaptive quality are considered for mobile.
- Generated resources have a disposal/reuse strategy.
- The worst-case gameplay scene, not only idle view, is inspected.
- Visual detail remains readable at mobile resolution without excessive GPU cost.
