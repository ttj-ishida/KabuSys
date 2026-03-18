# Changelog

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システムの基盤となる以下の機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージ定義 (kabusys) とバージョン情報を追加 (kabusys.__version__ = "0.1.0")。
  - パッケージの公開 API を __all__ で定義: data, strategy, execution, monitoring。

- 環境設定 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能をプロジェクトルート (.git または pyproject.toml) に基づいて実行。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装（export プレフィックス、クォート内エスケープ、インラインコメント扱い等に対応）。
  - 必須環境変数未設定時に ValueError を投げる _require ユーティリティ。
  - 設定プロパティ:
    - J-Quants: jquants_refresh_token (必須)
    - kabuステーション: kabu_api_password (必須)、kabu_api_base_url (デフォルト http://localhost:18080/kabusapi)
    - Slack: slack_bot_token, slack_channel_id (必須)
    - DB パス: duckdb_path (デフォルト data/kabusys.duckdb)、sqlite_path (デフォルト data/monitoring.db)
    - システム: env（development/paper_trading/live の検証）、log_level（DEBUG/INFO/… の検証）、ヘルパー is_live/is_paper/is_dev

- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しの共通処理 _request を実装（JSON デコード、エラーハンドリング）。
  - レート制限 (120 req/min) を固定間隔スロットリングで実装する _RateLimiter。
  - 冪等性・効率のための ID トークンのモジュールキャッシュと自動リフレッシュロジック（401 受信時に 1 回リフレッシュしてリトライ）。
  - リトライ機構（指数バックオフ、最大 3 回、408/429/>=500 を対象、429 の Retry-After 優先）。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB へ保存する冪等な保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes (raw_prices)
    - save_financial_statements (raw_financials)
    - save_market_calendar (market_calendar)
  - 型変換ユーティリティ _to_float, _to_int（不正値に対して安全に None を返す）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集と前処理、DuckDB への保存を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML Bomb 等に対処。
    - HTTP/HTTPS スキームのみ許可し、SSRF 対策としてリダイレクト先のスキームとホスト検査を行う _SSRFBlockRedirectHandler。
    - ホスト名の DNS 解決や IP 判定によりプライベートアドレスへのアクセスを拒否する _is_private_host。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を超える場合は取得を中止（Gzip 解凍後もチェック）。
  - URL 正規化:
    - トラッキングパラメータ（utm_, fbclid, gclid, ref_, _ga 等）を除去し、フラグメント削除・パラメータソートを行う _normalize_url。
    - 正規化 URL の SHA-256（先頭32文字）を記事IDとして使用して冪等性を確保。
  - テキスト前処理 (preprocess_text): URL 除去、空白正規化。
  - RSS 取得処理 fetch_rss（gzip 対応、pubDate パース、content:encoded の優先利用、非標準レイアウトへのフォールバック）。
  - DuckDB への保存:
    - save_raw_news: チャンク分割で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDだけを返す。トランザクションでまとめて処理。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの (news_id, code) 紐付けをチャンク・トランザクションで挿入し、挿入件数を正確に返す。
  - 銘柄コード抽出 (extract_stock_codes): 4桁数字パターンから既知の銘柄セットに含まれるものを抽出（重複排除）。
  - 統合収集ジョブ run_news_collection: 複数ソースを独立に処理し、新規保存数と銘柄紐付けを行う（ソース単位でエラーハンドリング）。

- スキーマ定義 (kabusys.data.schema)
  - DuckDB 用の包括的なスキーマ定義を追加（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 適切な CHECK 制約、PRIMARY KEY、外部キー、インデックスを定義。
  - init_schema(db_path): ディレクトリ作成を含む初期化関数（冪等）。
  - get_connection(db_path): 既存 DB への接続取得ユーティリティ。

- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass による ETL 集計結果の表現（取得数、保存数、品質問題、エラー等）。
  - 共通ユーティリティ:
    - _table_exists, _get_max_date: テーブル存在チェック / 日付最大値取得。
    - _adjust_to_trading_day: 非営業日の調整（market_calendar に基づく、最大 30 日遡り）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: raw テーブルの最終取得日取得関数。
  - run_prices_etl の骨組みを実装:
    - 差分更新ロジック（最終取得日から backfill_days の再取得、デフォルト _DEFAULT_BACKFILL_DAYS = 3）。
    - J-Quants からの取得と保存の流れを実装（fetch_daily_quotes → save_daily_quotes）。
    - 最小データ日付 _MIN_DATA_DATE = 2017-01-01 を利用した初回ロードサポート。
    - カレンダー先読み設定用定数 _CALENDAR_LOOKAHEAD_DAYS = 90。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### セキュリティ (Security)
- news_collector において SSRF 対策と defusedxml による XML パースで潜在的な外部参照・XML攻撃を軽減。
- RSS 取得時のスキーム検査、プライベートIPチェック、最大受信バイト制限によるメモリ DoS 緩和。

### 注意事項 / 今後の予定 (Notes / TODO)
- run_prices_etl のファイル末尾が途中（返り値などの続き）で切れている可能性があるため、ETL の完全なワークフロー（ファイナンシャル / カレンダー処理、品質チェック呼び出し quality モジュール連携など）は今後追加・補完が想定されます。
- strategy / execution / monitoring パッケージは __init__ が存在するのみで、各機能の実装は今後追加予定です。
- 単体テスト・統合テスト、CI（自動テスト）やパッケージ配布時の検証を今後整備することを推奨します。
- DB スキーマ・DDL は将来のマイグレーション設計（バージョン管理）を検討することを推奨します。

---

（この CHANGELOG はコードベースから実装内容を推測して作成しています。実際のリリースノートとして使用する場合は、変更日や担当者、影響範囲などをプロジェクト実情に合わせて追記してください。）