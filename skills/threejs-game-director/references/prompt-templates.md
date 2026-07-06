# Three.js Game Director Prompt Templates

Reusable prompt templates packaged with this skill. Use only templates relevant to the current request, and adapt placeholders to the game/project context.

---

# New Three.js Game Prompt

Use `threejs-game-director` for a complete or premium Three.js browser game. It should automatically route through gameplay systems, AAA graphics, UI, debug/profile, and QA/release phases.

Use `threejs-gameplay-systems` directly only when the requested output is explicitly a small first prototype or gameplay-system change.

Game idea:
- Core verb:
- Objective:
- Camera:
- Visual tone:
- Target devices:
- Time budget:

Requirements:
- Use TypeScript, Vite, and Three.js modules.
- Start with a compact game design brief, core loop contract, and level/encounter plan before implementation.
- Build a playable loop, not a static scene.
- Keep the first version small enough to verify quickly, then continue quality passes if the target is complete/premium.
- Include desktop keyboard input and mobile touch input when target devices include mobile.
- Add HUD feedback for objective, score, health, time, or state.
- For premium requests, replace prototype HUD/models/world detail with designed UI, procedural asset kits, technical art budget, and renderer diagnostics.
- During QA, decide whether a visual test harness is warranted; add/extend it for release-ready visual states or report the skip reason.
- Run build and visual verification before reporting done.

Final response:
- list files created or changed
- describe playable controls
- report build, browser, console, screenshot, canvas-pixel, and viewport evidence
- report game design brief, level/encounter plan, technical-art budget, and visual-harness decision when in scope
- list remaining risks

---

# AAA Three.js Game Pass Prompt

Use `threejs-game-director` to upgrade this Three.js browser game from prototype-quality to premium showcase quality.

Target:
- Genre:
- Core verb:
- Desired mood:
- Target devices:
- Performance budget:

Automatic skill flow:
- Use `threejs-gameplay-systems` first for game design brief, core loop contract, level/encounter plan, controls, camera, impact, difficulty, and restart loop.
- Use the director's active-play screenshot scorecard first if screenshots exist or can be captured.
- Use `threejs-aaa-graphics-builder` when screenshots still look basic or when multiple graphics surfaces are weak.
- Use `threejs-game-ui-designer` for HUD, menus, overlays, icons, text fit, and touch UI.
- Use `threejs-debug-profiler` before and after expensive visual changes.
- Use `threejs-qa-release` before calling the pass complete, including a visual test harness decision when release-ready visual regression risk exists.

Quality priorities:
- Prefer a smaller authored vertical slice over a larger placeholder game.
- Replace utility HUD boxes with designed, genre-specific interface states.
- Replace placeholder primitives with authored silhouettes and reusable procedural kits.
- Build a minimum premium asset set: hero/player, three obstacle/enemy variants, two reward/interactable variants, world prop kit, and material kit.
- Add a technical art brief: material kit, VFX language, instancing/LOD/culling strategy, imported asset cleanup, DPR/shadow/post tradeoffs, and render budget.
- Add depth layers, parallax, foreground/midground/background composition, and material contrast.
- Make rewards, threats, player state, and objectives readable during motion.
- Add feedback for speed, pickup, near miss, hit, fail, restart, streak, and milestone.
- Keep render cost visible through renderer diagnostics.

Prototype rejection tests:
- Main world is mostly stretched boxes or flat planes.
- Player/hero asset is mostly default primitives with glow.
- Obstacles/pickups are one repeated silhouette.
- HUD is mostly rectangular stat cards.
- Fog/darkness/bloom hides missing geometry.

Verification:
- Build and run locally.
- Capture desktop and mobile screenshots after interaction.
- Check console/page errors and nonblank canvas pixels.
- Check UI text fit, overlap, safe areas, and touch targets.
- Report draw calls, triangles, geometries, textures, and frame-time/FPS evidence when available.
- Report technical art budget/readability evidence and visual test harness added/extended/skipped.
- Compare against `threejs-aaa-graphics-builder/references/checklists/aaa-game-quality-gate.md`.
- Compare against `threejs-aaa-graphics-builder/references/checklists/aaa-visual-scorecard.md`.
- Do not report the task as premium-complete if any prototype rejection test still fails.

---

# Premium Endless Runner Pass Prompt

Use `threejs-game-director` to upgrade this endless runner into a premium, high-fidelity browser game.

Current blockers:
- 

Runner-specific targets:
- Player avatar/vehicle silhouette:
- Obstacle families:
- Reward/readability language:
- World theme:
- Speed/impact feel:
- HUD states:

Required upgrades:
- Replace simple stat-card HUDs with a genre-specific runner HUD: compact status, readable progress, combo/streak, overdrive/boost, fail/retry, pause/settings.
- Replace cube obstacles and basic pickups with distinct procedural model families that read instantly at speed.
- Build at least three obstacle families, two reward variants, one detailed player vehicle/avatar, and one reusable track/city prop kit.
- Add route/lane detail, near-field props, mid-field silhouettes, far parallax, and speed lines that do not hide hazards.
- Improve player avatar/vehicle detail: layered chassis/body, trim, emissive signals, animation, trail/wake, and readable collision footprint.
- Add hazard telegraphing, pickup magnet/collect feedback, near-miss feedback, speed ramp cues, milestone gates, and crash/retry polish.
- Tune camera FOV, follow lag, shake, roll, and effects for speed without disorientation.

Avoid:
- Giant untextured skyline boxes as the main world detail.
- Glow as the only fidelity technique.
- HUD panels that look like debug readouts.
- Repeating the same obstacle silhouette too frequently.
- Effects that obscure the next lane decision.

Verification:
- Use `threejs-gameplay-systems/references/checklists/endless-runner-premium-quality.md`.
- Capture desktop and mobile screenshots during action, not only idle.
- Report renderer diagnostics for worst-case visible segment.
- Play long enough to see speed ramp, pickups, hazards, fail/retry, and any boost state.
- If the screenshot still reads as road plus boxes plus basic pickups, continue modeling/world/UI passes instead of reporting done.
