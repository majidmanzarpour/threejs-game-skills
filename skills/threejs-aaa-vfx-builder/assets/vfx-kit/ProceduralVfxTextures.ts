import * as THREE from 'three';

/**
 * Startup-baked seamless procedural VFX texture suite (4 shared GPU textures,
 * zero external image fetches). Call createVfxTextureAtlas() once and share across
 * all effects; call atlas.dispose() on scene teardown.
 */

function hash2(ix: number, iy: number, seed: number): number {
  let n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) | 0;
  n = Math.imul(n ^ (n >>> 13), 1274126177);
  n = n ^ (n >>> 16);
  return (n >>> 0) / 4294967295;
}

function periodicNoise(x: number, y: number, px: number, py: number, seed: number): number {
  const fx = Math.floor(x);
  const fy = Math.floor(y);
  const tx = x - fx;
  const ty = y - fy;
  const ux = tx * tx * (3 - 2 * tx);
  const uy = ty * ty * (3 - 2 * ty);

  const x0 = ((fx % px) + px) % px;
  const x1 = (x0 + 1) % px;
  const y0 = ((fy % py) + py) % py;
  const y1 = (y0 + 1) % py;

  const a = hash2(x0, y0, seed);
  const b = hash2(x1, y0, seed);
  const c = hash2(x0, y1, seed);
  const d = hash2(x1, y1, seed);

  return a + (b - a) * ux + (c - a) * uy + (a - b - c + d) * ux * uy;
}

function periodicFbm(
  u: number,
  v: number,
  basePx: number,
  basePy: number,
  octaves: number,
  seed: number,
): number {
  let sum = 0;
  let amp = 0.5;
  let norm = 0;
  let px = basePx;
  let py = basePy;
  for (let o = 0; o < octaves; o += 1) {
    sum += amp * periodicNoise(u * px, v * py, px, py, seed + o * 31);
    norm += amp;
    amp *= 0.5;
    px *= 2;
    py *= 2;
  }
  return sum / norm;
}

function periodicVoronoiEdge(u: number, v: number, px: number, py: number, seed: number): number {
  const x = u * px;
  const y = v * py;
  const ix = Math.floor(x);
  const iy = Math.floor(y);

  let d1 = 10;
  let d2 = 10;
  for (let oy = -1; oy <= 1; oy += 1) {
    for (let ox = -1; ox <= 1; ox += 1) {
      const cx = (((ix + ox) % px) + px) % px;
      const cy = (((iy + oy) % py) + py) % py;
      const rx = hash2(cx, cy, seed);
      const ry = hash2(cx, cy, seed + 17);
      const dx = ix + ox + rx - x;
      const dy = iy + oy + ry - y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < d1) {
        d2 = d1;
        d1 = dist;
      } else if (dist < d2) {
        d2 = dist;
      }
    }
  }
  return Math.max(0, Math.min(1, 1.0 - (d2 - d1) * 2.5));
}

function finalizeDataTexture(
  data: Uint8Array,
  size: number,
  wrap: THREE.Wrapping,
): THREE.DataTexture {
  const tex = new THREE.DataTexture(data, size, size, THREE.RGBAFormat);
  tex.wrapS = wrap;
  tex.wrapT = wrap;
  tex.magFilter = THREE.LinearFilter;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.generateMipmaps = true;
  tex.needsUpdate = true;
  return tex;
}

/**
 * Seamless 4-channel stylized VFX noise atlas:
 *  R = Domain-warped organic FBM (erosion, vortex wisps, plasma)
 *  G = 4:1 anisotropic painterly brushstroke streaks
 *  B = 8:1 crisp calligraphy / energy shred streaks
 *  A = Seamless Voronoi caustic ridges (domes, cracks, shields)
 */
export function createVfxNoiseAtlas(size = 320): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const v = y / size;
    for (let x = 0; x < size; x += 1) {
      const u = x / size;
      const wx = periodicFbm(u, v, 4, 4, 3, 11) - 0.5;
      const wy = periodicFbm(u, v, 4, 4, 3, 29) - 0.5;

      const rVal = periodicFbm(u + wx * 0.26, v + wy * 0.26, 5, 5, 4, 47);
      const gWarp = (periodicFbm(u, v, 3, 8, 2, 71) - 0.5) * 0.15;
      const gVal = periodicFbm(u + gWarp * 0.4, v + gWarp * 0.15, 3, 14, 4, 103);
      const bRaw = periodicFbm(u, v + wy * 0.08, 4, 24, 3, 157);
      const bVal = Math.max(0, Math.min(1, (bRaw - 0.27) * 2.15));
      const aVal = periodicVoronoiEdge(u + wx * 0.08, v + wy * 0.08, 7, 7, 211);

      const idx = (y * size + x) * 4;
      data[idx] = Math.round(rVal * 255);
      data[idx + 1] = Math.round(gVal * 255);
      data[idx + 2] = Math.round(bVal * 255);
      data[idx + 3] = Math.round(aVal * 255);
    }
  }
  return finalizeDataTexture(data, size, THREE.RepeatWrapping);
}

/**
 * Seamless divergence-free 2D curl-noise flowmap for 2-phase UV advection:
 *  RG = Signed velocity (dPsi/dy, -dPsi/dx) packed into [0..1]
 *  B  = Curl magnitude
 *  A  = Stream-function scalar
 */
