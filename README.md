# Three.js Game Skills

Self-contained Codex and Claude Code skills for building playable, polished Three.js browser games. Install the skills, then ask your agent to use `threejs-game-director`; the director routes gameplay, graphics, UI, asset generation, audio, debugging, and release verification without requiring users to choose every specialist skill manually.

The package includes the runtime materials agents need: `SKILL.md` files, references, checklists, prompt templates, helper scripts, and a Vite + TypeScript + Three.js scaffold bundled inside the relevant skill folders. Generated games ship with deterministic test hooks, a seeded RNG, and Playwright templates for smoke tests, visual-regression baselines, and bot playtests so agents can verify their own work end to end.

Created by [Majid Manzarpour](https://x.com/majidmanzarpour).

## Demos

| Game | Video | Play |
| --- | --- | --- |
| Neon Ridge Drift | [Watch on X](https://x.com/majidmanzarpour/status/2064565389036540327) | [ridgedrift.netlify.app](https://ridgedrift.netlify.app) |
| Championship Snooker Arena | [Watch on X](https://x.com/majidmanzarpour/status/2064673249129071096) | [snookerarena.netlify.app](https://snookerarena.netlify.app) |
| Starship Dogfight | [Watch on X](https://x.com/majidmanzarpour/status/2065065340510281888) | [starshipdogfight.netlify.app](https://starshipdogfight.netlify.app) |
| Tide Singer | [Watch on X](https://x.com/majidmanzarpour/status/2065570428723007555) | [tidesinger.netlify.app](https://tidesinger.netlify.app) |
| Ripcore | [Watch on X](https://x.com/majidmanzarpour/status/2066687620709544070) | [ripcore.netlify.app](https://ripcore.netlify.app) |

## Install

Install all skills for Codex:

```bash
npx skills add majidmanzarpour/threejs-game-skills --skill '*' -a codex -g -y
```

Install all skills for Claude Code:

```bash
npx skills add majidmanzarpour/threejs-game-skills --skill '*' -a claude-code -g -y
```

If your installed `skills` CLI does not support one of these targets, install from a cloned checkout instead: `./install.sh --codex` for Codex, `./install.sh --claude` for Claude Code, or `./install.sh --all` for both.

For local development from a cloned checkout:

```bash
./install.sh --codex
./install.sh --claude
./install.sh --all
```

The local installer copies `skills/` into the selected agent skills directory. It skips same-named skills unless you pass `--force`, and it never removes unrelated user skills unless `--prune-managed` is explicitly requested.

```bash
./install.sh --codex --force
```

## Use The Skills

After installing, open Codex or Claude Code in an empty project folder, or in an existing Three.js game you want to improve. Then prompt the agent with the outcome you want and name the director skill:

```text
Use threejs-game-director to build a premium futuristic tower defense game from scratch.
Automatically use the relevant gameplay, graphics, UI, asset generation, audio, debug,
and QA skills. Build a playable loop first, then iterate until it passes browser,
mobile, visual, UI, performance, and release checks.
```

Both runners share the same `SKILL.md` files and auto-discover the skills once installed; the prompt above works in either:

- **Claude Code** reads skills from `~/.claude/skills` and routes from each `SKILL.md` description. Invoke the director with `/threejs-game-director`, or just name it in a prompt — it loads the sibling skills itself.
- **Codex** reads skills from `~/.codex/skills`, with each skill's `agents/openai.yaml` supplying its display name and a default kickoff prompt. Name the director in your prompt and it pulls in the specialists the same way.

The agent should:

- Load `threejs-game-director` first for broad game work.
- Load sibling skills for gameplay systems, AAA graphics, UI, debug/profile, QA/release, 3D generation, image generation, and audio generation when the request calls for them.
- Use the bundled scaffold internally when starting from an empty folder.
- Create or update the game code in your project.
- Run builds, browser checks, screenshots, canvas-pixel checks, mobile viewport checks, and QA gates before claiming completion.
- Report the skill-loading ledger, reference ledger, asset/audio sourcing decisions, visual scorecard, and remaining risks for premium work.

Users generally should not need to run the scaffold or QA helper scripts directly. Those scripts are packaged so the skills can use them as part of the workflow.

## Optional API Keys

The core Three.js skills work without paid API keys. When keys are missing, the director should report the credential probe output, skip external generation, and fall back to procedural/local assets. Add keys only when you want the agent to generate external models, images, or audio.

Never commit API keys or put them in browser-side game code. These skills use provider APIs from local agent tooling, then save generated assets into your game project.

| Provider | Skill | Environment variable | Use cases | Key setup |
| --- | --- | --- | --- | --- |
| Tripo API | `threejs-3d-generator` | `TRIPO_API_KEY` | Text/image/multiview to 3D, game-ready GLB/FBX hero models, vehicles, props, buildings, weapons, textures, rigging, animation, stylization, mesh conversion, post-processing. | [Tripo quick start](https://platform.tripo3d.ai/docs/quick-start) and [Tripo API overview](https://www.tripo3d.ai/api). |
| Gemini image API | `threejs-image-generator` | `GEMINI_API_KEY` | Concept art, image-to-3D source images, texture references, decals, skies, backgrounds, icons, logos, GUI art, title/menu art. | [Gemini API key docs](https://ai.google.dev/gemini-api/docs/api-key) and [Google AI Studio keys](https://aistudio.google.com/app/apikey). |
| ElevenLabs API | `threejs-audio-generator` | `ELEVENLABS_API_KEY` | SFX, ambience loops, UI sounds, announcer lines, dialogue TTS, voice conversion, audio cleanup, game audio manifests. | [ElevenLabs quickstart](https://elevenlabs.io/docs/eleven-api/quickstart) and [API authentication](https://elevenlabs.io/docs/api-reference/authentication). |

Set keys in your shell profile, then restart your terminal.

macOS/Linux with `zsh` or `bash`:

```bash
export TRIPO_API_KEY="..."
export GEMINI_API_KEY="..."
export ELEVENLABS_API_KEY="..."
```

For `zsh`, put those lines in `~/.zshrc` or `~/.zprofile`. For `bash`, put them in `~/.bashrc` or `~/.bash_profile`.

Windows PowerShell, current terminal session only:

```powershell
$env:TRIPO_API_KEY = "..."
$env:GEMINI_API_KEY = "..."
$env:ELEVENLABS_API_KEY = "..."
```

Windows PowerShell, persistent for your user account:

```powershell
[Environment]::SetEnvironmentVariable("TRIPO_API_KEY", "...", "User")
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "...", "User")
[Environment]::SetEnvironmentVariable("ELEVENLABS_API_KEY", "...", "User")
```

After setting persistent Windows variables, restart your terminal, Codex, or Claude Code so the agent process can see the new environment.

The director skill includes a credential probe that sources common shell profiles before deciding a key is missing. Run it from wherever you installed the skills:

```bash
# Claude Code
bash ~/.claude/skills/threejs-game-director/scripts/probe_asset_credentials.sh
# Codex
bash ~/.codex/skills/threejs-game-director/scripts/probe_asset_credentials.sh
```

It prints `TRIPO_API_KEY=SET|MISSING` (and the same for Gemini and ElevenLabs) without ever printing key values.

Provider notes:

- Tripo is optional but useful for high-value 3D surfaces that procedural code alone rarely makes premium: hero vehicles, bosses, weapons, buildings, creatures, props, and textured GLB/FBX assets.
- Gemini image generation is optional but useful before Tripo image-to-3D and for high-quality texture, sky, icon, logo, decal, and GUI sources.
- ElevenLabs is optional but useful for making games feel finished through interaction SFX, ambience, UI feedback, voice, and cleanup.
- Google also supports `GOOGLE_API_KEY`, but these skills standardize on `GEMINI_API_KEY` for clarity.
- Use provider-side key restrictions and quotas where available. ElevenLabs documents endpoint scopes, credit quotas, and secret-key handling; Google recommends environment variables and is migrating Gemini users toward auth keys.

## Best Entry Points

- Use `threejs-game-director` for complete games, major upgrades, premium polish, release-ready work, or anything broad.
- Use `threejs-gameplay-systems` for mechanics, architecture, input, camera, physics, scoring, objectives, and game feel.
- Use `threejs-aaa-graphics-builder` when screenshots look basic or the game needs stronger models, materials, lighting, VFX, world detail, or render polish.
- Use `threejs-game-ui-designer` for HUDs, menus, overlays, responsive layout, safe areas, icons, touch controls, and text fit.
- Use `threejs-debug-profiler` for black screens, runtime errors, loading issues, resize/mobile bugs, performance, draw calls, triangles, textures, and memory.
- Use `threejs-qa-release` for production builds, browser verification, screenshots, canvas pixels, mobile checks, release risk reports, and static-hosting readiness.
- Use `threejs-3d-generator` for Tripo API text/image-to-3D models, texture, rigging, animation, conversion, and GLB/FBX game assets.
- Use `threejs-image-generator` for Gemini-generated concepts, image-to-3D inputs, textures, decals, skies, backgrounds, icons, logos, GUI art, and title/menu art.
- Use `threejs-audio-generator` for ElevenLabs SFX, ambience, UI sounds, voice/TTS, voice conversion, cleanup, and Three.js audio integration.

For most user-facing game requests, start with `threejs-game-director` and let it pull in the specialists.

## What Good Usage Looks Like

For a new game:

```text
Use threejs-game-director to create a AAA-inspired hover racing game from scratch.
Make it playable, add premium track visuals, vehicle feel, HUD, SFX hooks, desktop and
mobile controls, and run the full verification pass before reporting done.
```

For visual upgrades:

```text
Use threejs-game-director to upgrade this Three.js game from prototype visuals to
premium browser-game quality. Use the AAA graphics, UI, image, 3D, audio, debug,
and QA skills as needed. Include the visual scorecard and evidence from active-play
screenshots.
```

For an existing broken game:

```text
Use threejs-game-director to debug and finish this Three.js game. First get it running,
then improve gameplay feel, UI, graphics, performance, and release verification until
the remaining risks are explicit.
```

For asset-heavy games:

```text
Use threejs-game-director to build a premium space dogfight game. Use threejs-image-generator
for concepts, skies, decals, icons, and GUI art; use threejs-3d-generator for hero ships
and weapons when credentials are available; use threejs-audio-generator for SFX and
ambience. If generation is blocked, report the credential probe output and fallback plan.
```

## Expected Evidence

For meaningful Three.js work, the skills should gather evidence before claiming success:

- `npm run build`
- local browser run
- browser console and page error check
- Playwright screenshot
- canvas nonblank pixel check, plus the inspector's measured metrics (color entropy, edge density, luminance contrast, render budget rows)
- desktop and mobile viewport pass
- interaction check for the main control path
- game design brief, core loop contract, and level/encounter plan for broad game creation
- performance snapshot when graphics, assets, shaders, or post-processing changed
- technical art budget target-vs-actuals when premium graphics changed
- UI text-fit, overlap, safe-area, and touch-target checks when UI changed
- visual scorecard with measured evidence and a fresh-eyes review for premium, AAA, showcase, or less-basic claims
- visual test harness decision (screenshot baselines added/extended/skipped) for release-ready visual QA
- bot playtest metrics for release-ready gameplay claims
- external asset/audio sourcing ledger when generated assets or audio are in scope

Premium/AAA claims should not rely on a static scene, placeholder cubes, generic stat-card HUDs, or unverified screenshots. The game should have an active playable loop and a filled visual scorecard.

## Skill System

- `threejs-game-director`: main entrypoint for complete game builds and orchestration — runner capability check, skill path ladder, phase playbook, ledgers, report audit.
- `threejs-gameplay-systems`: playable loop, architecture, game design and level design, mechanics, entities, controls, camera, physics selection, and game feel (hitstop, screenshake, easing, impact feedback).
- `threejs-aaa-graphics-builder`: visual scorecard with calibration anchors, technical art budgets, shader/material cookbook, asset architecture, models, materials, VFX, render polish.
- `threejs-game-ui-designer`: HUDs, menus, overlays, responsive UI, icons, safe areas, UI states.
- `threejs-debug-profiler`: scene/runtime/render bugs, mobile bugs, performance profiling, renderer metrics.
- `threejs-qa-release`: browser QA, screenshots, canvas pixels with measured metrics, visual test harness, bot playtests, responsive checks, production build, release risk report.
- `threejs-3d-generator`: Tripo API text/image-to-3D, texture, auto-rig, animation, conversion, download, and Three.js import guidance.
- `threejs-image-generator`: Gemini image generation for concepts, textures, decals, skies, icons, GUI art, and image-to-3D inputs.
- `threejs-audio-generator`: ElevenLabs-backed SFX, ambience, UI sounds, voice/TTS, voice conversion, cleanup, and Three.js audio integration.

## Packaged Resources

Installed skills are self-contained. They do not depend on root docs, root scaffolds, root prompts, or root checklists.

- `skills/`: the full public package. Each skill owns its required `SKILL.md`, `references/`, `scripts/`, and `assets/`.
- `skills/threejs-gameplay-systems/assets/threejs-vite-game/`: packaged game scaffold used by the skills when starting from an empty project. Ships deterministic test hooks (`__THREE_GAME_TEST_HOOKS__`), a seeded RNG, and `tests/` templates for smoke tests, visual-regression baselines, and bot playtests.
- `skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs`: packaged browser/canvas inspection helper — reports non-blank pixels, measured visual metrics (color entropy, edge density, luminance contrast), and render-budget rows; `--state`/`--seed` drive the test hooks for deterministic per-state captures.
- `skills/threejs-aaa-graphics-builder/assets/scorecard-anchors/`: calibration reference screenshots for the visual scorecard.
- `scripts/`: local validation helpers for maintainers.
- `install.sh`: local installer for working on this checkout.

## Maintainer Checks

Validate this workflow repository:

```bash
npm install
npm run check:scripts
npm run validate:skills
```

Maintainers can run packaged helpers directly when testing the skill package, but normal users should interact through agent prompts:

```bash
python3 skills/threejs-gameplay-systems/scripts/create_threejs_game.py ../my-threejs-game
node skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --mobile
node skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --state active-play --seed 12345
```

## License

MIT. See [LICENSE](LICENSE).
