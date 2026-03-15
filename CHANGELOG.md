# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-15
初回リリース。

### Added
- パッケージ初期化
  - パッケージメタデータを追加（src/kabusys/__init__.py）
    - __version__ = "0.1.0"
    - __all__ に ["data", "strategy", "execution", "monitoring"] を定義

- 環境設定管理モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定をロードする自動ロード機能を実装
    - プロジェクトルートを .git または pyproject.toml から検出して .env / .env.local を読み込む（CWD に依存しない探索）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途を想定）
  - .env パーサの実装（_parse_env_line）
    - コメント行と空行を無視
    - export KEY=val 形式をサポート
    - シングル／ダブルクォートで囲まれた値のエスケープ処理に対応（バックスラッシュによるエスケープを適切に解釈）
    - クォートなしの場合、インラインコメント判定を空白の前後ルールに基づいて処理
  - .env のロード処理（_load_env_file）
    - override フラグと protected キーセットで OS 環境変数の上書きを制御
    - ファイル読み込み失敗時に警告を発行
  - Settings クラスによる環境変数ラッパー
    - J-Quants、kabuステーション API、Slack、データベースパス等のプロパティを提供
      - jquants_refresh_token (必須)
      - kabu_api_password (必須)
      - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - slack_bot_token (必須)
      - slack_channel_id (必須)
      - duckdb_path (デフォルト: data/kabusys.duckdb)
      - sqlite_path (デフォルト: data/monitoring.db)
    - システム設定の検証付きプロパティ
      - env (KABUSYS_ENV): development / paper_trading / live のいずれかを許容、無効値は ValueError を送出
      - log_level (LOG_LEVEL): DEBUG/INFO/WARNING/ERROR/CRITICAL の検査
      - is_live / is_paper / is_dev のブールヘルパー

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - 3 層（Raw / Processed / Feature）+ Execution 層に基づくテーブル定義を実装
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対する型と制約（NOT NULL、CHECK、PRIMARY KEY、外部キー等）を定義
  - 頻出クエリ向けのインデックス定義を追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）
  - init_schema(db_path) を実装
    - 指定パスの親ディレクトリがなければ自動作成
    - テーブル作成は冪等（既存テーブルはスキップ）
    - :memory: によるインメモリ DB をサポート
    - 全 DDL およびインデックスを実行して接続を返す
  - get_connection(db_path) を実装（既存 DB への接続を返す。スキーマ初期化は行わない）

- パッケージ構造の初期プレースホルダ
  - src/kabusys/execution/__init__.py（空）
  - src/kabusys/strategy/__init__.py（空）
  - src/kabusys/data/__init__.py（空）
  - src/kabusys/monitoring/__init__.py（空）
  - 将来的な機能拡張のためのモジュール分割を確立

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Security
- 初回リリースのため該当なし

---

注:
- 必須環境変数が未設定の場合、Settings の該当プロパティ呼び出し時に ValueError が発生します（使用時は .env を用意するか環境変数を設定してください）。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされます。自動ロードを明示的に停止するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。