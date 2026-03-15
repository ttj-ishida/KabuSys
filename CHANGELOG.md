# Changelog

すべての注記は Keep a Changelog の慣習に従い、セマンティックバージョニングに基づいています。
リリース日付はソースコードスナップショットの日付（2026-03-15）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-15

### 追加
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージトップ: src/kabusys/__init__.py にてバージョン (0.1.0) と公開 API モジュール一覧を定義 (data, strategy, execution, monitoring)。
- 環境設定管理モジュール (src/kabusys/config.py)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト等で使用）。
    - プロジェクトルート検出: .git または pyproject.toml を基準に __file__ から親ディレクトリを探索してプロジェクトルートを特定する実装（配布後の動作を考慮）。
  - .env パーサーの実装 (_parse_env_line)
    - 空行やコメント行（先頭が #）を無視。
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート付値の解釈をサポート（バックスラッシュエスケープ対応、対応する閉じクォートまでを取得）。
    - クォートなし値の末尾コメント扱いは '#' の直前が空白またはタブの場合のみコメントとみなすなどの微妙なパースルールを実装。
  - _load_env_file による .env 読み込み処理
    - override と protected パラメータにより既存の OS 環境変数を保護しつつ上書き制御が可能。
    - 読み込み失敗時は警告を発行して処理を継続（ファイルアクセス例外の扱い）。
  - Settings クラスによる環境変数取得ラッパー
    - 必須設定を要求する _require() を使用して未設定時に ValueError を送出。
    - 実装済みプロパティ:
      - J-Quants: jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
      - kabuステーション API: kabu_api_password (KABU_API_PASSWORD), kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
      - Slack: slack_bot_token (SLACK_BOT_TOKEN), slack_channel_id (SLACK_CHANNEL_ID)
      - データベースパス: duckdb_path (デフォルト: data/kabusys.duckdb), sqlite_path (デフォルト: data/monitoring.db)
      - システム設定: env (KABUSYS_ENV, 有効値: development, paper_trading, live), log_level (LOG_LEVEL, 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL)
      - ヘルパープロパティ: is_live, is_paper, is_dev
- DuckDB スキーマ定義と初期化モジュール (src/kabusys/data/schema.py)
  - データレイヤ設計に基づくテーブル定義を実装（Raw / Processed / Feature / Execution の 4 層）。
    - Raw Layer:
      - raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer:
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer:
      - features, ai_scores
    - Execution Layer:
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック制約（CHECK）や主キー、外部キーを設定してデータ整合性を考慮。
  - パフォーマンス向けインデックスを複数定義:
    - 例: idx_prices_daily_code_date, idx_features_code_date, idx_signal_queue_status, idx_orders_status など。
  - 公開 API:
    - init_schema(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 指定した DuckDB ファイルを初期化し、全テーブル・インデックスを作成（冪等）。
      - db_path の親ディレクトリが存在しない場合は自動作成。
      - ":memory:" によるインメモリ DB に対応。
    - get_connection(db_path: str | Path) -> duckdb.DuckDBPyConnection
      - 既存 DB に接続するだけでスキーマ初期化は行わない（初回は init_schema を推奨）。
- パッケージ構成
  - 空のパッケージ初期化ファイルを用意: src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/monitoring/__init__.py
  - 将来的なモジュール拡張のための構成を準備。

### 変更
- 初期リリースのため変更点はなし。

### 修正
- 初期リリースのため修正点はなし。

### 削除
- 初期リリースのため削除点はなし。

---

注記:
- 本リリースは初期のスナップショットに基づいて作成しています。今後、機能追加（例: 実際のデータ取得 / 送受信ロジック、戦略実装、監視機能、テスト、ドキュメントの充実など）が予定されます。