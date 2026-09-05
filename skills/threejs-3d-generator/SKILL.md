---
name: threejs-3d-generator
description: "Generate, texture, rig, animate, stylize, convert, and download 3D assets for Three.js games via the Tripo API. Use for text-to-3D, image-to-3D, game-ready GLB/FBX, characters, creatures, buildings, props, weapons, terrain, auto-rigging, animation retargeting, model texturing, voxel/LEGO stylization, and low-poly conversion. Pair with threejs-image-generator for concept and texture references first."
---

# Three.js 3D Generator

Production 3D assets for browser games, prepared for Three.js. Provider: Tripo.

Resolve `<this-skill-dir>` from the actual loaded skill file. Resolve sibling skills beside it first, then use the runner's discovered paths. Do not mix installed versions or assume a particular home directory.

## References

| File | Read it when |
| --- | --- |
| `references/api-notes.md` | endpoint and task decisions, model versions, polling, postprocess, conversion, rigging, animation, downloads |
| `references/threejs-integration.md` | importing outputs into a browser game, GLB/FBX loading, root motion, animation wiring |
| `references/image-generator-workflows.md` | pairing `threejs-image-generator` for concepts, textures, UI art, or image-to-3D inputs |

## API key

The script reads `--api-key` or `TRIPO_API_KEY`. Keys never go in skill files, game code, or reports.

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py probe   # TRIPO_API_KEY=SET|MISSING
```

Keys defined only in a shell profile can be absent from the process env. If the plain probe unexpectedly prints MISSING, use `threejs-game-director/scripts/probe_asset_credentials.sh`, which sources the profile and probes all three providers at once.

Download URLs expire quickly — download immediately after a task succeeds.

## Commands

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py --help
```

Text to 3D, the default for a premium hero model:

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py text \
  --prompt "game-ready sci-fi hover bike, sleek armored panels, strong readable silhouette, layered hard-surface detail, PBR materials, clean topology, centered pivot, front facing, no text" \
  --model-version v3.1-20260211 --texture-quality detailed --geometry-quality detailed \
  --checkpoint artifacts/hover-bike-job.json \
  --wait --download --out-dir assets/models/hover-bike
```

Image to 3D from a generated concept:

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py image \
  --image assets/concepts/hover-bike-front.png --model-version v3.1-20260211 \
  --enable-image-autofix --texture-alignment original_image --texture-quality detailed \
  --wait --download --out-dir assets/models/hover-bike
```

Status, download, and postprocess (`texture_model`, `animate_prerigcheck`, `animate_rig`, `animate_retarget`, `conversion`, `stylize_model`):

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py status TASK_ID
python3 <this-skill-dir>/scripts/threejs_3d_asset.py download TASK_ID --out-dir assets/models
python3 <this-skill-dir>/scripts/threejs_3d_asset.py postprocess --type conversion \
  --original-task-id TASK_ID --format GLTF --face-limit 20000 --wait --download --out-dir assets/models/gltf
```

Animated character pipeline: generation, prerigcheck, validated rig with bounded retries, retargets, and downloads, routed by body plan. Use checkpoints and stop between stages to inspect before spending on dependent work:

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py character-pipeline \
  --prompt "stylized cyber runner character, T-pose, full body, game-ready outfit, readable silhouette" \
  --animations preset:idle,preset:walk,preset:run,preset:jump \
  --checkpoint artifacts/cyber-runner-job.json --stop-after model \
  --out-dir assets/models/cyber-runner

# After inspecting the downloaded model/preview:
python3 <this-skill-dir>/scripts/threejs_3d_asset.py resume artifacts/cyber-runner-job.json --stop-after rig
# After inspecting the validated rig:
python3 <this-skill-dir>/scripts/threejs_3d_asset.py resume artifacts/cyber-runner-job.json --stop-after animations

python3 <this-skill-dir>/scripts/threejs_3d_asset.py character-pipeline \
  --prompt "stylized wolf, quadrupedal stance, all four legs planted and separated, full body" \
  --rig-type quadruped --animations preset:quadruped:walk \
  --checkpoint artifacts/wolf-job.json --stop-after model --out-dir assets/models/wolf
```

## Resuming and Recovery

`--checkpoint PATH` is optional on `text`, `image`, `postprocess`, and `character-pipeline`. It records accepted task IDs immediately, stage status, and downloaded file fingerprints; no API keys or signed output URLs go in the checkpoint. Use a separate checkpoint per job. Existing checkpoints must be resumed, not overwritten, and concurrent use is locked.

