# Changelog

すべての重要な変更を記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。  

現在のバージョン順序: Unreleased / 0.1.0

## [Unreleased]

（未リリースの変更はここに記載してください）

---

## [0.1.0] - 2026-03-15

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: `kabusys`
  - エントリポイント: `src/kabusys/__init__.py` にて `__version__ = "0.1.0"`、および `__all__ = ["data", "strategy", "execution", "monitoring"]` を定義。
  - サブパッケージ（骨組み）を追加: `kabusys.data`, `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring`（各々の `__init__.py` を含む空のモジュール構成）。

- 環境変数・設定管理モジュール（`kabusys.config`）
  - .env ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: `_find_project_root()` により、`__file__` を起点に親ディレクトリで `.git` または `pyproject.toml` を探索してプロジェクトルートを特定（CWD に依存しない実装）。
  - .env パーサ: `_parse_env_line()` により .env の各行を安全にパース。
    - 空行やコメント（#）を無視。
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォートされた値を扱い、バックスラッシュによるエスケープを正しく解釈。
    - クォートなし値では、`#` が直前にスペース/タブのある場合のみコメントとみなす（値中の `#` を誤って切らない）。
  - .env 読み込み: `_load_env_file(path, override=False, protected=frozenset())`
    - ファイルが存在しない場合は無視。
    - 読み込み中にファイルオープンで失敗した場合は警告を発行して処理を続行（例外で停止しない）。
    - `override=False`（デフォルト）の場合は未設定のキーのみセット、`override=True` の場合は既存の OS 環境変数（protected）を除いて上書き。
    - OS 環境変数を保護するための `protected` 引数（frozenset）をサポート。
  - 自動ロードの優先順位:
    - OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用途等）。
    - プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - 必須設定取得: `_require(key)` により必須環境変数が未設定の場合は `ValueError` を発生させる。

- Settings クラス（`kabusys.config.Settings`）
  - 環境変数からアプリケーション設定を安全に取得するプロパティを提供。
  - 主要プロパティ:
    - J-Quants: `jquants_refresh_token`（必須: `JQUANTS_REFRESH_TOKEN`）
    - kabuステーション API: `kabu_api_password`（必須: `KABU_API_PASSWORD`）、`kabu_api_base_url`（省略時デフォルト: `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須: `SLACK_BOT_TOKEN`）、`slack_channel_id`（必須: `SLACK_CHANNEL_ID`）
    - データベースパス: `duckdb_path`（デフォルト: `data/kabusys.duckdb`）、`sqlite_path`（デフォルト: `data/monitoring.db`）
    - システム設定: `env`（`KABUSYS_ENV`、有効値: `development`, `paper_trading`, `live`）、`log_level`（`LOG_LEVEL`、有効値: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`）
    - ヘルパー: `is_live`, `is_paper`, `is_dev`
  - 不正な `KABUSYS_ENV` または `LOG_LEVEL` が設定された場合は `ValueError` を送出し、設定ミスを早期に検出。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

---

注意事項 / マイグレーション
- Settings の必須プロパティ（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）が不足していると `ValueError` が発生します。デプロイ前に .env または OS 環境変数にて設定してください。
- 自動で .env を読み込む機能は、CI/テスト等で邪魔になる場合があるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能です。
- .env のパース挙動により、値内の `#` やエスケープを含む文字列の取り扱い挙動がやや厳密です。必要に応じてクォートで囲んでエスケープしてください。

使用例
- 簡単な使用例:
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

（以降のリリースでは、変更点を Unreleased → 新バージョンへ移動して更新してください。）