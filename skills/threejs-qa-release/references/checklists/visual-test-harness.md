# Visual Test Harness Checklist

Use when visual regression testing is added, extended, or intentionally skipped for a meaningful Three.js game change.

- Harness decision is explicit: added / extended / skipped.
- Decision is justified by milestone risk: premium/release/UI/generated assets/visual style vs prototype/non-deterministic smoke only.
- Active-play desktop state is covered or a reason is reported.
- Active-play mobile state is covered when mobile is in scope or a reason is reported.
- Important menu/HUD/fail/retry/generated-asset states are covered when those surfaces changed.
- Randomness, camera shake, particles, time, debug UI, and dynamic overlays are seeded, paused, hidden, or intentionally excluded.
- Fonts, textures, GLTFs, and first rendered frames are awaited before screenshots.
- `toHaveScreenshot()` thresholds are narrow enough to catch real regressions.
- Masks are used only for dynamic areas that are not acceptance criteria.
- Canvas pixel/nonblank smoke checks still run; screenshot baselines do not replace interaction checks.
- Baseline update command and comparison command are reported.
- Artifacts/snapshot paths are reported.
- Flake risks and unsupported states are listed.
