# Meshy API Notes

Base URL `https://api.meshy.ai`, auth header `Authorization: Bearer $MESHY_API_KEY`.
Every create call returns `{"result": "<task-id>"}`; every retrieve call returns the task
object. Status values: `PENDING`, `IN_PROGRESS`, `SUCCEEDED`, `FAILED`, `CANCELED`.

## Endpoints (script `--kind` names on the left)

| kind | path | notes |
| --- | --- | --- |
| text | `/openapi/v2/text-to-3d` | two-stage: `mode: preview` then `mode: refine` |
| image | `/openapi/v1/image-to-3d` | single reference image |
| multi-image | `/openapi/v1/multi-image-to-3d` | 1-4 views of the same subject |
| retexture | `/openapi/v1/retexture` | restyle textures of an existing model |
| remesh | `/openapi/v1/remesh` | retopology / decimation / format conversion |
| rig | `/openapi/v1/rigging` | humanoid auto-rig only |
| animate | `/openapi/v1/animations` | one clip per task |
| motion | `/openapi/v1/text-to-motion` | custom clip from a text prompt |
| balance | `/openapi/v1/balance` | remaining credits |

`GET /<path>/:id/stream` exists (SSE) for every task type; the script polls instead
because polling is enough at these durations and needs no extra dependency.

## Text to 3D is two tasks, not one

`mode: preview` produces untextured geometry; `mode: refine` takes `preview_task_id` and
produces the textured model. `script text` chains both automatically when `--wait` is set
(`--no-refine` stops after geometry, which is the right call for props you will texture in
the engine or retexture later). Without `--wait` the refine cannot be chained: submit it
afterwards with `refine --preview-task-id ...`.

## Parameters that matter for browser games

- `model_type`: `standard` | `smart-topology` | `lowpoly`. `smart-topology` caps
  `target_polycount` at 15,000; `standard` remesh allows 100-300,000.
- `topology`: `quad` for anything that will be deformed or edited, `triangle` for props.
- `target_polycount` + `decimation_mode` (1-4) are the browser budget levers. Prefer
  generating at a sane count over decimating later.
- `pose_mode`: `a-pose` | `t-pose` | `empty`. Set `t-pose` for anything that will be rigged;
  this is a first-class parameter here, unlike prompt-only pose control elsewhere.
- `art_style`: `realistic` | `sculpture` (text only).
- `enable_pbr` gives metallic/roughness/normal maps; `texture_resolution` `2k` (default) is
  usually right for browser, `4k` only for hero assets.
- `remove_lighting` defaults true (meshy-6): bakes out the studio light. Keep it on for
  assets that will be lit by the scene; `--keep-lighting` only for flat/unlit looks.
- `target_formats`: `glb`, `obj`, `fbx`, `stl`, `usdz`, `3mf`. Ask for `glb` for Three.js;
  add `fbx` only if a DCC round-trip is planned.
- `should_remesh: false` (`--no-remesh`) keeps the raw generated mesh - denser but truer to
  the silhouette.
- `ai_model`: `meshy-5` | `meshy-6` | `meshy-7` | `latest`. `ultra_mode` is meshy-7 only.

## Images

`image_url` / `image_urls` / `texture_image_url` / `image_style_url` / `model_url` accept a
public URL **or a base64 data URI**. There is no upload endpoint. The script converts local
paths to data URIs automatically and warns above ~9 MB - downscale large concepts first.

## Rigging (humanoid only)

- Input: `input_task_id` (a prior Meshy task) or `model_url` (GLB).
- Hard limits: <= 300,000 faces, textured mesh, clear humanoid structure, character facing
  `+Z`. Non-humanoid meshes (quadrupeds, dragons, vehicles) FAIL - there is no creature rig.
  For creatures, either hand-rig, or use the Tripo skill (`threejs-3d-generator`), whose
  v2.5 rigger handles quadruped/avian/serpentine/aquatic body plans.
- `height_meters` (default 1.7) sets the output scale, so the GLB arrives in metres and
  needs no scaling in Three.js.
- Result fields: `rigged_character_glb_url`, `rigged_character_fbx_url`, plus free
  `walking_*` / `running_*` clips on some plans.
- The skeleton is Mixamo-like (`mixamorig:Hips`, `mixamorig:LeftArm`, ...), so Mixamo clips
  and Meshy clips retarget onto each other with no bone renaming.

## Animation

- `POST /openapi/v1/animations` with `rig_task_id` and EITHER `action_id` (library preset)
  OR `motion_task_id` (a `text-to-motion` result). One clip per task - batch by submitting
  several tasks; the script does this from a comma list.
- 678 library actions are bundled in `references/animations.csv` (id, name, category,
  subcategory). Search them with `list-animations --search sword`. Categories: WalkAndRun,
  BodyMovements, DailyActions, Fighting, Dancing.
- `post_process` `{operation_type: "change_fps", fps: 24|25|30|60}` also supports
  `fbx2usdz` and `extract_armature`.
- Result: `animation_glb_url`, `animation_fbx_url` (+ processed variants). Clips arrive as
  one animation per file, so name them at import; there is no in-place flag - strip
  horizontal root motion in the engine if the gameplay code drives locomotion.

## Text to Motion

`prompt` (<= 400 chars), `duration` 2-10s in 0.5 steps, `mode` `prime` (10 credits, FBX) or
`swift` (3 credits, BVH). Feed the returned task id to `animate --motion-task-id` within the
3-day asset retention window.

## Limits and retention

