---
name: threejs-gameplay-systems
description: "Build and iterate playable Three.js game systems. Combines starter scaffold creation, architecture, game design, level design, gameplay implementation, combat/encounter design, and game-feel tuning (hitstop, screenshake, easing, impact feedback). Use for first playable slices, new Vite/TypeScript/Three.js game setup, design briefs, core loops, level/arena/track/wave/hole/puzzle design, game loops, entity systems, input, collision/physics, scoring, objectives, audio hooks, camera, controls, difficulty, feedback, juice, and maintainable structure."
---

# Three.js Gameplay Systems

## Purpose

Create or evolve a playable browser game loop with clear ownership, responsive controls, deterministic update order, strong design intent, playable spaces, and verified player-facing behavior.

## Use When

Starting a new game, repairing a weak prototype, adding mechanics/entities, designing architecture, defining a game design brief, planning levels/arenas/tracks/waves/holes/puzzles, tuning camera/controls, implementing rules/objectives, building encounters, or improving game feel.

## Workflow

Load `references/gameplay-workflows.md` as the first action when the task includes first playable setup, architecture, mechanics, entities, input, camera, collision/physics, scoring, objectives, feedback, or feel tuning.

Load `references/game-design-level-design.md` before broad new-game creation, major gameplay changes, level/arena/track/wave/hole/puzzle design, combat/encounter design, progression/difficulty work, or any claim that gameplay is premium, polished, complete, or less generic.

Load `references/physics-engine-selection.md` before adding or changing physics, collision-heavy gameplay, vehicle movement, rolling balls, mini-golf, pool/snooker, pinball, rigid-body puzzles, character controllers, sensors, high-speed projectiles, moving platforms, or physics QA.

Load `references/game-feel.md` before feel/juice/impact tuning, or before claiming gameplay is premium or polished. Track every loaded reference in a reference ledger with yes/no, path, and failure reason. Do not mark the gameplay phase complete while a required reference is skipped.

Load `references/checklists/new-game-definition-of-done.md` before claiming a new game or first playable slice is complete.

Load `references/checklists/game-design-level-design.md` before claiming a new game, major gameplay upgrade, level/encounter pass, premium gameplay, or polished gameplay is complete.

Load `references/checklists/game-feel.md` before claiming feel/impact tuning or premium gameplay is complete.

Load `references/checklists/endless-runner-premium-quality.md` for endless runner work.

Load `references/prompt-templates.md` only when the user asks for reusable prompts, starter prompts, or a task template.

Load `threejs-audio-generator` when implementing real SFX, ambience, UI sounds, voice/TTS, or audio cleanup beyond simple placeholder hooks. Gameplay code should emit audio events; the audio skill should generate or process the actual assets and define the runtime audio matrix.

1. Inspect project structure, scripts, dependencies, current loop, input, camera, entities, state, UI, and diagnostics.
2. Write the compact game design brief: player promise, target feeling, primary verb, objective, pressure, reward, fail/retry, skill expression, non-goals.
3. Define the core loop contract: verb, objective, pressure, reward/progression, fail/retry.
4. Define the level/encounter plan before implementation: start, first decision, first threat, first reward, landmarks, escalation, recovery beats, readability, and tuning knobs.
5. Choose small architecture boundaries: `core`, `game`, `entities`, `systems`, `assets`, `ui`, `tests`.
6. Implement mechanics in playable increments: input, state, entity, collision/physics, feedback, HUD/audio hook, diagnostics.
7. Tune feel with `references/game-feel.md`: movement, acceleration, camera follow/FOV/shake, hitstop, impact feedback, cooldowns, difficulty, restart loop.
8. Keep hot paths allocation-light and update order explicit.
9. Verify with build, browser, screenshot, canvas pixels, console/page errors, and one real input path.

## Packaged Scaffold

Use the bundled scaffold when starting a new project or when the user asks for a starter game:

```bash
python3 <this-skill-dir>/scripts/create_threejs_game.py ./my-game
```

The script copies `assets/threejs-vite-game/`, rewrites the project name in `package.json` and `package-lock.json`, and keeps generated games self-contained with their own visual test and canvas-inspection script. Use `--force` only when the target directory may be overwritten.

## Library Guidance

- Use TypeScript, Vite, Three.js modules.
- Physics/collision engine choice (custom collision vs Rapier vs cannon-es), timestep, and collider strategy: follow `references/physics-engine-selection.md`.
- `lil-gui` for live-tuned constants when useful.
- Web Audio for runtime playback and procedural feedback; `threejs-audio-generator` for generated game audio assets.

## Common Failure Modes

- Static demo instead of playable loop.
- Static scene with mechanics bolted on after the fact, instead of a design brief plus level/encounter plan driving implementation.
- Core loop is described but not proven through real input, pressure, reward/progression, and fail/retry.
- Level/track/arena/map is decorative and does not shape player decisions.
- Mechanic compiles but cannot be triggered by real input.
- Camera/controls feel delayed or hide the next decision.
- State changes do not drive UI/audio/VFX.
- Architecture abstractions appear before mechanics need them.

## Final Response

Report the reference ledger, game design brief, core loop contract, level/encounter plan, gameplay checklist outcome, behavior, controls, changed files, architecture choices, tuned values, verification evidence, artifacts, and remaining edge cases.
