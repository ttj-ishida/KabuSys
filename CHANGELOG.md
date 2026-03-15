# CHANGELOG

すべての重要な変更はここに記録します。本ファイルは「Keep a Changelog」規約に従っています。

フォーマットの規約: https://keepachangelog.com/ja/1.0.0/

※この CHANGELOG は、提供されたコードベースの内容から推測して作成した初期の変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-15
初期リリース。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージの公開バージョンを 0.1.0 に設定。
  - __all__ に `data`, `strategy`, `execution`, `monitoring` を追加し、主要サブパッケージを公開。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定値を読み込む設定モジュールを追加。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。
  - .env ファイルの自動読み込みを実装（優先順位: OS環境変数 > .env.local > .env）。
  - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサを実装:
    - 空行・コメント行のスキップ。
    - `export KEY=val` 形式に対応。
    - シングルクォート／ダブルクォートのサポート（バックスラッシュエスケープ対応、閉じクォート以降は無視）。
    - クォート無し値でのインラインコメント判定ルール（'#' の直前が空白／タブの場合にコメントと認識）。
  - .env 読み込み時の挙動:
    - override=False: 未設定のキーのみ設定。
    - override=True: OS 環境変数（保護されたキー）を上書きしない形で上書き。
    - 読み込み失敗時は警告を発行（例外は送出しない）。
  - Settings クラスを追加し、以下のプロパティを提供:
    - J-Quants: jquants_refresh_token（必須）
    - kabuステーション API: kabu_api_password（必須）、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
    - Slack: slack_bot_token（必須）、slack_channel_id（必須）
    - データベースパス: duckdb_path（デフォルト: data/kabusys.duckdb）、sqlite_path（デフォルト: data/monitoring.db）
    - システム設定: env（KABUSYS_ENV。許可値: development, paper_trading, live）、log_level（LOG_LEVEL。許可値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
    - 環境判定プロパティ: is_live, is_paper, is_dev
  - 必須環境変数未設定時は ValueError を送出するユーティリティを追加。

- データスキーマ (src/kabusys/data/schema.py)
  - DuckDB 用のデータベーススキーマ定義を追加。3 層構造（Raw / Processed / Feature）と Execution 層を想定したテーブルを含む。
  - Raw レイヤー（例）:
    - raw_prices, raw_financials, raw_news, raw_executions（基本の生データ保存テーブル）
  - Processed レイヤー（例）:
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤー:
    - features, ai_scores
  - Execution レイヤー:
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型制約、NULL 制約、チェック制約、主キー、外部キー制約を定義（例: side カラムの CHECK、size の正値チェック等）。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）。
  - テーブル作成順を依存関係に配慮して定義（外部キー制約を考慮）。
  - スキーマ初期化関数を提供:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - ファイルシステムの親ディレクトリを自動作成（:memory: をサポート）。
      - 全 DDL とインデックスを実行し、冪等にテーブルを作成。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB への接続を返す（スキーマ初期化は行わない旨を明記）。

- 空のパッケージモジュールを追加
  - src/kabusys/execution/__init__.py
  - src/kabusys/strategy/__init__.py
  - src/kabusys/data/__init__.py
  - src/kabusys/monitoring/__init__.py
  - （今後の拡張ポイントとしてプレースホルダ）

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

---

[0.1.0]: -