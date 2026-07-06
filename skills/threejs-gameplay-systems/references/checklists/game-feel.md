# Game Feel Checklist

Use before claiming a game feels good, is juicy, is polished, or is premium. Pairs with references/game-feel.md.

- The primary verb produces a visible response within 100ms of input.
- Every scoring, pickup, damage, and death event has at least one visual and one audio response.
- Screenshake is trauma-based with the `trauma²` curve, per-second decay, and a hard cap.
- Trauma magnitude scales with event weight (pickup subtle, explosion unmistakable).
- Hitstop scales the gameplay delta only; camera, shake, tweens, and HUD keep the real delta.
- Hitstop is reserved for heavy contact, not fired on every minor event.
- The render loop is never paused to create a freeze; only gameplay delta is scaled.
- Squash-and-stretch preserves volume and settles with an overshoot (easeOutBack).
- FOV punch calls updateProjectionMatrix() and decays back to base.
- Impact flash stores the material's base emissive value and tweens back to it.
- Feedback never obscures the next player decision (shake/flash/hitstop stay readable).
- Gamepad rumble is feature-detected and matched in strength to the event.
- Repeated audio samples use pitch/volume variance so they never sound identical.
- All gameplay and effect randomness routes through createSeededRandom, never Math.random.
- Time-based effects are driven by accumulated game time, not wall clock.
- Each core event maps to a full feedback stack (see the tuning table), not a single cue.
