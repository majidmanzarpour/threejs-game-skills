import * as THREE from 'three';

/**
 * NaN-safe, HDR-controlled stylized VFX ShaderMaterials with WebGL2 DepthTexture
 * soft particles & glowing scene-intersection contact rims.
 */

export interface DepthSharedUniforms {
  tDepth: THREE.IUniform<THREE.DepthTexture | null>;
  uResolution: THREE.IUniform<THREE.Vector2>;
  uCameraNear: THREE.IUniform<number>;
  uCameraFar: THREE.IUniform<number>;
  uHasDepth: THREE.IUniform<number>;
}

export const DEPTH_FADE_GLSL = /* glsl */ `
  uniform sampler2D tDepth;
  uniform vec2 uResolution;
  uniform float uCameraNear;
  uniform float uCameraFar;
  uniform float uHasDepth;

  float linearizeSceneDepth(float z) {
    float ndc = z * 2.0 - 1.0;
    return (2.0 * uCameraNear * uCameraFar) /
           max(0.0001, uCameraFar + uCameraNear - ndc * (uCameraFar - uCameraNear));
  }

  float getSceneDepthDiff() {
    if (uHasDepth < 0.5) return 99.0;
    vec2 suv = gl_FragCoord.xy / max(uResolution, vec2(1.0));
    float rawScene = texture2D(tDepth, suv).r;
    float sceneZ = linearizeSceneDepth(rawScene);
    float fragZ = linearizeSceneDepth(gl_FragCoord.z);
    return max(0.0, sceneZ - fragZ);
  }
`;

export function makeDepthUniforms(depthShared?: DepthSharedUniforms | null): DepthSharedUniforms {
  if (depthShared) {
    return {
      tDepth: depthShared.tDepth,
      uResolution: depthShared.uResolution,
      uCameraNear: depthShared.uCameraNear,
      uCameraFar: depthShared.uCameraFar,
      uHasDepth: depthShared.uHasDepth,
    };
  }
  return {
    tDepth: { value: null },
    uResolution: { value: new THREE.Vector2(1280, 720) },
    uCameraNear: { value: 0.1 },
    uCameraFar: { value: 160.0 },
    uHasDepth: { value: 0.0 },
  };
}

export interface GroundVortexOptions {
  flowTex?: THREE.Texture | null;
  colorOuter?: THREE.ColorRepresentation;
  colorMid?: THREE.ColorRepresentation;
  colorInner?: THREE.ColorRepresentation;
  colorHot?: THREE.ColorRepresentation;
  swirlTwist?: number;
  spinSpeed?: number;
  radialSpeed?: number;
  flowStrength?: number;
  noiseScaleU?: number;
  noiseScaleV?: number;
  innerFade?: number;
  outerFade?: number;
  serration?: number;
  hdrBoost?: number;
  additive?: boolean;
}

/**
 * Polar-twisted stylized ground vortex / shockwave disc with 2-phase curl flowmap advection
 * and hot dissolve rim. Pair with createPolarRingGeometry().
 */
