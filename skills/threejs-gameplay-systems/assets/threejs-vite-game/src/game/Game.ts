import * as THREE from 'three';
import { InputController } from '../core/InputController';
import { Loop } from '../core/Loop';
import { createRenderer, resizeRenderer } from '../core/Renderer';
import { Pickup } from '../entities/Pickup';
import { Player, type ArenaBounds } from '../entities/Player';
import { AudioSystem } from '../systems/AudioSystem';
import { CameraRig } from '../systems/CameraRig';
import { CollisionSystem } from '../systems/CollisionSystem';
import { DebugTools, type DebugTuning } from '../systems/DebugTools';
import { Hud } from '../systems/Hud';
import { createSeededRandom } from '../utils/random';

const ARENA: ArenaBounds = {
  halfWidth: 11,
  halfDepth: 7,
};

export class Game {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(48, 1, 0.1, 80);
  private readonly input: InputController;
  private readonly player = new Player();
  private readonly pickups: Pickup[] = [];
  private readonly collision = new CollisionSystem();
  private readonly audio = new AudioSystem();
  private readonly hud = new Hud();
  private readonly cameraRig = new CameraRig(this.camera);
  private readonly loop = new Loop(
    (delta, elapsed) => this.update(delta, elapsed),
    () => this.render(),
  );

  private readonly tuning: DebugTuning = {
    speed: 5.8,
    dashMultiplier: 1.75,
    acceleration: 13,
    cameraLag: 0.16,
    exposure: 1.05,
    maxDpr: 2,
  };

  private readonly debugTools: DebugTools;
  private frame = 0;
  private score = 0;
  private elapsed = 0;
  private complete = false;
  // Route ALL gameplay randomness through this.rng (never Math.random) so the
  // seed() test hook keeps screenshot baselines and bot playtests deterministic.
  private rng = createSeededRandom(1);
  private pausedForScreenshot = false;
  private reducedMotion = false;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.renderer = createRenderer(canvas);
    this.renderer.toneMappingExposure = this.tuning.exposure;

    const stick = this.getElement('#touch-stick');
    const knob = this.getElement('#touch-knob');
    const dashButton = this.getElement('#dash-button');
    this.input = new InputController(stick, knob, dashButton);

    this.debugTools = new DebugTools(this.tuning, () => {
      this.renderer.toneMappingExposure = this.tuning.exposure;
      resizeRenderer(this.renderer, this.camera, this.tuning.maxDpr);
    });

