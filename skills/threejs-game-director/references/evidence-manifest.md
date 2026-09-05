# Current-Run Evidence

The manifest declares what one verification pass must capture. It checks coverage and file existence, not artistic quality, gameplay correctness, or whether an acknowledged state was implemented faithfully. Inspect the pictures, exercise real input, and check motion when animation matters.

## Declare the Capture Set

Choose states and viewports from the change before capturing. A full desktop/mobile game needs active play in both plus relevant failure, late-game, or stress states. A narrow desktop HUD fix can use only the affected desktop state. Do not drop a required entry because its capture failed. Use a fresh run ID and output directory when code or assets change; never relabel old reports as new evidence.

Write `artifacts/evidence.json` in the game project:

```json
{
  "version": 1,
  "runId": "pass-1",
  "captures": [
    {
      "mode": "desktop",
      "state": "active-play",
      "report": "artifacts/pass-1/desktop-active-play.json"
    },
    {
      "mode": "mobile",
      "state": "active-play",
      "report": "artifacts/pass-1/mobile-active-play.json"
    }
  ],
  "artifacts": ["assets/models/hero.glb", "artifacts/pass-1/locomotion.webm"]
}
```

`captures` must be nonempty, with distinct viewport/state pairs and report paths. `mode` is `desktop` or `mobile`. `state` is an exact hook state or explicitly `null` for an uncontrolled current-view capture; null does not prove active play or a boss encounter. `artifacts` is optional: declare only files this change actually requires. All relative paths resolve from the game project, not the manifest directory. Absolute paths and spaces are supported; project-relative paths are more portable.

## Capture and Check

From the project with its server running:

```bash
node <threejs-qa-release-skill-dir>/scripts/inspect-threejs-canvas.mjs \
  --url http://127.0.0.1:5188 --out artifacts/pass-1 \
  --state active-play --seed 42 --run-id pass-1
node <threejs-qa-release-skill-dir>/scripts/inspect-threejs-canvas.mjs \
  --url http://127.0.0.1:5188 --out artifacts/pass-1 --mobile \
  --state active-play --seed 42 --run-id pass-1
python3 <director-skill-dir>/scripts/check_evidence.py . --manifest artifacts/evidence.json
```

Explicit `--state` calls and awaits `setState(name)`. The hook must finish scene setup and return `{ state: name }`. Named captures also require `setPausedForScreenshot(paused)`, which immediately stops simulation/state transitions while rendering continues. The inspector freezes immediately after setup, then awaits visual stabilization and rendered frames within a bounded preparation timeout. Missing hooks, unknown states, timeouts, or mismatched acknowledgments fail. Explicit `--seed` likewise requires a working seed hook. Implement hooks for real project states instead of faking acknowledgments. The inspector records `state`, `requestedState`, `appliedState`, and `runId` alongside existing diagnostics, pixel metrics, and screenshot paths.

Run the standalone inspector from the game directory. It resolves Playwright and PNG dependencies from its own installation or that project's npm packages; if missing, install `@playwright/test` and `pngjs` in the game and the matching Playwright Chromium browser. No npm dependencies need to live inside globally installed skills.

The checker reads only declared reports and verifies run ID, viewport, state fields, successful nonblank inspection, absence of recorded browser errors, and nontrivial artifact files. Historical reports elsewhere are ignored. Motion clips belong in `artifacts`, but their animation quality still needs visual inspection. Builds, input tests, audio, collision, and performance require their own observations; this file checker cannot prove those ran.

## Reports and Legacy Use

Put detailed findings in `artifacts/final-evidence.md` and keep the user-facing close-out concise. Markdown artifact links may be absolute or project-relative; use angle brackets for paths with spaces or parentheses, such as `[motion](<artifacts/pass-1/hero motion.webm>)`.

`check_evidence.py <project> --report <report.md>` remains a basic path/build-presence check. Without `--manifest` it discovers inspector reports across the project, including historical ones, and cannot establish freshness or required capture coverage. Combine `--report` with `--manifest` for linked-file checks scoped to a declared capture set. `--skip-inspector` is legacy file-only use and cannot be combined with `--manifest`.
