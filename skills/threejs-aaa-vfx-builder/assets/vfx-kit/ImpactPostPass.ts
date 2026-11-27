import * as THREE from 'three';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';

/**
 * Unified Optical VFX Post-Processing Pass (place AFTER OutputPass).
 * Includes an early-out dormant fast-path when all effect intensities are 0.
 *
 * Capabilities:
 *  - Expanding radial optical shockwave refraction + chromatic fringe
 *  - Localized thermal heat-haze shimmer
 *  - Spherical lens refraction (shields / stasis bubbles)
 *  - Einstein-ring gravitational lensing + event horizon
 *  - 5 bespoke 1-3 frame anime/graphic impact modes (disable when reducedMotion=true):
 *      0 = Shattered Clockwork / Radial Dial
 *      1 = Diagonal Dimension-Cut Slash Inversion
 *      2 = Pitch-Black Solar Eclipse Corona
 *      3 = Shattered Voronoi Crystal Fracture
 *      4 = High-Voltage Inverted RGB Scan-Glitch
 */

export const ImpactPostShader = {
  uniforms: {
    tDiffuse: { value: null as THREE.Texture | null },
    uTime: { value: 0 },
    uAspect: { value: 16 / 9 },
    uTargetUV: { value: new THREE.Vector2(0.5, 0.5) },
    uImpactFrame: { value: 0 },
    uImpactMode: { value: 0 },
    uImpactAngle: { value: -0.45 },
    uColorWash: { value: 0 },
    uWashColorA: { value: new THREE.Color('#20e0c0') },
    uWashColorB: { value: new THREE.Color('#f6f8b0') },
    uChroma: { value: 0 },
    uFlash: { value: 0 },
    uShockwaveProgress: { value: 0 },
    uShockwaveStrength: { value: 0 },
    uHeatHaze: { value: 0 },
    uBubbleDistort: { value: 0 },
    uBubbleRadius: { value: 0.28 },
    uBlackHoleMass: { value: 0 },
    uBlackHoleRadius: { value: 0.14 },
  },
  vertexShader: /* glsl */ `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: /* glsl */ `
    uniform sampler2D tDiffuse;
    uniform float uTime;
    uniform float uAspect;
    uniform vec2 uTargetUV;
    uniform float uImpactFrame;
    uniform float uImpactMode;
    uniform float uImpactAngle;
    uniform float uColorWash;
    uniform vec3 uWashColorA;
    uniform vec3 uWashColorB;
    uniform float uChroma;
    uniform float uFlash;
    uniform float uShockwaveProgress;
    uniform float uShockwaveStrength;
    uniform float uHeatHaze;
    uniform float uBubbleDistort;
    uniform float uBubbleRadius;
    uniform float uBlackHoleMass;
    uniform float uBlackHoleRadius;
    varying vec2 vUv;

    float sq(float x) {
      return x * x;
    }

    float hash11(float p) {
      p = fract(p * 0.1031);
      p *= p + 33.33;
      p *= p + p;
      return fract(p);
    }

    vec2 hash22(vec2 p) {
      p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
      return fract(sin(p) * 43758.5453);
    }

    float angularNoise(float ang, float freq, float seed) {
      float x = (ang / 6.2831853 + 0.5) * freq;
      float i = floor(x);
      float f = fract(x);
      float u = f * f * (3.0 - 2.0 * f);
      float a = hash11(mod(i, freq) + seed * 37.0);
      float b = hash11(mod(i + 1.0, freq) + seed * 37.0);
      return mix(a, b, u);
    }

    float voronoiCrack(vec2 x) {
      vec2 n = floor(x);
      vec2 f = fract(x);
      float md = 8.0;
      vec2 mr = vec2(0.0);
      for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
          vec2 g = vec2(float(i), float(j));
          vec2 r = g + hash22(n + g) - f;
          float d = dot(r, r);
          if (d < md) {
            md = d;
            mr = r;
          }
        }
      }
      md = 8.0;
      for (int j = -1; j <= 1; j++) {
        for (int i = -1; i <= 1; i++) {
          vec2 g = vec2(float(i), float(j));
          vec2 r = g + hash22(n + g) - f;
          if (dot(mr - r, mr - r) > 0.0001) {
            md = min(md, dot(0.5 * (mr + r), normalize(r - mr)));
          }
        }
      }
      return md;
    }

    float speedLines(float ang, float r, float seed) {
      float l1 = angularNoise(ang, 160.0, 2.0 + seed);
      float l2 = angularNoise(ang, 320.0, 8.0 + seed);
      float base = clamp(l1 * 0.5 + l2 * 0.65, 0.0, 1.0);
      return pow(max(0.0001, base), 3.0) * smoothstep(0.12, 0.36, r);
    }

    void main() {
      // Dormant fast-path: single texture fetch when no optical VFX are active
      float activeSum = uImpactFrame + uColorWash + uChroma + uFlash +
                        uShockwaveStrength + uHeatHaze + uBubbleDistort + uBlackHoleMass;
      if (activeSum <= 0.001) {
        gl_FragColor = texture2D(tDiffuse, vUv);
        return;
      }

      vec2 uv = vUv;
      vec2 toTarget = uv - uTargetUV;
      vec2 toAspect = vec2(toTarget.x * uAspect, toTarget.y);
      float r = length(toAspect);
      float ang = atan(toAspect.y, toAspect.x);
      vec2 radDir = (r > 1e-4) ? (toTarget / max(length(toTarget), 1e-4)) : vec2(0.0);

      // 1. Expanding radial optical shockwave refraction
      float shockCa = 0.0;
      if (uShockwaveStrength > 0.001 && uShockwaveProgress > 0.001 && uShockwaveProgress < 0.999) {
        float waveR = uShockwaveProgress * 1.15;
        float distWave = r - waveR;
        float bandArg = distWave / 0.065;
        float waveBand = exp(-(bandArg * bandArg));
        float fadeWave = (1.0 - uShockwaveProgress) * uShockwaveStrength;
        uv += radDir * sin(distWave * 42.0) * waveBand * 0.024 * fadeWave;
        shockCa = waveBand * fadeWave * 0.014;
      }

      // 2. Localized thermal heat-haze shimmer
      if (uHeatHaze > 0.001) {
        float heatMask = exp(-r * r * 5.2) * uHeatHaze;
        float hX = sin(uv.y * 58.0 - uTime * 14.0 + uv.x * 16.0);
        float hY = cos(uv.x * 46.0 - uTime * 11.5);
        uv += vec2(hX, hY) * 0.0038 * heatMask;
      }

      // 3. Spherical lens refraction (shields / stasis bubbles)
      if (uBubbleDistort > 0.001 && r < uBubbleRadius * 1.08) {
        float normR = clamp(r / max(uBubbleRadius, 0.001), 0.0, 1.0);
        float lens = sin(normR * 3.14159265);
        uv -= toTarget * (lens * lens * 0.048 * uBubbleDistort * (1.0 + 0.45 * normR));
      }

      // 4. Einstein-ring gravitational lensing
      float bhPhoton = 0.0;
      float bhCoreMask = 0.0;
      if (uBlackHoleMass > 0.001) {
        float rs = max(uBlackHoleRadius, 0.02);
        float outside = smoothstep(rs * 0.72, rs * 1.08, r);
        float bend = (rs * rs * 1.65 * uBlackHoleMass) / max(r * r + rs * 0.25, 0.004);
        uv -= radDir * min(bend, 0.22) * outside;
        float ringArg = (r - rs * 1.06) / max(rs * 0.16, 0.005);
        bhPhoton = exp(-(ringArg * ringArg)) * uBlackHoleMass;
        bhCoreMask = (1.0 - smoothstep(rs * 0.68, rs * 0.96, r)) * uBlackHoleMass;
      }

      // Sample scene with optional radial chromatic aberration
      float totalCa = uChroma + shockCa;
      vec3 col;
      if (totalCa > 0.0005) {
        vec2 caOff = radDir * totalCa;
        col.r = texture2D(tDiffuse, clamp(uv + caOff, 0.001, 0.999)).r;
        col.g = texture2D(tDiffuse, clamp(uv, 0.001, 0.999)).g;
        col.b = texture2D(tDiffuse, clamp(uv - caOff, 0.001, 0.999)).b;
      } else {
        col = texture2D(tDiffuse, clamp(uv, 0.001, 0.999)).rgb;
      }

      if (bhCoreMask > 0.001) col *= (1.0 - clamp(bhCoreMask, 0.0, 1.0));
      if (bhPhoton > 0.001) col += mix(uWashColorA, uWashColorB, 0.5) * bhPhoton * 1.65;

      // 5. Color wash & brief radial flash
      if (uColorWash > 0.001) {
        vec3 wash = mix(uWashColorA, uWashColorB, smoothstep(0.1, 0.9, vUv.x + vUv.y * 0.35));
        col = mix(col, col * wash * 1.35 + wash * 0.14, clamp(uColorWash, 0.0, 0.85));
      }
      if (uFlash > 0.001) {
        float radialFlash = exp(-r * r * 2.2) * uFlash;
        col += mix(uWashColorB, vec3(1.0), 0.6) * radialFlash * 0.85;
      }

      // 6. Bespoke 1-3 frame anime/graphic impact frames
      if (uImpactFrame > 0.001) {
        float lum = dot(col, vec3(0.299, 0.587, 0.114));
        float lines = speedLines(ang, r, floor(uImpactMode + 0.5));
        vec3 impactCol = col;

        if (uImpactMode < 0.5) {
          // Mode 0: Shattered clockwork dial inversion
          float dial = exp(-sq((r - 0.34) * 42.0)) + exp(-sq((r - 0.44) * 34.0));
          float ticks = smoothstep(0.94, 0.99, cos(ang * 12.0)) * smoothstep(0.32, 0.36, r) * (1.0 - smoothstep(0.42, 0.46, r));
          float ink = step(0.38, 1.0 - lum);
          impactCol = mix(vec3(0.03, 0.04, 0.06), uWashColorB, ink) + uWashColorA * (dial + ticks + lines * 0.9);
        } else if (uImpactMode < 1.5) {
          // Mode 1: Diagonal dimension-cut slash inversion
          float ca = cos(uImpactAngle), sa = sin(uImpactAngle);
          vec2 rot = vec2(toAspect.x * ca - toAspect.y * sa, toAspect.x * sa + toAspect.y * ca);
          float cut = exp(-abs(rot.y) * 55.0);
          float sideInvert = step(0.0, rot.y);
          vec3 hi = mix(vec3(0.04, 0.01, 0.02), uWashColorA, step(0.32, lum));
          impactCol = mix(hi, 1.0 - hi, sideInvert * 0.78) + vec3(1.0) * cut * 1.8 + uWashColorB * lines * 0.8;
        } else if (uImpactMode < 2.5) {
          // Mode 2: Pitch-black solar eclipse corona
          float sun = 1.0 - smoothstep(0.18, 0.21, r);
          float corona = exp(-sq((r - 0.22) * 18.0)) * (1.2 + lines * 2.2);
          impactCol = mix(vec3(0.02, 0.015, 0.03), uWashColorA * 1.4, corona + lines * 0.7) * (1.0 - sun);
        } else if (uImpactMode < 3.5) {
          // Mode 3: Shattered Voronoi crystal fracture
          float crack = 1.0 - smoothstep(0.01, 0.06, voronoiCrack(toAspect * 6.5));
          impactCol = mix(vec3(0.03, 0.07, 0.14), uWashColorA, step(0.42, lum)) +
                      mix(uWashColorB, vec3(1.0), 0.7) * (crack * 1.5 + lines * 0.65);
        } else {
          // Mode 4: High-voltage RGB scan-glitch inversion
          float scan = step(0.5, fract(vUv.y * 90.0 + uTime * 20.0));
          vec3 inv = vec3(1.0) - col;
          impactCol = mix(inv * uWashColorA * 1.5, vec3(0.02, 0.03, 0.08), scan * 0.55) +
                      uWashColorB * lines * 1.15;
        }

        col = mix(col, impactCol, clamp(uImpactFrame, 0.0, 1.0));
      }

      gl_FragColor = vec4(col, 1.0);
    }
  `,
};

export function createImpactPostPass(aspect = 16 / 9): ShaderPass {
  const pass = new ShaderPass(ImpactPostShader);
  pass.uniforms.uAspect.value = aspect;
  return pass;
}

export function resetImpactPostUniforms(pass: ShaderPass): void {
  const u = pass.uniforms;
  u.uImpactFrame.value = 0;
  u.uColorWash.value = 0;
  u.uChroma.value = 0;
  u.uFlash.value = 0;
  u.uShockwaveProgress.value = 0;
  u.uShockwaveStrength.value = 0;
  u.uHeatHaze.value = 0;
  u.uBubbleDistort.value = 0;
  u.uBlackHoleMass.value = 0;
}

const _projTmp = new THREE.Vector3();

/**
 * Projects a world-space VFX anchor into screen UV space for optical shockwaves/lensing.
 * Returns false if the anchor is behind the camera so callers can suppress offscreen warps.
 */
export function setImpactTargetWorldPos(
  pass: ShaderPass,
  worldPos: THREE.Vector3,
  camera: THREE.Camera,
): boolean {
  _projTmp.copy(worldPos).project(camera);
  if (_projTmp.z > 1.0) return false;
  (pass.uniforms.uTargetUV.value as THREE.Vector2).set(
    _projTmp.x * 0.5 + 0.5,
    _projTmp.y * 0.5 + 0.5,
  );
  return true;
}
