# CHANGELOG

すべての重要な変更は Keep a Changelog のガイドラインに従って記載しています。  
このファイルはコードベースから推測できる変更内容・機能を元に作成しています。

全般: 日付は 2026-03-15 に設定しています。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。

### Added
- パッケージ構成を追加
  - パッケージ名: `kabusys`
  - エクスポート: `__all__ = ["data", "strategy", "execution", "monitoring"]`
  - バージョン: `__version__ = "0.1.0"`

- 環境設定管理モジュールを追加 (`src/kabusys/config.py`)
  - .env ファイルや環境変数から設定値を読み込む Settings クラスを提供。
  - 自動ロードの挙動:
    - プロジェクトルート（`.git` または `pyproject.toml` を基準）を基に `.env` / `.env.local` を自動読み込み。
    - 読み込み優先順位: OS 環境変数 > `.env.local` > `.env`
    - 自動ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をサポート（テスト用途等）。
  - .env パーサを実装（堅牢なパース機能）
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォート有無に応じた挙動）
    - 無効行（空行、コメント行、不正な行）をスキップ
  - .env 読み込み時の保護機能
    - OS 環境変数を保護する `protected` セットを利用し、`override` フラグにより上書き挙動を制御
  - 必須環境変数の取得ヘルパ `_require()`（未設定時は ValueError を送出）
  - 提供される主要設定項目（プロパティ）
    - J-Quants: `jquants_refresh_token`（必須: `JQUANTS_REFRESH_TOKEN`）
    - kabu API: `kabu_api_password`（必須: `KABU_API_PASSWORD`）、`kabu_api_base_url`（デフォルト `http://localhost:18080/kabusapi`）
    - Slack: `slack_bot_token`（必須: `SLACK_BOT_TOKEN`）、`slack_channel_id`（必須: `SLACK_CHANNEL_ID`）
    - データベースパス: `duckdb_path`（デフォルト `data/kabusys.duckdb`）、`sqlite_path`（デフォルト `data/monitoring.db`）
    - 実行環境判定と検証: `env`（有効値: `development`, `paper_trading`, `live`）、`log_level`（有効値: `DEBUG`,`INFO`,`WARNING`,`ERROR`,`CRITICAL`）、`is_live`/`is_paper`/`is_dev`

- DuckDB スキーマ定義と初期化モジュールを追加 (`src/kabusys/data/schema.py`)
  - データレイヤ構成（コメント・設計に従う）
    - Raw Layer: 生データ（raw_prices, raw_financials, raw_news, raw_executions）
    - Processed Layer: 整形済みデータ（prices_daily, market_calendar, fundamentals, news_articles, news_symbols）
    - Feature Layer: 戦略/AI 用特徴量（features, ai_scores）
    - Execution Layer: シグナル〜注文〜トレード〜ポジション（signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）
  - 各テーブルの DDL 定義を実装
    - 主キー、外部キー、CHECK 制約（負数・列範囲・enum 系チェック等）を含む丁寧なスキーマ
    - 例: `prices_daily` の low <= high チェック、`raw_executions.side` といった列に対する IN チェックなど
  - よく使うクエリのためのインデックス定義を追加（銘柄×日付、ステータス検索等）
  - スキーマ初期化 API
    - `init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 指定 DB に対して全テーブルとインデックスを作成（冪等）
      - `:memory:` のサポート
      - ファイル DB の場合は親ディレクトリを自動作成
    - `get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection`
      - 既存 DB への接続を返す（スキーマ初期化は行わない）
  - 主要テーブル/インデックスの一覧化によりマイグレーション設計やクエリ最適化に配慮

- モジュールプレースホルダを追加
  - `src/kabusys/execution/__init__.py`（空の初期化）
  - `src/kabusys/strategy/__init__.py`（空の初期化）
  - `src/kabusys/data/__init__.py`（空の初期化）
  - `src/kabusys/monitoring/__init__.py`（空の初期化）
  - これにより将来的な機能拡張のための名前空間を確保

### Changed
- 初回リリースのため特になし（初期機能追加のみ）

### Fixed
- 初回リリースのため特になし

### Removed
- 初回リリースのため特になし

### Security
- 初回リリースのため特になし

---

補足（使い方・注意点）
- 自動 .env ロードを抑止する場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます。
- .env の読み込み順と上書きルール:
  - OS 環境変数は常に優先され、`.env` は既存キーを上書きしない（デフォルト）。`.env.local` は上書き可能（override=True）としてロードされる。
- 必須環境変数が未設定の場合、Settings の対応プロパティ呼び出しで ValueError が発生します（明示的なエラー通知）。
- DuckDB スキーマ初期化の使用例:
  - `from kabusys.data.schema import init_schema; conn = init_schema(settings.duckdb_path)`
  - 初回は init_schema を呼び、以降は get_connection を使うことが推奨されます。

（この CHANGELOG はコードを解析して推測した内容に基づいて作成しています。実際のリリースノートや仕様変更があれば適宜更新してください。）