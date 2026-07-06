import * as THREE from 'three';

export class Pickup {
  readonly group = new THREE.Group();
  readonly radius = 0.62;
  active = true;

  private readonly coreGeometry = new THREE.IcosahedronGeometry(0.42, 1);
  private readonly ringGeometry = new THREE.TorusGeometry(0.58, 0.028, 8, 32);
  private readonly coreMaterial = new THREE.MeshStandardMaterial({
    color: '#48baa7',
    emissive: '#0f5249',
    emissiveIntensity: 0.8,
    roughness: 0.28,
    metalness: 0.1,
  });
  private readonly ringMaterial = new THREE.MeshBasicMaterial({
    color: '#f6f1df',
  });

  constructor(
    readonly index: number,
    position: THREE.Vector3,
  ) {
    const core = new THREE.Mesh(this.coreGeometry, this.coreMaterial);
    core.castShadow = true;
    this.group.add(core);

    const ring = new THREE.Mesh(this.ringGeometry, this.ringMaterial);
    ring.rotation.x = Math.PI / 2;
    this.group.add(ring);

    this.group.position.copy(position);
  }

  update(delta: number, elapsed: number): void {
    if (!this.active) return;
    this.group.rotation.y += delta * 1.8;
    this.group.children[0].rotation.x -= delta * 1.2;
    this.group.position.y = 0.78 + Math.sin(elapsed * 2.6 + this.index) * 0.16;
  }

  collect(): void {
    this.active = false;
    this.group.visible = false;
  }

  reset(): void {
    this.active = true;
    this.group.visible = true;
  }

  dispose(): void {
    this.coreGeometry.dispose();
    this.ringGeometry.dispose();
    this.coreMaterial.dispose();
    this.ringMaterial.dispose();
  }
}