export function createFlowmapTexture(size = 256): THREE.DataTexture {
  const psi = new Float32Array(size * size);
  for (let y = 0; y < size; y += 1) {
    const v = y / size;
    for (let x = 0; x < size; x += 1) {
      psi[y * size + x] = periodicFbm(x / size, v, 4, 4, 4, 521);
    }
  }

  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const ym = (y - 1 + size) % size;
    const yp = (y + 1) % size;
    for (let x = 0; x < size; x += 1) {
      const xm = (x - 1 + size) % size;
      const xp = (x + 1) % size;
      const dPsiDx = (psi[y * size + xp] - psi[y * size + xm]) * size * 0.14;
      const dPsiDy = (psi[yp * size + x] - psi[ym * size + x]) * size * 0.14;

      const vx = Math.max(-1, Math.min(1, dPsiDy));
      const vy = Math.max(-1, Math.min(1, -dPsiDx));
      const mag = Math.min(1, Math.sqrt(vx * vx + vy * vy));

      const idx = (y * size + x) * 4;
      data[idx] = Math.round((vx * 0.5 + 0.5) * 255);
      data[idx + 1] = Math.round((vy * 0.5 + 0.5) * 255);
      data[idx + 2] = Math.round(mag * 255);
      data[idx + 3] = Math.round(psi[y * size + x] * 255);
    }
  }
  return finalizeDataTexture(data, size, THREE.RepeatWrapping);
}

/**
 * Stylized painterly smoke puff texture:
 *  R = Top-lit directional shading
 *  G = Coarse billow FBM
 *  B = Fine erosion detail
 *  A = Soft radial silhouette mask
 */
export function createSmokePuffTexture(size = 256): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const ny = (y / size) * 2 - 1;
    const v = y / size;
    for (let x = 0; x < size; x += 1) {
      const nx = (x / size) * 2 - 1;
      const r = Math.sqrt(nx * nx + ny * ny);
      const u = x / size;

      const fbm = periodicFbm(u, v, 4, 4, 4, 313);
      const fbmFine = periodicFbm(u, v, 8, 8, 3, 409);

      const shape = Math.max(0, Math.min(1, (1.0 - r) * 1.18 + (fbm - 0.48) * 0.68));
      const topLit = Math.max(0, Math.min(1, 0.38 + (0.5 - ny * 0.48) * 0.48 + (fbmFine - 0.5) * 0.42));

      const idx = (y * size + x) * 4;
      data[idx] = Math.round(topLit * 255);
      data[idx + 1] = Math.round(fbm * 255);
      data[idx + 2] = Math.round(fbmFine * 255);
      data[idx + 3] = Math.round(shape * 255);
    }
  }
  return finalizeDataTexture(data, size, THREE.ClampToEdgeWrapping);
}

/**
 * Crisp 4-point concave diamond/star glint texture for sparks, embers, and motes.
 */
export function createStarGlintTexture(size = 128): THREE.DataTexture {
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const ny = ((y + 0.5) / size) * 2 - 1;
    for (let x = 0; x < size; x += 1) {
      const nx = ((x + 0.5) / size) * 2 - 1;
      const r = Math.sqrt(nx * nx + ny * ny);
      const ax = Math.abs(nx);
      const ay = Math.abs(ny);

      const core = Math.exp(-r * r * 28.0);
      const spikeX = Math.exp(-ay * 18.0) * Math.max(0, 1.0 - ax * 1.04);
      const spikeY = Math.exp(-ax * 18.0) * Math.max(0, 1.0 - ay * 1.04);
      const spikes = Math.pow(Math.max(0.0001, Math.max(spikeX, spikeY)), 1.35) * 0.92;
      const halo = Math.exp(-r * r * 6.5) * 0.32 * Math.max(0, 1.0 - r);
      const edgeFade = Math.max(0, Math.min(1, (1.0 - r) * 4.5));

      const intensity = Math.max(0, Math.min(1, (core + spikes + halo) * edgeFade));
      const val = Math.round(intensity * 255);

      const idx = (y * size + x) * 4;
      data[idx] = val;
      data[idx + 1] = val;
      data[idx + 2] = val;
      data[idx + 3] = val;
    }
  }
  return finalizeDataTexture(data, size, THREE.ClampToEdgeWrapping);
}

export interface VfxTextureAtlas {
  noise: THREE.DataTexture;
  flowmap: THREE.DataTexture;
  smokePuff: THREE.DataTexture;
  starGlint: THREE.DataTexture;
  dispose: () => void;
}

export function createVfxTextureAtlas(mobile = false): VfxTextureAtlas {
  const noise = createVfxNoiseAtlas(mobile ? 256 : 320);
  const flowmap = createFlowmapTexture(mobile ? 192 : 256);
  const smokePuff = createSmokePuffTexture(mobile ? 192 : 256);
  const starGlint = createStarGlintTexture(128);
  return {
    noise,
    flowmap,
    smokePuff,
    starGlint,
    dispose() {
      noise.dispose();
      flowmap.dispose();
      smokePuff.dispose();
      starGlint.dispose();
    },
  };
}
