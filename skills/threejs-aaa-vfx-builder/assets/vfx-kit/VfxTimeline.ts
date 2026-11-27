/**
 * Deterministic VFX choreography timeline, easing curves, seeded PRNG,
 * and one-shot beat cue helpers. Compatible with pause, scrub, hitstop,
 * and deterministic Playwright screenshot baselines.
 */

export const clamp01 = (v: number): number => Math.max(0, Math.min(1, v));

export const lerp = (a: number, b: number, t: number): number => a + (b - a) * t;

export const remap = (x: number, inMin: number, inMax: number): number =>
  inMax === inMin ? (x >= inMax ? 1 : 0) : clamp01((x - inMin) / (inMax - inMin));

export const smoothstep = (e0: number, e1: number, x: number): number => {
  const t = remap(x, e0, e1);
  return t * t * (3 - 2 * t);
};

export const easeInQuad = (t: number): number => {
  const c = clamp01(t);
  return c * c;
};

export const easeOutQuad = (t: number): number => {
  const c = clamp01(t);
  return 1 - (1 - c) * (1 - c);
};

export const easeInCubic = (t: number): number => {
  const c = clamp01(t);
  return c * c * c;
};

export const easeOutCubic = (t: number): number => {
  const c = 1 - clamp01(t);
  return 1 - c * c * c;
};

export const easeOutExpo = (t: number): number => {
  const c = clamp01(t);
  return c >= 1 ? 1 : 1 - Math.pow(2, -10 * c);
};

export const easeInExpo = (t: number): number => {
  const c = clamp01(t);
  return c <= 0 ? 0 : Math.pow(2, 10 * c - 10);
};

export const easeOutBack = (t: number): number => {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  const x = clamp01(t) - 1;
  return 1 + c3 * x * x * x + c1 * x * x;
};

/**
 * Symmetric attack-hold-decay envelope in [0..1] over a local [start, end] window.
 */
export function pulseEnvelope(
  t: number,
  start: number,
  peakStart: number,
  peakEnd: number,
  end: number,
): number {
  if (t <= start || t >= end) return 0;
  if (t < peakStart) return smoothstep(start, peakStart, t);
  if (t <= peakEnd) return 1;
  return 1 - smoothstep(peakEnd, end, t);
}

/**
 * Deterministic LCG PRNG in [0, 1). Never use Math.random() inside VFX paths.
 */
export function createSeededRng(seed: number): () => number {
  let state = seed | 0;
  return () => {
    state = (state * 1664525 + 1013904223) | 0;
    return ((state >>> 0) % 1_000_000) / 1_000_000;
  };
}

export interface VfxAudioCue {
  id: string;
  at: number;
  volume?: number;
  pitchJitter?: number;
}

/**
 * Collects one-shot cues crossed between prevTime and currTime without firing
 * duplicates on pause, reverse scrub, or large discontinuity jumps.
 */
export function collectCrossedCues(
  cues: readonly VfxAudioCue[],
  prevTime: number,
  currTime: number,
  maxStep = 0.25,
): VfxAudioCue[] {
  if (currTime <= prevTime || currTime - prevTime > maxStep) return [];
  const fired: VfxAudioCue[] = [];
  for (const cue of cues) {
    if (prevTime < cue.at && currTime >= cue.at) {
      fired.push(cue);
    }
  }
  return fired;
}
