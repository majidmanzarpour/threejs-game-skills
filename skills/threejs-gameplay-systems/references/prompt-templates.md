# Three.js Gameplay Systems Prompt Templates

Reusable prompt templates packaged with this skill. Use only templates relevant to the current request, and adapt placeholders to the game/project context.

---

# Gameplay System Prompt

Use `threejs-gameplay-systems` to add or modify this gameplay system:

System:
- Player-facing behavior:
- Entities affected:
- State changes:
- Collision/physics needs:
- Audio/visual/HUD feedback:
- Edge cases:

Constraints:
- Preserve existing controls and camera unless the task asks to change them.
- Keep update order deterministic.
- Use simple custom collision unless the mechanics justify a physics library.
- Add debug controls only when they speed tuning.
- Verify through build, local browser run, console check, screenshot, canvas-pixel check, and interaction test.

---

# Game Design And Level Design Prompt

Use `threejs-gameplay-systems` to design or improve this game's player-facing loop before implementation:

Game:
- Target fantasy / player promise:
- Primary verb:
- Desired feeling:
- Genre:
- Target session length:
- Target devices:

Produce and then implement:
- Compact game design brief.
- Core loop contract: verb -> objective -> pressure -> reward/progression -> fail/retry.
- Level/encounter plan: start, first decision, first threat, first reward, landmarks, escalation, recovery beats, readability.
- Difficulty curve and tuning constants.
- Fun-factor rejection tests.

Constraints:
- Build a playable loop first.
- Do not treat a static scene as a game.
- Make the level/arena/track/wave/hole/puzzle shape player decisions.
- Verify with real input, active-play screenshot, canvas-pixel check, and fail/retry or setback path when relevant.
