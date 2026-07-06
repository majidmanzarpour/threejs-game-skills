# Game Feel

Use this reference when a game "works" but does not feel good: the primary verb lands without weight, hits read as bookkeeping, pickups vanish silently. Game feel (juice) is the layer of response, contact feedback, and audio-visual sync that turns correct mechanics into satisfying ones.

Game feel is state communication, not decoration. Apply effects in this order of operations; each layer depends on the one before it:

1. Input latency: the primary verb must produce a visible response within ~100ms. Fix this first; no amount of juice hides a laggy control.
2. Response curves: acceleration, easing, and overshoot on the player's own motion.
3. Contact feedback: what happens at the moment of impact, pickup, or score (flash, squash, hitstop, shake).
4. Camera: shake, kick, FOV punch that amplify contact without hiding the field of play.
5. Audio-visual sync: sound fires on the same frame as the visual, with pitch/volume variance so repeats stay alive.

Readability rule: feedback must clarify game state, never obscure the next decision. If shake, flash, or hitstop hides the thing the player must react to next, it is a bug, not polish. Scale every effect so the strongest events (death, explosion) are unmistakable and the weakest (pickup) stay subtle.

All code below is copy-pasteable, strict-TS clean, dependency-free, and matches the scaffold (`update(delta, elapsed)`, class systems, `createSeededRandom`).

## Tween / Easing Helper

No external tween library. A tiny manager updated with `delta`, plus three curves that cover 90% of feel work.

```ts
export type Easing = (t: number) => number;

export const easeInQuad: Easing = (t) => t * t;
export const easeOutCubic: Easing = (t) => 1 - Math.pow(1 - t, 3);
export const easeOutBack: Easing = (t) => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};

interface ActiveTween {
  elapsed: number;
  duration: number;
  easing: Easing;
  onUpdate: (value: number) => void;
  onComplete?: () => void;
}

export class TweenManager {
  private readonly tweens: ActiveTween[] = [];

  tween(
    durationSec: number,
    onUpdate: (value: number) => void,
    easing: Easing = easeOutCubic,
    onComplete?: () => void,
  ): void {
    this.tweens.push({ elapsed: 0, duration: durationSec, easing, onUpdate, onComplete });
  }

  update(delta: number): void {
    for (let i = this.tweens.length - 1; i >= 0; i -= 1) {
      const t = this.tweens[i];
      t.elapsed += delta;
      const k = Math.min(t.elapsed / t.duration, 1);
      t.onUpdate(t.easing(k));
      if (t.elapsed >= t.duration) {
        t.onComplete?.();
        this.tweens.splice(i, 1);
      }
    }
  }
}
```

Update the manager with the **real** delta (feedback must stay live during hitstop). `easeOutBack` returns values above 1 near the end; that overshoot is the bounce.

## Trauma-Based Screenshake

Add trauma on events; shake is `trauma²` so small events barely move the camera and big ones snap hard. Trauma decays linearly per second and is hard-capped. Drive the noise from accumulated game time (deterministic), not wall clock.

```ts
import * as THREE from 'three';

const TRAUMA_MAX = 1;
const TRAUMA_DECAY = 1.4; // trauma units per second
const MAX_OFFSET = 0.55; // world units at full shake
const MAX_ROLL = 0.1; // radians at full shake

// Deterministic value noise in [-1, 1]; per-axis seed keeps axes independent.
function pseudoNoise(t: number, seed: number): number {
  const x = Math.sin(t * 12.9898 + seed * 78.233) * 43758.5453;
  return (x - Math.floor(x)) * 2 - 1;
}

export class ShakeRig {
  private trauma = 0;
  private time = 0;

  addTrauma(amount: number): void {
    this.trauma = Math.min(TRAUMA_MAX, this.trauma + amount);
  }

  // Call every frame AFTER CameraRig has written the base transform.
  update(delta: number, camera: THREE.PerspectiveCamera): void {
    this.time += delta;
    this.trauma = Math.max(0, this.trauma - TRAUMA_DECAY * delta);
    if (this.trauma <= 0) return;
    const shake = this.trauma * this.trauma;
    const freq = this.time * 32;
    camera.position.x += MAX_OFFSET * shake * pseudoNoise(freq, 1);
    camera.position.y += MAX_OFFSET * shake * pseudoNoise(freq, 2);
    camera.rotation.z += MAX_ROLL * shake * pseudoNoise(freq, 3);
  }
}
```

