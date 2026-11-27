---
name: threejs-3d-generator
description: "Generate, texture, rig, animate, decimate, convert, and download 3D assets for Three.js games via the Tripo OpenAPI v3. Use for text-to-3D, image-to-3D, game-ready GLB/FBX hero characters, creatures, vehicles, buildings, props, weapons, auto-rigging, animation retargeting, model retexturing, and smart low-poly decimation; not for procedural kits (threejs-aaa-graphics-builder) or real-time VFX (threejs-aaa-vfx-builder). Pair with threejs-image-generator for concepts first."
---

# Three.js 3D Generator

Production 3D assets for browser games, prepared for Three.js. Provider: Tripo OpenAPI v3 (`https://openapi.tripo3d.ai/v3`).

Resolve `<this-skill-dir>` from the actual loaded skill file. Resolve sibling skills beside it first, then use the runner's discovered paths. Do not mix installed versions or assume a particular home directory.

## References

| File | Read it when |
| --- | --- |
| `references/api-notes.md` | Tripo v3 endpoint paths, H-series vs P-series model versions, polling, postprocess, decimation, conversion, rigging, animation, downloads |
| `references/threejs-integration.md` | importing outputs into a browser game, GLB/FBX loading, root motion, animation wiring |
| `references/image-generator-workflows.md` | pairing `threejs-image-generator` for concepts, textures, UI art, or image-to-3D inputs |

## API key

The script reads `--api-key` or `TRIPO_API_KEY` (optional `TRIPO_BASE_URL` for regional endpoints). Keys never go in skill files, game code, or reports.

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py probe             # TRIPO_API_KEY=SET|MISSING
python3 <this-skill-dir>/scripts/threejs_3d_asset.py probe --validate  # checks GET /v3/account/balance
```

Keys defined only in a shell profile can be absent from the process env. If the plain probe unexpectedly prints MISSING, use `threejs-game-director/scripts/probe_asset_credentials.sh`, which sources the profile and probes all three providers at once.

Download URLs expire quickly — download immediately after a task succeeds.

## Commands

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py --help
```

Text to 3D — `v3.1-20260211` (H3.1 flagship) or `P2-20260801` (P2.0 native-quad game assets):

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py text \
  --prompt "game-ready sci-fi hover bike, sleek armored panels, strong readable silhouette, layered hard-surface detail, PBR materials, clean topology, centered pivot, front facing, no text" \
  --model v3.1-20260211 --texture-quality detailed --geometry-quality detailed \
  --checkpoint artifacts/hover-bike-job.json \
  --wait --download --out-dir assets/models/hover-bike
```

Image to 3D from a generated concept:

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py image \
  --image assets/concepts/hover-bike-front.png --model v3.1-20260211 \
  --enable-image-autofix --texture-alignment original_image --texture-quality detailed \
  --wait --download --out-dir assets/models/hover-bike
```

Status, download, and postprocess (`texture_model`, `rig-check`, `rig`, `retarget`, `conversion`, `decimate`; note `stylize_model` was removed in v3):

```bash
python3 <this-skill-dir>/scripts/threejs_3d_asset.py status TASK_ID
python3 <this-skill-dir>/scripts/threejs_3d_asset.py download TASK_ID --out-dir assets/models
python3 <this-skill-dir>/scripts/threejs_3d_asset.py postprocess --type conversion \
  --input TASK_ID --format GLB --face-limit 20000 --pivot-to-center-bottom \
  --wait --download --out-dir assets/models/glb
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

For coordinated games follow `threejs-game-director/references/asset-recovery.md`; continue independent implementation while generation runs. Explicitly procedural or no-external-service requests override generated-asset defaults. Record pending jobs and user corrections in the project note, preserving completed assets instead of repeating generation.

## Rigging and animation guardrails

Hard-stop rules preventing the expensive failure modes (full measurements, preset tables, and engine fixes live in `references/api-notes.md` and `references/threejs-integration.md`):

| Rule | Requirement |
| --- | --- |
| Source mesh | One fused mesh in full-body symmetric T-pose/A-pose (arms away, legs separated, complete head-to-feet body, no fused props). Keep `--quad` and `--generate-parts` off; verify `rendered_image` before rigging. |
| Pre-rig check | Run free `rig-check` (`POST /v3/animations/rig-check`) first and use detected `rig_type`. `riggable=false` → regenerate pose, never force-rig. |
| Rig version routing | Humanoids & `others` → `v3.0-20260909` (default; supports `tripo`, `mixamo`, `actorcore`, `unity`, `unreal`, `vrm` specs); creatures → `v2.5-20260210`; legacy `v1.0-20240301` remains available via `--rig-model-version v1.0-20240301` (`character-pipeline` routes automatically). |
| Mandatory rig gate | Run `validate-rig rig-model.glb --rig-type <type>` before spending retarget credits; retry degenerate rigs within budget before regenerating the model. |
| Retarget input & format | Pass the **rig** task ID via `--input` (not generation ID). On `v3.0-20260909` and `v2.5` rigs: GLB works, up to 5 presets per task (map `NlaTrack*` by index). If overriding to legacy `v1.0-20240301`: one preset per task, `--model default`, `--out-format fbx` (v1.0 GLB bakes corrupt twist bones). |
| Root motion | **Avoid `--animate-in-place`** (historically corrupted v1.0/v2.5 bakes). Keep root motion baked and strip horizontal `Root.position` X/Z at import (`references/threejs-integration.md`). |
| External skeleton specs | Only `--spec tripo` works with Tripo preset retargeting. Choose `mixamo`, `unity`, `unreal`, `actorcore`, or `vrm` (`v3.0-20260909`) for external clip libraries (apply Blender Z-up Hips bind compensation from `references/threejs-integration.md` when retargeting Mixamo FBX onto Blender GLBs). |
| Post-download QA | Run `validate-animation <clip>` and verify `gltf.animations` track counts before wiring `AnimationMixer`. Creatures have 1 locomotion preset each (use `preset:slash`/`preset:shoot` for biped attacks; rig a dragon twice for ground + `avian` wing chains). |

## Quality

Improve the user's prompt with material, silhouette, camera readability, scale, and game-use constraints. Request GLB/PBR with face limits and texture quality matched to the performance budget; for mobile, favor `smart_low_poly`, `face_limit`, or a later low-poly postprocess. Use generated 3D as hero content and build the surrounding prop kit procedurally.

Inspect unpaused in-game motion after integration: clip transitions, deformation, root motion, foot sliding, and attack/contact timing. Use the QA motion pass for animated work; a successful download or skeleton check is not proof of good animation.

Report task IDs, checkpoint/output paths, model version, texture and geometry settings, animations, conversion settings, Three.js import notes, renderer diagnostics before and after import, active-play screenshots, observed motion, and anything that failed. Put detailed evidence in the project artifact for the lead's consolidated report.
