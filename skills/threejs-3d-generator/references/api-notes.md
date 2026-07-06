# Tripo API Notes

These notes summarize the official Tripo OpenAPI docs used by this skill.

## Base API

- Base URL: `https://api.tripo3d.ai/v2/openapi`
- Auth: `Authorization: Bearer <TRIPO_API_KEY>`
- Task create: `POST /task`
- Task query: `GET /task/:task_id`
- Direct image upload: `POST /upload/sts` with `multipart/form-data`
- STS token upload flow: `POST /upload/sts/token`

Task responses use `code` and `data`. Treat nonzero `code` as an API error.

## Task Status

Ongoing:

- `queued`
- `running`

Final:

- `success`
- `failed`
- `banned`
- `expired`
- `cancelled`
- `unknown`

Query a task with the same API key that created it. Output download URLs usually expire after a few minutes, so download immediately.

## Core Task Types

- `text_to_model`: prompt to model.
- `image_to_model`: uploaded image token or image URL to model.
- `multiview_to_model`: four directional views to model.
- `import_model`: import an uploaded model file.
- `texture_model`: retexture or PBR texture an existing model task.
- `stylize_model`: stylize a model as LEGO, voxel, Voronoi, or Minecraft style when supported.
- `animate_prerigcheck`: check whether a model can be rigged. See "Rigging and Animation".
- `animate_rig`: auto-rig a model. See "Rigging and Animation".
- `animate_retarget`: retarget preset animations onto a rig task. See "Rigging and Animation".
- `conversion`: export/convert model format.
- `mesh_segmentation`: segment model parts.
- `mesh_completion`: complete selected model parts.
- `highpoly_to_lowpoly`: smart low-poly conversion.

## Rigging and Animation

Chain: generation task -> `animate_prerigcheck` -> `animate_rig` -> `animate_retarget`. Each step has different task-ID and version semantics; getting them wrong is the main cause of silent rig/animation failures.

### Source-model requirements

- Rig/retarget/prerigcheck accept source generation tasks with `model_version` `Turbo-v1.0-20250506` or `v2.0-20240919` and newer. 1.x generation tasks are not supported. `v3.1-20260211` works.
- Generate characters as one fused mesh. `generate_parts` is incompatible with `texture=true`/`pbr=true` and with `quad=true`, so a parts-segmented character cannot be textured and does not fit the rig pipeline.
- Avoid `quad=true` for characters bound for GLB: quad forces FBX output and defaults `face_limit` to 10000 when unset.

### `animate_prerigcheck`

- Request takes only `type` and `original_model_task_id`. There is no `model_version` parameter.
- Output: `riggable` (bool) plus detected `rig_type` (`biped`, `quadruped`, `hexapod`, `octopod`, `avian`, `serpentine`, `aquatic`).
- Use the detected `rig_type` to choose the `animate_rig` rig type and compatible presets.
- Official docs note `riggable=false` "doesn't necessarily mean it cannot be rigged". Treat false as a strong warning: the best response is to regenerate with a clearer full-body T-pose, not to force the rig.

### `animate_rig`

Version choice is THE quality lever, and the right answer differs by body plan (measured June 2026):

- HUMANOIDS: use `model_version=v1.0-20240301`. It produces a proper anatomical skeleton (Hip, Pelvis, Spine01/02, Head, L_/R_ Clavicle/Upperarm/Forearm/Hand/Thigh/Calf/Foot/ToeBase plus twist bones) and unlocks the large `preset:biped:*` clip library. The v2.x "Limb chain" rigger went 0/16 on humanoid test meshes (plate armor, fitted armor, T-pose, A-pose — always asymmetric chains like a 9-bone arm vs 4, or a 1-bone leg), while v1.0 produced a clean symmetric skeleton first try with 39-40 channel clips.
- CREATURES (quadruped/hexapod/octopod/avian/serpentine/aquatic): use `model_version=v2.5-20260210`. The v2.x limb-chain rigger handles creatures well (symmetric 5-6 bone chains observed on quadruped and avian dragons).
- `original_model_task_id`: the generation task ID.
- `rig_type`: defaults to `biped`. Pass the prerigcheck-detected type for creatures.
- `spec`: `tripo` (default) or `mixamo`. Only `spec=tripo` rigs can be used with Tripo `animate_retarget`. Choose `mixamo` only when retargeting external animation libraries (Mixamo/custom clips) outside Tripo.
- `out_format`: `glb` (default) or `fbx`.

### Rig validation gate (mandatory before retargeting)

