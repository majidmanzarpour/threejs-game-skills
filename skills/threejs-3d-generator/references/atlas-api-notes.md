# Atlas Cloud 3D API Notes

Load this reference before using Atlas Cloud for text-to-3D or image-to-3D work.

## Runtime contract

- Set `ATLASCLOUD_API_KEY`; never place it in browser code, generated game assets, logs, or committed files. The optional `ATLASCLOUD_MEDIA_API_BASE` overrides the API root for compatible deployments; do not use an OpenAI-compatible `/v1` base URL here.
- Query `GET https://api.atlascloud.ai/api/v1/models` before generation. Atlas classifies 3D models as `Image`; select an exact model ID and fetch its published `input_schema` URL.
- Submit the request once to the schema's POST path. A network timeout is ambiguous and must not trigger another POST.
- Save `job.json` immediately after submission. Resume polling the saved prediction ID with `atlas_3d_asset.py resume --job ...`; do not regenerate when polling or downloading fails.
- Poll only the GET path published by the selected model schema. Stop after the configured timeout and preserve the job file.
- Download result URLs without an Authorization header. Download URLs may expire, so fetch completed outputs promptly.

## Provider scope

Atlas is an optional generation provider for text-to-3D and image-to-3D. The bundled Tripo client remains the provider for texture, rigging, retargeting, animation, stylization, and conversion tasks. Do not claim that Atlas generation includes those Tripo-specific post-process operations.

For Three.js, prefer GLB with PBR materials. Validate the GLB header and declared length, then follow `threejs-integration.md` for scale, pivot, bounds, triangle, texture, material, and animation inspection.

## Commands

List the live 3D catalog:

```bash
python3 <this-skill-dir>/scripts/atlas_3d_asset.py models
```

Generate and download a text-to-3D asset:

```bash
python3 <this-skill-dir>/scripts/atlas_3d_asset.py text \
  --prompt "game-ready sci-fi hover bike, centered pivot, PBR materials" \
  --pbr --format GLB --wait --download --out-dir assets/models/hover-bike
```

Generate from a public URL or local JPEG/PNG/WebP image:

```bash
python3 <this-skill-dir>/scripts/atlas_3d_asset.py image \
  --image assets/concepts/hover-bike.png \
  --pbr --format GLB --wait --download --out-dir assets/models/hover-bike
```

Resume after a timeout or interrupted download without another generation POST:

```bash
python3 <this-skill-dir>/scripts/atlas_3d_asset.py resume \
  --job assets/models/hover-bike/job.json --wait --download
```
