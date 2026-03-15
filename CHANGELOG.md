# Changelog

すべての注目すべき変更はこのファイルに記録します。  
形式は Keep a Changelog に準拠しています。

現在のリリース履歴は以下の通りです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-15
初回リリース。本パッケージの基礎機能とデータスキーマ、設定管理を実装。

### Added
- パッケージ初期構成
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" と __all__ を定義。
  - サブパッケージのプレースホルダを追加: execution, strategy, data, monitoring（各 __init__.py を用意）。

- 環境変数・設定管理モジュール（src/kabusys/config.py）
  - .env ファイルまたは既存の OS 環境変数から設定をロードする自動読み込み機構を実装。
    - 読み込み順序: OS 環境変数（最優先） > .env.local > .env
    - OS 側の環境変数は保護（上書き不可）される実装（protected set を利用）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化可能（テストなどで利用）。
    - プロジェクトルート検出: __file__ を起点に親ディレクトリに .git または pyproject.toml を探すことで、CWD に依存しないプロジェクトルート判定を行う。
  - .env パーサ実装（_parse_env_line）
    - 空行・コメント（#）の扱い
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のエスケープ（バックスラッシュ）を正しく処理
    - クォートなし値におけるインラインコメントの扱い（直前が空白/タブの場合はコメントと見なす）
  - .env 読み込み: _load_env_file にてファイル読み取り、override と protected オプションを実装
  - Settings クラスによるアクセスラッパーを提供（settings オブジェクト）
    - 必須環境変数取得用の _require を実装（未設定時は ValueError を送出）
    - 設定プロパティ:
      - J-Quants: jquants_refresh_token（必須: JQUANTS_REFRESH_TOKEN）
      - kabuステーション: kabu_api_password（必須: KABU_API_PASSWORD）、kabu_api_base_url（デフォルト: http://localhost:18080/kabusapi）
      - Slack: slack_bot_token（必須: SLACK_BOT_TOKEN）、slack_channel_id（必須: SLACK_CHANNEL_ID）
      - DB パス: duckdb_path（デフォルト: data/kabusys.duckdb）、sqlite_path（デフォルト: data/monitoring.db）
      - システム関連: env（KABUSYS_ENV、有効値: development, paper_trading, live）、log_level（LOG_LEVEL、有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）
      - is_live / is_paper / is_dev の便利プロパティ

- DuckDB スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - Data Lake の多層構造（Raw / Processed / Feature / Execution）に対応したスキーマを実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに対して適切な型、CHECK 制約、PRIMARY KEY、FOREIGN KEY を設定（データ整合性重視）
    - 例: side カラムは ('buy','sell') に限定、size は正数、価格は非負など
    - 外部キー制約で参照整合性を確保（ON DELETE の振る舞いも定義）
  - 頻出クエリに対応するインデックスを定義（銘柄×日付、ステータス検索、order_id など）
  - init_schema(db_path) を実装
    - 指定したパスに対して親ディレクトリを自動作成（":memory:" の場合はインメモリを利用）
    - すべてのテーブルとインデックスを作成（冪等性あり）
    - DuckDB の接続オブジェクトを返す
  - get_connection(db_path) を実装（スキーマ初期化は行わない: 初回は init_schema を使用すること）

### Notes / ドキュメント補足
- .env の自動読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後も安全に動作する設計。
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- デフォルトの DuckDB ファイルパス: data/kabusys.duckdb（必要に応じて設定で変更）
- 初回セットアップ手順（例）
  1. .env（または .env.local）をプロジェクトルートに用意し、必須環境変数を設定
  2. Python から kabusys.data.schema.init_schema(settings.duckdb_path) を実行して DB スキーマを作成
- テストや CI の際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化し、テスト用の環境を明示的に設定することが可能。

### Fixed
- （なし）

### Changed
- （初回リリースのため無し）

### Breaking Changes
- （初回リリースのため無し）

---

今後のアップデートでは、strategy / execution / monitoring の具体的実装、データ取り込みジョブ、取引ラッパー（kabu API 統合）、Slack 通知機能などを追加していく予定です。必要であれば、次回リリースでの変更案やリリースノート案も作成します。