`riggable=true` from prerigcheck does NOT guarantee a usable rig. Auto-rigging can silently produce a degenerate skeleton (observed in practice: a biped rig with only 9 bones — Root, Spine_0-2, and one arm; no legs, no right arm, no head). Every retarget on such a rig inherits the damage: clips contain channels only for the mapped bones and the character stays frozen in bind pose at runtime.

After downloading the rig GLB and before spending retarget credits, validate the skeleton:

```bash
python3 .../threejs_3d_asset.py validate-rig path/to/rig-model.glb --rig-type biped
```

A structurally valid rig has both `_Left_Limb_` and `_Right_Limb_` chains with matching chain depths per limb row (±1 bone is normal variance; healthy rigs are 5/5, 6/6, or 6/5 — broken ones are 9/4, 2/4, or 4/1, and a 1-bone leg cannot bend a knee, warping every clip), at least 3 bones per limb chain for biped/quadruped, two limb rows (`0_` arms, `1_` legs), and a plausible bone count. v1.0 rigs use anatomical names instead (validated as L_/R_ pairs: Clavicle, Upperarm, Forearm, Hand, Thigh, Calf, Foot). The `character-pipeline` command runs this check automatically; `validate-rig` runs it standalone, and `validate-animation` QAs the retargeted clips (scale tracks, limb-stretch translations, durations, channel coverage).

Auto-rigging is NONDETERMINISTIC: the same model can produce a degenerate skeleton on one attempt and a healthy one on the next. When validation fails, retry the rig task first (~25 credits) before regenerating the model (~30+ credits); `character-pipeline --rig-retries N` does this automatically (default 2). Hard-surface armored characters (plate knights, mechs) fail rig validation far more often than organic meshes — budget several retries or prefer visible-anatomy designs. If retries keep failing, regenerate the base model with clearer limb separation — strict T-pose, arms horizontal, legs apart and fully visible, no long skirt/tabard/cape/props fusing limbs into the body silhouette. Use `character-pipeline --model-task-id TASK_ID` to resume from an existing generation without paying for regeneration.

### `animate_retarget`

- `original_model_task_id`: the RIG task ID, not the original generation task ID.
- For v2.5 rigs, pass `model_version: v2.5-20260210`. For v1.0 rigs, OMIT model_version entirely (the CLI accepts `--model-version default`): the retarget enum rejects an explicit `v1.0-20240301` with HTTP 400 `code: 2017` "The version value is invalid", but the server default retargets v1.0 rigs correctly.
- Exactly one of `animation` (single preset string) or `animations` (array, max length 5) is required. Batch clips into one task instead of one task per clip; it is faster and cheaper.
- `out_format`: `glb` (default) or `fbx`. `bake_animation`: default true, glb only. `export_with_geometry`: default true.
- v1.0 RIGS: ONE ANIMATION PER RETARGET TASK. Batching via `animations` makes the FBX contain one armature object per clip (`Armature.001`, `.002`, …) with name-colliding bones; engines bind takes to the wrong skeleton and the body pitches sideways/prone. Submit one task per preset (10 credits each — batching saves nothing).
- v1.0 RIGS MUST RETARGET WITH `out_format=fbx`. Root cause (verified June 2026): Tripo's animation pipeline is FBX-native (their own tutorials are FBX end-to-end and never use GLB for animation). The GLB bake of v1.0 retargets exports twist-bone transforms in the wrong space — and the limb mesh is skinned almost entirely to twist bones, so arms/legs collapse into the torso in every engine (reproduced identically in three.js and Babylon; the FBX of the same task is correct, with real clip names like `walk_normal_m_remap` instead of `NlaTrack`). Load FBX with three.js `FBXLoader`, or convert FBX→GLB offline (Blender / FBX2glTF). v2.5 creature-rig retargets export GLB correctly.
- NEVER set `animate_in_place=true`. Verified June 2026: it corrupts the baked clips — on v1.0 rigs limbs mirror/cross sides (arms fold into the chest, legs cross the midline, "twisted opposite directions"), on v2.5 rigs skinned regions explode into shards. Keep root motion baked and strip the root translation track in the engine instead (see `threejs-integration.md`). Forward-kinematics fingerprint of the corruption: in a walk clip, both hands sit on the same side of the hip instead of mirrored sides.
- Set quality expectations honestly: Tripo's own blog describes auto-rigging as "80-90% of the way there" with shoulders, hips, and fingers needing the most manual refinement. For hero characters, plan a manual pass (or a Mixamo pipeline via `spec=mixamo` + their FBX clips).
- A batched task returns one GLB containing all requested clips, named `NlaTrack`, `NlaTrack.001`, … in request order. Map clips by index, not name.
- Observed credits (June 2026): retarget costs ~10 credits per animation whether batched or separate (batch of 4 = 40); prerigcheck is free (0 credits); rig ~25; text_to_model with detailed texture ~30. Batching saves task count, not credits. Failed rig tasks consume 0 credits, but rig retries on success do — budget ~25 credits per retry when planning character work.
- Out-of-credit error: HTTP 403 with `code: 2010` ("You don't have enough credit"). Surface this to the user as a purchase/top-up blocker; do not retry.

