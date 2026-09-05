---
name: threejs-gameplay-systems
description: "Build and iterate playable Three.js game systems: starter scaffold, architecture, design briefs, core loops, level and encounter design, entities, input, camera, collision and physics, scoring, objectives, and game feel. Use for first playable slices, new Vite/TypeScript/Three.js setups, level/arena/track/wave/hole/puzzle design, combat encounters, difficulty tuning, and juice."
---

# Three.js Gameplay Systems

Create or evolve a playable browser game loop with clear ownership, responsive controls, deterministic update order, and a space that shapes player decisions.

Resolve `<this-skill-dir>` and local references from the actual loaded skill file; resolve sibling skills beside it before using runner-discovered alternatives.

## References

| File | Read it when |
| --- | --- |
| `references/game-feel.md` | tuning feel, juice, impact, hitstop, screenshake, or claiming polished gameplay |
| `references/genre-design.md` | designing levels, arenas, tracks, waves, holes, puzzles, encounters, or difficulty curves |
| `references/physics-engine-selection.md` | adding or changing physics, collision-heavy gameplay, vehicles, rolling balls, character controllers, sensors, moving platforms |

## Start here

```bash
python3 <this-skill-dir>/scripts/create_threejs_game.py ./my-game
```

Copies `assets/threejs-vite-game/`, rewrites the project name, and gives the game its own visual test and canvas inspector. `--force` overwrites an existing directory.

## Design first

For broad game creation or a substantial design change, write three short artifacts or update the existing ones. A narrow mechanic fix uses the existing design and preserves unrelated systems:

**Design brief.** Player promise (the fantasy in one sentence) · target feeling · primary verb · secondary verbs · what the player repeats every 5–30 seconds · what changes across 1–5 minutes · how they lose, learn, and restart · what is rewarded and what creates risk · what a better player does differently · how the next decision is communicated · non-goals for this slice.

**Core loop contract.** `Player does [verb] to achieve [objective] while [pressure] creates risk; success gives [reward], failure causes [cost/retry].` Then prove each clause in code: the verb is mapped to real input, the objective is visible in world or HUD, pressure exists inside the first playable minute, reward changes state rather than only visuals, failure teaches what happened, and restart is fast enough to invite another attempt.

**Level or encounter plan.** Spatial format · what the camera can and cannot see · player start, first decision, first threat, first reward · landmarks · how challenge escalates every 20–60 seconds or per wave/hole/lap · recovery beats · how hazards are telegraphed · which pieces are modular or parameterized.

"Explore a cool scene" is not a design brief. A brief needs decisions, pressure, feedback, and consequence.

## Build

1. Inspect existing structure, scripts, dependencies, loop, input, camera, entities, state, UI, diagnostics.
2. Keep small ownership boundaries: `core`, `game`, `entities`, `systems`, `assets`, `ui`, `tests`.
3. Implement in playable increments — input, state, entity, collision, feedback, HUD and audio hooks, diagnostics — so something is playable at every step.
   Establish one representative encounter at the intended camera scale with the actual hero and feedback before expanding content. Enemy, reward, and prop variety should serve the genre's decisions, not a universal asset quota.
4. Tune feel: movement, acceleration, camera follow and FOV, hitstop, impact feedback, cooldowns, difficulty, restart.
5. Keep hot paths allocation-light and update order explicit.
6. Route all gameplay randomness through the scaffold's seeded RNG so the deterministic test hooks keep working.

For coordinated work, define input intents, entity/asset interfaces, and events before delegating independent modules. Report changed behavior and local checks to the lead, who owns the consolidated browser pass. When a user changes requirements, update the existing brief and pending tasks instead of restarting completed work.

Gameplay code emits audio events; `threejs-audio-generator` produces the actual assets and the runtime audio matrix.

## Stack

TypeScript, Vite, Three.js modules, `three/addons/...` for official controls, loaders, and post-processing. `lil-gui` for live-tuned constants. Web Audio for runtime playback. Physics engine choice, timestep, and collider strategy follow `references/physics-engine-selection.md` — Rapier by default when the game needs real simulation.

## What goes wrong

A static demo instead of a playable loop · mechanics bolted onto a scene that was built first · a core loop described but never proven through real input, pressure, reward, and fail/retry · a track or arena that decorates rather than shapes decisions · a mechanic that compiles but no input can trigger · camera and controls that lag or hide the next decision · state changes that never reach UI, audio, or VFX · abstractions built before any mechanic needed them.

## Report

Behavior and controls, the three design artifacts for broad builds, architecture choices and tuned values, changed files, and what you saw when you played it. Note the physics engine, timestep, and collider strategy when physics is in scope.
