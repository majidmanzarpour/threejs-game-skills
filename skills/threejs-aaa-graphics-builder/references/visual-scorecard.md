# Visual Scorecard

Score active-play screenshots, not idle title screens or isolated showroom models. Use desktop and mobile screenshots when mobile is in scope.

Scores are self-assessed against the anchors below, so they drift optimistic. Two countermeasures are mandatory for premium/AAA/showcase claims: cite Measured Evidence for the categories it supports, and run the Fresh-Eyes Review before finalizing.

## Calibration Anchors

Reference screenshots for score calibration are packaged in `threejs-aaa-graphics-builder/assets/scorecard-anchors/`:

- `scene-1.jpg` — score ~1: primitive player and pickups on a flat sparse arena, utility HUD.
- `scene-2.jpg` — score ~2: authored track kit, imported hero asset, designed genre HUD, intentional lighting.
- `scene-3.jpg` — score ~2.5-3: dense layered world in active play, readable hero silhouette, event VFX, cohesive HUD.

Before scoring World/environment, Hero/player, Materials/textures, or Lighting/render, view the anchors and compare: if your screenshot reads closer to `scene-1.jpg` than `scene-3.jpg` for that surface, the category is at most a 1-2 regardless of how much code was written.

## Scoring Scale

- 0: Placeholder. Default primitives, sparse world, unreadable state, debug UI, or no evidence.
- 1: Basic styled. Playable and themed, but still obvious prototype assets, flat composition, repeated silhouettes, or generic UI.
- 2: Premium stylized. Authored silhouettes, material/detail systems, readable state, cohesive UI/world, measured performance.
- 3: Showcase. Strong art direction, memorable hero and world, dense authored detail, excellent readability, polished VFX/rendering, and diagnostics.

## Categories

1. Art direction.
   - 0: No clear theme.
   - 1: Theme is mostly colors/fog.
   - 2: Theme affects forms, materials, UI, world, and feedback.
   - 3: Distinct identity visible in every surface.
2. Hero/player.
   - 0: Default primitive stack.
   - 1: Basic object with glow or simple attachments.
   - 2: Authored silhouette, decals/trim, state cues, collision proxy.
   - 3: Memorable model with layered construction and expressive feedback.
3. Obstacles/enemies.
   - 0: Cubes/cones/spheres.
   - 1: Recolored repeated silhouette.
   - 2: Three readable variants with telegraphs and material cues.
   - 3: Varied family with animation, anticipation, and gameplay clarity.
4. Rewards/interactables.
   - 0: Plain sphere/ring/token.
   - 1: Repeated object with simple glow.
   - 2: Two authored forms with idle/collect states and UI feedback.
   - 3: Desirable, animated, and clearly valued during motion.
5. World/environment.
   - 0: Flat plane, empty arena, box skyline.
   - 1: Themed but sparse repeated blocks.
   - 2: Layered prop kit with foreground/midground/background and scale cues.
   - 3: Dense authored world that supports gameplay readability.
6. Materials/textures.
   - 0: Flat colors.
   - 1: Basic roughness/metalness or emissive color.
   - 2: Shared material roles, procedural decals, trim, panel lines, wear/noise.
   - 3: Rich cohesive material language with measured texture/resource use.
7. Lighting/render.
   - 0: Default lights or unreadable darkness.
   - 1: Fog/bloom used as main style.
   - 2: Intentional tone mapping, exposure, key/fill/rim, contact, depth.
   - 3: Cinematic but readable composition with disciplined post-processing.
8. VFX/motion.
   - 0: None or random particles.
   - 1: Generic particles/trails.
   - 2: Event-driven VFX for boost, pickup, hit, fail, combo, shield, or spawn.
   - 3: High-impact effects that clarify gameplay and remain performant.
9. UI/HUD.
   - 0: Debug text or missing UI.
   - 1: Generic stat-card dashboard.
   - 2: Genre-specific HUD states, meters/icons, responsive text fit.
   - 3: Cohesive game interface with strong hierarchy and polished transitions.
