# Visual Verification Checklist

- Open the local dev or preview URL in a browser.
- Check browser console errors and page errors.
- Confirm the canvas has nonzero display size and drawing-buffer size.
- Capture a screenshot.
- Sample canvas pixels for nonblank output and color variance.
- Test at desktop, laptop, and mobile viewport sizes.
- Confirm camera aspect updates after resize.
- Confirm UI/HUD text does not overlap or clip.
- Interact for at least one core action and observe visible state change.
- If using snapshots, make dynamic effects deterministic or mask them.
- If the game is premium, release-ready, UI-heavy, or generated-asset-heavy, also use `threejs-qa-release/references/visual-test-harness.md` and `threejs-qa-release/references/checklists/visual-test-harness.md`, or record why a baseline harness is not warranted.
- If HUD/menu layout changed, also use `threejs-game-ui-designer/references/checklists/game-ui-quality.md`, `threejs-game-ui-designer/references/checklists/hud-readability.md`, and `threejs-game-ui-designer/references/checklists/responsive-ui-fit.md`.
- If procedural models/materials changed, also use `threejs-aaa-graphics-builder/references/checklists/procedural-model-quality.md`, `threejs-aaa-graphics-builder/references/checklists/material-lighting-quality.md`, and `threejs-aaa-graphics-builder/references/checklists/performance-safe-visual-detail.md`.
- If the target is premium, AAA, complete, release-ready, or showcase quality, also use `threejs-aaa-graphics-builder/references/checklists/aaa-game-quality-gate.md`.
- If screenshots still look basic, also use `threejs-aaa-graphics-builder/references/checklists/aaa-visual-scorecard.md`.
- If the game is an endless runner, also use `threejs-gameplay-systems/references/checklists/endless-runner-premium-quality.md`.
