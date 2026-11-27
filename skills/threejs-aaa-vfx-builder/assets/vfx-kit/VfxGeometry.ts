import * as THREE from 'three';
import { createSeededRng } from './VfxTimeline';

/**
 * Parametric, motion-aligned VFX geometries and zero-allocation dynamic
 * camera-facing strips (fractal lightning & ring-buffer weapon/socket trails).
 */

/**
 * Polar-mapped flat or cupped disc/ring.
 * U = normalized angle [0..1] (seamless), V = normalized radius [0..1].
 */
export function createPolarRingGeometry(
  innerR: number,
  outerR: number,
  thetaSegs = 96,
  radSegs = 12,
  cupHeight = 0,
): THREE.BufferGeometry {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let ir = 0; ir <= radSegs; ir += 1) {
    const v = ir / radSegs;
    const r = innerR + (outerR - innerR) * v;
    const y = cupHeight * v * v;
    for (let it = 0; it <= thetaSegs; it += 1) {
      const u = it / thetaSegs;
      const ang = u * Math.PI * 2;
      positions.push(Math.cos(ang) * r, y, Math.sin(ang) * r);
      uvs.push(u, v);
    }
  }

  const stride = thetaSegs + 1;
  for (let ir = 0; ir < radSegs; ir += 1) {
    for (let it = 0; it < thetaSegs; it += 1) {
      const a = ir * stride + it;
      const b = a + 1;
      const c = (ir + 1) * stride + it;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

export interface ArcRibbonOptions {
  radiusStart?: number;
  radiusEnd?: number;
  width?: number;
  arcAngle?: number;
  yStart?: number;
  yEnd?: number;
  yArch?: number;
  bankAngle?: number;
  bankTwist?: number;
  segsU?: number;
  segsV?: number;
  widthTaper?: number;
}

/**
 * Sweeping 3D slash / helical energy ribbon with calligraphic width tapering and banking.
 * U runs [0..1] along arc length; V runs [0..1] across width.
 */
export function createArcRibbonGeometry({
  radiusStart = 2.0,
  radiusEnd = 2.0,
  width = 0.55,
  arcAngle = Math.PI * 1.65,
  yStart = 0.0,
  yEnd = 0.0,
  yArch = 0.0,
  bankAngle = 0.35,
  bankTwist = 0.0,
  segsU = 72,
  segsV = 4,
  widthTaper = 0.55,
}: ArcRibbonOptions = {}): THREE.BufferGeometry {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let iu = 0; iu <= segsU; iu += 1) {
    const u = iu / segsU;
    const theta = u * arcAngle;
    const r = radiusStart + (radiusEnd - radiusStart) * u;
    const cy = yStart + (yEnd - yStart) * u + Math.sin(u * Math.PI) * yArch;
    const cx = Math.cos(theta) * r;
    const cz = Math.sin(theta) * r;

    const radX = Math.cos(theta);
    const radZ = Math.sin(theta);
    const taper = 1.0 - widthTaper * Math.pow(Math.abs(u * 2.0 - 1.0), 2.2);
    const halfW = width * 0.5 * taper;

    const bank = bankAngle + bankTwist * (u - 0.5);
    const cosB = Math.cos(bank);
    const sinB = Math.sin(bank);
    const dirX = radX * cosB;
    const dirY = sinB;
    const dirZ = radZ * cosB;

    for (let iv = 0; iv <= segsV; iv += 1) {
      const v = iv / segsV;
      const offset = (v - 0.5) * 2.0 * halfW;
      positions.push(cx + dirX * offset, cy + dirY * offset, cz + dirZ * offset);
      uvs.push(u, v);
    }
  }

  const stride = segsV + 1;
  for (let iu = 0; iu < segsU; iu += 1) {
    for (let iv = 0; iv < segsV; iv += 1) {
      const a = iu * stride + iv;
      const b = a + 1;
      const c = (iu + 1) * stride + iv;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

/**
 * Conically flared shockwave ring oriented perpendicular to +Z (muzzle/thruster axis).
 */
export function createMuzzleRingGeometry(
  radius = 1.0,
  width = 0.42,
  arcAngle = Math.PI * 1.85,
  segsU = 64,
): THREE.BufferGeometry {
  const geo = createArcRibbonGeometry({
    radiusStart: radius,
    radiusEnd: radius * 1.04,
    width,
    arcAngle,
    bankAngle: 0.95,
    segsU,
    segsV: 3,
    widthTaper: 0.72,
  });
  geo.rotateX(Math.PI / 2);
  return geo;
}

/**
 * Open-bottom cupola energy dome with slight base flare for depth-softened contact rims.
 */
export function createEnergyDomeGeometry(
  radius = 3.5,
  segsW = 64,
  segsH = 32,
): THREE.BufferGeometry {
  const positions: number[] = [];
  const normals: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let ih = 0; ih <= segsH; ih += 1) {
    const v = ih / segsH;
    const phi = (1.0 - v) * (Math.PI * 0.495);
    const sinP = Math.sin(phi);
    const cosP = Math.cos(phi);
    const r = radius * (sinP * (1.0 + 0.05 * Math.pow(1.0 - v, 3.0)));
    const y = radius * 0.98 * cosP;

    for (let iw = 0; iw <= segsW; iw += 1) {
      const u = iw / segsW;
      const theta = u * Math.PI * 2;
      const cosT = Math.cos(theta);
      const sinT = Math.sin(theta);

      positions.push(cosT * r, y, sinT * r);
      normals.push(cosT * sinP, cosP, sinT * sinP);
      uvs.push(u, v);
    }
  }

  const stride = segsW + 1;
  for (let ih = 0; ih < segsH; ih += 1) {
    for (let iw = 0; iw < segsW; iw += 1) {
      const a = ih * stride + iw;
      const b = a + 1;
      const c = (ih + 1) * stride + iw;
      const d = c + 1;
      indices.push(a, b, c, b, d, c);
    }
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  return geo;
}

/**
 * Tapered open cylinder oriented from z=0 to z=+length for lasers, lances, and railguns.
 */
export function createBeamGeometry(
  length = 1.0,
  radiusStart = 0.09,
  radiusEnd = 0.16,
  radialSegs = 16,
  heightSegs = 20,
): THREE.BufferGeometry {
  const geo = new THREE.CylinderGeometry(radiusEnd, radiusStart, length, radialSegs, heightSegs, true);
  geo.rotateX(Math.PI / 2);
  geo.translate(0, 0, length * 0.5);
  return geo;
}

/**
 * Twisting 3D helical energy ribbon wrapping around a beam along +Z.
 */
export function createBeamHelixGeometry(
  length = 1.0,
  radius = 0.24,
  turns = 3.2,
  width = 0.14,
  segsU = 64,
): THREE.BufferGeometry {
  const positions: number[] = [];
  const uvs: number[] = [];
  const indices: number[] = [];

  for (let iu = 0; iu <= segsU; iu += 1) {
    const u = iu / segsU;
    const z = u * length;
    const ang = u * Math.PI * 2 * turns;
    const r = radius * (0.45 + 0.75 * Math.sin(u * Math.PI));
    const cx = Math.cos(ang) * r;
    const cy = Math.sin(ang) * r;
    const nx = Math.cos(ang);
    const ny = Math.sin(ang);
    const hw = width * 0.5 * Math.sin(u * Math.PI);

    positions.push(cx - nx * hw, cy - ny * hw, z);
    uvs.push(u, 0);
    positions.push(cx + nx * hw, cy + ny * hw, z);
    uvs.push(u, 1);
  }

  for (let iu = 0; iu < segsU; iu += 1) {
    const a = iu * 2;
    indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geo.setIndex(indices);
  geo.computeVertexNormals();
  return geo;
}

/**
 * Flat-shaded razor shard geometry for crystal shatters, glass bursts, and sparks.
 */
export function createShardGeometry(): THREE.BufferGeometry {
  const geo = new THREE.OctahedronGeometry(0.5, 0);
  geo.scale(0.38, 1.0, 0.22);
  const flat = geo.toNonIndexed();
  geo.dispose();
  flat.computeVertexNormals();
  return flat;
}

/**
 * Flat-shaded rugged angular rock/debris chunk geometry for impacts and orbiters.
 */
export function createDebrisChunkGeometry(): THREE.BufferGeometry {
  const geo = new THREE.DodecahedronGeometry(0.45, 0);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i += 1) {
    const x = pos.getX(i);
    const y = pos.getY(i);
    const z = pos.getZ(i);
    const n = 0.78 + 0.34 * Math.abs(Math.sin(x * 7.3 + y * 11.1 + z * 5.7));
    pos.setXYZ(i, x * n * 1.15, y * n * 0.62, z * n * 0.95);
  }
  const flat = geo.toNonIndexed();
  geo.dispose();
  flat.computeVertexNormals();
  return flat;
}

export interface LightningUpdateOptions {
  cameraPos: THREE.Vector3;
  seed?: number;
  jitter?: number;
  widthStart?: number;
  widthEnd?: number;
  archY?: number;
}

export interface DynamicLightningStrip {
  mesh: THREE.Mesh;
  update: (start: THREE.Vector3, end: THREE.Vector3, opts: LightningUpdateOptions) => void;
  dispose: () => void;
}

/**
 * Zero-allocation camera-facing jagged fractal lightning ribbon strip.
 * Pass quantized time `Math.floor(t * 24)` into `seed` for crisp 24fps stepped arcs.
 */
export function createLightningStrip(
  segments = 20,
  material: THREE.Material,
): DynamicLightningStrip {
  const vertCount = (segments + 1) * 2;
  const positions = new Float32Array(vertCount * 3);
  const uvs = new Float32Array(vertCount * 2);
  const indices: number[] = [];

  for (let i = 0; i <= segments; i += 1) {
    const u = i / segments;
    uvs[i * 4 + 0] = u;
    uvs[i * 4 + 1] = 0;
    uvs[i * 4 + 2] = u;
    uvs[i * 4 + 3] = 1;
    if (i < segments) {
      const a = i * 2;
      indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  }

  const geo = new THREE.BufferGeometry();
  const posAttr = new THREE.BufferAttribute(positions, 3);
  posAttr.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute('position', posAttr);
  geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geo.setIndex(indices);

  const mesh = new THREE.Mesh(geo, material);
  mesh.frustumCulled = false;

  const pts = Array.from({ length: segments + 1 }, () => new THREE.Vector3());
  const tmpDir = new THREE.Vector3();
  const tmpRight = new THREE.Vector3();
  const tmpUp = new THREE.Vector3();
  const tmpSeg = new THREE.Vector3();
  const tmpToCam = new THREE.Vector3();
  const tmpSide = new THREE.Vector3();

  function update(
    start: THREE.Vector3,
    end: THREE.Vector3,
    {
      cameraPos,
      seed = 1,
      jitter = 0.55,
      widthStart = 0.14,
      widthEnd = 0.04,
      archY = 0.0,
    }: LightningUpdateOptions,
  ): void {
    tmpDir.subVectors(end, start);
    const len = tmpDir.length();
    if (len < 1e-4) {
      mesh.visible = false;
      return;
    }
    mesh.visible = true;
    tmpDir.divideScalar(len);

    if (Math.abs(tmpDir.y) < 0.92) {
      tmpRight.set(0, 1, 0).cross(tmpDir).normalize();
    } else {
      tmpRight.set(1, 0, 0).cross(tmpDir).normalize();
    }
    tmpUp.crossVectors(tmpDir, tmpRight).normalize();

    const rng = createSeededRng(seed);
    let driftR = 0;
    let driftU = 0;

    for (let i = 0; i <= segments; i += 1) {
      const u = i / segments;
      const env = Math.sin(u * Math.PI);
      if (i > 0 && i < segments) {
        driftR = driftR * 0.45 + (rng() - 0.5) * 2.0 * jitter;
        driftU = driftU * 0.45 + (rng() - 0.5) * 2.0 * jitter;
      } else {
        driftR = 0;
        driftU = 0;
      }
      pts[i]
        .lerpVectors(start, end, u)
        .addScaledVector(tmpRight, driftR * env)
        .addScaledVector(tmpUp, driftU * env);
      pts[i].y += archY * env;
    }

    for (let i = 0; i <= segments; i += 1) {
      const u = i / segments;
      const p = pts[i];
      if (i < segments) tmpSeg.subVectors(pts[i + 1], p);
      else tmpSeg.subVectors(p, pts[i - 1]);
      if (tmpSeg.lengthSq() < 1e-8) tmpSeg.copy(tmpDir);
      else tmpSeg.normalize();

      tmpToCam.subVectors(cameraPos, p);
      if (tmpToCam.lengthSq() < 1e-8) tmpToCam.set(0, 1, 0);
      else tmpToCam.normalize();

      tmpSide.crossVectors(tmpSeg, tmpToCam);
      if (tmpSide.lengthSq() < 1e-8) tmpSide.copy(tmpRight);
      else tmpSide.normalize();

      const hw = (widthStart + (widthEnd - widthStart) * u) * 0.5;
      const v0 = i * 6;
      positions[v0 + 0] = p.x - tmpSide.x * hw;
      positions[v0 + 1] = p.y - tmpSide.y * hw;
      positions[v0 + 2] = p.z - tmpSide.z * hw;
      positions[v0 + 3] = p.x + tmpSide.x * hw;
      positions[v0 + 4] = p.y + tmpSide.y * hw;
      positions[v0 + 5] = p.z + tmpSide.z * hw;
    }
    posAttr.needsUpdate = true;
  }

  return {
    mesh,
    update,
    dispose() {
      geo.dispose();
    },
  };
}

export interface DynamicRibbonTrail {
  mesh: THREE.Mesh;
  reset: (origin: THREE.Vector3) => void;
  push: (headPos: THREE.Vector3, cameraPos: THREE.Vector3, headWidth?: number) => void;
  dispose: () => void;
}

/**
 * Zero-allocation camera-facing ring-buffer trail for weapon swings, hands, missiles, and thrusters.
 * Call reset(origin) on teleport, respawn, or timeline scrub jumps to prevent stretching.
 */
export function createRibbonTrail(
  maxPoints = 20,
  material: THREE.Material,
): DynamicRibbonTrail {
  const count = Math.max(4, maxPoints);
  const positions = new Float32Array(count * 2 * 3);
  const uvs = new Float32Array(count * 2 * 2);
  const indices: number[] = [];

  for (let i = 0; i < count; i += 1) {
    const u = i / (count - 1);
    uvs[i * 4 + 0] = u;
    uvs[i * 4 + 1] = 0;
    uvs[i * 4 + 2] = u;
    uvs[i * 4 + 3] = 1;
    if (i < count - 1) {
      const a = i * 2;
      indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  }

  const geo = new THREE.BufferGeometry();
  const posAttr = new THREE.BufferAttribute(positions, 3);
  posAttr.setUsage(THREE.DynamicDrawUsage);
  geo.setAttribute('position', posAttr);
  geo.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geo.setIndex(indices);

  const mesh = new THREE.Mesh(geo, material);
  mesh.frustumCulled = false;

  const history = Array.from({ length: count }, () => new THREE.Vector3());
  const tmpTan = new THREE.Vector3();
  const tmpToCam = new THREE.Vector3();
  const tmpSide = new THREE.Vector3();

  function reset(origin: THREE.Vector3): void {
    for (let i = 0; i < count; i += 1) history[i].copy(origin);
    for (let i = 0; i < count; i += 1) {
      const idx = i * 6;
      positions[idx + 0] = origin.x;
      positions[idx + 1] = origin.y;
      positions[idx + 2] = origin.z;
      positions[idx + 3] = origin.x;
      positions[idx + 4] = origin.y;
      positions[idx + 5] = origin.z;
    }
    posAttr.needsUpdate = true;
  }

  function push(headPos: THREE.Vector3, cameraPos: THREE.Vector3, headWidth = 0.22): void {
    for (let i = count - 1; i > 0; i -= 1) {
      history[i].copy(history[i - 1]);
    }
    history[0].copy(headPos);

    for (let i = 0; i < count; i += 1) {
      const u = i / (count - 1);
      const p = history[i];
      if (i === 0) tmpTan.subVectors(history[0], history[1]);
      else if (i === count - 1) tmpTan.subVectors(history[count - 2], history[count - 1]);
      else tmpTan.subVectors(history[i - 1], history[i + 1]);

      if (tmpTan.lengthSq() < 1e-8) tmpTan.set(0, 1, 0);
      else tmpTan.normalize();

      tmpToCam.subVectors(cameraPos, p);
      if (tmpToCam.lengthSq() < 1e-8) tmpToCam.set(0, 0, 1);
      else tmpToCam.normalize();

      tmpSide.crossVectors(tmpTan, tmpToCam);
      if (tmpSide.lengthSq() < 1e-8) tmpSide.set(1, 0, 0);
      else tmpSide.normalize();

      const hw = headWidth * 0.5 * (1.0 - u);
      const idx = i * 6;
      positions[idx + 0] = p.x - tmpSide.x * hw;
      positions[idx + 1] = p.y - tmpSide.y * hw;
      positions[idx + 2] = p.z - tmpSide.z * hw;
      positions[idx + 3] = p.x + tmpSide.x * hw;
      positions[idx + 4] = p.y + tmpSide.y * hw;
      positions[idx + 5] = p.z + tmpSide.z * hw;
    }
    posAttr.needsUpdate = true;
  }

  return {
    mesh,
    reset,
    push,
    dispose() {
      geo.dispose();
    },
  };
}
