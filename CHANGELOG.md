CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
セマンティック バージョニングを採用しています。

Unreleased
----------

- （現在なし）

0.1.0 - YYYY-MM-DD
------------------

Added
- パッケージ初期リリース。
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機構:
    - プロジェクトルートを .git または pyproject.toml から探索して決定。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - ファイル読み込み失敗時は警告を出す（安全にフォールバック）。
  - .env パーサーは export プレフィックス・クォート・インラインコメントを適切に処理。
  - 必須環境変数を取得する _require 関数と、以下のプロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト付き）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev の便利プロパティ

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得機能を実装。
  - レート制限管理: 固定間隔スロットリングによる 120 req/min（_RateLimiter）。
  - リトライ戦略:
    - 最大3回リトライ（指数バックオフ、base=2.0）。
    - 408/429 と 5xx をリトライ対象に設定。
    - 429 の場合は Retry-After ヘッダを優先。
  - 認証:
    - refresh_token から id_token を取得する get_id_token（POST）。
    - 401 受信時は id_token を自動リフレッシュして 1 回だけ再試行（無限再帰回避）。
    - ページネーション間で使えるモジュールレベルの id_token キャッシュを保持。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes: raw_prices へ保存（PK: date, code）
    - save_financial_statements: raw_financials へ保存（PK: code, report_date, period_type）
    - save_market_calendar: market_calendar へ保存（PK: date）
  - データ変換ユーティリティ (_to_float, _to_int) による堅牢な型変換。
  - fetched_at に UTC タイムスタンプを記録し、Look-ahead bias を意識した設計。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を収集して raw_news / news_symbols に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクトハンドラによるスキーム/ホスト検証と、事前のホストプライベート判定。
    - 許可スキームは http / https のみ。
    - レスポンス読み込み上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査を実施（メモリ DoS 対策）。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid, gclid, ref_, _ga）を除去。
    - スキーム・ホストを小文字化、フラグメント除去、クエリソート。
    - 正規化 URL の SHA-256 ハッシュ（先頭32文字）を記事IDとして使用し冪等性を担保。
  - フィードパース:
    - content:encoded を優先し、description をフォールバックとして利用。
    - pubDate を UTC に正規化（パース失敗時は警告ログと現在時刻で代替）。
    - 記事本文の前処理（URL除去・空白正規化）。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDを返す。チャンク単位で一括挿入（チャンクサイズ 1000）。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への一括挿入（ON CONFLICT DO NOTHING RETURNING を使用）で正確な挿入数を返す。
  - 銘柄コード抽出:
    - テキストから 4 桁数字（日本株）を抽出し、既知コード集合でフィルタ。
  - run_news_collection: 複数ソースを順次処理、ソース単位で独立してエラーハンドリング。known_codes があれば新規挿入記事に対して銘柄紐付けを一括挿入。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）+ Execution 層のテーブル群を定義。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な制約（PK・CHECK・外部キー）を付与。
  - 検索用インデックスを複数定義（銘柄×日付・ステータス検索等）。
  - init_schema(db_path): DB の親ディレクトリ自動作成、全テーブルとインデックスを冪等に作成して接続を返す。
  - get_connection(db_path): 既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETLResult データクラスを追加（取得/保存数、品質問題、エラー等を保持）。
  - 差分更新ヘルパー:
    - _table_exists / _get_max_date による DB 状態確認ユーティリティ。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を提供。
  - 市場カレンダー補正: _adjust_to_trading_day により非営業日は直近営業日に調整（最大30日遡り）。
  - run_prices_etl:
    - 差分更新ロジック（最終取得日から backfill_days を考慮した date_from 自動算出）。
    - J-Quants から差分を取得して保存（fetch_daily_quotes / save_daily_quotes を利用）。
    - backfill_days のデフォルトは 3 日、最小取得日を 2017-01-01 と定義。
  - 設計上の配慮:
    - id_token を引数注入可能にしてテスト容易性を確保。
    - 品質チェックモジュール（quality）との連携を想定（品質問題は集約し呼び出し元が対応）。

Security
- ニュース収集における SSRF 対策、XML パース安全化、レスポンス大きさ制限等、外部入力に対する複数の防御を実装。
- J-Quants クライアントは認証トークンの安全なリフレッシュとキャッシュを行い、無限再帰を回避する仕組みを導入。

Notes / Migration
- 以下の環境変数は本リリースで必須または推奨:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - KABUSYS_ENV（development/paper_trading/live、デフォルト development）
  - LOG_LEVEL（デフォルト INFO）
  - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
- テスト時や環境によっては KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化してください。
- ニュース収集の HTTP 処理部分はテストしやすいように _urlopen をモック可能。

Acknowledgement
- 初期実装のため、今後以下を順次追加または改善する予定:
  - 品質チェック（quality モジュール）の実装との統合および詳細なルール
  - pipeline の他 ETL ジョブ（財務・カレンダーの差分ETL や統合ジョブ）
  - execution 層（注文送信・約定取り込み）との接続ロジック

もしリリース日（YYYY-MM-DD）や追加の説明を入れてほしい場合はお知らせください。