export function createGroundVortexMaterial(
  noiseTex: THREE.Texture,
  {
    flowTex = null,
    colorOuter = '#064a5e',
    colorMid = '#16c892',
    colorInner = '#d8ea54',
    colorHot = '#f6ffe4',
    swirlTwist = 2.6,
    spinSpeed = 1.6,
    radialSpeed = 0.45,
    flowStrength = 0.14,
    noiseScaleU = 3.0,
    noiseScaleV = 1.8,
    innerFade = 0.08,
    outerFade = 0.96,
    serration = 0.22,
    hdrBoost = 1.25,
    additive = false,
  }: GroundVortexOptions = {},
): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    uniforms: {
      uNoise: { value: noiseTex },
      uFlow: { value: flowTex ?? noiseTex },
      uUseFlow: { value: flowTex ? 1.0 : 0.0 },
      uFlowStrength: { value: flowStrength },
      uTime: { value: 0 },
      uOpacity: { value: 1 },
      uDissolve: { value: 0 },
      uSwirlTwist: { value: swirlTwist },
      uSpinSpeed: { value: spinSpeed },
      uRadialSpeed: { value: radialSpeed },
      uScaleUV: { value: new THREE.Vector2(noiseScaleU, noiseScaleV) },
      uFades: { value: new THREE.Vector2(innerFade, outerFade) },
      uSerration: { value: serration },
      uHdrBoost: { value: hdrBoost },
      uColorOuter: { value: new THREE.Color(colorOuter) },
      uColorMid: { value: new THREE.Color(colorMid) },
      uColorInner: { value: new THREE.Color(colorInner) },
      uColorHot: { value: new THREE.Color(colorHot) },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uNoise;
      uniform sampler2D uFlow;
      uniform float uUseFlow;
      uniform float uFlowStrength;
      uniform float uTime;
      uniform float uOpacity;
      uniform float uDissolve;
      uniform float uSwirlTwist;
      uniform float uSpinSpeed;
      uniform float uRadialSpeed;
      uniform vec2 uScaleUV;
      uniform vec2 uFades;
      uniform float uSerration;
      uniform float uHdrBoost;
      uniform vec3 uColorOuter;
      uniform vec3 uColorMid;
      uniform vec3 uColorInner;
      uniform vec3 uColorHot;
      varying vec2 vUv;

      void main() {
        if (uOpacity <= 0.001) discard;
        float angle = vUv.x;
        float rad = clamp(vUv.y, 0.0, 1.0);

        float twist = pow(max(0.0001, 1.0 - rad), 1.35) * uSwirlTwist;
        vec2 baseUV = vec2(angle * uScaleUV.x + twist - uTime * uSpinSpeed, rad * uScaleUV.y + uTime * uRadialSpeed);

        vec4 n1;
        if (uUseFlow > 0.5) {
          vec2 flowVec = (texture2D(uFlow, vec2(angle * 2.0, rad * 1.5)).rg * 2.0 - 1.0) * uFlowStrength;
          float fTime = uTime * 0.65;
          float p0 = fract(fTime);
          float p1 = fract(fTime + 0.5);
          float blend = abs(p0 * 2.0 - 1.0);
          n1 = mix(texture2D(uNoise, baseUV + flowVec * p0), texture2D(uNoise, baseUV + flowVec * p1), blend);
        } else {
          n1 = texture2D(uNoise, baseUV);
        }

        vec2 warpUV = vec2(
          angle * (uScaleUV.x * 1.5) + twist * 1.3 - uTime * (uSpinSpeed * 1.25) + (n1.r - 0.5) * 0.24,
          rad * (uScaleUV.y * 1.35) - uTime * (uRadialSpeed * 0.6) + (n1.g - 0.5) * 0.16
        );
        vec4 n2 = texture2D(uNoise, warpUV);

        float rDist = rad + (n2.g - 0.45) * uSerration + (n1.b - 0.4) * (uSerration * 0.65);
        float radialMask = smoothstep(uFades.x, uFades.x + 0.14, rDist) *
                           (1.0 - smoothstep(uFades.y - 0.18, uFades.y, rDist));

        float energy = clamp(n1.r * 0.42 + n2.g * 0.36 + n1.b * 0.32, 0.0, 1.0) * radialMask;
        float mask = smoothstep(uDissolve, uDissolve + 0.16, energy);
        float erodeEdge = smoothstep(uDissolve, uDissolve + 0.04, energy) *
                          (1.0 - smoothstep(uDissolve + 0.04, uDissolve + 0.16, energy));

        vec3 col = mix(uColorOuter, uColorMid, smoothstep(0.14, 0.48, energy));
        col = mix(col, uColorInner, smoothstep(0.48, 0.78, energy));
        col = mix(col, uColorHot * uHdrBoost, smoothstep(0.78, 0.96, energy));
        col += uColorHot * erodeEdge * uHdrBoost * 0.85;

        float alpha = clamp(mask * uOpacity, 0.0, 1.0);
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(col, alpha);
      }
    `,
  });
}

export interface EnergyRibbonOptions {
  colorOuter?: THREE.ColorRepresentation;
  colorMid?: THREE.ColorRepresentation;
  colorHot?: THREE.ColorRepresentation;
  scrollSpeed?: number;
  hdrBoost?: number;
  additive?: boolean;
}

/**
 * Calligraphic sweeping ribbon shader for melee slashes, weapon trails, and energy arcs.
 */
export function createEnergyRibbonMaterial(
  noiseTex: THREE.Texture,
  {
    colorOuter = '#0a5e78',
    colorMid = '#22e4c8',
    colorHot = '#f4ffea',
    scrollSpeed = 2.4,
    hdrBoost = 1.45,
    additive = true,
  }: EnergyRibbonOptions = {},
): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    uniforms: {
      uNoise: { value: noiseTex },
      uTime: { value: 0 },
      uOpacity: { value: 1 },
      uDissolve: { value: 0 },
      uScrollSpeed: { value: scrollSpeed },
      uHdrBoost: { value: hdrBoost },
      uColorOuter: { value: new THREE.Color(colorOuter) },
      uColorMid: { value: new THREE.Color(colorMid) },
      uColorHot: { value: new THREE.Color(colorHot) },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform sampler2D uNoise;
      uniform float uTime;
      uniform float uOpacity;
      uniform float uDissolve;
      uniform float uScrollSpeed;
      uniform float uHdrBoost;
      uniform vec3 uColorOuter;
      uniform vec3 uColorMid;
      uniform vec3 uColorHot;
      varying vec2 vUv;

      void main() {
        if (uOpacity <= 0.001) discard;
        vec2 uv1 = vec2(vUv.x * 2.2 - uTime * uScrollSpeed, vUv.y * 1.15);
        vec4 n = texture2D(uNoise, uv1);

        float endFade = smoothstep(0.0, 0.14, vUv.x) * (1.0 - smoothstep(0.76, 1.0, vUv.x));
        float crossCenter = 1.0 - abs(vUv.y * 2.0 - 1.0);
        float coreBand = pow(max(0.0001, crossCenter), 1.65);

        float energy = clamp((coreBand * 0.72 + n.g * 0.35 + n.b * 0.25) * endFade, 0.0, 1.0);
        float mask = smoothstep(uDissolve, uDissolve + 0.18, energy);

        vec3 col = mix(uColorOuter, uColorMid, smoothstep(0.18, 0.56, energy));
        col = mix(col, uColorHot * uHdrBoost, smoothstep(0.56, 0.88, energy));

        float alpha = clamp(mask * uOpacity, 0.0, 1.0);
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(col, alpha);
      }
    `,
  });
}