For background single-task generation omit `--wait`, retain the printed task ID/checkpoint, and run `resume CHECKPOINT` later. Single-task resume waits/downloads that task only; it does not add rigging. Character resume reuses completed stages and continues through animations unless `--stop-after model|rig|animations` limits this invocation. Credentials still come from the current environment. The checkpoint records absolute local paths, so keep its referenced files in place.

The helper retries safe status/download reads with bounded backoff, never paid task submissions. Missing credentials, exhausted credits, invalid input, transient errors, and uncertain submissions are reported distinctly. On interruption, resume the existing job rather than starting over. If a POST may have succeeded but no task ID was received, find it in provider history and use `resume CHECKPOINT --task-id RECOVERED_ID`; do not invent an ID or submit a replacement blindly. Without a recoverable ID, report the uncertainty before any potentially duplicate charge.

For coordinated games follow the director's `references/asset-recovery.md`; continue independent implementation while generation runs. Explicitly procedural or no-external-service requests override generated-asset defaults. Record pending jobs and user corrections in the project note, preserving completed assets instead of repeating generation.

## Rigging and animation

These rules prevent nearly every expensive failure. Full parameter tables and the measurements behind them are in `references/api-notes.md`.

- Generate characters as one fused mesh: keep `--quad` and `--generate-parts` off (`generate_parts` disables texturing, `quad` forces FBX output).
- Require full-body T-pose or A-pose, arms away from the body, symmetric, no props fused to the silhouette. Check the rendered preview really is in that pose before rigging; regenerate if not.
- Run `animate_prerigcheck` first (it takes no model version, costs nothing) and use the detected `rig_type`. `riggable=false` means regenerate with a clearer pose, not force a rig.
- **Rig version is routed by body plan.** Humanoids use `v1.0-20240301` — the anatomical skeleton with twist bones and the large `preset:biped:*` library. The v2.x limb-chain rigger went 0/16 on humanoid meshes, armored or not, always producing asymmetric chains. Creatures use `v2.5-20260210`. `character-pipeline` routes this automatically.
- `riggable=true` does not guarantee a usable rig. Validate the skeleton before retargeting — `validate-rig rig-model.glb --rig-type biped` — checking both bone presence and chain depth, since a 1-bone leg warps every clip. A missing or malformed rig GLB is a failure, including with `--force-rig`. Auto-rigging is nondeterministic: on failure retry the rig task (~25 credits) within the chosen budget before regenerating the model. Armored hard-surface characters need the most retries.
- `animate_retarget` takes the **rig** task ID, not the generation task ID. Non-biped rigs batch up to 5 presets per task; batched clips come back as `NlaTrack`, `NlaTrack.001`, … in request order, so map by index and rename after import.
- Retarget v1.0 rigs with `--model-version default` — the enum rejects an explicit `v1.0-20240301` with HTTP 400 code 2017, but the server default handles them.
- v1.0 retargets must use `--out-format fbx` (the script enforces it): Tripo's GLB bake on this path writes twist-bone transforms in the wrong space and limbs collapse into the torso. v2.5 creature retargets are fine as GLB.
- **Never pass `--animate-in-place`.** It corrupts the bake — mirrored and crossed limbs on v1.0, exploded skinning on v2.5. Keep root motion baked and strip it at import instead; the engine snippet is in `references/threejs-integration.md`.
- Creatures get one locomotion preset each, and there is no `preset:attack` (use `preset:slash` or `preset:shoot`). A creature's mesh stance drives how a preset reads — a quadruped walk on an upright dragon looks like a person walking, so generate creatures in the stance the animation expects.
- Multi-mode creatures (a dragon that crawls and flies) need the same model rigged twice: the ground rig type for locomotion, `avian` for wing chains.
- Use `--spec tripo` (default) when Tripo presets will be retargeted; `--spec mixamo` rigs cannot be retargeted by Tripo and are for external pipelines only.
- After download, run `validate-animation clip.glb` (flags scale tracks, limb-stretching translation, extreme rotations, per-clip duration and channel coverage), then check `gltf.animations` names and counts before wiring the `AnimationMixer`.

## Quality

Improve the user's prompt with material, silhouette, camera readability, scale, and game-use constraints. Request GLB/PBR with face limits and texture quality matched to the performance budget; for mobile, favor `smart_low_poly`, `face_limit`, or a later low-poly postprocess. Use generated 3D as hero content and build the surrounding prop kit procedurally.

Inspect unpaused in-game motion after integration: clip transitions, deformation, root motion, foot sliding, and attack/contact timing. Use the QA motion pass for animated work; a successful download or skeleton check is not proof of good animation.

Report task IDs, checkpoint/output paths, model version, texture and geometry settings, animations, conversion settings, Three.js import notes, observed motion, and anything that failed. Put detailed evidence in the project artifact for the lead's consolidated report.