- 20 requests/second; concurrent generation tasks depend on plan (Pro 10, Premium 30,
  Ultra 100, Studio 20). `429` is either `RateLimitExceeded` or `NoMoreConcurrentTasks`.
- Generated assets and their URLs are retained ~3 days. Download immediately after success;
  `--download` does this in the same run.
- `GET /openapi/v1/balance` before a long pipeline; a full character run (preview + refine +
  rig + N clips) is the expensive path.

## Meshy vs Tripo (which skill to use)

- Meshy wins on: humanoid animation (678 mocap clips + text-to-motion vs 16 presets),
  explicit `pose_mode`, retexture with multi-view references, one-call remesh/convert.
- Tripo wins on: non-humanoid rigs (quadruped/avian/serpentine/aquatic), stylization
  (lego/voxel/minecraft/voronoi), part generation.
- Both: text-to-3D, image-to-3D, quad topology, face limits, PBR.

## Measured behaviour (verified live, Sept 2026)

- Text-to-3D **preview alone cost 20 credits** and took ~50s (`model_type lowpoly`,
  `target_polycount 3000`). Budget the refine pass on top of that; check `balance` first.
- `target_polycount` is approximate at the preview stage: the 3,000-request came back as
  7,691 triangles, untextured (0 materials). For a hard budget, run `remesh` afterwards.
- The API bakes **every** model format even when `target_formats` is not set: one preview
  returned glb + fbx + obj + stl + usdz. The script therefore saves only `glb` by default;
  `--download-formats glb,fbx` or `--all-formats` widens it.
- Rigging validates at SUBMIT time, not during the task: a non-humanoid model is rejected
  with `HTTP 422 {"message":"Pose estimation failed, please provide a valid model"}` and
  **costs no credits**. That makes "try the rig" a free humanoid check.
- Retrieve responses for rig/animate tasks carry their assets in a nested `result` object
  while the task fields (`status`, `progress`) stay at the top level; the script only
  unwraps an envelope that has no `status` of its own.

## should_remesh is the trap (verified live)

`target_polycount` and `topology` are silently IGNORED unless `should_remesh` is true, and
its default depends on the model version. A text-to-3D run asking for `target_polycount:
20000` came back with **1,936,276 faces** and a **74 MB** GLB - unusable in a browser and
rejected by the rigger. The script now sets `should_remesh: true` whenever a polycount or
topology is requested (`--no-remesh` still forces it off), but if you build payloads by
hand, send the flag explicitly.

Rigging enforces its own gate at submit time:

```
HTTP 400 {"message":"The input model has 1,936,276 faces which exceeds the 320,000 face
limit for rigging. Please use the Remesh API (POST /openapi/v2/remesh) with a
target_polycount of 300000 or less before rigging."}
```

Two things about that message: the ceiling is **320,000** faces (the docs say 300,000), and
the `/openapi/v2/remesh` path it recommends **does not exist** - `GET /openapi/v2/remesh`
returns 404 while `/openapi/v1/remesh` returns 200. Use v1.

`character-pipeline` recovers from this automatically: it catches the face-limit rejection,
runs a remesh to `--target-polycount` (default 30,000), and rigs the remeshed task instead.

## Recovery, checkpoints, and error categories

`--checkpoint PATH` on a submitting command records an operational journal: the command
arguments, each stage's accepted task ID, its last known status, and the fingerprints of
downloaded files. It never records API keys, image data URIs, or signed asset URLs. One
checkpoint per job, and an existing path must be resumed rather than overwritten; a second
writer is rejected through an OS lock.

Stage names are stable, so a resume maps back to the same work: `preview`/`refine` for
`text`, `model` for `image`/`multi-image`, `task` for `refine`/`retexture`/`remesh`/`rig`/
`motion`, `animation-N` in request order for `animate`, and `preview`, `refine`, `remesh`,
`rig`, `rig-remeshed`, `animation-N` for `character-pipeline`.

`resume CHECKPOINT` waits for accepted tasks and downloads their outputs; it never
resubmits an accepted stage. Download links are read from a fresh task status first, which
is what makes a resume work after the three-day asset expiry. Files whose size and SHA-256
still match are not downloaded again, so a resume after a corrupted or deleted file repairs
only that file. `--stop-after model|rig|animations` applies to `character-pipeline`; single
jobs never grow extra paid stages on resume.

Errors are classified so a blocker is not confused with a retryable failure:

| category | meaning |
| --- | --- |
| `missing_credentials` | no `--api-key` and no `MESHY_API_KEY` in the process environment |
| `credentials` | HTTP 401/403; the key or its permissions are wrong |
| `exhausted_credits` | HTTP 402, or a credit message in the response body |
| `invalid_input` | HTTP 4xx the request itself caused (bad pose, face limit, unknown id) |
| `transient` | HTTP 408/425/429/5xx on a read; retried with bounded backoff and `Retry-After` |
| `unknown_submission` | a POST whose outcome is unknown; never retried automatically |
| `expired_download` | a signed asset URL that is no longer valid; refresh it from task status |
| `task_failed` | the task itself ended `FAILED`/`CANCELED`, or a validator rejected its output |
| `checkpoint_error` | the checkpoint is missing, malformed, locked, or already exists |

Only idempotent reads are retried. A POST is never retried automatically: if its outcome is
uncertain the stage is parked, and the fix is to find the real task ID in the Meshy
dashboard and run `resume CHECKPOINT --task-id ID`, which verifies the task against the
saved submission intent before adopting it. Rerunning the original command in that state is
refused rather than risking a duplicate charge.
