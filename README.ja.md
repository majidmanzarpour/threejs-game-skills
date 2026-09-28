# Three.js ゲームスキル

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)

プレイ可能で洗練された Three.js ブラウザーゲームを構築するための、自己完結型の Codex および Claude Code スキル集です。スキルをインストールしたら、エージェントに `threejs-game-director` を使用するよう指示してください。ディレクタースキルがゲームプレイ、グラフィックス、UI、アセット生成、オーディオ、デバッグ、リリース検証を振り分けるため、ユーザーが各専門スキルを手動で選ぶ必要はありません。

このパッケージには、エージェントの実行に必要な素材が含まれています。`SKILL.md` ファイル、リファレンス、チェックリスト、プロンプトテンプレート、ヘルパースクリプトに加え、該当するスキルフォルダー内に Vite + TypeScript + Three.js のスキャフォールドが同梱されています。生成されるゲームには、決定論的テストフック、シード付き乱数生成器、スモークテスト、ビジュアルリグレッションのベースライン、ボットプレイテスト用の Playwright テンプレートが備わっており、エージェントは自らの作業をエンドツーエンドで検証できます。

[Majid Manzarpour](https://x.com/majidmanzarpour) によって作成されました。

## デモ

| ゲーム | 動画 | プレイ |
| --- | --- | --- |
| Neon Ridge Drift | [X で見る](https://x.com/majidmanzarpour/status/2064565389036540327) | [ridgedrift.netlify.app](https://ridgedrift.netlify.app) |
| Championship Snooker Arena | [X で見る](https://x.com/majidmanzarpour/status/2064673249129071096) | [snookerarena.netlify.app](https://snookerarena.netlify.app) |
| Starship Dogfight | [X で見る](https://x.com/majidmanzarpour/status/2065065340510281888) | [starshipdogfight.netlify.app](https://starshipdogfight.netlify.app) |
| Tide Singer | [X で見る](https://x.com/majidmanzarpour/status/2065570428723007555) | [tidesinger.netlify.app](https://tidesinger.netlify.app) |
| Ripcore | [X で見る](https://x.com/majidmanzarpour/status/2066687620709544070) | [ripcore.netlify.app](https://ripcore.netlify.app) |

## インストール

Codex 向けのすべてのスキルをインストールします。

```bash
npx skills add majidmanzarpour/threejs-game-skills --skill '*' -a codex -g -y
```

Claude Code 向けのすべてのスキルをインストールします。

```bash
npx skills add majidmanzarpour/threejs-game-skills --skill '*' -a claude-code -g -y
```

インストール済みの `skills` CLI がいずれかのターゲットに対応していない場合は、クローンしたチェックアウトからインストールしてください。Codex には `./install.sh --codex`、Claude Code には `./install.sh --claude`、両方には `./install.sh --all` を使用します。

クローンしたチェックアウトからローカル開発を行う場合：

```bash
./install.sh --codex
./install.sh --claude
./install.sh --all
```

ローカルインストーラーは `skills/` を選択したエージェントのスキルディレクトリにコピーします。`--force` を指定しない限り同名のスキルをスキップし、`--prune-managed` を明示的に要求しない限り、無関係なユーザースキルを削除することはありません。

```bash
./install.sh --codex --force
```

## スキルの使用方法

インストール後、空のプロジェクトフォルダー、または改善したい既存の Three.js ゲームで Codex か Claude Code を開きます。次に、求める結果をエージェントに伝え、ディレクタースキルを指定します。

```text
Use threejs-game-director to build a premium futuristic tower defense game from scratch.
Automatically use the relevant gameplay, graphics, UI, asset generation, audio, debug,
and QA skills. Build a playable loop first, then iterate until it passes browser,
mobile, visual, UI, performance, and release checks.
```

どちらの実行環境も同じ `SKILL.md` ファイルを共有し、インストール後にスキルを自動検出します。上記のプロンプトはどちらでも使用できます。

- **Claude Code** は `~/.claude/skills` からスキルを読み込み、各 `SKILL.md` の説明に基づいて振り分けます。`/threejs-game-director` でディレクターを呼び出すか、プロンプト内で名前を指定するだけで、同階層のスキルが自動的に読み込まれます。
- **Codex** は `~/.codex/skills` からスキルを読み込み、各スキルの `agents/openai.yaml` が表示名とデフォルトの開始プロンプトを提供します。プロンプト内でディレクターを指定すると、同じ方法で専門スキルが取り込まれます。

エージェントは次のことを行うべきです。

- 広範なゲーム作業では、最初に `threejs-game-director` を読み込む。
- 要求に応じて、ゲームプレイシステム、AAA グラフィックス、UI、デバッグ/プロファイリング、QA/リリース、3D 生成、画像生成、オーディオ生成の同階層スキルを読み込む。
- 空のフォルダーから始める場合は、同梱のスキャフォールドを内部で使用する。
- プロジェクト内のゲームコードを作成または更新する。
- 完了を報告する前に、ビルド、ブラウザーチェック、スクリーンショット、キャンバスピクセルチェック、モバイルビューポートチェック、QA ゲートを実行する。
- 高品質な作業では、スキル読み込み台帳、リファレンス台帳、アセット/オーディオの調達判断、ビジュアルスコアカード、残存リスクを報告する。

通常、ユーザーがスキャフォールドや QA ヘルパースクリプトを直接実行する必要はありません。これらのスクリプトは、スキルがワークフローの一部として使用できるようパッケージ化されています。

## オプションの API キー

中核となる Three.js スキルは、有料 API キーなしでも動作します。キーがない場合、ディレクターは認証情報の確認結果を報告し、外部生成をスキップして、プロシージャル/ローカルアセットにフォールバックするべきです。外部のモデル、画像、オーディオをエージェントに生成させたい場合にのみキーを追加してください。

API キーをコミットしたり、ブラウザー側のゲームコードに含めたりしないでください。これらのスキルは、ローカルのエージェントツールからプロバイダー API を使用し、生成されたアセットをゲームプロジェクトに保存します。

| プロバイダー | スキル | 環境変数 | 用途 | キーの設定 |
| --- | --- | --- | --- | --- |
| Tripo API | `threejs-3d-generator` | `TRIPO_API_KEY` | テキスト/画像/マルチビューから 3D への変換、ゲーム対応の GLB/FBX ヒーローモデル、乗り物、小物、建物、武器、テクスチャ、リギング、アニメーション、スタイル化、メッシュ変換、後処理。 | [Tripo クイックスタート](https://platform.tripo3d.ai/docs/quick-start)と [Tripo API の概要](https://www.tripo3d.ai/api)。 |
| Gemini image API | `threejs-image-generator` | `GEMINI_API_KEY` | コンセプトアート、画像から 3D への変換用ソース画像、テクスチャリファレンス、デカール、空、背景、アイコン、ロゴ、GUI アート、タイトル/メニューアート。 | [Gemini API キーのドキュメント](https://ai.google.dev/gemini-api/docs/api-key)と [Google AI Studio のキー](https://aistudio.google.com/app/apikey)。 |
| ElevenLabs API | `threejs-audio-generator` | `ELEVENLABS_API_KEY` | SFX、環境音ループ、UI サウンド、アナウンス台詞、会話 TTS、音声変換、オーディオのクリーンアップ、ゲームオーディオマニフェスト。 | [ElevenLabs クイックスタート](https://elevenlabs.io/docs/eleven-api/quickstart)と [API 認証](https://elevenlabs.io/docs/api-reference/authentication)。 |

シェルプロファイルにキーを設定し、ターミナルを再起動してください。

`zsh` または `bash` を使用する macOS/Linux：

```bash
export TRIPO_API_KEY="..."
export GEMINI_API_KEY="..."
export ELEVENLABS_API_KEY="..."
```

`zsh` では、これらの行を `~/.zshrc` または `~/.zprofile` に記述します。`bash` では、`~/.bashrc` または `~/.bash_profile` に記述します。

Windows PowerShell、現在のターミナルセッションのみ：

```powershell
$env:TRIPO_API_KEY = "..."
$env:GEMINI_API_KEY = "..."
$env:ELEVENLABS_API_KEY = "..."
```

Windows PowerShell、現在のユーザーに永続的に設定：

```powershell
[Environment]::SetEnvironmentVariable("TRIPO_API_KEY", "...", "User")
[Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "...", "User")
[Environment]::SetEnvironmentVariable("ELEVENLABS_API_KEY", "...", "User")
```

永続的な Windows 変数を設定した後は、エージェントプロセスが新しい変数を認識できるよう、ターミナル、Codex、または Claude Code を再起動してください。

ディレクタースキルには認証情報プローブが含まれています。キーがないと判断する前に、一般的なシェルプロファイルを読み込みます。スキルをインストールした場所から実行してください。

```bash
# Claude Code
bash ~/.claude/skills/threejs-game-director/scripts/probe_asset_credentials.sh
# Codex
bash ~/.codex/skills/threejs-game-director/scripts/probe_asset_credentials.sh
```

`TRIPO_API_KEY=SET|MISSING`（Gemini と ElevenLabs についても同じ形式）を表示しますが、キーの値を出力することはありません。

プロバイダーに関する注意：

- Tripo はオプションですが、プロシージャルコードだけでは高品質に仕上げにくい重要な 3D サーフェス、すなわちヒーロー用の乗り物、ボス、武器、建物、クリーチャー、小物、テクスチャ付き GLB/FBX アセットに有用です。
- Gemini の画像生成はオプションですが、Tripo の画像から 3D への変換前の素材や、高品質なテクスチャ、空、アイコン、ロゴ、デカール、GUI 素材の作成に有用です。
- ElevenLabs はオプションですが、インタラクション SFX、環境音、UI フィードバック、音声、クリーンアップによってゲームの完成度を高めるのに有用です。
- Google は `GOOGLE_API_KEY` にも対応していますが、これらのスキルでは明確さのため `GEMINI_API_KEY` に統一しています。
- 利用可能な場合は、プロバイダー側のキー制限とクォータを使用してください。ElevenLabs はエンドポイントスコープ、クレジットクォータ、シークレットキーの扱いを文書化しています。Google は環境変数を推奨し、Gemini ユーザーを認証キーへ移行しています。

## 最適なエントリーポイント

- ゲーム全体、大規模なアップグレード、高品質な仕上げ、リリース対応、または広範な作業には `threejs-game-director` を使用します。
- メカニクス、アーキテクチャ、入力、カメラ、物理、スコアリング、目標、ゲームフィールには `threejs-gameplay-systems` を使用します。
- スクリーンショットが簡素に見える場合や、より優れたモデル、マテリアル、ライティング、VFX、ワールドのディテール、レンダリングの仕上げが必要な場合は `threejs-aaa-graphics-builder` を使用します。
- HUD、メニュー、オーバーレイ、レスポンシブレイアウト、セーフエリア、アイコン、タッチ操作、テキストの収まりには `threejs-game-ui-designer` を使用します。
- ブラックスクリーン、実行時エラー、読み込み問題、リサイズ/モバイルの不具合、パフォーマンス、ドローコール、三角形、テクスチャ、メモリには `threejs-debug-profiler` を使用します。
- 本番ビルド、ブラウザー検証、スクリーンショット、キャンバスピクセル、モバイルチェック、リリースリスクレポート、静的ホスティング対応には `threejs-qa-release` を使用します。
- Tripo API によるテキスト/画像から 3D モデルへの変換、テクスチャ、リギング、アニメーション、変換、GLB/FBX ゲームアセットには `threejs-3d-generator` を使用します。
- Gemini で生成するコンセプト、画像から 3D への入力、テクスチャ、デカール、空、背景、アイコン、ロゴ、GUI アート、タイトル/メニューアートには `threejs-image-generator` を使用します。
- ElevenLabs の SFX、環境音、UI サウンド、音声/TTS、音声変換、クリーンアップ、Three.js オーディオ統合には `threejs-audio-generator` を使用します。

ユーザー向けゲームの大半の要求では、`threejs-game-director` から始め、専門スキルを取り込ませてください。

## 適切な使用例

新しいゲームの場合：

```text
Use threejs-game-director to create a AAA-inspired hover racing game from scratch.
Make it playable, add premium track visuals, vehicle feel, HUD, SFX hooks, desktop and
mobile controls, and run the full verification pass before reporting done.
```

ビジュアルアップグレードの場合：

```text
Use threejs-game-director to upgrade this Three.js game from prototype visuals to
premium browser-game quality. Use the AAA graphics, UI, image, 3D, audio, debug,
and QA skills as needed. Include the visual scorecard and evidence from active-play
screenshots.
```

既存の壊れたゲームの場合：

```text
Use threejs-game-director to debug and finish this Three.js game. First get it running,
then improve gameplay feel, UI, graphics, performance, and release verification until
the remaining risks are explicit.
```

アセットを多用するゲームの場合：

```text
Use threejs-game-director to build a premium space dogfight game. Use threejs-image-generator
for concepts, skies, decals, icons, and GUI art; use threejs-3d-generator for hero ships
and weapons when credentials are available; use threejs-audio-generator for SFX and
ambience. If generation is blocked, report the credential probe output and fallback plan.
```

## 期待される証拠

重要な Three.js 作業では、成功を報告する前にスキルが証拠を収集するべきです。

- `npm run build`
- ローカルブラウザーでの実行
- ブラウザーコンソールとページエラーの確認
- Playwright のスクリーンショット
- キャンバスの非空白ピクセルチェックと、インスペクターによる測定指標（色エントロピー、エッジ密度、輝度コントラスト、レンダリング予算行）
- デスクトップおよびモバイルビューポートの合格
- 主要操作経路のインタラクションチェック
- 広範なゲーム作成に対するゲームデザイン概要、コアループ契約、レベル/エンカウンター計画
- グラフィックス、アセット、シェーダー、後処理を変更した場合のパフォーマンススナップショット
- 高品質なグラフィックスを変更した場合のテクニカルアート予算の目標値と実績値
- UI を変更した場合のテキストの収まり、重なり、セーフエリア、タッチターゲットのチェック
- 高品質、AAA、ショーケース、または「もっと高度に」という主張に対する、測定証拠付きビジュアルスコアカードと新たな視点でのレビュー
- リリース対応のビジュアル QA に対するビジュアルテストハーネスの判断（スクリーンショットベースラインの追加/拡張/省略）
- リリース対応のゲームプレイに関する主張に対するボットプレイテストの指標
- 生成アセットやオーディオが対象に含まれる場合の外部アセット/オーディオ調達台帳

高品質/AAA という主張は、静的なシーン、プレースホルダーの立方体、一般的な統計カード型 HUD、未検証のスクリーンショットに依存するべきではありません。ゲームには実際にプレイ可能なループと、記入済みのビジュアルスコアカードが必要です。

## スキルシステム

- `threejs-game-director`：ゲーム全体の構築とオーケストレーションの主要エントリーポイント——実行環境の機能確認、スキルパスの段階、フェーズプレイブック、台帳、レポート監査。
- `threejs-gameplay-systems`：プレイ可能なループ、アーキテクチャ、ゲームデザインとレベルデザイン、メカニクス、エンティティ、操作、カメラ、物理選択、ゲームフィール（ヒットストップ、画面揺れ、イージング、衝撃フィードバック）。
- `threejs-aaa-graphics-builder`：キャリブレーションアンカー、テクニカルアート予算、シェーダー/マテリアルのクックブック、アセットアーキテクチャ、モデル、マテリアル、VFX、レンダリングの仕上げを含むビジュアルスコアカード。
- `threejs-game-ui-designer`：HUD、メニュー、オーバーレイ、レスポンシブ UI、アイコン、セーフエリア、UI 状態。
- `threejs-debug-profiler`：シーン/実行時/レンダリングの不具合、モバイルの不具合、パフォーマンスプロファイリング、レンダラーの指標。
- `threejs-qa-release`：ブラウザー QA、スクリーンショット、測定指標付きキャンバスピクセル、ビジュアルテストハーネス、ボットプレイテスト、レスポンシブチェック、本番ビルド、リリースリスクレポート。
- `threejs-3d-generator`：Tripo API によるテキスト/画像から 3D への変換、テクスチャ、自動リギング、アニメーション、変換、ダウンロード、Three.js へのインポート指針。
- `threejs-image-generator`：コンセプト、テクスチャ、デカール、空、アイコン、GUI アート、画像から 3D への入力向けの Gemini 画像生成。
- `threejs-audio-generator`：ElevenLabs を利用した SFX、環境音、UI サウンド、音声/TTS、音声変換、クリーンアップ、Three.js オーディオ統合。

## パッケージ化されたリソース

インストールされたスキルは自己完結型です。ルートのドキュメント、スキャフォールド、プロンプト、チェックリストには依存しません。

- `skills/`：完全な公開パッケージ。各スキルは、必要な `SKILL.md`、`references/`、`scripts/`、`assets/` を所有します。
- `skills/threejs-gameplay-systems/assets/threejs-vite-game/`：スキルが空のフォルダーから開始する際に使用する、パッケージ化されたゲームスキャフォールド。決定論的テストフック（`__THREE_GAME_TEST_HOOKS__`）、シード付き乱数生成器、スモークテスト、ビジュアルリグレッションのベースライン、ボットプレイテスト用の `tests/` テンプレートを備えています。
- `skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs`：パッケージ化されたブラウザー/キャンバス検査ヘルパー——非空白ピクセル、測定されたビジュアル指標（色エントロピー、エッジ密度、輝度コントラスト）、レンダリング予算行を報告します。`--state`/`--seed` はテストフックを駆動し、状態ごとの決定論的キャプチャを行います。
- `skills/threejs-aaa-graphics-builder/assets/scorecard-anchors/`：ビジュアルスコアカード用のキャリブレーション参照スクリーンショット。
- `scripts/`：メンテナー向けのローカル検証ヘルパー。
- `install.sh`：このチェックアウトで作業するためのローカルインストーラー。

## メンテナーチェック

このワークフローリポジトリを検証します。

```bash
npm install
npm run check:scripts
npm run validate:skills
```

メンテナーはスキルパッケージのテスト時に、パッケージ化されたヘルパーを直接実行できます。ただし、通常のユーザーはエージェントへのプロンプトを通じて操作するべきです。

```bash
python3 skills/threejs-gameplay-systems/scripts/create_threejs_game.py ../my-threejs-game
node skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --mobile
node skills/threejs-qa-release/scripts/inspect-threejs-canvas.mjs --url http://127.0.0.1:5188 --state active-play --seed 12345
```

## ライセンス

MIT。詳細は [LICENSE](LICENSE) を参照してください。
