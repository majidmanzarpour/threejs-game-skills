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
| Voice | announcer, boss, tutorial, combat barks | optional | no | voice |

For a first premium pass, generate at least:

- 1 ambience loop.
- 3 UI sounds.
- 5 gameplay SFX tied to real events.
- Optional voice only if the design benefits from dialogue or callouts.

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
- Loop ambience through `AudioBufferSourceNode` or a library wrapper that handles loop restarts.
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

Ambience loops stacking after a pause or restart · autoplay blocked because nothing unlocked the context from a user gesture · mute or volume reaching only some groups · decode/load errors swallowed silently · mobile Safari needing its own unlock path.