Recommended trauma per event: pickup `0.15`, hit `0.4`, explosion `0.7`. Cap at `1.0` so stacked events cannot fling the camera. The additive offset does not accumulate because `CameraRig` re-derives position from the follow target and `lookAt` re-derives rotation every frame.

## Hitstop

A brief freeze on heavy contact sells weight. Scale the gameplay delta, never the render loop.

```ts
// Fields on Game:
private timeScale = 1;
private hitstopRemaining = 0;

hitstop(durationMs: number, scale = 0.05): void {
  this.hitstopRemaining = Math.max(this.hitstopRemaining, durationMs / 1000);
  this.timeScale = scale;
}

private update(delta: number, elapsed: number): void {
  if (this.hitstopRemaining > 0) {
    this.hitstopRemaining -= delta; // decay in REAL time
    if (this.hitstopRemaining <= 0) this.timeScale = 1;
  }
  const gameplayDelta = delta * this.timeScale;

  // Gameplay reads the scaled delta so the world crawls...
  this.player.update(gameplayDelta, elapsed, this.input, this.tuning, ARENA);
  for (const pickup of this.pickups) pickup.update(gameplayDelta, elapsed);

  // ...but camera, shake, tweens, and HUD read the REAL delta so feedback stays live.
  this.cameraRig.update(delta, this.player.group.position, this.tuning.cameraLag);
  this.shakeRig.update(delta, this.camera);
  this.tweens.update(delta);
}
```

Recommended: 60-90ms at `0.05` scale on heavy hits only. Never call `loop.stop()` or skip `requestAnimationFrame` to freeze — the frame must keep drawing so the frozen moment is visible. Only the gameplay delta is scaled.

## Squash-and-Stretch

Deform on impact or jump, then overshoot back with `easeOutBack`. Preserve volume: when one axis scales by `s`, scale the other two by `1 / sqrt(s)`.

```ts
// Impact squash (squashY < 1); jump stretch uses squashY > 1.
squash(target: THREE.Object3D, squashY = 0.85, durationSec = 0.18): void {
  const startXZ = 1 / Math.sqrt(squashY); // volume-preserving counter-scale
  this.tweens.tween(
    durationSec,
    (t) => {
      const y = squashY + (1 - squashY) * t; // squashY -> 1
      const xz = startXZ + (1 - startXZ) * t; // stretch -> 1
      target.scale.set(xz, y, xz);
    },
    easeOutBack, // overshoot past 1 gives the bouncy settle
  );
}
```

Use ~1.15 stretch on jump takeoff and ~0.9 squash on landing, both returning over ~180ms.

## Camera Kick / FOV Punch

An additive FOV bump reads as acceleration or shock. Decay it toward 0 with a ~200ms time constant.

```ts
private baseFov = 48;
private fovPunch = 0; // additive degrees

punchFov(degrees: number): void {
  this.fovPunch = Math.min(10, this.fovPunch + degrees); // additive, clamped
}

private updateFov(delta: number): void {
  if (this.fovPunch <= 0.001) return;
  this.fovPunch *= Math.exp(-delta / 0.2);
  if (this.fovPunch < 0.001) this.fovPunch = 0;
  this.camera.fov = this.baseFov + this.fovPunch;
  this.camera.updateProjectionMatrix(); // REQUIRED after any fov change
}
```

Recommended +4..8° on boost, dash, or hit. Forgetting `updateProjectionMatrix()` leaves the FOV visually unchanged.

## Impact Flash

Pulse `emissiveIntensity` on the hit material and tween it back. Store the base value once; the material's `emissive` color must be non-black for the pulse to show.

```ts
flashHit(material: THREE.MeshStandardMaterial, peak = 2.4, durationSec = 0.22): void {
  const base = (material.userData.baseEmissive ??= material.emissiveIntensity);
  this.tweens.tween(
    durationSec,
    (t) => {
      material.emissiveIntensity = base + (peak - base) * (1 - t); // peak -> base
    },
    easeOutCubic,
  );
}
```

For big events (explosion, death), add a one-frame full-screen white flash: a `position: fixed` DOM `<div>` with `pointer-events: none`, animated `opacity: 0.8 -> 0` over ~90-120ms via `element.animate(...)`. Cheaper than a render-target flash and it never touches the 3D pipeline.

## Pickup Pop

Collected items should pop, rise, and fade rather than blink out.

