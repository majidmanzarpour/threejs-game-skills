# Visual Scorecard

Score active-play screenshots, not idle title screens or isolated showroom models. Use desktop and mobile screenshots when mobile is in scope.

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
Average:
Automatic failures remaining:
```

If any category remains below threshold, state the exact next pass instead of declaring completion.
