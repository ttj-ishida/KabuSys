# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース

### 追加
- パッケージの基本構成を追加
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`（src/kabusys/__init__.py）
  - 公開モジュール一覧: `__all__ = ["data", "strategy", "execution", "monitoring"]`（src/kabusys/__init__.py）
  - 空のサブパッケージを作成: `data`, `strategy`, `execution`, `monitoring`（各 __init__.py を配置）

- 環境設定・ロード機能を追加（src/kabusys/config.py）
  - Settings クラスを実装し、アプリケーション設定を環境変数から参照可能にしました。
    - 必須設定として取得するプロパティ:
      - J-Quants: `jquants_refresh_token`（環境変数 `JQUANTS_REFRESH_TOKEN`）
      - kabuステーション API: `kabu_api_password`（環境変数 `KABU_API_PASSWORD`）
      - Slack: `slack_bot_token`（環境変数 `SLACK_BOT_TOKEN`）、`slack_channel_id`（環境変数 `SLACK_CHANNEL_ID`）
    - 任意またはデフォルト値ありの設定:
      - `kabu_api_base_url`（環境変数 `KABU_API_BASE_URL`、デフォルト: `http://localhost:18080/kabusapi`）
      - データベースパス: `duckdb_path`（環境変数 `DUCKDB_PATH`、デフォルト: `data/kabusys.duckdb`）
      - 監視用 SQLite パス: `sqlite_path`（環境変数 `SQLITE_PATH`、デフォルト: `data/monitoring.db`）
    - 実行環境判定・ログレベル検証:
      - `env`（環境変数 `KABUSYS_ENV`、有効値: `development`, `paper_trading`, `live`。デフォルト: `development`）
      - `log_level`（環境変数 `LOG_LEVEL`、有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。デフォルト: `INFO`）
      - 環境判定プロパティ: `is_live`, `is_paper`, `is_dev`

  - 自動 .env ロード機能
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - プロジェクトルートの検出は `__file__` を起点に親ディレクトリを探索し、`.git` または `pyproject.toml` を基準に行う（配布後も動作するように CWD に依存しない実装）
    - 自動ロードを無効化するための環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
    - OS の既存環境変数は保護（.env/.env.local による上書き防止）。ただし `.env.local` は `override=True` の扱いで優先して読み込む（保護された OS 環境変数を除く）

  - .env 解析の強化
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォートされた値におけるバックスラッシュエスケープを考慮して正確にパース
    - クォートされていない値に対しては `#` をインラインコメントとして扱う際に直前がスペースまたはタブである場合のみコメントと認識（誤認防止のため）
    - 無効行・コメント行（先頭 `#`）は無視
    - ファイル読み込み時に OSError が発生した場合は警告を出して続行

  - 環境変数の読み込みロジックを分離した関数:
    - `_find_project_root()`：プロジェクトルート検出
    - `_parse_env_line()`：1行のパース
    - `_load_env_file()`：.env ファイルの読み込みと os.environ への反映（override/protected 対応）
    - `_require()`：必須環境変数の取得（未設定時は ValueError）

  - settings シングルトンの提供: `from kabusys.config import settings` で利用可能

### 変更
- なし（初版のため）

### 修正
- なし（初版のため）

---

注記:
- .env 自動読み込みはプロジェクトルートが特定できない場合はスキップされます（ライブラリ配布後の安全策）。
- 設定の検証（env/log_level）は早期に不正な値を検出するため ValueError を送出します。プロダクションで利用する際は適切な環境変数を設定してください。