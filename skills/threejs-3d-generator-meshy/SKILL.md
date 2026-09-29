---
name: threejs-3d-generator-meshy
description: "Generate, texture, retexture, remesh, rig, animate, and download 3D assets for Three.js games via the Meshy API. Use for text-to-3D, image-to-3D, multi-view image-to-3D, game-ready GLB/FBX, characters, creatures, props, weapons, buildings, humanoid auto-rigging, a 678-clip mocap animation library, text-to-motion clips, retopology, and browser asset pipelines. Use instead of threejs-3d-generator (Tripo) when the user asks for Meshy, when a humanoid character needs many animation clips, or when Tripo credits are exhausted. Pair with threejs-image-generator for concept and texture references first."
---

# Three.js 3D Generator (Meshy)

Production 3D assets for browser games, prepared for Three.js. Provider: Meshy.

Resolve `<this-skill-dir>` from the actual loaded skill file. Resolve sibling skills beside it first, then use the runner's discovered paths. Do not mix installed versions or assume a particular home directory.

## Provider choice

This skill and `threejs-3d-generator` do the same job through different providers, so pick deliberately and say which one the assets came from:

- **Meshy** for humanoid characters that need real animation coverage (678 mocap clips plus text-to-motion against Tripo's preset list), for explicit `pose_mode` control, for retexturing from multi-view references, and for one-call remesh/convert.
- **Tripo** (`threejs-3d-generator`) for non-humanoid rigs — quadruped, avian, serpentine, aquatic — which Meshy's rigger rejects outright, and for stylization (lego/voxel/minecraft/voronoi) and part generation.

Meshy skeletons are Mixamo-like (`mixamorig:*`), so Meshy clips and Mixamo clips interoperate without bone renaming.

## References

| File | Read it when |
| --- | --- |
| `references/api-notes.md` | endpoint and task decisions, model versions, parameters, polling, rigging limits, retention, checkpoints, error categories |
| `references/threejs-integration.md` | importing outputs into a browser game, rigged GLB plus one-clip GLBs, root motion, scale/pivot, budget checks |
| `references/image-generator-workflows.md` | pairing `threejs-image-generator` for concepts, multi-view references, textures, or image-to-3D inputs |
| `references/animations.csv` | the bundled animation library; search it through `list-animations`, do not read the whole file into context |

## API key

The script reads `--api-key` or `MESHY_API_KEY`. Keys never go in skill files, game code, checkpoints, or reports.

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py probe   # MESHY_API_KEY=SET|MISSING
```

Keys defined only in a shell profile can be absent from the process env — on Ubuntu, a `~/.bashrc` export below the non-interactive guard is invisible to a plain `bash -c`. If the plain probe unexpectedly prints MISSING, use `threejs-game-director/scripts/probe_asset_credentials.sh`, which sources the profile and probes every provider at once, and run the helper through the same profile-loaded shell.

Download URLs are retained about three days — download immediately after a task succeeds.

## Commands

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py --help
python3 <this-skill-dir>/scripts/meshy_3d_asset.py balance   # credits before a long run
```

Text to 3D, the default for a premium hero model (submits preview geometry, then chains the texture/refine pass):

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py text \
  --prompt "game-ready sci-fi hover bike, sleek armored panels, strong readable silhouette, PBR materials, centered pivot, no text" \
  --model-type standard --topology triangle --target-polycount 20000 \
  --texture-resolution 2k --pbr --checkpoint artifacts/hover-bike-job.json \
  --wait --download --out-dir assets/models/hover-bike --name hover-bike
```

Untextured geometry only, for props textured in-engine or retextured later:

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py text --prompt "low poly stone crate prop" \
  --model-type lowpoly --target-polycount 3000 --no-refine --wait --download
```

Image to 3D from a generated concept, and multi-view for a sharper silhouette (1-4 images of the same subject; local files become data URIs, there is no upload endpoint):

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py image --image assets/concepts/hover-bike-front.png \
  --texture-resolution 2k --pbr --wait --download --out-dir assets/models/hover-bike

python3 <this-skill-dir>/scripts/meshy_3d_asset.py multi-image \
  --images assets/concepts/front.png,assets/concepts/side.png,assets/concepts/back.png \
  --wait --download --out-dir assets/models/hero
```

Retexture, remesh, status, and download:

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py retexture --input-task-id TASK_ID \
  --text-style-prompt "brushed gunmetal, orange hazard decals, worn edges" --pbr --wait --download
python3 <this-skill-dir>/scripts/meshy_3d_asset.py remesh --input-task-id TASK_ID \
  --topology quad --target-polycount 8000 --wait --download
python3 <this-skill-dir>/scripts/meshy_3d_asset.py status TASK_ID
python3 <this-skill-dir>/scripts/meshy_3d_asset.py download TASK_ID --out-dir assets/models
```

Animation library search — 678 clips, never guess an `action_id`:

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py list-animations --search sword
python3 <this-skill-dir>/scripts/meshy_3d_asset.py list-animations --category Fighting --limit 60
```

Rig and animate an existing humanoid, or generate a custom clip from a prompt first:

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py rig --input-task-id TASK_ID \
  --height-meters 1.8 --wait --download --out-dir assets/models/hero
python3 <this-skill-dir>/scripts/meshy_3d_asset.py animate --rig-task-id RIG_TASK_ID \
  --animations idle,Walking_Woman,Running,4 --wait --download --out-dir assets/models/hero --name hero

python3 <this-skill-dir>/scripts/meshy_3d_asset.py motion \
  --prompt "spin a spear overhead then thrust forward" --duration 3 --mode prime --wait
python3 <this-skill-dir>/scripts/meshy_3d_asset.py animate --rig-task-id RIG_TASK_ID \
  --motion-task-id MOTION_TASK_ID --wait --download
```

Animated character pipeline — generation, texture, rig with an automatic remesh when the face gate trips, clips, downloads, and rig/clip validation in between. Use checkpoints and stop between stages to inspect before spending on dependent work:

```bash
python3 <this-skill-dir>/scripts/meshy_3d_asset.py character-pipeline \
  --prompt "stylized cyber runner character, game-ready outfit, readable silhouette" \
  --pose-mode t-pose --animations idle,walking,running \
  --checkpoint artifacts/cyber-runner-job.json --stop-after model \
  --out-dir assets/models/cyber-runner

# After inspecting the downloaded model:
python3 <this-skill-dir>/scripts/meshy_3d_asset.py resume artifacts/cyber-runner-job.json --stop-after rig
# After inspecting the validated rig:
python3 <this-skill-dir>/scripts/meshy_3d_asset.py resume artifacts/cyber-runner-job.json
```

## Resuming and recovery

`--checkpoint PATH` is optional on every submitting command. It records accepted task IDs immediately, stage status, and downloaded file fingerprints; no API keys, image data URIs, or signed output URLs go in the checkpoint. Use a separate checkpoint per job. Existing checkpoints must be resumed, not overwritten, and concurrent use is locked.

For background generation omit `--wait`, retain the printed task ID/checkpoint, and run `resume CHECKPOINT` later. Single-task resume waits and downloads that task only; it never adds rigging. Character resume reuses completed stages and continues through animations unless `--stop-after model|rig|animations` limits this invocation. Credentials still come from the current environment. The checkpoint records absolute local paths, so keep its referenced files in place; an image source that was a URL or data URI is not stored and must be re-supplied with `resume ... --image PATH`.

The helper retries safe status/download reads with bounded backoff, never paid task submissions. Missing credentials, exhausted credits, invalid input, transient errors, and uncertain submissions are reported as distinct categories (table in `references/api-notes.md`). On interruption, resume the existing job rather than starting over. If a POST may have succeeded but no task ID was received, find it in the Meshy dashboard and use `resume CHECKPOINT --task-id RECOVERED_ID`; do not invent an ID or submit a replacement blindly. Without a recoverable ID, report the uncertainty before any potentially duplicate charge.

For coordinated games follow the director's `references/asset-recovery.md`; continue independent implementation while generation runs. Explicitly procedural or no-external-service requests override generated-asset defaults. Record pending jobs and user corrections in the project note, preserving completed assets instead of repeating generation.

## Rigging and animation

These rules prevent nearly every expensive failure. Full parameter tables and the measurements behind them are in `references/api-notes.md`.

- **Humanoid only.** Meshy's rigger rejects quadrupeds, birds, dragons, and vehicles at submit time, and that rejection costs no credits. A creature that needs a skeleton goes to the Tripo skill; do not retry it here.
- Rig input must be textured, under the face gate, and facing `+Z`. Generate with `--pose-mode t-pose` (or `a-pose`) — a real API parameter here, not prompt wishing.
- Generate characters as one fused mesh and keep props out of the silhouette.
- **Always pass `--target-polycount`** for anything that will be rigged or shipped to a browser. Without it the mesh comes back in the millions of faces (measured: 1.9M faces, 74 MB) and rigging rejects it at 320,000. `character-pipeline` defaults to 30,000 and remeshes automatically if the gate still trips.
- `--height-meters` (default 1.7) sets the output scale, so the rigged GLB arrives in metres.
- One clip per animation task; a comma list becomes several tasks. Names in `--animations` resolve against the bundled library (case-insensitive, prefix match), and an ambiguous token prints the alternatives it did not pick.
- After download, run `validate-rig rig.glb` (core plus symmetric limb chains) and `validate-animation clip.glb` (scale tracks, limb-stretch translation tracks, per-clip duration and channel coverage), then verify motion visually in the engine.
- Clips are baked with root motion. Strip only the horizontal root translation at import; vertical carries jumps and gait bob. The engine snippet is in `references/threejs-integration.md`.

## Verify rigged characters in the browser

A rig and its clips are not verified until they have played in three.js. The validators read the files; the viewer plays them on the actual skeleton and measures the result, which is how the clip-rescale trap in `references/threejs-integration.md` was caught.

```bash
python3 <this-skill-dir>/scripts/slim_glb.py clip assets/models/hero/hero-000-Idle-animation_glb.glb preview/idle.glb
python3 <this-skill-dir>/scripts/slim_glb.py rig assets/models/hero/hero-rig-rigged_character_glb.glb preview/rig.glb --max-px 1024
cp <this-skill-dir>/viewer/clip-viewer.html preview/
cd preview && python3 -m http.server 8322
# http://localhost:8322/clip-viewer.html?rig=rig.glb&clips=idle.glb,walk.glb,run.glb
```

The viewer lists the clips, plays them on the rig, and reports per-clip measurements: track counts before and after the import fixes, unresolved bone targets, hips travel, foot travel, and head height. The import fixes are toggles, so turning one off shows the raw failure it prevents. For automation it exposes `window.__ready`, `window.__report`, and `window.__pose(clipIndex, seconds)`; add `&headless=1` to start paused.

Check that `unresolved` is 0 on every clip, that head height is consistent across clips, that foot travel is large while hips travel is small once root motion is stripped, and that the character reads correctly in motion.

## Quality

Improve the user's prompt with material, silhouette, camera readability, scale, and game-use constraints. Match `target_polycount`, `model_type`, and `texture_resolution` to the browser budget at generation time; remeshing afterwards costs another task. Use `--topology quad` for anything deformed or edited later and `triangle` for static props. Keep `remove_lighting` on (the default) so scene lighting does the work. Use generated 3D as hero content and build the surrounding prop kit procedurally.

Inspect unpaused in-game motion after integration: clip transitions, deformation, root motion, foot sliding, and attack/contact timing. A successful download or skeleton check is not proof of good animation.

Report the key probe output, task IDs (preview, refine, rig, each clip), checkpoint and output paths, model type, topology, polycount and texture settings, credits consumed and remaining balance, viewer measurements for rigged characters, Three.js import notes, and anything that failed. Put detailed evidence in the project artifact for the lead's consolidated report.
