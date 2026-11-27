# Tripo OpenAPI v3 Notes

These notes summarize the official Tripo OpenAPI **v3** docs used by this skill (Tripo retired the legacy v2 `/v2/openapi/task` endpoint in late 2026).

## Base API (v3)

- Base URL: `https://openapi.tripo3d.ai/v3` (China region: `https://openapi.tripo3d.com/v3`, override via `TRIPO_BASE_URL`).
- Auth: `Authorization: Bearer <TRIPO_API_KEY>`.
- Account balance check (`probe --validate`): `GET /v3/account/balance`.
- File upload: `POST /v3/files` (`multipart/form-data`, field `file`; images `png/jpeg/webp` <= 20MB, 3D models `glb/gltf/fbx/obj/stl` <= 150MB) → returns `data.file_token`.
- Task query: `GET /v3/tasks/:task_id`.

Task responses use `code` (`0` = success, nonzero = API error) and `data`. Common v3 metadata fields include `created_at`, `completed_at`, and `credits_consumed`.

## Task Status

Ongoing: `queued`, `running`.

Final: `success`, `failed`, `banned`, `expired`, `cancelled`, `unknown`.

Query a task with the same API key that created it. Output download URLs expire quickly (often within minutes to 2 hours), so download immediately.

## Checkpointed Jobs

Usage is in `SKILL.md` → Resuming and Recovery. The helper's guarantees behind it:

- Checkpoint writes are atomic and concurrent access is locked. A saved submission intent with no accepted ID is uncertain, even after a crash: reconcile it with a real recovered task ID via `resume PATH --task-id ID`, and never edit the journal to pretend it was rejected.
- Remote input URLs are not stored; if an image task was never accepted, `resume PATH --image URL` supplies the source again. Local paths and completed files must stay available.
- Safe GETs get up to four attempts with bounded exponential backoff and `Retry-After` handling; task POSTs are never auto-retried. A polling timeout leaves a resumable accepted job, and `resume` refreshes expired download URLs from task status.

## Core v3 Endpoints

Instead of v2's universal `POST /task` + `type`, v3 routes each capability to a dedicated REST path and uses `model` (instead of `model_version`) and `input` (`task_id`, `file_token`, or URL, instead of `original_model_task_id` / `file`):

| Capability | v3 Endpoint | Notes |
| --- | --- | --- |
| Text to 3D | `POST /v3/generation/text-to-model` | `prompt`, `model` (`v3.1-20260211` H-series or `P2-20260801` P-series quads), `texture_quality` (`fast`/`standard`/`detailed`/`extreme`), `geometry_quality`, `pbr`, `face_limit`. |
| Image to 3D | `POST /v3/generation/image-to-model` | `input` (`file_token` from `/v3/files` or URL), `model`, `enable_image_autofix`, `texture_alignment` (`original_image`/`geometry`), `orientation` (`default`/`align_image`). |
| Multiview to 3D | `POST /v3/generation/multiview-to-model` | Directional reference inputs for higher silhouette accuracy. |
| Retexture | `POST /v3/models/texture` | `input`, `model` (default `v3.5-20260815`), `texture_prompt` (`text`/`image`/`images`), `texture_quality`, `delight` (default `true` on v3.5). |
| Format conversion | `POST /v3/models/convert` | `input`, `format` (`GLB`, `GLTF`, `FBX`, `OBJ`, `STL`, `USDZ`, `3MF`), `face_limit`, `quad`, `texture_size`, `texture_format` (`PNG`/`JPG`), `bake`, `flatten_bottom`, `pivot_to_center_bottom`, `scale_factor`, `export_orientation` (`+x`/`-x`/`+y`/`-y`), `texture_packaging` (`embedded`/`zip` for FBX). |
| Smart low-poly / decimate | `POST /v3/mesh/decimate` | `input`, `model` (`v2.0` or `v3.0`), `face_limit` (`500–20000` tris / `500–10000` quads), `quad`, `smart_uv` (`v3.0`). |
| Pre-rig check | `POST /v3/animations/rig-check` | Free check; `input` only → returns `riggable` (bool) and `rig_type`. |
| Auto-rig | `POST /v3/animations/rig` | `input`, `model`, `rig_type`, `spec` (biped only), `out_format` (`glb`/`fbx`). |
| Animation retarget | `POST /v3/animations/retarget` | `input` (the rig task ID), `animation` or `animations` (max 5), `out_format`. |

> **Removed in v3:** `stylize_model` (LEGO / voxel / Voronoi / Minecraft) was deprecated and removed in Tripo API v3.

## Rigging and Animation

Chain: generation task → `POST /v3/animations/rig-check` → `POST /v3/animations/rig` → `POST /v3/animations/retarget`.

### Source-model requirements

- Generate characters as one fused mesh. `generate_parts` requires `texture=false` and `pbr=false`, so a parts-segmented character cannot be textured and does not fit the rig pipeline.
- Avoid `quad=true` for characters bound for GLB: quad forces FBX output and caps default face counts.

### `POST /v3/animations/rig-check`

- Request takes only `input` (`task_id`, `file_token`, or model URL); no `model` parameter; free (0 credits).
- Output: `riggable` (bool) plus detected `rig_type` (`biped`, `quadruped`, `hexapod`, `octopod`, `avian`, `serpentine`, `aquatic`, `others`).
- Treat `riggable=false` as a strong warning: regenerate with a clearer full-body T-pose rather than forcing a rig.