### Preset catalog (v2.5-20260210 / v2.0-20250506 rigs)

This is the complete documented list. There is no `preset:attack`; the attack-like presets are `preset:slash` and `preset:shoot`.

- Biped (11): `preset:idle`, `preset:walk`, `preset:run`, `preset:dive`, `preset:climb`, `preset:jump`, `preset:slash`, `preset:shoot`, `preset:hurt`, `preset:fall`, `preset:turn`.
- Quadruped: `preset:quadruped:walk`. Hexapod: `preset:hexapod:walk`. Octopod: `preset:octopod:walk`. Serpentine: `preset:serpentine:march`. Aquatic: `preset:aquatic:march`.
- Avian: no documented preset for v2.5 rigs.
- The large legacy `preset:biped:*` library (~100 clips: dance variants, etc.) only works with `v1.0-20240301` rigs (biped only). Tradeoff: current-quality v2.5 rig with 16 presets vs legacy v1.0 rig with the big biped clip library.

Non-biped coverage is one locomotion clip per rig type — there is NO fly, crawl-variant, attack, idle, or hurt preset for creatures. Plan multi-mode creatures (e.g. a dragon that crawls AND flies) as:

- Ground locomotion: rig the creature's ground rig type (e.g. quadruped) and retarget its walk preset.
- Flight/secondary modes: rig the SAME model task again with `rig_type=avian` (a second ~25-credit rig task on one model is allowed) to get wing limb chains, then drive wing bones procedurally in the engine (sinusoidal flap on the wing chain) or retarget external clips via `spec=mixamo`.
- Per-mode rigs are separate GLBs of the same mesh; swap or crossfade them at the engine level by game state.

### Riggable-character generation recipe

- Prompt or reference image: full-body T-pose or A-pose, arms away from body, legs separated, front-facing, symmetric, no props fused into the silhouette, whole body in frame.
- The body must be anatomically complete, including a head. Over-constraining a prompt ("no cape, no shield, slim silhouette") can yield an empty/headless armor shell; the rig task then fails outright (`status: failed`, `error_code: 1001`, no credits consumed). Check the rendered preview for a complete head-to-feet body before rigging.
- Keep `texture`/`pbr` on, `quad` off, `generate_parts` off, and a sane `face_limit`.
- Before rigging, check `rendered_image` actually shows a T/A-pose. If not, regenerate with a stronger pose instruction or a `threejs-image-generator` T-pose reference image instead of rigging a bad pose.
- For non-biped creatures, expect only the single locomotion preset for that rig type; plan extra animations via external retargeting (`spec=mixamo`) or procedural motion in Three.js.

## Common Output Fields

- `model`: model download URL.
- `base_model`: untextured/base model URL.
- `pbr_model`: PBR model URL.
- `rendered_image`: preview image URL.
- `generated_image`: generated image URL.
- `generate_multiview_image`: front/left/back/right view URLs.

## Game Defaults

- Prefer H3 text/image-to-model: `v3.1-20260211` when quality matters.
- Prefer GLB/PBR for Three.js runtime imports.
- Use `texture_quality=detailed` for high-value hero assets; use `standard` for background assets.
- Use `geometry_quality=detailed` only when the asset needs it and budget allows.
- Use `face_limit`, `smart_low_poly`, conversion, or low-poly postprocess for browser/mobile budgets.
- Use T-pose/A-pose references for rigged characters; keep `quad` and `generate_parts` off for anything that will be rigged.
- Rig/retarget version routing: the CLI routes by `--rig-type` (biped -> `v1.0-20240301`, creatures -> `v2.5-20260210`; v1.0 retargets omit `model_version` because the enum rejects it). Pass `--rig-type` on standalone `postprocess` calls so the routing is correct; only pin `--model-version` to override. Raw API callers must pin explicitly — the server's unpinned defaults are legacy versions.
