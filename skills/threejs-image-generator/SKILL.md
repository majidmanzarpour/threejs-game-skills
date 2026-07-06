---
name: threejs-image-generator
description: "Generate and edit 2D image assets for Three.js games using Google's Gemini image API. Use for concept sheets, image-to-3D inputs, texture references, sky/background plates, decals, logos, icons, GUI art, title/menu art, thumbnails, marketing stills, and source images that feed threejs-3d-generator. Also use for direct image editing when the user provides an image path."
---

# Three.js Image Generator

## Purpose

Create game-useful 2D assets and references for Three.js projects. This skill is the image-generation layer for the Three.js game system: it produces concepts, textures, decals, UI art, and 2D inputs that can be handed to `threejs-3d-generator` for image-to-3D model creation.

Provider: Google's Gemini image API.

Resolve `<this-skill-dir>` in the commands below in this order: `~/.claude/skills/threejs-image-generator`, `~/.codex/skills/threejs-image-generator`, `~/.agents/skills/threejs-image-generator`, or repo `skills/threejs-image-generator`.

## When To Use

Use this skill before procedural-only fallback when a Three.js game needs:

- 2D-to-3D reference images for `threejs-3d-generator`: characters, creatures, buildings, ships, cars, weapons, props, pickups, terrain modules.
- Texture and material references: terrain, road, rock, sand, metal, sci-fi panels, trim sheets, decals, hazard labels, signs.
- Environment images: skies, backdrops, city horizons, nebula plates, menu backgrounds, parallax layers.
- UI art: logos, faction marks, icons, item cards, ability badges, cockpit decals, GUI panels, title art.
- Existing-image edits, style variants, cleanup, palette alignment, or concept sheet refinements.

For premium/AAA/showcase graphics work, generate at least one relevant image for high-value 2D surfaces or image-to-3D inputs unless the credential probe or a real generation attempt shows a blocker.

## API Key

Never store API keys in skill files or browser/game code, and never paste a key value into a report. The script reads `--api-key` or `GEMINI_API_KEY`.

Step 0, before declaring the key unavailable: run this skill's own probe and paste its literal output into the report.

```bash
uv run <this-skill-dir>/scripts/generate_image.py probe   # prints GEMINI_API_KEY=SET|MISSING
```

`GEMINI_API_KEY=MISSING` is only a valid skip/blocker reason when this output is shown. Keys defined only in a shell profile can be absent from the process env; if the plain probe prints MISSING unexpectedly, wrap it: `zsh -lc 'source ~/.zprofile 2>/dev/null || true; source ~/.zshrc 2>/dev/null || true; uv run <this-skill-dir>/scripts/generate_image.py probe'`. When the director skill is loaded, prefer `threejs-game-director/scripts/probe_asset_credentials.sh`, which probes all three asset keys at once.

## Tool Script

Run from the user's current project directory so output lands in the game project:

```bash
uv run <this-skill-dir>/scripts/generate_image.py --prompt "your image description" --filename assets/concepts/output.png --resolution 2K
```

Edit an existing image:

```bash
uv run <this-skill-dir>/scripts/generate_image.py \
  --input-image assets/concepts/ship.png \
  --prompt "turn this into a battle-worn red racing livery with clearer material zones" \
  --filename assets/concepts/ship-red-livery.png \
  --resolution 2K
```

Resolution mapping:

- `1K`: quick concepts, icons, draft sheets.
- `2K`: default production reference for image-to-3D, textures, backgrounds, UI panels. This is also the script default when `--resolution` is omitted.
- `4K`: hero splash/title art, high-detail texture references, large sky/background plates.

## Prompt Patterns

Image-to-3D reference:

```text
Create a clean 3D-generation reference image of [asset]. Centered single object, full object visible, plain light background, readable silhouette, clear material zones, game-ready [genre/style], no motion blur, no cropped parts, no text.
```

Riggable character/creature reference:

```text
Create a full-body [T-pose/A-pose/side-view creature] reference for 3D rigging: [details]. Symmetric stance, visible hands/feet/limbs, plain background, readable costume/anatomy layers, no weapon fused to hands.
```

Texture/material reference:

```text
Create a seamless game texture reference for [surface]. Orthographic/top-down, PBR-friendly albedo, clear material variation, no perspective, no baked strong shadows, [style/material details].
```

Logo/icon/UI art:

```text
Create a crisp game UI [logo/icon/badge/panel] for [faction/item/ability]. Transparent-friendly silhouette, high contrast at small size, [genre styling], no tiny unreadable text.
```

Sky/background:

```text
Create a wide game background plate of [environment]. Layered depth, readable horizon, [time/weather/style], suitable behind a real-time Three.js scene, no foreground subject.
```

## Three.js Integration Rules

- Save concepts and image-to-3D sources under `assets/concepts/`.
- Save textures, decals, icons, and GUI source images under `assets/textures/`, `assets/decals/`, or `assets/ui/`.
- For image-to-3D, hand the saved image path to `threejs-3d-generator` and record the chain in the external asset ledger.
- Do not call the image API from client-side game code.
- Convert generated PNGs into runtime formats deliberately: PNG for alpha/UI, JPG/WebP/KTX2 for larger opaque textures where the project pipeline supports it.
- Verify how the image appears in game, not only that the file exists.

## Required Report

Report:

- Credential probe output or command blocker.
- Prompt and purpose.
- Output path.
- Resolution.
- Whether the image was used directly, edited further, or handed to `threejs-3d-generator`.
- Any remaining integration work such as compression, UV assignment, alpha cleanup, or atlas packing.

Do not mark a premium graphics phase complete if the needed image outputs are missing and the only justification is "procedural is enough" for high-value UI, texture, sky, decal, logo, or image-to-3D surfaces.
