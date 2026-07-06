# Bot Playtest Checklist

Use with `threejs-qa-release/references/playtest-bot.md`.

- Diagnostics publish frame, score/objective, complete/fail state, and player position.
- Test hooks expose `seed()` and `setState()`; the run seed is reported.
- `INPUT_SCRIPT` expresses the game's core verb, not just arbitrary key mashing.
- The bot run completed with zero console and page errors.
- Player moved in response to scripted input (distance above threshold).
- The objective progressed during the run (score, waves, distance, or completion).
- Softlock windows are within threshold, or each one is explained.
- Games with fail states: a reckless run triggers the fail state and the retry path restores play.
- Difficulty claims are backed by two-skill-level bot runs, not intuition.
- Bot playtest decision reported as added/extended/skipped with reason.
