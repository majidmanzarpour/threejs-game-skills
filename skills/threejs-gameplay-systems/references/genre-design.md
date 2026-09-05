# Genre Design Patterns

Per-genre design vocabulary, difficulty shaping, and the tests that separate a real game from a scene you can move around in. The design brief, core loop contract, and level plan templates live in this skill's `SKILL.md` under "Design first".

## Contents

- Genre patterns (runner, racer, dogfight, tower defense, billiards, mini golf, boss, puzzle)
- Difficulty and pacing
- Fun-factor tests

## Genre patterns

**Endless runner** — teach lanes or steering with an early safe segment. Alternate compression and release: dense hazard groups, then reward and visibility windows. Use distinct silhouettes and telegraphs for each obstacle role; choose the number of families from the planned decisions and scope. Ramp difficulty through speed, lane pressure, obstacle combinations, and reward placement.

**Arcade racer** — define the handling fantasy first (drift-heavy, grip, hover glide, combat, rally). Tracks need readable apexes, braking and drift cues, recovery width, landmarks, and route rhythm. Skill tests: racing line, boost timing, drift angle, traffic threading, shortcut risk.

**Dogfight / space shooter** — define engagement range, turn rate, projectile speed, lead or lock-on affordance, and escape options. Encounters need target readability, off-screen threat indicators, and moments to reacquire orientation. Waves should force movement rather than circular chasing.

**Tower defense** — define path topology, chokepoints, build zones, enemy archetypes, tower roles, economy cadence, and wave tells. Good maps create placement decisions rather than one obvious optimal tile. Waves test different tower roles and reveal upcoming enemy types before punishing.

**Billiards / pool / snooker** — physics and rules *are* the design. Readable shot aim, cue force, spin, turn state, legal-target feedback, foul feedback, camera reset. Level design is table readability: pockets, rails, ball colors, aim lines, shadows, overhead and low camera options.

**Mini golf** — each hole gets one clear read, one trick, and one risk/reward route. Escalate through ramps, banks, moving blockers, portals, split paths, gravity changes, timing windows. The first shot's outcome should be readable from the tee.

**Boss fight / action arena** — define phases, telegraphs, recovery windows, player punish windows, arena hazards, camera lock behavior. Every attack needs a readable tell, an avoid or defend option, impact feedback, and a cooldown. Later phases add combinations or arena pressure, not just health.

**Puzzle / physics** — state the rule each puzzle teaches. First puzzle teaches, second confirms, third twists. Failure should reveal information; avoid hidden dependency chains that require guessing.

## Difficulty and pacing

A curve, not random escalation: introduce one new concept at a time, combine known concepts once they are understood, and leave breathing space after high-pressure moments. Raise challenge through timing, density, speed, resource scarcity, enemy mix, or spatial constraint. Keep early failures recoverable unless the genre is deliberately harsh. Tune with named constants and record what changed.

Greybox first — simple shapes prove scale, route, timing, line-of-sight, collision, and pacing before art detail is worth building.

## Fun-factor tests

Iterate if any of these is true:

- The first 30 seconds contain no real decision.
- The player can ignore the main mechanic and still progress.
- The objective is unclear without reading the source.
- Failure happens before the player can understand why.
- Challenge is "more things" rather than better combinations.
- Rewards change nothing about strategy, score, progression, or feel.
- The space is decorative and does not shape decisions.
- The game is fun in the explanation but not in active play.

If the intended feeling does not emerge from the current mechanics, change mechanics or layout. Graphics do not fix missing dynamics.