export interface EnergyDomeOptions {
  depthShared?: DepthSharedUniforms | null;
  colorBase?: THREE.ColorRepresentation;
  colorRim?: THREE.ColorRepresentation;
  colorHot?: THREE.ColorRepresentation;
  fresnelPower?: number;
  contactWidth?: number;
  hdrBoost?: number;
}

/**
 * Depth-softened translucent forcefield / shield / barrier dome with glowing floor contact rim.
 */
export function createEnergyDomeMaterial(
  noiseTex: THREE.Texture,
  {
    depthShared = null,
    colorBase = '#0b4a68',
    colorRim = '#24e8d4',
    colorHot = '#f0fff8',
    fresnelPower = 2.4,
    contactWidth = 0.65,
    hdrBoost = 1.5,
  }: EnergyDomeOptions = {},
): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.NormalBlending,
    uniforms: {
      ...makeDepthUniforms(depthShared),
      uNoise: { value: noiseTex },
      uTime: { value: 0 },
      uOpacity: { value: 1 },
      uFresnelPower: { value: fresnelPower },
      uContactWidth: { value: contactWidth },
      uHdrBoost: { value: hdrBoost },
      uColorBase: { value: new THREE.Color(colorBase) },
      uColorRim: { value: new THREE.Color(colorRim) },
      uColorHot: { value: new THREE.Color(colorHot) },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      varying vec3 vNormalW;
      varying vec3 vViewDir;
      void main() {
        vUv = uv;
        vec4 wp = modelMatrix * vec4(position, 1.0);
        vNormalW = normalize(mat3(modelMatrix) * normal + vec3(1e-5));
        vViewDir = normalize(cameraPosition - wp.xyz + vec3(1e-5));
        gl_Position = projectionMatrix * viewMatrix * wp;
      }
    `,
    fragmentShader: /* glsl */ `
      ${DEPTH_FADE_GLSL}
      uniform sampler2D uNoise;
      uniform float uTime;
      uniform float uOpacity;
      uniform float uFresnelPower;
      uniform float uContactWidth;
      uniform float uHdrBoost;
      uniform vec3 uColorBase;
      uniform vec3 uColorRim;
      uniform vec3 uColorHot;

      varying vec2 vUv;
      varying vec3 vNormalW;
      varying vec3 vViewDir;

      void main() {
        if (uOpacity <= 0.001) discard;
        float ndotv = clamp(abs(dot(normalize(vNormalW), normalize(vViewDir))), 0.0, 1.0);
        float fresnel = pow(max(0.0001, 1.0 - ndotv), uFresnelPower);

        vec4 n1 = texture2D(uNoise, vec2(vUv.x * 3.0 - uTime * 0.25, vUv.y * 2.0 + uTime * 0.18));
        float caustics = smoothstep(0.45, 0.92, n1.a);

        float depthDiff = getSceneDepthDiff();
        float contactRim = (1.0 - smoothstep(0.0, max(0.01, uContactWidth), depthDiff)) * step(0.5, uHasDepth);
        float baseRim = (1.0 - smoothstep(0.0, 0.12, vUv.y)) * 0.55;
        float seam = max(contactRim, baseRim);

        vec3 col = mix(uColorBase, uColorRim * 1.25, clamp(fresnel + caustics * 0.45, 0.0, 1.0));
        col += uColorHot * (seam * 1.35 + fresnel * caustics * 0.65) * uHdrBoost;

        float alpha = clamp((0.18 + fresnel * 0.68 + caustics * 0.22 + seam * 0.7) * uOpacity, 0.0, 1.0);
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(col, alpha);
      }
    `,
  });
}

export interface SoftSmokeOptions {
  depthShared?: DepthSharedUniforms | null;
  colorShadow?: THREE.ColorRepresentation;
  colorLit?: THREE.ColorRepresentation;
  softRange?: number;
}

/**
 * Depth-softened painterly cel-smoke material. Eliminates hard floor/wall plane clipping.
 */
export function createSoftSmokeMaterial(
  smokeTex: THREE.Texture,
  {
    depthShared = null,
    colorShadow = '#1a2030',
    colorLit = '#6b7e98',
    softRange = 0.85,
  }: SoftSmokeOptions = {},
): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    uniforms: {
      ...makeDepthUniforms(depthShared),
      uSmoke: { value: smokeTex },
      uOpacity: { value: 1 },
      uDissolve: { value: 0 },
      uSoftRange: { value: softRange },
      uColorShadow: { value: new THREE.Color(colorShadow) },
      uColorLit: { value: new THREE.Color(colorLit) },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      ${DEPTH_FADE_GLSL}
      uniform sampler2D uSmoke;
      uniform float uOpacity;
      uniform float uDissolve;
      uniform float uSoftRange;
      uniform vec3 uColorShadow;
      uniform vec3 uColorLit;
      varying vec2 vUv;

      void main() {
        if (uOpacity <= 0.001) discard;
        vec4 s = texture2D(uSmoke, vUv);
        float shape = smoothstep(uDissolve, uDissolve + 0.24, s.a);
        float softFade = smoothstep(0.0, max(0.01, uSoftRange), getSceneDepthDiff());
        float alpha = clamp(shape * softFade * uOpacity, 0.0, 1.0);
        if (alpha < 0.01) discard;
        vec3 col = mix(uColorShadow, uColorLit, smoothstep(0.22, 0.78, s.r));
        gl_FragColor = vec4(col, alpha);
      }
    `,
  });
}