```ts
playPickupPop(mesh: THREE.Mesh, material: THREE.MeshStandardMaterial): void {
  const startY = mesh.position.y;
  material.transparent = true;
  this.tweens.tween(
    0.28,
    (t) => {
      mesh.scale.setScalar(1 + 0.6 * (1 - t)); // 1.6 -> 1.0
      mesh.position.y = startY + t * 1.2; // rise
      material.opacity = 1 - t; // fade
    },
    easeOutCubic,
    () => {
      mesh.visible = false;
    },
  );
}
```

Punch the HUD counter on the same event (add to `Hud`, reusing the scaffold's WAAPI pattern):

```ts
punchScore(): void {
  this.scoreValue.animate(
    [{ transform: 'scale(1.2)' }, { transform: 'scale(1)' }],
    { duration: 120, easing: 'ease-out' },
  );
}
```

## Gamepad Rumble

Feature-detect `vibrationActuator`; `playEffect` returns a promise that may reject on unsupported hardware, so swallow it.

```ts
export function rumble(durationMs: number, strong = 0.6, weak = 0.3): void {
  const pads = navigator.getGamepads?.() ?? [];
  for (const pad of pads) {
    const actuator = pad?.vibrationActuator;
    if (!actuator) continue; // optional chaining covers older browsers
    void actuator.playEffect('dual-rumble', {
      duration: durationMs,
      strongMagnitude: strong,
      weakMagnitude: weak,
    });
  }
}
```

Match rumble to the hit: light (180ms, 0.3) on pickups, heavy (250ms, 0.9) on death or explosion.

## Audio Feel Coupling

Identical repeated samples feel cheap: the ear detects the exact repeat as artificial (the "machine-gun" effect). Vary pitch per playback, and duck ambient/music while hitstop holds so the impact reads.

```ts
// AudioSystem: pitch-vary each shot; duck holds during hitstop.
private duck = 1;

play(buffer: AudioBuffer, rng: () => number, baseGain = 0.8): void {
  if (!this.context || this.context.state !== 'running') return;
  const source = this.context.createBufferSource();
  const gain = this.context.createGain();
  source.buffer = buffer;
  source.playbackRate.value = 1 + (rng() - 0.5) * 0.12; // +/-6% pitch
  gain.gain.value = baseGain * this.duck;
  source.connect(gain).connect(this.context.destination);
  source.start();
}

setDuck(value: number): void {
  this.duck = value; // e.g. 0.6 while hitstop is active, 1 otherwise
}
```

Pass `this.rng` (the seeded RNG) as the `rng` argument so pitch variance stays deterministic under test.

## Tuning Table

Map each event to a full feedback stack. Stronger events get more layers and higher magnitudes.

| Event          | Feedback stack                                                                 |
| -------------- | ------------------------------------------------------------------------------ |
| Pickup         | pickup pop + HUD counter punch + pitch-varied chime + `0.15` trauma            |
| Player hit     | hitstop 70ms + `0.4` trauma + impact flash + rumble (180ms) + HUD pulse        |
| Enemy killed   | hitstop 40ms + `0.3` trauma + impact flash + pitch-varied boom                 |
| Boost / dash   | FOV punch +6° + stretch (1.15) + whoosh + light rumble                         |
| Jump / land    | stretch on takeoff, squash (0.9) on landing + step audio + `0.2` trauma on land |
| Explosion      | hitstop 90ms + `0.7` trauma + white overlay flash + FOV punch +8° + heavy rumble |

## Anti-Patterns

- Constant camera shake, or shake with no decay: nauseating and it hides the play field.
- Trauma added without the `trauma²` curve or the hard cap: small events feel violent, stacked events fling the camera.
- Hitstop on every minor event: the game feels laggy instead of weighty. Reserve it for heavy contact.
- Feedback that blocks or delays input: never gate the primary verb behind an animation finishing.
- Effects driven by wall clock or fixed-timestep gameplay delta: they desync from the simulation and break during hitstop or on frame drops. Drive time-based effects from accumulated game time; drive feedback tweens/camera from the real render delta.
- Emissive flash on a material with a black `emissive` color: nothing shows.
- `Math.random` in any gameplay or effect path: it breaks the deterministic test hooks and screenshot baselines.

## Determinism

Route **all** randomness — pitch variance, spawn jitter, shake seeds if you seed them — through `createSeededRandom` (see `src/utils/random.ts`), never `Math.random`. Drive time-based effects (shake noise, ambient motion) from accumulated game time passed through `update(delta, elapsed)`, not `performance.now()` or `Date.now()`. This keeps the `seed()` and `setReducedMotion()` test hooks reproducible so visual baselines and bot playtests stay stable.
