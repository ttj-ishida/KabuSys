# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用します。
リリース日はパッケージ内の現在の状態に基づいて推定しています。

## [0.1.0] - 2026-03-15

初回リリース — KabuSys: 日本株自動売買システムの基本モジュール群を実装。

### 追加
- パッケージの基本構成を追加
  - src/kabusys/__init__.py にバージョン (0.1.0) と公開モジュール一覧を定義。
  - モジュール構成: data, strategy, execution, monitoring（各パッケージのプレースホルダを含む）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出: __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を基準にルートを特定（パッケージ配布後も安定動作）。
  - .env パースの強化:
    - 空行やコメント行（#）のスキップ。
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート内のエスケープ処理を適切に扱う。
    - クォート無し値では、直前が空白／タブの場合のみ '#' 以降をコメントとして扱う。
  - .env 読み込みの優先順位: OS環境変数 > .env.local > .env。
    - .env.local は .env の上書き（override）として読み込まれる。
    - OS 環境変数は保護され、.env/.env.local によって上書きされない（protected set）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを抑止可能（テスト用途など）。
  - 読み込み失敗時は警告を発行（warnings.warn）。
  - 必須環境変数未設定時に ValueError を発生させる _require() を提供。
  - Settings クラスで各種設定値をプロパティとして公開:
    - J-Quants: jquants_refresh_token (JQUANTS_REFRESH_TOKEN, 必須)
    - kabuステーション API: kabu_api_password (KABU_API_PASSWORD, 必須)、kabu_api_base_url (既定: http://localhost:18080/kabusapi)
    - Slack: slack_bot_token (SLACK_BOT_TOKEN, 必須)、slack_channel_id (SLACK_CHANNEL_ID, 必須)
    - データベース: duckdb_path (既定: data/kabusys.duckdb)、sqlite_path (既定: data/monitoring.db)
    - システム: env (KABUSYS_ENV、有効値: development / paper_trading / live、既定: development)、log_level (LOG_LEVEL、有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL、既定: INFO)
    - 便利フラグ: is_live / is_paper / is_dev

- DuckDB スキーマ管理 (src/kabusys/data/schema.py)
  - DataSchema.md を想定した 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を追加。
  - Raw レイヤー: raw_prices, raw_financials, raw_news, raw_executions
  - Processed レイヤー: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
  - Feature レイヤー: features, ai_scores
  - Execution レイヤー: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型・チェック制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を付与し、データ品質を担保。
  - 頻出クエリ向けのインデックスを定義（例: idx_prices_daily_code_date, idx_signal_queue_status, idx_orders_status など）。
  - スキーマ作成順序を考慮して DDL を順次実行。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - db_path が ":memory:" でない場合は親ディレクトリを自動作成し、全テーブルとインデックスを作成して DuckDB 接続を返す（冪等）。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB へ接続（スキーマ初期化は行わない。初回は init_schema() を推奨）。

### 変更
- 初回リリースのため、既存プロジェクトからの変更はありません。

### 修正
- 初回リリースのため、既存の不具合修正はありません。

### セキュリティ
- OS 環境変数は .env/.env.local によって上書きされないよう保護（protected set）。重要な環境変数を意図せず上書きするリスクを軽減。

### 既知の注意点 / 移行メモ
- Settings の必須フィールドが未設定の場合、ValueError が発生します。デプロイ前に以下の環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- KABUSYS_ENV の値は "development", "paper_trading", "live" のいずれかにする必要があります。
- LOG_LEVEL は大文字で指定する必要があり、有効な値は DEBUG/INFO/WARNING/ERROR/CRITICAL です。
- 自動 .env 読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（例えばユニットテスト中など）。
- DuckDB の初期化は init_schema() を使用すること。get_connection() は既存 DB 接続用でスキーマ作成は行いません。
- .env のパースはシェル互換の一部仕様（export プレフィックス、クォート、エスケープ、コメント）に対応していますが、完全なシェルパーサではないため特殊ケースは想定外になる可能性があります。

---
（今後のリリースでは、strategy / execution / monitoring の具体的な実装、CLI や運用用ドキュメント、マイグレーションツール、テストケースと CI 設定などを追加予定です。）