export type SdfSigilStyle = 0 | 1 | 2 | 3 | 4 | 5;

export interface SdfSigilOptions {
  style?: SdfSigilStyle; // 0=Hex, 1=Astrolabe, 2=Arcane Star, 3=Waveform, 4=Void Corona, 5=Cyber 90deg
  coreColor?: THREE.ColorRepresentation;
  primaryColor?: THREE.ColorRepresentation;
  secondaryColor?: THREE.ColorRepresentation;
  spinDir?: number;
}

/**
 * Texture-free procedural SDF emitter sigil / targeting reticle quad shader (6 styles).
 */
export function createSdfSigilMaterial({
  style = 0,
  coreColor = '#fff6dc',
  primaryColor = '#24e8d0',
  secondaryColor = '#6898ff',
  spinDir = 1.0,
}: SdfSigilOptions = {}): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    uniforms: {
      uTime: { value: 0 },
      uIntensity: { value: 1 },
      uStyle: { value: style },
      uSpinDir: { value: spinDir },
      uCoreColor: { value: new THREE.Color(coreColor) },
      uPrimaryColor: { value: new THREE.Color(primaryColor) },
      uSecondaryColor: { value: new THREE.Color(secondaryColor) },
    },
    vertexShader: /* glsl */ `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: /* glsl */ `
      uniform float uTime;
      uniform float uIntensity;
      uniform float uStyle;
      uniform float uSpinDir;
      uniform vec3 uCoreColor;
      uniform vec3 uPrimaryColor;
      uniform vec3 uSecondaryColor;
      varying vec2 vUv;

      float sdPolygon(vec2 p, float r, float n) {
        float a = atan(p.y, p.x);
        float seg = 6.2831853 / n;
        return cos(floor(0.5 + a / seg) * seg - a) * length(p) - r;
      }

      float glowLine(float d, float sharp) {
        float x = d * sharp;
        return exp(-(x * x));
      }

      void main() {
        if (uIntensity <= 0.001) discard;
        vec2 p = (vUv - 0.5) * 2.0;
        float r = length(p);
        if (r > 1.02) discard;

        float a0 = atan(p.y, p.x);
        float rot1 = uTime * 2.0 * uSpinDir;
        float rot2 = -uTime * 2.9 * uSpinDir;
        vec2 p1 = vec2(p.x * cos(rot1) - p.y * sin(rot1), p.x * sin(rot1) + p.y * cos(rot1));
        vec2 p2 = vec2(p.x * cos(rot2) - p.y * sin(rot2), p.x * sin(rot2) + p.y * cos(rot2));

        float line = 0.0;
        float accent = 0.0;

        if (uStyle < 0.5) {
          // 0: Hexagonal accelerator / prism ring
          line = glowLine(abs(sdPolygon(p1, 0.72, 6.0)), 26.0) * 1.1 +
                 glowLine(abs(sdPolygon(p2, 0.48, 6.0)), 30.0) * 0.85 +
                 glowLine(r - 0.88, 28.0) * 0.7;
          accent = smoothstep(0.92, 0.99, cos(atan(p1.y, p1.x) * 6.0)) *
                   smoothstep(0.46, 0.52, r) * (1.0 - smoothstep(0.84, 0.92, r)) * 1.2;
        } else if (uStyle < 1.5) {
          // 1: Clockwork / astrolabe dial
          float teeth = smoothstep(0.45, 0.75, cos(atan(p1.y, p1.x) * 12.0)) *
                        smoothstep(0.78, 0.82, r) * (1.0 - smoothstep(0.90, 0.94, r));
          line = glowLine(r - 0.82, 32.0) + glowLine(r - 0.60, 34.0) * 0.85 + teeth * 0.95;
          accent = (exp(-abs(p2.x) * 38.0) + exp(-abs(p2.y) * 38.0)) * (1.0 - smoothstep(0.42, 0.58, r));
        } else if (uStyle < 2.5) {
          // 2: Interlocking arcane star / runic seal
          line = (glowLine(abs(sdPolygon(p1, 0.64, 3.0)), 28.0) +
                  glowLine(abs(sdPolygon(-p1, 0.64, 3.0)), 28.0)) * 0.95 +
                 glowLine(r - 0.86, 30.0) * 0.9;
          accent = smoothstep(0.70, 0.95, sin(atan(p2.y, p2.x) * 16.0) * cos(atan(p2.y, p2.x) * 5.0)) *
                   smoothstep(0.68, 0.74, r) * (1.0 - smoothstep(0.80, 0.85, r)) * 1.15;
        } else if (uStyle < 3.5) {
          // 3: High-voltage harmonic waveform ring
          float waveR = 0.68 + 0.10 * sin(a0 * 8.0 + uTime * 8.0 * uSpinDir);
          line = glowLine(r - waveR, 28.0) * 1.2 + glowLine(r - 0.88, 30.0) * 0.65;
          accent = glowLine(r - 0.36, 26.0) * (0.5 + 0.5 * cos(a0 * 12.0 - uTime * 10.0));
        } else if (uStyle < 4.5) {
          // 4: Void eclipse corona ring
          float corona = glowLine(r - 0.64, 18.0) * (0.75 + 0.35 * sin(a0 * 5.0 + uTime * 5.0));
          line = corona * 1.25 + glowLine(r - 0.88, 24.0) * 0.6;
          accent = glowLine(r - 0.52, 26.0) * 1.1;
        } else {
          // 5: 90-degree orthogonal cyber reticle
          vec2 ap = abs(p);
          float boxOuter = max(ap.x, ap.y);
          float cornerMask = step(0.45, min(ap.x, ap.y));
          line = glowLine(boxOuter - 0.78, 30.0) * (0.35 + 0.85 * cornerMask) +
                 glowLine(boxOuter - 0.44, 32.0) * 0.7;
          accent = (exp(-abs(p.x) * 42.0) + exp(-abs(p.y) * 42.0)) *
                   smoothstep(0.24, 0.30, r) * (1.0 - smoothstep(0.82, 0.88, r));
        }

        float edgeFade = 1.0 - smoothstep(0.92, 1.0, r);
        vec3 col = uPrimaryColor * line * 1.2 + uSecondaryColor * accent * 1.3 +
                   uCoreColor * max(line, accent) * 0.45;
        float alpha = clamp((line + accent) * edgeFade * uIntensity, 0.0, 1.0);
        if (alpha < 0.01) discard;
        gl_FragColor = vec4(col * uIntensity, alpha);
      }
    `,
  });
}