    this.createScene();
    this.hud.setTarget(this.pickups.length);
    this.cameraRig.snapTo(this.player.group.position);
    resizeRenderer(this.renderer, this.camera, this.tuning.maxDpr);
    this.installTestHooks();
    this.publishDiagnostics();
  }

  start(): void {
    this.loop.start();
  }

  dispose(): void {
    this.loop.stop();
    this.input.dispose();
    this.audio.dispose();
    this.debugTools.dispose();
    for (const pickup of this.pickups) pickup.dispose();
    this.player.dispose();
    this.renderer.dispose();
    window.__THREE_GAME_DIAGNOSTICS__ = undefined;
    window.__THREE_GAME_TEST_HOOKS__ = undefined;
  }

  private update(delta: number, elapsed: number): void {
    this.frame += 1;
    if (this.pausedForScreenshot) {
      this.publishDiagnostics();
      return;
    }
    if (!this.complete) this.elapsed += delta;

    resizeRenderer(this.renderer, this.camera, this.tuning.maxDpr);
    // Reduced motion freezes ambient animation time so screenshots are stable.
    const animDelta = this.reducedMotion ? 0 : delta;
    const animElapsed = this.reducedMotion ? 0 : elapsed;
    this.player.update(delta, animElapsed, this.input, this.tuning, ARENA);

    for (const pickup of this.pickups) {
      pickup.update(animDelta, animElapsed);
    }

    const collected = this.collision.collectPickups(this.player.group.position, this.pickups, 0.55);
    for (const pickup of collected) {
      this.score += 1;
      this.audio.pickup(pickup.index);
      this.hud.flashPickup();
    }

    if (this.score >= this.pickups.length) {
      this.complete = true;
    }

    this.cameraRig.update(delta, this.player.group.position, this.tuning.cameraLag);
    this.hud.update(this.score, this.pickups.length, this.elapsed, this.complete);
    this.publishDiagnostics();
  }

  private render(): void {
    this.renderer.render(this.scene, this.camera);
  }

  private createScene(): void {
    this.scene.background = new THREE.Color('#151713');
    this.scene.fog = new THREE.Fog('#151713', 20, 44);

    const hemisphere = new THREE.HemisphereLight('#f6f1df', '#2b322d', 1.7);
    this.scene.add(hemisphere);

    const sun = new THREE.DirectionalLight('#fff1bf', 2.6);
    sun.position.set(-5, 9, 6);
    sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    sun.shadow.camera.near = 0.5;
    sun.shadow.camera.far = 30;
    sun.shadow.camera.left = -14;
    sun.shadow.camera.right = 14;
    sun.shadow.camera.top = 12;
    sun.shadow.camera.bottom = -12;
    this.scene.add(sun);

    this.scene.add(this.createArena());
    this.scene.add(this.player.group);
    this.createPickups();
  }

  private createArena(): THREE.Group {
    const arena = new THREE.Group();
    const floorTexture = this.createFloorTexture();
    floorTexture.wrapS = THREE.RepeatWrapping;
    floorTexture.wrapT = THREE.RepeatWrapping;
    floorTexture.repeat.set(ARENA.halfWidth / 2, ARENA.halfDepth / 2);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(ARENA.halfWidth * 2, ARENA.halfDepth * 2, 1, 1),
      new THREE.MeshStandardMaterial({
        color: '#2a2c25',
        map: floorTexture,
        roughness: 0.72,
        metalness: 0.02,
      }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    arena.add(floor);

    const railMaterial = new THREE.MeshStandardMaterial({
      color: '#d94f35',
      roughness: 0.52,
      metalness: 0.08,
    });
    const longRailGeometry = new THREE.BoxGeometry(ARENA.halfWidth * 2 + 1, 0.55, 0.42);
    const shortRailGeometry = new THREE.BoxGeometry(0.42, 0.55, ARENA.halfDepth * 2 + 1);
    const rails = [
      new THREE.Mesh(longRailGeometry, railMaterial),
      new THREE.Mesh(longRailGeometry, railMaterial),
      new THREE.Mesh(shortRailGeometry, railMaterial),
      new THREE.Mesh(shortRailGeometry, railMaterial),
    ];
    rails[0].position.set(0, 0.28, -ARENA.halfDepth - 0.24);
    rails[1].position.set(0, 0.28, ARENA.halfDepth + 0.24);
    rails[2].position.set(-ARENA.halfWidth - 0.24, 0.28, 0);
    rails[3].position.set(ARENA.halfWidth + 0.24, 0.28, 0);
    for (const rail of rails) {
      rail.castShadow = true;
      rail.receiveShadow = true;
      arena.add(rail);
    }

    const markerMaterial = new THREE.MeshBasicMaterial({ color: '#f5ba49' });
    const markerGeometry = new THREE.RingGeometry(0.68, 0.72, 48);
    const centerMarker = new THREE.Mesh(markerGeometry, markerMaterial);
    centerMarker.rotation.x = -Math.PI / 2;
    centerMarker.position.y = 0.018;
    arena.add(centerMarker);

    return arena;
  }

  private createPickups(): void {
    const positions = [
      [-8, -4],
      [-3, -5],
      [3, -4.8],
      [8, -3],
      [-7.5, 3.5],
      [-1.5, 4.7],
      [4.5, 3.8],
      [8.2, 1.4],
    ];

    positions.forEach(([x, z], index) => {
      const pickup = new Pickup(index, new THREE.Vector3(x, 0.8, z));
      this.pickups.push(pickup);
      this.scene.add(pickup.group);
    });
  }

  private createFloorTexture(): THREE.CanvasTexture {
    const size = 256;
    const textureCanvas = document.createElement('canvas');
    textureCanvas.width = size;
    textureCanvas.height = size;
    const context = textureCanvas.getContext('2d');
    if (!context) throw new Error('Could not create floor texture context.');

    context.fillStyle = '#282a24';
    context.fillRect(0, 0, size, size);
    context.strokeStyle = 'rgba(246, 241, 223, 0.08)';
    context.lineWidth = 1;
    for (let i = 0; i <= size; i += 32) {
      context.beginPath();
      context.moveTo(i, 0);
      context.lineTo(i, size);
      context.moveTo(0, i);
      context.lineTo(size, i);
      context.stroke();
    }
    context.strokeStyle = 'rgba(245, 186, 73, 0.24)';
    context.lineWidth = 2;
    context.strokeRect(8, 8, size - 16, size - 16);

    const texture = new THREE.CanvasTexture(textureCanvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  private installTestHooks(): void {
    // Deterministic hooks consumed by tests/visual-regression.template.ts and
    // bot playtests. Keep these real when evolving the game: silent no-op hooks
    // produce flaky screenshot baselines.
    window.__THREE_GAME_TEST_HOOKS__ = {
      seed: (value: number) => {
        this.rng = createSeededRandom(value);
      },
      setState: (name: string) => {
        if (name === 'active-play') this.resetRun();
        else if (name === 'complete') this.completeRun();
        else console.warn(`Unknown test state: ${name}`);
      },
      setPausedForScreenshot: (paused: boolean) => {
        this.pausedForScreenshot = paused;
      },
      setReducedMotion: (enabled: boolean) => {
        this.reducedMotion = enabled;
      },
      hideDebugUi: (hidden: boolean) => {
        this.debugTools.setHidden(hidden);
      },
    };
  }

  private resetRun(): void {
    this.score = 0;
    this.elapsed = 0;
    this.complete = false;
    this.player.group.position.set(0, this.player.group.position.y, 0);
    this.player.velocity.set(0, 0, 0);
    for (const pickup of this.pickups) {
      pickup.reset();
      pickup.group.rotation.y = this.rng() * Math.PI * 2;
    }
    this.cameraRig.snapTo(this.player.group.position);
    this.hud.setTarget(this.pickups.length);
    this.hud.update(this.score, this.pickups.length, this.elapsed, this.complete);
  }

  private completeRun(): void {
    for (const pickup of this.pickups) {
      if (pickup.active) pickup.collect();
    }
    this.score = this.pickups.length;
    this.complete = true;
    this.hud.update(this.score, this.pickups.length, this.elapsed, this.complete);
  }

  private publishDiagnostics(): void {
    const info = this.renderer.info;
    window.__THREE_GAME_DIAGNOSTICS__ = {
      frame: this.frame,
      elapsed: this.elapsed,
      score: this.score,
      targetScore: this.pickups.length,
      complete: this.complete,
      player: {
        position: {
          x: this.player.group.position.x,
          y: this.player.group.position.y,
          z: this.player.group.position.z,
        },
        speed: this.player.velocity.length(),
      },
      renderer: {
        calls: info.render.calls,
        triangles: info.render.triangles,
        geometries: info.memory.geometries,
        textures: info.memory.textures,
      },
      canvas: {
        clientWidth: this.canvas.clientWidth,
        clientHeight: this.canvas.clientHeight,
        width: this.canvas.width,
        height: this.canvas.height,
        dpr: Math.min(window.devicePixelRatio || 1, this.tuning.maxDpr),
      },
    };
  }

  private getElement(selector: string): HTMLElement {
    const element = document.querySelector<HTMLElement>(selector);
    if (!element) throw new Error(`Missing element: ${selector}`);
    return element;
  }
}
