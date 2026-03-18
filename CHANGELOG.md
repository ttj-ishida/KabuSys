# Changelog

すべての注目すべき変更をこのファイルに記録します。
このプロジェクトは Keep a Changelog の形式に従っています。  
リリースの互換性はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-18

初回リリース。本バージョンでは日本株自動売買プラットフォームのコア基盤を実装しました。
主な追加点、設計方針、運用上の注意を以下にまとめます。

### Added
- パッケージ骨組み
  - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0）。
  - 主要モジュール群を公開: data, strategy, execution, monitoring（空の __init__ を含むモジュール構成）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルート判定ロジック（.git または pyproject.toml を起点に探索）を実装し、カレントワーキングディレクトリに依存しない自動ロードを実現。
  - .env / .env.local の読み込み優先度をサポート（OS環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動 .env ロードを無効化可能（テスト用）。
  - .env パースの堅牢化（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント判定など）。
  - 必須設定取得ヘルパー _require と Settings クラスを実装。主な設定項目:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得機能を実装。
  - 設計上の特徴:
    - API レート制御（120 req/min 固定間隔スロットリング）を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータスは 408/429/5xx。
    - 401 受信時はリフレッシュトークンで id_token を自動更新して 1 回リトライ（無限再帰回避）。
    - ページネーション対応（pagination_key を用いた取得ループ）。
    - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止するためのトレーサビリティ確保。
    - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複や差分を安全に扱う。
  - ユーティリティ: _to_float / _to_int の安全変換処理。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する一連の処理を実装。
  - 設計上の特徴（セキュリティ・堅牢性重視）:
    - defusedxml を使った XML パース（XML Bomb 等対策）。
    - SSRF 対策: リダイレクトハンドラでスキーム/ホストを検査、プライベートIPや非 http(s) を拒否。
    - レスポンスの受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリDoS対策。
    - gzip デコード後のサイズチェック（gzip bomb 対策）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 先頭32文字）による冪等性確保。
    - RSS の pubDate パース・フォールバック、title/description 前処理（URL除去・空白正規化）。
  - DB保存:
    - raw_news へチャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id（挿入されたIDを返す）。
    - news_symbols への紐付けを一括 INSERT（重複除去、トランザクション内で処理）。
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ（config 内 DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md 想定の 3 層（Raw / Processed / Feature / Execution）に基づくテーブル群を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切なデータ型・チェック制約・主キー・外部キーを定義。
  - 頻出クエリのためのインデックスを追加（例: idx_prices_daily_code_date 等）。
  - init_schema(db_path) 関数でディレクトリ作成（必要に応じ）→ 全DDL とインデックスを実行（冪等）。
  - get_connection(db_path) で既存DBへ接続（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - データ差分取得・保存・品質チェックを行う ETL の土台を実装。
  - 主な設計:
    - 差分更新ロジック（DB の最終取得日から backfill_days 日分を再取得して API の後出し修正を吸収）。
    - 市場カレンダーの先読み（デフォルト _CALENDAR_LOOKAHEAD_DAYS）。
    - 品質チェックは全件を収集し、エラーがあっても ETL を継続（呼び出し元が対応を判断）。
    - id_token の注入可能化でテスト容易性を配慮。
  - ETLResult データクラスを追加（実行結果、品質問題、エラー等の集約）。
  - run_prices_etl の骨組み（差分算出、fetch_daily_quotes 呼び出し、保存処理）を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサで defusedxml を使用して XML 関連の攻撃を緩和。
- ネットワークに対する SSRF 対策を導入（リダイレクト時のスキーム検査、プライベートIPの拒否、最終 URL 再検証）。
- 外部入力（.env、RSS、API等）のパース処理を堅牢化（サイズ制限、エンコーディング、クォート処理など）。
- DB 操作はトランザクションにまとめ、例外時はロールバックしてログ出力。

### Notes / Migration / Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 任意 / デフォルト:
  - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV (development/paper_trading/live; default: development)
  - LOG_LEVEL (default: INFO)
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。
- データベース初期化:
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
- ETL 実行例（株価差分 ETL）:
  - from kabusys.data.pipeline import run_prices_etl
  - from kabusys.data.schema import get_connection
  - conn = get_connection("data/kabusys.duckdb")
  - run_prices_etl(conn, target_date=date.today())
- 依存（主なランタイム依存）:
  - duckdb
  - defusedxml
  - 標準ライブラリ（urllib, json, hashlib 等）
- 設計上の注意:
  - J-Quants API のレート制限（120 req/min）を厳守するため RateLimiter が導入されています。大量バッチ処理の際は考慮してください。
  - save_* 関数は冪等性を保つため ON CONFLICT を使用しています。既存データの更新は許容される仕様です。
  - ニュース記事 ID は URL 正規化後のハッシュで生成されるため、トラッキングパラメータの違いに依存しません。

今後の予定（例）
- モニタリング・実行（kabuステーション連携）モジュールの具体的実装
- 品質チェックモジュール（kabusys.data.quality）との連携強化
- strategy レイヤーの具体的戦略実装およびバックテスト機能
- Slack 等通知・アラート機能の統合

---
この CHANGELOG はコードベースからの推測に基づいて作成しています。実際の設計方針や外部仕様の変更がある場合は適宜更新してください。