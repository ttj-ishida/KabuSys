# Changelog

すべての重大な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」仕様に準拠します。

※バージョンはパッケージの __version__（0.1.0）に合わせています。

## [0.1.0] - 2026-03-17

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基盤機能を追加。
- パッケージ構成
  - モジュール群: kabusys.data, kabusys.strategy, kabusys.execution, kabusys.monitoring（パッケージ公開インターフェースを __all__ で定義）。
- 設定管理（kabusys.config）
  - .env / .env.local および環境変数から設定を自動読み込みする機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - 自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env パースの細かい取り扱い（export プレフィックス、クォート内エスケープ、インラインコメント処理）を実装。
  - 必須環境変数を取得する _require()、および Settings クラスを提供。
  - 主要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）と既定値（KABUS_API_BASE_URL、データベースパスなど）を定義。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API 呼び出し共通の _request() 実装：レート制限、再試行（指数バックオフ）、JSON デコード検証、401 時の自動トークンリフレッシュなどを実装。
  - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
  - ID トークンのモジュールレベルキャッシュおよび get_id_token() 実装。
  - DuckDB へ保存する冪等な保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による更新/スキップを採用。
  - データ変換ユーティリティ（_to_float, _to_int）を実装し、欠損や型不正を安全に扱う。
  - 取得時刻（fetched_at）を UTC タイムスタンプで記録し、Look-ahead Bias のトレースを可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得して raw_news に保存する機能を実装（fetch_rss, save_raw_news）。
  - 記事IDを正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - defusedxml を用いた XML パース（XML Bomb 等を防止）。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカルの場合アクセス拒否（DNS 解決による A/AAAA 検査を含む）。
    - リダイレクト時のスキームとホスト検証を行うカスタムリダイレクトハンドラを実装。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェックの実装（メモリ DoS / Gzip bomb 対策）。
  - INSERT ... RETURNING を用いた新規挿入レコード検出、チャンク化（_INSERT_CHUNK_SIZE）とトランザクションによる一括保存。
  - 銘柄コード抽出機能（extract_stock_codes）と、news_symbols テーブルへの紐付け保存（save_news_symbols, _save_news_symbols_bulk）。
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネスカテゴリ）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataPlatform に基づく3層（Raw / Processed / Feature）と Execution 層を含む包括的なテーブル定義を追加。
  - 定義テーブル（主なもの）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK 等）とインデックスを定義（頻出クエリに対応）。
  - init_schema(db_path) によるデータベース初期化（親ディレクトリ自動作成、冪等的に DDL を実行）と get_connection() を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass により ETL 実行結果を構造化（取得数、保存数、品質問題、エラー等を含む）。
  - 差分更新ユーティリティ（最終取得日の取得 get_last_price_date / get_last_financial_date / get_last_calendar_date）を実装。
  - 営業日調整ヘルパー(_adjust_to_trading_day) を実装。
  - run_prices_etl() を実装（差分取得ロジック、backfill_days による再取得、jquants_client 経由の取得と save の連携）。
  - ETL の設計方針としてバックフィル／後出し修正吸収、品質チェックは収集継続を前提とする動作を明示。

### Changed
- （初回公開のため変更履歴はなし）

### Fixed
- （初回公開のため修正履歴はなし）

### Security
- defusedxml の採用、SSRF 対策、レスポンスサイズ制限、gzip 解凍後サイズ検査など、外部入力（RSS/HTTP）に対する複数の防御を実装。
- .env ファイル読み込みで OS 環境変数を保護する protected オプションを用意（.env.local を上書き可能にしつつ OS 変数を上書きしない等の挙動を制御）。

### Notes / Requirements / Known limitations
- 必須環境変数（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）をセットする必要があります。未設定時は Settings のプロパティが ValueError を送出します。
- J-Quants API はレート制限（120 req/min）に従います。内部で固定間隔スロットリングと再試行ロジックを実装していますが、大量の並列リクエストは避けてください。
- DuckDB を使用するため、実行環境に duckdb パッケージが必要です。
- news_collector の URL 検証は安全側の判断（DNS 失敗時は非プライベートとみなす）を採っています。内部ネットワーク環境での利用時は注意してください。
- run_prices_etl とパイプラインは手短に実装されています。大規模運用でのスケーラビリティ/ロバストネス向上は今後の課題です。

もしリリースノートに追記してほしい点（例えば各関数の利用例、期待する DB スキーマのサンプル、環境変数一覧など）があれば指示してください。