### `POST /v3/animations/rig`

Routing by body plan:

- **Humanoids & custom (`biped`, `others`):** Default to **`model: "v3.0-20260909"`**. Introduced in late 2026 as the recommended humanoid rigger, superseding the June 2026 v2.x limb-chain rigger (which went 0/16 on humanoids). Supports engine-standard biped skeleton `spec` values: `tripo` (default, required for Tripo preset retargeting), `mixamo`, `actorcore`, `unity`, `unreal`, and `vrm`. Still run `validate-rig` and inspect live motion in Three.js before multiplying clips.
- **Creatures (`quadruped`, `hexapod`, `octopod`, `avian`, `serpentine`, `aquatic`):** Default to **`model: "v2.5-20260210"`** (verified symmetric 5–6 bone chains on quadrupeds/dragons).
- **Legacy humanoid fallback (`v1.0-20240301`):** Pass `--rig-model-version v1.0-20240301` if you specifically need the v1.0 anatomical skeleton (`L_`/`R_` bones + twist bones). Remember v1.0 retargets must run **one clip per task**, omit `model` (`--model default`), and export **`out_format="fbx"`** because v1.0's GLB bake corrupts twist-bone space.

### Rig validation gate (mandatory before retargeting)

`riggable=true` from rig-check does not guarantee a usable rig. Auto-rigging is nondeterministic and can still produce degenerate or asymmetric skeletons. Always validate the downloaded rig GLB before spending retarget credits:

```bash
python3 .../threejs_3d_asset.py validate-rig path/to/rig-model.glb --rig-type biped
```

`validate-rig` validates `tripo::` limb-chain depth/symmetry (v2.x/v3.0), legacy `L_`/`R_` anatomical pairs (v1.0), and standard skinned joint hierarchies (`mixamo`/`unity`/`unreal`/`vrm`/`actorcore`). `character-pipeline --rig-retries N` retries automatically (default 2) before regenerating the base model.

### `POST /v3/animations/retarget`

- `input`: the **rig** task ID, not the generation task ID.
- Supply exactly one of `animation` (single preset string) or `animations` (array, max length 5).
- `out_format`: `glb` (default) or `fbx`. (`bake_animation` is largely obsolete in v3; `export_with_geometry` controls mesh inclusion.)
- Batched GLB retargets name clips `NlaTrack`, `NlaTrack.001`, … in request order — map by index and rename after import.
- **Avoid `animate_in_place=true`**: verified to corrupt baked clips on v1.0/v2.5 rigs (mirrored limbs / exploded skinning). Keep root motion baked and strip horizontal `Root.position` X/Z in Three.js (`references/threejs-integration.md`).
- Out-of-credit error: code `2010` ("You don't have enough credit to create this task"). Surface as a top-up blocker; do not retry.

### Preset catalog

There is no `preset:attack`; the biped attack presets are `preset:slash` and `preset:shoot`.

- **Biped (`v3.0-20260909` / `v2.5`):** `preset:idle`, `preset:walk`, `preset:run`, `preset:dive`, `preset:climb`, `preset:jump`, `preset:slash`, `preset:shoot`, `preset:hurt`, `preset:fall`, `preset:turn` (plus legacy `preset:biped:*` options on `v3.0` / `v1.0`).
- **Non-biped:** `preset:quadruped:walk`, `preset:hexapod:walk`, `preset:octopod:walk`, `preset:serpentine:march`, `preset:aquatic:march`. (Avian has no documented preset — rig once for ground locomotion and a second time with `rig_type=avian` for procedural wing flapping or external retargeting.)

### Riggable-character generation recipe

- Prompt or reference image: full-body T-pose or A-pose, arms horizontal and away from body, legs apart, front-facing, symmetric, anatomically complete head-to-feet body, no fused props/capes.
- Keep `texture`/`pbr` on, `quad` off, `generate_parts` off, and inspect `rendered_image` before rigging.

## Common v3 Output Fields

`GET /v3/tasks/{task_id}` returns `output` with v3 `*_url` keys (the helper normalizes both v3 `*_url` and legacy v2 keys):

- `pbr_model_url` (or `pbr_model`): PBR model download URL (GLB unless `quad=true`).
- `model_url` (or `model`): primary textured/rigged/converted model URL.
- `base_model_url` (or `base_model`): untextured base mesh URL (when `texture=false` and `pbr=false`).
- `rendered_image_url` (or `rendered_image`): rendered preview thumbnail URL.
- `generated_image_url` (or `generated_image`): intermediate generated image URL.

## Game Defaults

- **Hero organic/AAA props:** `v3.1-20260211` (H3.1 flagship) with `texture_quality=detailed`, GLB/PBR.
- **Clean game topology / native quads:** `P2-20260801` (Tripo P2.0) or `P1-20260311`, with `face_limit` matched to desktop/mobile budgets.
- **Background props:** `texture_quality=standard` (or `fast` for quick drafts), plus `/v3/mesh/decimate` (`face_limit`) or `/v3/models/convert` (`pivot_to_center_bottom`, `texture_size`).
- **Retexturing:** `/v3/models/texture` defaults to `v3.5-20260815` (`delight: true` by default for clean PBR albedo).
- **Rigging:** CLI auto-routes `biped`/`others` → `v3.0-20260909` and creatures → `v2.5-20260210`; override with `--rig-model-version v1.0-20240301` when targeting legacy FBX bipeds.
