# Three.js Audio Workflows

Use this reference before generating or integrating audio for a game.

## Audio Planning

Create an audio matrix before generating files:

| Category | Required events | Asset count | Loop? | Runtime group |
| --- | --- | ---: | --- | --- |
| UI | hover, confirm, cancel, pause, fail | 3-8 | no | ui |
| Movement | jump, dash, boost, landing, drift | 3-10 | sometimes | sfx |
| Interaction | pickup, hit, shield, score, checkpoint | 4-12 | no | sfx |
| Threat | enemy attack, warning, impact, boss cue | 4-12 | no | sfx |
| Ambience | room tone, wind, engines, crowd, weather | 1-4 | yes | ambience |
| Music | menu, gameplay, boss, win/lose stingers | 1-5 | tracks yes, stingers no | music |
| Voice | announcer, boss, tutorial, combat barks | optional | no | voice |

For a first premium pass, fill the rows the game's events actually produce — typically an ambience loop, the core UI actions, and each primary gameplay event.

Music and voice are optional; add a gameplay loop when the genre and pacing benefit from a score, and voice when the design benefits from dialogue or callouts. An explicit no-music or silent brief wins.

## Prompting

Good prompts specify source, transient, tail, mix density, genre, and gameplay use:

```text
short [event] sound for [game genre], [material/source], clear transient, [tail length], no music, no voice, readable under gameplay mix
```

Examples:

- `short shield absorb impact for sci-fi boss fight, glassy plasma hit, bright transient, low sub thump, 0.8s tail, no music, no voice`
- `looping abandoned cathedral ambience for dark fantasy arena, distant wind through stone arches, subtle torch crackle, no melody, seamless loop`
- `tiny premium menu confirm click, soft mechanical latch, warm sparkle tail, no harsh beep`

Avoid prompts that are only mood words (`epic`, `AAA`, `cool`). Name the gameplay event.

## Generation Strategy

- Generate short SFX individually instead of one long mixed file.
- Make loops deliberately with `--loop`; test them looping in the game.
- Avoid music inside SFX prompts unless the user asked for music.
- Keep UI sounds quieter and shorter than gameplay SFX.
- Generate variants for high-frequency events to avoid repetition.
- Normalize in the game through volume groups, not by editing every file manually during early iteration.

## Music Strategy

Music prompts name genre, tempo (BPM), key instrumentation, energy curve, and the game moment: `tense orchestral boss theme, 140 BPM, low brass ostinato, taiko hits, relentless energy, no intro, loopable, instrumental`. Use `--instrumental` unless the user wants vocals, since vocals compete with SFX and dialogue.

- Gameplay and menu loops: 30–90s. Ask for constant energy with no intro, outro, or fade so the ends meet; the API has no loop flag.
- Stingers (victory, defeat, level-up, boss reveal): 3–8s, not looped.
- Sectioned tracks (intro → loop → outro, calm → combat): write a `composition_plan` JSON with global styles and sections, and pass it with `--plan`. Plans also accept `--seed` for reproducible regeneration.
- Intensity layers (explore → combat): generate matching variants from the same prompt with one changed energy term, then crossfade them from game state.
- Keep the music group below SFX in the mix; duck it under dialogue, and during hitstop or big impacts.

Listen to the loop seam in game before generating variants. If it clicks or jumps, set `loopStart`/`loopEnd` on beat boundaries, or crossfade two sources, rather than regenerating blindly.

## Voice Strategy

Use TTS when the line can be generated from text and exact acting is less important.

Use voice-change when:

- The user or agent can record a scratch performance.
- Timing, breaths, laughter, anger, fear, or delivery need to be preserved.
- A boss, announcer, narrator, or character line needs stronger acting than text prompt alone.

Clean noisy scratch recordings with `isolate` before conversion unless `voice-change --remove-background-noise` is sufficient.

Do not generate or convert voices that imply impersonation of a real private person. For characters, describe a fictional voice style or use a licensed/available voice ID.

## Runtime Integration

Use a small audio manager instead of ad hoc `new Audio()` calls once a game has more than a few sounds:

- Load sounds after user gesture unlock.
- Maintain groups: `master`, `sfx`, `ui`, `ambience`, `voice`, `music`.
- Expose mute and per-group volume.
- Loop ambience and music through `AudioBufferSourceNode` (`loop = true`, with `loopStart`/`loopEnd` for music) or a library wrapper that handles loop restarts. Crossfade music tracks with two gains rather than hard-cutting.
- Stop/dispose old sources when restarting scenes.
- Do not trigger the same high-volume SFX every frame; add cooldowns or variant pools.
- Pause/resume audio with the game pause state and page visibility.

Minimal Web Audio shape:

```ts
class GameAudio {
  private ctx = new AudioContext();
  private buffers = new Map<string, AudioBuffer>();
  private gains = new Map<string, GainNode>();

  async unlock() {
    if (this.ctx.state !== 'running') await this.ctx.resume();
  }

  async load(id: string, url: string) {
    const data = await fetch(url).then(r => r.arrayBuffer());
    this.buffers.set(id, await this.ctx.decodeAudioData(data));
  }

  play(id: string, group = 'sfx', volume = 1) {
    const buffer = this.buffers.get(id);
    if (!buffer) return;
    const source = this.ctx.createBufferSource();
    const gain = this.ctx.createGain();
    gain.gain.value = volume;
    source.buffer = buffer;
    source.connect(gain).connect(this.gains.get(group) ?? this.ctx.destination);
    source.start();
  }
}
```

## Runtime failure modes

Ambience or music loops stacking after a pause or restart · audible clicks at a music loop seam · music masking gameplay SFX · autoplay blocked because nothing unlocked the context from a user gesture · mute or volume reaching only some groups · decode/load errors swallowed silently · mobile Safari needing its own unlock path.
