# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。  

## [Unreleased]


## [0.1.0] - 2026-03-15
初回リリース

### Added
- パッケージの基本骨格を追加
  - パッケージ名: `kabusys`
  - エクスポートモジュール: `data`, `strategy`, `execution`, `monitoring`
- 環境変数・設定管理モジュールを追加 (`src/kabusys/config.py`)
  - プロジェクトルート自動検出:
    - 現在ファイル位置を起点に親ディレクトリを探索し、`.git` または `pyproject.toml` を見つけてプロジェクトルートを特定
    - ルートが見つからない場合は自動ロードをスキップ
  - .env ファイル読み込み機能:
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - `.env` の読み込みはプロジェクトルートから行う
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` 環境変数で自動ロードを無効化可能（テスト用）
    - ファイルが開けない場合は警告を出して処理を続行
    - OS上の既存環境変数は保護され、デフォルトでは上書きされない（`.env.local` は上書きを許可）
  - .env の行パーサーを実装:
    - コメント行・空行を無視
    - `export KEY=val` 形式に対応
    - シングル／ダブルクォートで囲まれた値の扱い（バックスラッシュによるエスケープを考慮）
    - クォートなし値でのインラインコメント認識（`#` の直前がスペースまたはタブの場合のみ）
  - 環境変数読み込みの振る舞い:
    - `_load_env_file(path, override=False, protected=frozenset(...))` により、`override` と `protected` を指定して読み込み動作を制御
- Settings クラス（アプリケーション設定）を追加
  - 必須設定を取得する `_require(key)` を内部で利用し、未設定時は分かりやすいエラーメッセージで `ValueError` を送出
  - 以下のプロパティを提供:
    - J-Quants: `jquants_refresh_token`（必須: `JQUANTS_REFRESH_TOKEN`）
    - kabuステーション API: `kabu_api_password`（必須: `KABU_API_PASSWORD`）、`kabu_api_base_url`（デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須: `SLACK_BOT_TOKEN`）、`slack_channel_id`（必須: `SLACK_CHANNEL_ID`）
    - データベースパス: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`） — Path オブジェクトを返す
    - システム設定: `env`（`development` / `paper_trading` / `live` のいずれか。デフォルト `development`、不正値は `ValueError`）、`log_level`（`DEBUG|INFO|WARNING|ERROR|CRITICAL`、デフォルト `INFO`、不正値は `ValueError`）
    - 環境判定ヘルパー: `is_live`, `is_paper`, `is_dev`
  - 環境変数名の一覧（必須）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など
- パッケージ空ディレクトリ（モジュール初期化ファイル）を追加:
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
  - （現時点ではプレースホルダ）

### Fixed
- .env 読み込み時のエラーをワーニング出力して処理を続行するようにし、ユーザーの作業を妨げないよう改善

### Notes / Migration
- 初回リリースのため、API としては最小限の設定取得機能に留まります。端末や CI 環境で動作させる際には、必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定してください。
- 自動で .env を読み込ませたくない場合は、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- .env の記法は一般的な形式をサポートしていますが、特殊なケース（複雑なクォートやコメントの扱い）では挙動に注意してください。

### Breaking Changes
- なし（初回リリース）

---

(この CHANGELOG はコードベースから推測して作成しています。実際の機能追加や変更がある場合は適宜更新してください。)