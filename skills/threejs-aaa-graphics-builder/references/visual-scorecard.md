# Visual Scorecard

Score active-play screenshots — not title screens, not isolated showroom models. Desktop and mobile when mobile is in scope.

## Calibration anchors

Packaged in `threejs-aaa-graphics-builder/assets/scorecard-anchors/`. View them before scoring World, Hero, Materials, or Lighting:

- `scene-1.jpg` — **1**: primitive player and pickups, flat sparse arena, utility HUD.
- `scene-2.jpg` — **2**: authored track kit, imported hero asset, designed genre HUD, intentional lighting.
- `scene-3.jpg` — **2.5–3**: dense layered world in active play, readable hero silhouette, event VFX, cohesive HUD.

If a surface reads closer to `scene-1` than `scene-3`, it is a 1–2 no matter how much code went into it.

## Categories

Scale: **0** placeholder / no evidence · **1** basic styled · **2** premium stylized · **3** showcase.

| Category | 1 | 2 | 3 |
| --- | --- | --- | --- |
| Art direction | theme is mostly colors and fog | theme drives forms, materials, UI, world, feedback | distinct identity in every surface |
| Hero/player | basic object with glow or simple attachments | authored silhouette, decals/trim, state cues, collision proxy | memorable layered model with expressive feedback |
| Obstacles/enemies | gameplay roles are hard to distinguish | readable role-specific forms, telegraphs, and material cues | expressive challenge geometry or varied family with anticipation |
| Rewards/interactables | important interactions have generic or absent feedback | authored forms, readable interaction states, UI feedback | purpose and value stay clear during motion |
| World/environment | themed but sparse repeated blocks | layered prop kit, foreground/midground/background, scale cues | dense authored world that aids readability |
| Materials/textures | basic roughness/metalness or emissive color | shared material roles, procedural decals, trim, panel lines, wear | rich cohesive material language, measured resource use |
| Lighting/render | fog and bloom used as the style | intentional tone mapping, exposure, key/fill/rim, contact, depth | cinematic but readable, disciplined post |
| VFX/motion | generic particles and trails | event-driven VFX: boost, pickup, hit, fail, combo, shield, spawn | high-impact effects that clarify gameplay and stay cheap |
| UI/HUD | generic stat-card dashboard | genre-specific states, meters/icons, responsive text fit | cohesive interface, strong hierarchy, polished transitions |
| Performance evidence | informal "seems fine" | renderer counts, build/browser QA, target-viewport shots, budget notes | baseline/post metrics, bottleneck notes, asset strategy, tradeoffs |

Keep all ten categories, but name their genre equivalents before scoring. In pool, Hero can mean the table/cue/ball presentation, Obstacles the rails/pockets and shot constraints, and Interactables the balls/aim/contact feedback. In a puzzle game these may be the board, constraints, and manipulable pieces. Do not invent enemies, loot, neon trim, or extra props to increase a score. Repeated identical forms can be correct for the rules; score their authorship and readability, not an arbitrary variant count. Deliberately minimal art can score well when its composition, material decisions, and feedback are demonstrably finished.

## Thresholds

- **Premium**: every category ≥ 2, average ≥ 2.3, renderer diagnostics reported after graphics changes.
- **Showcase**: no category below 2, at least six at 3, average ≥ 2.7, before/after performance evidence.

## Automatic failures

Any one of these means the work is not premium yet, whatever the individual scores say:

- Active screenshot is dominated by unrefined placeholders or empty space that the design does not justify, rather than authored composition and readable gameplay.
- Hero asset is an unrefined primitive placeholder plus glow. Different gameplay roles are indistinguishable without a deliberate design reason.
- HUD is mostly rectangular stat/debug cards.
- Fog, darkness, bloom, or particles are standing in for missing authored geometry.
- UI overlaps the play path, clips text, or breaks safe areas on a target viewport.
- The game is not playable through real input, or no active-play screenshot exists.
- No renderer diagnostics after major graphics work.

## Measured evidence

Run the canvas inspector (`npm run inspect:canvas`, or `threejs-qa-release/scripts/inspect-threejs-canvas.mjs`) on the target viewports and cite its `metrics` and `renderBudget` blocks. These are advisory signals; a low value needs an explanation, not a higher score. Do not add noise, clutter, or particles just to raise pixel metrics; an intentional clean composition may legitimately measure low.

- `colorEntropyBits` below ~3.0, or `dominantColorShare` above ~0.6 — sparse flat scene. Evidence against World or Materials above 2.
- `edgeDensity` below ~0.04 — primitive-dominant or empty framing. Evidence against World and Hero above 2.
- `luminance.contrast` below ~60 — fog/darkness compression. Evidence against Lighting above 2.
- `renderBudget` rows over the tier budget need a documented tradeoff (see `technical-art.md`).

Score the **complete declared** capture set for the change, including desktop and mobile when both are targets. Use acknowledged `--state` captures for relevant mid-run states (late waves, fail, stress); a requested label without a working state hook is not evidence. Animated work also needs unpaused motion evidence of transitions and contact timing. A still image cannot establish animation quality.

## Reporting

Give each category a before/after number with one line of evidence, then the average and any automatic failures still standing. For a new game with no baseline, use `not captured` for before; never invent a score. If a category is below threshold, name the next pass that fixes it. A narrow fix does not require re-scoring unchanged categories or re-establishing the entire game's premium status.
