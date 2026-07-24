# Three.js 游戏技能

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

这是一套用于构建可游玩、精致的 Three.js 浏览器游戏的独立 Codex 和 Claude Code 技能。安装这些技能后，让你的智能体使用 `threejs-game-director`；该导演技能会调度玩法、图形、UI、资产生成、音频、调试和发布验证，无需用户手动选择每一项专业技能。

该软件包包含智能体运行所需的材料：`SKILL.md` 文件、参考资料、检查清单、提示词模板、辅助脚本，以及相关技能文件夹中内置的 Vite + TypeScript + Three.js 脚手架。生成的游戏带有确定性测试钩子、带种子的随机数生成器，以及用于冒烟测试、视觉回归基线和机器人试玩的 Playwright 模板，使智能体能够端到端验证自己的工作。

由 [Majid Manzarpour](https://x.com/majidmanzarpour) 创建。

## 演示

| 游戏 | 视频 | 试玩 |
| --- | --- | --- |
| Neon Ridge Drift | [在 X 上观看](https://x.com/majidmanzarpour/status/2064565389036540327) | [ridgedrift.netlify.app](https://ridgedrift.netlify.app) |
| Championship Snooker Arena | [在 X 上观看](https://x.com/majidmanzarpour/status/2064673249129071096) | [snookerarena.netlify.app](https://snookerarena.netlify.app) |
| Starship Dogfight | [在 X 上观看](https://x.com/majidmanzarpour/status/2065065340510281888) | [starshipdogfight.netlify.app](https://starshipdogfight.netlify.app) |
| Tide Singer | [在 X 上观看](https://x.com/majidmanzarpour/status/2065570428723007555) | [tidesinger.netlify.app](https://tidesinger.netlify.app) |
| Ripcore | [在 X 上观看](https://x.com/majidmanzarpour/status/2066687620709544070) | [ripcore.netlify.app](https://ripcore.netlify.app) |

## 安装

为 Codex 安装全部技能：

```bash
npx skills add majidmanzarpour/threejs-game-skills --skill '*' -a codex -g -y
```

为 Claude Code 安装全部技能：

```bash
npx skills add majidmanzarpour/threejs-game-skills --skill '*' -a claude-code -g -y
```

如果你安装的 `skills` CLI 不支持其中某个目标，请改为从克隆的检出目录安装：Codex 使用 `./install.sh --codex`，Claude Code 使用 `./install.sh --claude`，两者都安装则使用 `./install.sh --all`。

从克隆的检出目录进行本地开发：

```bash
./install.sh --codex
./install.sh --claude
./install.sh --all
```

本地安装程序会将 `skills/` 复制到所选智能体的技能目录。除非传入 `--force`，否则会跳过同名技能；除非明确请求 `--prune-managed`，否则绝不会删除不相关的用户技能。

```bash
./install.sh --codex --force
```

## 使用这些技能

安装后，在空项目文件夹或想要改进的现有 Three.js 游戏中打开 Codex 或 Claude Code。然后向智能体描述所需结果，并指定导演技能：

```text
Use threejs-game-director to build a premium futuristic tower defense game from scratch.
Automatically use the relevant gameplay, graphics, UI, asset generation, audio, debug,
and QA skills. Build a playable loop first, then iterate until it passes browser,
mobile, visual, UI, performance, and release checks.
```

两个运行器共享相同的 `SKILL.md` 文件，安装后会自动发现这些技能；上述提示词在两者中都可使用：

- **Claude Code** 从 `~/.claude/skills` 读取技能，并根据每个 `SKILL.md` 的描述进行调度。可以用 `/threejs-game-director` 调用导演，也可以直接在提示词中指定它——它会自行加载同级技能。
- **Codex** 从 `~/.codex/skills` 读取技能，每项技能的 `agents/openai.yaml` 提供其显示名称和默认启动提示词。在提示词中指定导演，它会以相同方式引入专业技能。

智能体应当：

- 首先加载 `threejs-game-director` 以处理广泛的游戏工作。
- 在请求需要时，为玩法系统、AAA 图形、UI、调试/分析、QA/发布、3D 生成、图像生成和音频生成加载同级技能。
- 从空文件夹开始时，在内部使用内置脚手架。
- 在你的项目中创建或更新游戏代码。
- 在宣称完成前运行构建、浏览器检查、截图、画布像素检查、移动视口检查和 QA 门禁。
- 针对高品质工作，报告技能加载台账、参考资料台账、资产/音频来源决策、视觉评分卡和剩余风险。

用户通常不需要直接运行脚手架或 QA 辅助脚本。这些脚本已打包，供技能在工作流程中使用。

## 可选 API 密钥

核心 Three.js 技能无需付费 API 密钥即可运行。缺少密钥时，导演应报告凭据探测结果，跳过外部生成，并回退到程序化/本地资产。仅当希望智能体生成外部模型、图像或音频时才添加密钥。

切勿提交 API 密钥，也不要将其放入浏览器端游戏代码。这些技能通过本地智能体工具调用提供商 API，然后将生成的资产保存到你的游戏项目中。

| 提供商 | 技能 | 环境变量 | 用途 | 密钥设置 |
| --- | --- | --- | --- | --- |
| Tripo API | `threejs-3d-generator` | `TRIPO_API_KEY` | 文本/图像/多视图转 3D、可用于游戏的 GLB/FBX 主角模型、载具、道具、建筑、武器、纹理、绑定、动画、风格化、网格转换和后处理。 | [Tripo 快速入门](https://platform.tripo3d.ai/docs/quick-start)和 [Tripo API 概览](https://www.tripo3d.ai/api)。 |
| Gemini image API | `threejs-image-generator` | `GEMINI_API_KEY` | 概念图、图像转 3D 的源图像、纹理参考、贴花、天空、背景、图标、徽标、GUI 美术以及标题/菜单美术。 | [Gemini API 密钥文档](https://ai.google.dev/gemini-api/docs/api-key)和 [Google AI Studio 密钥](https://aistudio.google.com/app/apikey)。 |
| ElevenLabs API | `threejs-audio-generator` | `ELEVENLABS_API_KEY` | 音效、环境循环、UI 声音、播报台词、对话 TTS、语音转换、音频清理和游戏音频清单。 | [ElevenLabs 快速入门](https://elevenlabs.io/docs/eleven-api/quickstart)和 [API 身份验证](https://elevenlabs.io/docs/api-reference/authentication)。 |

在 shell 配置文件中设置密钥，然后重新启动终端。

使用 `zsh` 或 `bash` 的 macOS/Linux：

```bash
export TRIPO_API_KEY="..."
export GEMINI_API_KEY="..."
export ELEVENLABS_API_KEY="..."
```

对于 `zsh`，请将这些行放入 `~/.zshrc` 或 `~/.zprofile`。对于 `bash`，请将其放入 `~/.bashrc` 或 `~/.bash_profile`。

Windows PowerShell，仅限当前终端会话：

```powershell
$env:TRIPO_API_KEY = "..."
$env:GEMINI_API_KEY = "..."
$env:ELEVENLABS_API_KEY = "..."
```

Windows PowerShell，为当前用户永久设置：

```powershell
[Environment]::SetEnvironmentVariable("TRIPO_API_KEY", "...", "User")
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "...", "User")
[Environment]::SetEnvironmentVariable("ELEVENLABS_API_KEY", "...", "User")
```

设置永久 Windows 变量后，请重新启动终端、Codex 或 Claude Code，以便智能体进程能够看到新变量。

导演技能包含凭据探测程序，它会先加载常见的 shell 配置文件，再判断密钥是否缺失。请从安装技能的位置运行它：

```bash
# Claude Code
bash ~/.claude/skills/threejs-game-director/scripts/probe_asset_credentials.sh
# Codex
bash ~/.codex/skills/threejs-game-director/scripts/probe_asset_credentials.sh
```

它会输出 `TRIPO_API_KEY=SET|MISSING`（Gemini 和 ElevenLabs 也会输出相同格式），绝不会输出密钥值。

提供商说明：

- Tripo 是可选的，但适合生成仅靠程序化代码很难达到高品质的重要 3D 表面：主角载具、Boss、武器、建筑、生物、道具和带纹理的 GLB/FBX 资产。
- Gemini 图像生成是可选的，但适合在 Tripo 图像转 3D 之前生成素材，也适合制作高质量纹理、天空、图标、徽标、贴花和 GUI 素材。
- ElevenLabs 是可选的，但可以通过交互音效、环境声、UI 反馈、语音和清理让游戏更完整。
- Google 也支持 `GOOGLE_API_KEY`，但这些技能为清晰起见统一使用 `GEMINI_API_KEY`。
- 在可用时使用提供商侧的密钥限制和配额。ElevenLabs 记录了端点作用域、额度配额和密钥处理方式；Google 建议使用环境变量，并正在引导 Gemini 用户迁移到身份验证密钥。

## 最佳入口

- 对于完整游戏、重大升级、高品质打磨、发布就绪工作或任何范围广泛的任务，请使用 `threejs-game-director`。
- 对于机制、架构、输入、镜头、物理、计分、目标和游戏手感，请使用 `threejs-gameplay-systems`。
- 当截图显得基础，或游戏需要更强的模型、材质、光照、VFX、世界细节或渲染打磨时，请使用 `threejs-aaa-graphics-builder`。
- 对于 HUD、菜单、叠加层、响应式布局、安全区域、图标、触控操作和文本适配，请使用 `threejs-game-ui-designer`。
- 对于黑屏、运行时错误、加载问题、尺寸调整/移动端错误、性能、绘制调用、三角形、纹理和内存，请使用 `threejs-debug-profiler`。
- 对于生产构建、浏览器验证、截图、画布像素、移动端检查、发布风险报告和静态托管就绪，请使用 `threejs-qa-release`。
- 对于 Tripo API 文本/图像转 3D 模型、纹理、绑定、动画、转换和 GLB/FBX 游戏资产，请使用 `threejs-3d-generator`。
- 对于 Gemini 生成的概念图、图像转 3D 输入、纹理、贴花、天空、背景、图标、徽标、GUI 美术以及标题/菜单美术，请使用 `threejs-image-generator`。
- 对于 ElevenLabs 音效、环境声、UI 声音、语音/TTS、语音转换、清理和 Three.js 音频集成，请使用 `threejs-audio-generator`。

对于大多数面向用户的游戏请求，请从 `threejs-game-director` 开始，让它引入专业技能。

## 良好使用方式

创建新游戏：

```text
Use threejs-game-director to create a AAA-inspired hover racing game from scratch.
Make it playable, add premium track visuals, vehicle feel, HUD, SFX hooks, desktop and
mobile controls, and run the full verification pass before reporting done.
```

视觉升级：

```text
Use threejs-game-director to upgrade this Three.js game from prototype visuals to
premium browser-game quality. Use the AAA graphics, UI, image, 3D, audio, debug,
and QA skills as needed. Include the visual scorecard and evidence from active-play
screenshots.
```

现有损坏的游戏：

```text
Use threejs-game-director to debug and finish this Three.js game. First get it running,
then improve gameplay feel, UI, graphics, performance, and release verification until
the remaining risks are explicit.
```

资产密集型游戏：

```text
Use threejs-game-director to build a premium space dogfight game. Use threejs-image-generator
for concepts, skies, decals, icons, and GUI art; use threejs-3d-generator for hero ships
and weapons when credentials are available; use threejs-audio-generator for SFX and
ambience. If generation is blocked, report the credential probe output and fallback plan.
```

## 预期证据

对于有实际意义的 Three.js 工作，这些技能应在宣称成功前收集证据：

- `npm run build`
- 本地浏览器运行
- 浏览器控制台和页面错误检查
- Playwright 截图
- 画布非空白像素检查，以及检查器测得的指标（色彩熵、边缘密度、亮度对比度、渲染预算行）
- 桌面端和移动端视口通过
- 主要控制路径的交互检查
- 对于范围广泛的游戏创建，提供游戏设计简报、核心循环契约和关卡/遭遇计划
- 当图形、资产、着色器或后处理发生变化时，提供性能快照
- 当高品质图形发生变化时，提供技术美术预算目标与实际值
- 当 UI 发生变化时，提供文本适配、重叠、安全区域和触控目标检查
- 对于高品质、AAA、展示级或“不那么基础”的声明，提供带有测量证据的视觉评分卡和全新视角审查
- 对于发布就绪的视觉 QA，提供视觉测试工具决策（添加/扩展/跳过截图基线）
- 对于发布就绪的玩法声明，提供机器人试玩指标
- 当生成的资产或音频属于工作范围时，提供外部资产/音频来源台账

高品质/AAA 声明不应依赖静态场景、占位立方体、通用统计卡片式 HUD 或未经验证的截图。游戏应具有可实际游玩的循环，并填写完整的视觉评分卡。

## 技能系统

- `threejs-game-director`：完整游戏构建和编排的主要入口——运行器能力检查、技能路径阶梯、阶段手册、台账和报告审计。
- `threejs-gameplay-systems`：可游玩循环、架构、游戏设计和关卡设计、机制、实体、控制、镜头、物理选型和游戏手感（顿帧、屏幕震动、缓动、冲击反馈）。
- `threejs-aaa-graphics-builder`：包含校准锚点、技术美术预算、着色器/材质手册、资产架构、模型、材质、VFX 和渲染打磨的视觉评分卡。
- `threejs-game-ui-designer`：HUD、菜单、叠加层、响应式 UI、图标、安全区域和 UI 状态。
- `threejs-debug-profiler`：场景/运行时/渲染错误、移动端错误、性能分析和渲染器指标。
- `threejs-qa-release`：浏览器 QA、截图、带测量指标的画布像素检查、视觉测试工具、机器人试玩、响应式检查、生产构建和发布风险报告。
- `threejs-3d-generator`：Tripo API 文本/图像转 3D、纹理、自动绑定、动画、转换、下载和 Three.js 导入指导。
- `threejs-image-generator`：Gemini 图像生成，用于概念图、纹理、贴花、天空、图标、GUI 美术和图像转 3D 输入。
- `threejs-audio-generator`：基于 ElevenLabs 的音效、环境声、UI 声音、语音/TTS、语音转换、清理和 Three.js 音频集成。

## 打包资源

安装后的技能是自包含的，不依赖根目录文档、根目录脚手架、根目录提示词或根目录检查清单。

- `skills/`：完整的公共软件包。每项技能都拥有所需的 `SKILL.md`、`references/`、`scripts/` 和 `assets/`。
- `skills/threejs-gameplay-systems/assets/threejs-vite-game/`：技能从空文件夹开始时使用的打包游戏脚手架。它附带确定性测试钩子（`__THREE_GAME_TEST_HOOKS__`）、带种子的随机数生成器，以及用于冒烟测试、视觉回归基线和机器人试玩的 `tests/` 模板。
- `skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs`：打包的浏览器/画布检查辅助程序——报告非空白像素、测量的视觉指标（色彩熵、边缘密度、亮度对比度）和渲染预算行；`--state`/`--seed` 驱动测试钩子，以便按状态进行确定性捕获。
- `skills/threejs-aaa-graphics-builder/assets/scorecard-anchors/`：视觉评分卡的校准参考截图。
- `scripts/`：面向维护者的本地验证辅助程序。
- `install.sh`：用于此检出目录的本地安装程序。

## 维护者检查

验证此工作流仓库：

```bash
npm install
npm run check:scripts
npm run validate:skills
```

维护者测试技能软件包时可以直接运行打包的辅助程序，但普通用户应通过智能体提示词进行交互：

```bash
python3 skills/threejs-gameplay-systems/scripts/create_threejs_game.py ../my-threejs-game
node skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --mobile
node skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --state active-play --seed 12345
```

## 许可证

MIT。请参阅 [LICENSE](LICENSE)。
