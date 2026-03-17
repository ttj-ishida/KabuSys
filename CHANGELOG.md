# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
セマンティック バージョニングに従います。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-03-17
最初のリリース — 日本株自動売買システムのコア機能を実装。

### Added
- パッケージ初期化
  - `kabusys.__init__` を追加し、パッケージ名とバージョン (`0.1.0`) を定義。
  - サブパッケージ公開: `data`, `strategy`, `execution`, `monitoring`。

- 環境設定管理 (`kabusys.config`)
  - `.env` / `.env.local` を自動読み込みする仕組みを実装（自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
  - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない設計。
  - `.env` のパースロジックを実装:
    - コメント行、`export KEY=val` 形式、クォート処理、インラインコメントの扱いに対応。
  - `Settings` クラスを導入し、以下の設定プロパティを提供:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`, `sqlite_path`
    - 実行環境判定: `env`, `log_level`, `is_live`, `is_paper`, `is_dev`
  - 環境変数の妥当性検証（`KABUSYS_ENV` と `LOG_LEVEL` の有効値チェック）。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - 基本的な HTTP リクエストラッパー `_request` を実装:
    - レート制限（120 req/min）を守る `_RateLimiter`。
    - 再試行ロジック（指数バックオフ、最大3回）と 429 の `Retry-After` サポート。
    - 401 受信時の自動 ID トークンリフレッシュ（1回のみ）に対応。
    - JSON デコードエラーハンドリング。
  - 認証ヘルパー `get_id_token`（リフレッシュトークン → idToken）。
  - データ取得関数（ページネーション対応）:
    - `fetch_daily_quotes`（株価日足）
    - `fetch_financial_statements`（四半期財務）
    - `fetch_market_calendar`（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等):
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
    - 各関数は INSERT ... ON CONFLICT DO UPDATE を利用し、重複を排除して更新。
  - 型変換ユーティリティ `_to_float`, `_to_int` を実装し、不正な数値や空値を安全に扱う。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからのニュース取得と DuckDB 保存処理を実装:
    - `fetch_rss` : RSS 取得と XML パース、記事抽出（title, content, pubDate, link）。
    - `save_raw_news` : `raw_news` へチャンク挿入、INSERT ... RETURNING を使用して実際に挿入された記事IDを返す。
    - `save_news_symbols` / `_save_news_symbols_bulk` : 記事と銘柄コードの紐付けを一括保存（ON CONFLICT DO NOTHING、トランザクション管理）。
    - `run_news_collection` : 複数ソースの統合収集ジョブ（個々のソース失敗を他へ影響させない設計）。
  - セキュリティ・耐障害性の考慮:
    - defusedxml を利用して XML Bomb 等から保護。
    - SSRF 対策: URL スキーム検証、リダイレクト先のスキーム/ホスト検査（プライベートアドレス拒否）、DNS 解決済み IP の検査。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後の再チェック（Gzip bomb 対策）。
    - 記事IDは正規化済 URL の SHA-256（先頭32文字）で生成し冪等性を確保。トラッキングパラメータ（utm_ 等）を除去して正規化。
    - URL 正規化、テキスト前処理（URL 除去・空白正規化）。
  - 銘柄コード抽出:
    - 正規表現で 4 桁数字を抽出し、与えられた `known_codes` セットと照合する `extract_stock_codes` を実装。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - Data Lake/Platform 層に対応するスキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - Raw: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature / AI: `features`, `ai_scores`
    - Execution: `signals`, `signal_queue`, `portfolio_targets`, `orders`, `trades`, `positions`, `portfolio_performance`
  - 各テーブルに制約（PRIMARY KEY、CHECK、FOREIGN KEY）を設定。
  - 利用頻度を考慮したインデックスを作成（銘柄×日付、ステータス検索等）。
  - `init_schema(db_path)` : ディレクトリ作成（必要なら）と全 DDL/インデックスの冪等実行による初期化を提供。
  - `get_connection(db_path)` : 既存 DB へ接続を返すユーティリティ。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の基本設計と一部実装を追加:
    - 差分更新ロジックに基づくデータ取得戦略（最終取得日を基に date_from を決定、backfill 日数で後出し修正に対応）。
    - 市場カレンダーの先読み（lookahead）設計パラメータを定義。
    - ETL 実行結果を格納する `ETLResult` データクラス（品質チェック結果、エラー集約、便利な to_dict）。
    - DB 存在チェック、最大日付取得のヘルパー `_table_exists`, `_get_max_date`。
    - 市場営業日調整 `_adjust_to_trading_day`（非営業日の場合の直近取引日への調整）。
    - 差分更新ジョブ `run_prices_etl` の雛形（date_from 自動算出、fetch -> save のフロー）。品質チェックフック（quality モジュール）を想定。
  - 設計方針として Fail-Fast を避け、品質チェックがエラーでも ETL を継続して呼び出し元に判断を委ねる仕様。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- RSS パーサーに defusedxml を採用し、XML パース時の安全対策を実装。
- ニュース取得時の SSRF 対策（スキーム検査、プライベートアドレス拒否、リダイレクト検査）。
- .env 読み込みは既存の OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Migration
- 初回セットアップ時には必ず `kabusys.data.schema.init_schema(db_path)` を実行して DuckDB スキーマを作成してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD（`Settings` の必須プロパティとして参照されます）
- 自動 .env 読み込みはパッケージがインポートされる際に行われます。テストや環境によって無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API はレート制限（120 req/min）を想定しています。大量取得時は `_RateLimiter` により制御されます。

今後の改善候補（非網羅）
- pipeline 側の財務・カレンダー ETL ジョブを `run_prices_etl` にならって実装する。
- quality モジュールの具体的なチェック実装と ETL 結果への統合。
- strategy / execution / monitoring サブパッケージの具体的な実装追加（現状はプレースホルダ）。

---