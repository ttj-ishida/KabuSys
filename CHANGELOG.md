# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従い、セマンティックバージョニングを使用します。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-15
初回公開リリース。

### Added
- パッケージ初期化
  - パッケージメタ情報を追加: バージョン `0.1.0` を `src/kabusys/__init__.py` に設定。
  - パッケージの公開モジュールを `__all__ = ["data", "strategy", "execution", "monitoring"]` として定義（各サブパッケージの雛形を用意）。
- 環境変数・設定管理モジュールを追加 (`src/kabusys/config.py`)
  - .env ファイルや OS 環境変数から設定を読み込む Settings クラスを実装。
  - 利用例ドキュメントを追加（モジュールトップの docstring）。
  - 自動ロード機能:
    - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env/.env.local を自動で読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - テスト等で自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサ実装:
    - 行単位でパースし、空行やコメント行（# で始まる）を無視。
    - `export KEY=val` 形式に対応。
    - クォートあり（シングル/ダブル）の値を正しく扱い、バックスラッシュによるエスケープを解釈。
    - クォートなしの値では、`#` が直前にスペースまたはタブを伴う場合にのみインラインコメントとして扱う挙動を実装。
  - .env 読み込み制御:
    - `override` フラグにより既存の環境変数を上書き可能（ただし protected に含まれるキーは上書きしない）。
    - OS 環境変数を protected として扱い、.env による上書きを防止。
  - 必須環境変数の取得ユーティリティ `_require` を実装。未設定時は ValueError を送出し、.env.example を参照するよう案内。
  - Settings プロパティ（主な項目）:
    - J-Quants / kabuステーション / Slack などの必須トークン/設定取得（例: `jquants_refresh_token`, `kabu_api_password`, `slack_bot_token`, `slack_channel_id`）。
    - `kabu_api_base_url` にデフォルト `http://localhost:18080/kabusapi` を設定可能。
    - データベース関連のパスにデフォルトを設定（`duckdb_path` のデフォルト `data/kabusys.duckdb`、`sqlite_path` のデフォルト `data/monitoring.db`）。
    - 環境 (`KABUSYS_ENV`) の検証: 有効な値は `development`, `paper_trading`, `live`。無効な値は ValueError。
    - ログレベル (`LOG_LEVEL`) の検証: 有効な値は `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`。無効な値は ValueError。
    - 環境判定プロパティ: `is_live`, `is_paper`, `is_dev` を提供。
- サブパッケージ雛形の追加
  - `src/kabusys/data/__init__.py`
  - `src/kabusys/strategy/__init__.py`
  - `src/kabusys/execution/__init__.py`
  - `src/kabusys/monitoring/__init__.py`
  - （いずれも現時点ではモジュール初期化ファイルのみ）

### Changed
- 該当なし（初版のため）

### Fixed
- 該当なし（初版のため）

### Deprecated
- 該当なし

### Removed
- 該当なし

### Security
- 環境変数の自動上書きを防ぐため、OS 環境変数を保護する仕組みを導入（.env による意図しない上書きを防止）。

注意:
- .env の読み込みはプロジェクトルートの特定に依存するため、パッケージ配布後の動作や異なるファイル構成での挙動を確認してください。
- 必須設定が未提供の場合は起動時に ValueError が発生します。README や .env.example を用意して利用方法を文書化することを推奨します。