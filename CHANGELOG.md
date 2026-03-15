CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。

フォーマット:
- 変更はカテゴリ別（Added, Changed, Fixed, Removed, Deprecated, Security）にまとめています。
- バージョンと日付を併記しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-03-15
------------------

Added
- 初期リリース。kabusys パッケージの基本構成と主要機能を追加。
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、公開モジュール（data, strategy, execution, monitoring）を __all__ に設定。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数からの設定読み込み機能を実装。
  - プロジェクトルートの自動検出: .git または pyproject.toml を探索してプロジェクトルートを決定（CWD に依存しない実装）。
  - .env パーサ実装: コメント行、export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォートなしの場合は '#' の直前がスペース/タブのときのみコメントとして扱う）を実装。
  - .env 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - _load_env_file による読み込み時に既存 OS 環境変数を保護する protected 機構を実装（override フラグあり）。
  - Settings クラスを追加し、アプリケーション設定をプロパティで提供:
    - J-Quants: jquants_refresh_token (必須)
    - kabuステーション API: kabu_api_password (必須)、kabu_api_base_url（デフォルト "http://localhost:18080/kabusapi"）
    - Slack: slack_bot_token, slack_channel_id（いずれも必須）
    - データベース: duckdb_path（デフォルト data/kabusys.duckdb）、sqlite_path（デフォルト data/monitoring.db）
    - システム設定: env (development/paper_trading/live の検証)、log_level（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）、is_live/is_paper/is_dev のヘルパー
  - 必須環境変数未設定時は明示的に ValueError を送出し、.env.example を参照するよう案内。
- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の4層に対応するテーブル DDL を定義:
    - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
    - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature レイヤー: features, ai_scores
    - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な PRIMARY KEY、CHECK 制約、DEFAULT 値、外部キー制約を設定。
  - パフォーマンスを考慮したインデックスを複数定義（銘柄×日付スキャンやステータス検索を想定）。
  - init_schema(db_path) を実装:
    - 指定した DuckDB ファイルを初期化し、DDL とインデックスを順次実行。既存テーブルはスキップ（冪等）。
    - db_path の親ディレクトリを自動作成（":memory:" の場合はインメモリ DB を使用可能）。
    - 初期化済みの duckdb 接続を返す。
  - get_connection(db_path) を実装: 既存 DB への接続を返す（スキーマ初期化は行わない）。
- パッケージ構造
  - 空のサブパッケージ（プレースホルダ）を追加: src/kabusys/execution, src/kabusys/strategy, src/kabusys/data, src/kabusys/monitoring（将来的な実装箇所を明確化）。

Notes / Usage
- 初回利用時は必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定してください。未設定時は Settings のプロパティ参照で ValueError が発生します。
- DB を用いる場合は init_schema() を実行してスキーマを初期化してください。例:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- 自動 .env 読み込みを無効化したいテスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Known issues / Limitations
- 現時点では strategy / execution / monitoring の具体実装は含まれておらず、各サブパッケージはプレースホルダです。
- マイグレーションツール（スキーマ変更管理）は未実装のため、スキーマ変更時は手動対応が必要です。
- 並列アクセスやトランザクション設計に関する運用上の指針は含まれていません（DuckDB の特性に依存）。

Changed
- なし

Fixed
- なし

Removed
- なし

Security
- なし

---

（補足）この CHANGELOG はコードベースから推測して作成した初期リリース記録です。実際のリリースノートや運用ドキュメントと差異がある場合はそちらを優先してください。