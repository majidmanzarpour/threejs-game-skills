# Three.js QA/Release Prompt Templates

Reusable prompt templates packaged with this skill. Use only templates relevant to the current request, and adapt placeholders to the game/project context.

---

# Release Pass Prompt

Use `threejs-qa-release` to prepare this Three.js game for release.

Release target:
- static host, GitHub Pages, Netlify, Vercel, itch.io, or other:

Requirements:
- Run production build and preview.
- Verify asset paths under the intended base path.
- Check bundle size and large assets.
- Run desktop and mobile visual QA.
- Confirm no debug-only UI leaks unless intentionally enabled.
- Produce final report with commands, artifacts, screenshots, and residual risks.

---

# Visual Test Harness Prompt

Use `threejs-qa-release` to add or evaluate a visual test harness for this Three.js game.

Context:
- Game/milestone:
- Visual surfaces to protect:
- Dynamic/random systems:
- Target viewports:

Requirements:
- Load `references/visual-test-harness.md`.
- Decide whether to add, extend, or skip screenshot baselines.
- Cover active-play desktop and mobile when warranted.
- Add deterministic hooks or setup for seed, state, pause, reduced motion, camera shake, debug UI, and asset loading where practical.
- Keep canvas-pixel smoke and interaction checks.
- Report baseline update command, compare command, artifact paths, thresholds/masks, and flake risks.
