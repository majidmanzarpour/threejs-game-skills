---
name: threejs-audio-generator
description: "Generate, convert, clean, and integrate audio for Three.js browser games with ElevenLabs: sound effects, looping ambience, UI sounds, impact/weapon/vehicle audio, creature and boss stingers, announcer and dialogue TTS, voice conversion from a scratch performance, voice cleanup, audio manifests, and Web Audio integration."
---

# Three.js Audio Generator

Game-ready audio for Three.js projects: generation, voice work, cleanup, and runtime integration. Provider: ElevenLabs.

Resolve `<this-skill-dir>` from the actual loaded skill file. Resolve sibling skills beside it first, then use the runner's discovered paths. Do not mix installed versions or assume a particular home directory.

## Reference

`references/audio-workflows.md` — the audio matrix, prompt patterns, generation and voice strategy, Web Audio manager shape, and runtime failure modes. Read it before planning a game's audio, generating a batch, wiring runtime playback, or converting voices.

## When to use

SFX (jumps, hits, weapons, explosions, pickups, collisions, UI clicks) · ambience (wind, rain, city bed, engine hum, room tone, arena beds) · voice (announcer barks, boss lines, tutorial prompts, menu narration) · voice conversion from a scratch performance when timing and acting matter · cleanup and isolation before conversion or final use · Web Audio integration with loading, looping, manifests, volume groups, pause/resume, and gesture unlock.

Audio is not cosmetic for a premium game. Build an audio matrix from the events the game actually has; do not add dialogue, weapons, or ambience layers just to fill categories. Respect explicit silent, procedural-audio, accessibility, and external-service constraints. A narrow sound fix does not need a new soundtrack.

## API key

The script reads `--api-key` or `ELEVENLABS_API_KEY`. Keys never go in skill files, game code, or reports.

```bash
python3 <this-skill-dir>/scripts/threejs_audio_asset.py probe   # ELEVENLABS_API_KEY=SET|MISSING
```

Keys defined only in a shell profile can be absent from the process env; `threejs-game-director/scripts/probe_asset_credentials.sh` sources the profile and probes the agent-executed keyed providers.

Add `--validate` to call `GET /user` and confirm the key actually works (prints `VALID_USER=...`) when a key is present but generation fails. A valid key can still be blocked by credit or plan limits, which surface as an `HTTP 4xx` from a real generation attempt — report that as a plan blocker rather than a missing key.

## Commands

Run from the game project directory:

```bash
python3 <this-skill-dir>/scripts/threejs_audio_asset.py sfx \
  --prompt "tight futuristic boost pickup, bright transient, short sparkling tail, arcade racing game" \
  --duration 1.2 --prompt-influence 0.65 --out assets/audio/sfx/boost-pickup.mp3

python3 <this-skill-dir>/scripts/threejs_audio_asset.py sfx \
  --prompt "seamless cyber resort ambience, distant surf, soft neon transformer hum, gentle crowd bed" \
  --duration 12 --loop --prompt-influence 0.45 --out assets/audio/ambience/cyber-resort-loop.mp3

python3 <this-skill-dir>/scripts/threejs_audio_asset.py tts \
  --text "Perfect shot." --voice-id JBFqnCBsd6RMkjVDRZzb --out assets/audio/voice/perfect-shot.mp3

python3 <this-skill-dir>/scripts/threejs_audio_asset.py isolate \
  --input assets/audio/source/noisy-boss-line.wav --out assets/audio/voice/boss-line-clean.mp3

python3 <this-skill-dir>/scripts/threejs_audio_asset.py voice-change \
  --input assets/audio/source/scratch-boss-line.wav --voice-id JBFqnCBsd6RMkjVDRZzb \
  --remove-background-noise --out assets/audio/voice/boss-line-final.mp3
```

## Defaults

- SFX: `mp3_44100_128`, 0.5–2.5s, prompt influence 0.55–0.8.
- UI: 0.15–0.8s, high prompt influence, transients kept clear.
- Ambience: 8–30s with `--loop`, prompt influence 0.3–0.55.
- Voice: TTS for clean generated lines; `voice-change` when timing and acting from a scratch performance matter. Isolate noisy speech first.
- Runtime: generate into the game project and load through Web Audio. Follow the project's asset/version-control policy; do not commit or publish unless asked. No API keys in browser code.

## Recovery and Coordination

For coordinated games use the director's `references/asset-recovery.md`. Preserve outputs and the audio trigger mapping before retrying work. Distinguish missing credentials, permissions, exhausted credits, invalid input, and transient service failures. Reconcile an uncertain paid request before resubmitting; these one-shot commands do not implement Tripo task resume. Keep independent gameplay work moving and provide a local/synthesized fallback with honest limitations when genuinely blocked.

Listen to a representative effect or line before generating a batch. Test it through its real game event, then give the lead paths and local playback findings for one consolidated QA pass.

## Report

Generated and processed file paths, the prompts, text, source files, voice IDs, durations, loop flags and formats behind them, the runtime trigger mapping and audio groups, and any remaining gaps or plan limits.
