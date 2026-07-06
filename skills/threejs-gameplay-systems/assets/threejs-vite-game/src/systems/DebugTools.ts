import GUI from 'lil-gui';
import type { PlayerTuning } from '../entities/Player';

export type DebugTuning = PlayerTuning & {
  cameraLag: number;
  exposure: number;
  maxDpr: number;
};

export class DebugTools {
  private gui: GUI | null = null;

  constructor(tuning: DebugTuning, onChange: () => void) {
    const enabled = new URLSearchParams(window.location.search).has('debug');
    if (!enabled) return;

    this.gui = new GUI({ title: 'Game tuning' });
    this.gui.add(tuning, 'speed', 2, 14, 0.1);
    this.gui.add(tuning, 'dashMultiplier', 1, 3, 0.05);
    this.gui.add(tuning, 'acceleration', 4, 22, 0.1);
    this.gui.add(tuning, 'cameraLag', 0.02, 0.8, 0.01);
    this.gui.add(tuning, 'maxDpr', 1, 2, 0.25).onChange(onChange);
    this.gui.add(tuning, 'exposure', 0.6, 1.8, 0.01).onChange(onChange);
  }

  setHidden(hidden: boolean): void {
    if (!this.gui) return;
    if (hidden) this.gui.hide();
    else this.gui.show();
  }

  dispose(): void {
    this.gui?.destroy();
    this.gui = null;
  }
}
