# Asset Jobs and Recovery

Use this policy before treating a provider error as permission to downgrade art. User constraints come first: explicitly procedural art, no external services, or a fixed budget do not require a paid generation attempt. Choose asset roles from the design, not a universal asset quota.

## Start Early, Inspect Between Stages

1. For agent-executed keyed providers, probe credentials without printing their values. A missing process variable is not proof that the user's configured key is missing; use the packaged credential probe. Codex's built-in imagegen path needs no project key and should not be blocked by a missing Gemini key. Tripo is user-executed and does not use the agent credential probe. Do not change shell profiles or expose keys in commands, checkpoints, browser code, or reports.
2. Submit only the high-value image or audio assets the current design needs. For Tripo, prepare the exact prompt, settings, destination, acceptance checks, and user-run CLI command or Studio checklist instead of submitting. Record provider, task ID or pending handoff, local checkpoint, purpose, and intended runtime path in `artifacts/game-progress.md` immediately. Keep independent gameplay and UI work moving while jobs run.
3. Inspect the concept before handing off image-to-3D. For animated Tripo models, structure the user handoff in stages: generate and download the model first, inspect its preview/model locally, then give the user the rig/animation follow-up. Inspection is work for the agent; the provider execution remains with the user.
4. Test silhouette, scale, materials, and motion in a representative playable scene before producing a large asset family. Preserve useful accepted work when requirements change; mark obsolete jobs and do not automatically regenerate them.

The probe runs in a child shell; `KEY=SET` does not export the key into later tool calls. If the provider helper still reports missing credentials, launch it in the same profile-loaded shell instead of downgrading the asset or copying the key into an argument. For example, on zsh:

```bash
zsh -lc '
  source "$HOME/.zprofile" >/dev/null 2>&1 || true
  source "$HOME/.zshrc" >/dev/null 2>&1 || true
  exec "$@"
' asset-job python3 <threejs-3d-generator-skill-dir>/scripts/threejs_3d_asset.py resume artifacts/hero-job.json
```

Use the corresponding bash profiles for bash; on Windows ensure the agent process inherits the configured user environment. Preserve the working directory and arguments, and never enable shell tracing around secrets.

## Classify Before Recovering

| Evidence | Action |
| --- | --- |
| Agent-executed credentials genuinely missing after probe | Continue independent work. Use an available native tool, existing licensed assets, or a deliberate procedural alternative; disclose the affected asset limitation. Never invent credentials. |
| Tripo asset needed | Prepare a user-executed CLI or Studio handoff. Continue independent work and integrate the downloaded artifact when the user supplies it; do not submit, retry, or top up from the agent workflow. |
| Authentication/permission rejected | Check the documented key variable and provider permissions without showing secrets. Do not label this a credit problem. |
| Credits exhausted or plan restricts this operation | Preserve task/output IDs, stop paid retries, and identify only the dependent work as blocked. Do not purchase credits or wait indefinitely. |
| Invalid input, unsupported version, preset, or pose | Correct the specific request using the generator's references. Keep working version and rigging workarounds; do not replace them with guessed latest versions. A rejected request is not proof the provider is unavailable. |
| Transient timeout, rate limit, or service failure during status/download | Retry these safe operations with bounded backoff and respect `Retry-After`. Refresh expired download links from task status. Exhausting safe retries leaves the job pending, not permission to submit a duplicate. |
| Submission outcome uncertain (connection lost or ambiguous server response) | Reconcile the accepted task ID/checkpoint or provider task history before any new paid request. If no ID can be recovered, disclose uncertainty and obtain authorization before a potentially duplicate charge. |
| Task succeeded but output is malformed or visually unsuitable | Preserve the output and diagnose the failed stage. A missing rig GLB or failed skeleton validation is a failure, not a successful rig. Retry only that stage within the chosen attempt/budget limit. |

The Tripo helper implements checkpointed tasks and safe-operation retry behavior. Use `resume`, `status`, or `download` for an existing task, not a second `text`/`image` submission. Codex imagegen, Gemini, and ElevenLabs generation do not share Tripo's task/checkpoint API: retain existing files and reconcile uncertain requests through the actual provider instead of inventing a resume command.

## Progress and Fallback

Use the runner's available background execution or submit/status/download tools for agent-executed providers; do not busy-poll. For Tripo, record the pending user handoff instead. Bound the current wait and leave a recoverable pending job in the project note if a provider remains unavailable. Continue all work that does not depend on it. Ask only when the answer changes cost, constraints, or a material visual choice.

A single transient error is not a completed recovery attempt. After a confirmed blocker or bounded safe recovery, integrate the best alternative consistent with the user's design and state the remaining quality gap. Do not silently relabel placeholders as premium. A procedural-only brief is a valid art direction, not a provider failure.

Native async tools, user steering delivery, and reasoning settings belong to the hosting application. A skill can use exposed capabilities but cannot enable them by adding `async: true` or changing model settings itself.