10. Performance evidence.
   - 0: No metrics after visual changes.
   - 1: Informal "seems fine".
   - 2: Renderer counts, build/browser QA, desktop/mobile screenshots, and technical-art budget notes.
   - 3: Baseline/post metrics, bottleneck notes, budgets, optimized asset strategy, and VFX/readability tradeoffs.

## Thresholds

Premium:

- Every category at least 2.
- Average at least 2.3.
- Desktop and mobile active-play screenshots captured when mobile is in scope.
- Renderer diagnostics reported after graphics changes.

Showcase:

- At least six categories score 3.
- No category below 2.
- Average at least 2.7.
- Performance evidence includes before/after or budget-aware notes.

## Automatic Failures

Any of these prevents a premium/AAA/showcase claim:

- Active screenshot is primitive-dominant.
- Main world is mostly stretched boxes, flat planes, or a sparse arena.
- Hero asset is mostly default primitives plus glow.
- Obstacles or rewards are one repeated silhouette.
- HUD is mostly rectangular stat/debug cards.
- Fog, darkness, bloom, or particles hide missing authored geometry.
- UI overlaps the play path, clips text, or fails mobile safe areas.
- The game is not playable through real input.
- No active-play screenshot was captured.
- No renderer diagnostics were collected after major graphics work.
- No technical-art budget or imported/generated asset diagnostics were reported for premium graphics work.

## Measured Evidence

Run the canvas inspector (`npm run inspect:canvas`, or `threejs-qa-release/scripts/inspect-threejs-canvas.mjs`) on desktop and mobile and cite its `metrics` and `renderBudget` blocks in the scorecard. The numbers are advisory signals, not gates, but they must be reported and low values must be explained rather than ignored:

- `colorEntropyBits` below ~3.0 or `dominantColorShare` above ~0.6 suggests a sparse, flat scene — supporting evidence against World/environment or Materials/textures scores above 2.
- `edgeDensity` below ~0.04 suggests primitive-dominant or empty framing — supporting evidence against World/environment and Hero/player scores above 2.
- `luminance.contrast` below ~60 suggests fog/darkness compression — supporting evidence against Lighting/render scores above 2.
- `renderBudget` rows over the tier budget require a documented tradeoff in the technical-art budget (see `references/technical-art.md`).
- Renderer diagnostics (calls, triangles, geometries, textures) back the Performance evidence category.

## Fresh-Eyes Review

The builder must not be the only grader. For premium/AAA/showcase claims:

- If the runner supports subagents (Task tool or equivalent), spawn a reviewer with ONLY: the screenshots, this scorecard file, and the inspector metrics JSON. No build context, no prior scores. The reviewer must receive the COMPLETE capture set — every captured state, desktop and mobile — never a hand-picked subset; a curated selection can hide weak states or miss content the builder knows exists (capture states with the inspector's `--state` flag so nothing is gated behind live play). The reviewer fills the scorecard independently; reconcile by taking the lower score per category unless concrete evidence overturns it. Report both score sets.
- If subagents are unavailable, run an adversarial self-review before finalizing: for each category, write one sentence making the strongest case that the score is a 1, citing what is visible in the screenshot; only then assign the score. Include these sentences in the report.

## Report Format

```text
Visual scorecard:
- Art direction: before X / after Y - evidence:
- Hero/player: before X / after Y - evidence:
- Obstacles/enemies: before X / after Y - evidence:
- Rewards/interactables: before X / after Y - evidence:
- World/environment: before X / after Y - evidence:
- Materials/textures: before X / after Y - evidence:
- Lighting/render: before X / after Y - evidence:
- VFX/motion: before X / after Y - evidence:
- UI/HUD: before X / after Y - evidence:
- Performance evidence: before X / after Y - evidence:
Measured evidence: colorEntropyBits / edgeDensity / luminance.contrast /
  dominantColorShare per viewport, renderer diagnostics, render budget rows
Fresh-eyes review: subagent scores or adversarial self-review notes
Average:
Automatic failures remaining:
```

If any category remains below threshold, state the exact next pass instead of declaring completion.
