# Changelog

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

- リリース履歴は逆順（最新が上）で記載しています。
- 日付はリリース日を示します。

## [Unreleased]
（無し）

## [0.1.0] - 2026-03-15

### Added
- 初回リリース: `kabusys` パッケージを導入。
  - パッケージメタ情報: `__version__ = "0.1.0"`。
  - エクスポート対象モジュール: `data`, `strategy`, `execution`, `monitoring`（各サブパッケージのプレースホルダを含む）。

- 環境設定管理モジュールを追加 (`src/kabusys/config.py`)。
  - .env ファイルまたは OS 環境変数から設定を読み込む仕組みを実装。
  - プロジェクトルート自動検出:
    - 現在ファイル位置から親ディレクトリを辿り、`.git` または `pyproject.toml` を基準にプロジェクトルートを判定する関数 `_find_project_root()` を実装。
    - プロジェクトルートが見つからない場合は自動読み込みをスキップ。
  - 自動読み込みの挙動:
    - 読み込み優先順位は OS 環境変数 > `.env.local` > `.env`。
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト用途などを想定）。
    - OS 環境変数を保護するため、既存の OS 環境変数はデフォルトで上書きされない（ただし `.env.local` は override=True として読み込まれ、保護キーは依然として上書きされない）。
  - .env パーサーの実装:
    - `export KEY=val` 形式をサポート。
    - シングルクォート/ダブルクォートで囲まれた値に対してバックスラッシュによるエスケープを解釈し、対応する閉じクォートまでを値として扱う。
    - クォートなしの値については、`#` をインラインコメントと見なす条件を厳密に判定（`#` の直前が空白またはタブの場合のみコメントとして扱う）。
    - 無効行（空行や `#` で始まる行、`KEY=val` 形式でない行）は無視。
  - ファイル読み込み時の安全性:
    - ファイルオープンに失敗した場合は警告を発生 (`warnings.warn`) し、処理を継続（例外でプロセスを停止しない）。

- 設定ラッパー `Settings` クラスを提供。
  - 各種設定をプロパティとして公開し、必要に応じて環境変数を必須化するメソッド `_require()` を利用。
  - 主要プロパティ:
    - J-Quants: `jquants_refresh_token` (`JQUANTS_REFRESH_TOKEN` が必須)
    - kabuステーション API:
      - `kabu_api_password` (`KABU_API_PASSWORD` が必須)
      - `kabu_api_base_url`（デフォルト `http://localhost:18080/kabusapi`）
    - Slack:
      - `slack_bot_token` (`SLACK_BOT_TOKEN` が必須)
      - `slack_channel_id` (`SLACK_CHANNEL_ID` が必須)
    - データベースパス:
      - `duckdb_path`（デフォルト `data/kabusys.duckdb`、`Path.expanduser()` を適用）
      - `sqlite_path`（デフォルト `data/monitoring.db`、`Path.expanduser()` を適用）
    - システム設定:
      - `env`（`KABUSYS_ENV`、既定は `development`。許容値: `development`, `paper_trading`, `live`。不正値は `ValueError` を送出）
      - `log_level`（`LOG_LEVEL`、既定は `INFO`。許容値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。不正値は `ValueError` を送出）
      - 補助ブールプロパティ: `is_live`, `is_paper`, `is_dev`（`env` の判定を簡易にするためのラッパー）

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Removed
- なし（初回リリース）

Notes
- 必須環境変数が未設定の場合、`Settings` のアクセスは `ValueError` を投げます。実行環境では必要な環境変数を `.env` または OS 環境として設定してください。
- .env 読み込みの細かい振る舞い（コメントの解釈・クォートのエスケープ処理・エクスポート文のサポートなど）は、既存の .env フォーマットの互換性を考慮して実装されていますが、特殊ケースでは期待どおりに動作しない可能性があるため注意してください。