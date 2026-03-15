CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-03-15
--------------------

Added
-----

- 初回リリース: KabuSys 日本株自動売買システムの基盤モジュールを追加。
  - パッケージ初期化
    - src/kabusys/__init__.py にパッケージバージョン (__version__ = "0.1.0") と公開サブパッケージ一覧を定義（data, strategy, execution, monitoring）。
  - 環境設定管理モジュール（src/kabusys/config.py）
    - .env ファイルまたは OS 環境変数から設定を読み込む機能を実装。
    - プロジェクトルート検出: __file__ の親ディレクトリから .git または pyproject.toml を探索してプロジェクトルートを特定するロジックを追加（カレントワーキングディレクトリに依存しない）。
    - .env パーサを実装:
      - 空行やコメント行（#）の無視、`export KEY=val` 形式への対応。
      - シングル/ダブルクォート付き値の扱い（バックスラッシュエスケープを考慮）。
      - クォート無し値の行内コメント判定（# の直前がスペース/タブの場合にコメント扱い）。
    - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートが見つからない場合は自動ロードをスキップ。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用）。
    - 環境変数保護: OS の既存環境変数は protected として上書きを防ぐ実装（.env.local の override を許可するが protected は除外）。
    - 必須設定取得ヘルパー _require() を実装し、未設定時は ValueError を投げる。
    - Settings クラスを追加し、以下のプロパティを定義:
      - J-Quants / kabuステーション / Slack / データベースパス / システム設定関連（例: jquants_refresh_token, kabu_api_password, kabu_api_base_url(default: http://localhost:18080/kabusapi), slack_bot_token, slack_channel_id, duckdb_path(default: data/kabusys.duckdb), sqlite_path(default: data/monitoring.db)）。
      - KABUSYS_ENV の妥当性チェック（許可値: development, paper_trading, live）。無効値は ValueError。
      - LOG_LEVEL の妥当性チェック（許可値: DEBUG, INFO, WARNING, ERROR, CRITICAL）。無効値は ValueError。
      - 環境判定ヘルパー: is_live, is_paper, is_dev。
  - データベーススキーマ定義モジュール（src/kabusys/data/schema.py）
    - DuckDB 用のスキーマを定義（3 層 + 実行層のテーブル群）:
      - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
      - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature Layer: features, ai_scores
      - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルに対して型・NULL制約・CHECK 制約・PRIMARY KEY・外部キー（必要箇所）を定義。
    - よく使うクエリに備えたインデックス群を定義（例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status など）。
    - init_schema(db_path) を実装:
      - 指定 DB (ファイルパスまたは ":memory:") に対してテーブルとインデックスを作成する。冪等で既存テーブルはスキップ。
      - db_path がファイルパスの場合、親ディレクトリが存在しなければ自動で作成する。
      - 初期化済みの duckdb 接続オブジェクト（DuckDBPyConnection）を返す。
    - get_connection(db_path) を実装:
      - 既存の DuckDB に接続するための薄いラッパー。スキーマ初期化は行わない（初回は init_schema を使用すること）。
  - パッケージ構成に空のサブパッケージプレースホルダを追加:
    - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py

Notes / Migration
-----------------

- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定の場合 Settings の各プロパティ参照時に ValueError が発生します。 .env.example を基に .env を準備してください。
- デフォルト値:
  - KABUSYS_API_BASE_URL: http://localhost:18080/kabusapi
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - LOG_LEVEL: INFO
- 自動 .env 読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に決定します。パッケージ配布後やテスト環境で CWD が変わる場合でも動作するよう設計されていますが、プロジェクトルートが検出できない環境では自動読み込みは行われません。
  - 自動読み込みを明示的に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB 初期化:
  - init_schema はデータファイルの親ディレクトリを自動作成します。ファイルベースの DB を使う場合はファイルパスの親ディレクトリ作成権限に注意してください。
  - スキーマは冪等に作成されるため既存データベースにも安全に適用できます。

Changed
-------

- なし（初回リリース）

Fixed
-----

- なし（初回リリース）