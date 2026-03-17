# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従っています。

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを追加しました。
主要な機能・実装内容は以下の通りです。

### 追加 (Added)
- パッケージ構成
  - パッケージルート: `kabusys`（__version__ = 0.1.0、`__all__` に "data", "strategy", "execution", "monitoring" を公開）
  - 空のサブパッケージ雛形: `kabusys.execution`, `kabusys.strategy`, `kabusys.monitoring`（将来的な実装用）

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env/.env.local の読み込み順序（OS環境変数 > .env.local > .env）および上書き/保護ロジック。
  - .env 行のパース（コメント、export プレフィックス、クォート・エスケープ対応）。
  - 必須設定取得用のヘルパー `_require` と Settings クラス（プロパティで設定値を提供）。
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
    - `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の値検証。
    - デフォルト DuckDB/SQLite パス（`data/kabusys.duckdb`, `data/monitoring.db`）。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しラッパー `_request`：
    - レート制限遵守（120 req/min）用の固定間隔スロットリング `_RateLimiter` を実装。
    - 再試行ロジック（指数バックオフ、最大リトライ回数 3、408/429/5xx に対応）。
    - 429 の場合は `Retry-After` ヘッダを優先。
    - 401 (Unauthorized) 受信時は ID トークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止）。
    - JSON デコードエラー検知。
  - トークン管理:
    - `get_id_token` によるリフレッシュトークン → ID トークン取得（POST）。
    - モジュールレベルのトークンキャッシュ `_ID_TOKEN_CACHE` と `_get_cached_token`。
  - データ取得関数（ページネーション対応）
    - `fetch_daily_quotes`（株価日足, OHLCV）
    - `fetch_financial_statements`（四半期財務データ）
    - `fetch_market_calendar`（JPX マーケットカレンダー）
    - 取得ログ（取得件数）出力、pagination_key によるページ継続
  - DuckDB への保存（冪等）
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
    - `fetched_at` を UTC ISO8601 で記録して Look-ahead Bias のトレーサビリティを確保
    - ON CONFLICT DO UPDATE を用いた冪等保存、主キー欠損行はスキップして警告ログを出力
    - データ型変換ユーティリティ `_to_float`, `_to_int`（堅牢な変換ロジック）

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからの記事収集（標準ソース: Yahoo Finance のカテゴリ RSS をデフォルトで含む）。
  - セキュアな XML パース（defusedxml を使用）と XML Bomb 対策。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストでないかを判定する `_is_private_host`（直接 IP と DNS 解決の両方を検査）。
    - リダイレクト時にスキームとホストを検証する `_SSRFBlockRedirectHandler`。
    - 最終 URL の再検証。
  - レスポンスサイズ制限（デフォルト 10 MB）と gzip 解凍の安全チェック（gzip 解凍後もサイズ上限を検証）。
  - URL 正規化 `_normalize_url`（小文字化、トラッキングパラメータ除去、フラグメント除去、クエリキーソート）、記事ID は正規化 URL の SHA-256（先頭32文字）。
  - テキスト前処理 `preprocess_text`（URL 除去・空白正規化）。
  - RSS 取得処理 `fetch_rss`（項目抽出、content:encoded の優先、pubDate のパースと UTC 正規化）。
  - DuckDB 保存:
    - `save_raw_news`：チャンク分割・1 トランザクションで INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された ID を返す。
    - `save_news_symbols` / `_save_news_symbols_bulk`：記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING RETURNING を使用して実際に挿入された数を返す）。
  - 銘柄コード抽出 `extract_stock_codes`（4桁数字パターンと known_codes に基づくフィルタリング）

- DuckDB スキーマ定義・初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution の 3 層（+実行層）に基づくテーブル DDL を実装。
  - 主要テーブル（例）
    - Raw: `raw_prices`, `raw_financials`, `raw_news`, `raw_executions`
    - Processed: `prices_daily`, `market_calendar`, `fundamentals`, `news_articles`, `news_symbols`
    - Feature: `features`, `ai_scores`
    - Execution: `signals`, `signal_queue`, `orders`, `trades`, `positions`, `portfolio_targets`, `portfolio_performance`
  - 制約・チェック（NOT NULL / PRIMARY KEY / CHECK 等）を定義。
  - 推奨インデックス群（銘柄×日付検索、ステータス検索など）。
  - 初期化関数 `init_schema(db_path)`：
    - 親ディレクトリ自動作成、DDL とインデックスを順番に実行して冪等にスキーマを作成。
  - 既存 DB への単純接続 `get_connection(db_path)`。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計思想と差分取得・バックフィル方針を実装（ドキュメントに基づく）。
  - ETL 実行結果を表す `ETLResult` データクラス（品質問題やエラーの集約、辞書化メソッドを提供）。
  - ヘルパー関数:
    - テーブル存在チェック `_table_exists`
    - 最大日付取得 `_get_max_date`（`get_last_price_date` / `get_last_financial_date` / `get_last_calendar_date` を公開）
    - 取引日の調整 `_adjust_to_trading_day`（market_calendar を参照して直近の営業日に調整）
  - 個別 ETL ジョブ（株価差分 ETL の骨組み）
    - `run_prices_etl`（差分算出ロジック、バックフィル日数デフォルト 3 日、J-Quants からの取得と保存を呼び出す）
    - （品質チェック統合や他ジョブは品質モジュールとの連携を想定）

### 改善 (Improved)
- ロギングを各処理段階で充実（取得件数、保存件数、警告・例外ログ）。
- DB 保存処理を可能な限り冪等化（ON CONFLICT / DO UPDATE / DO NOTHING）して再実行可能に設計。

### セキュリティ (Security)
- RSS XML のパースに defusedxml を採用、XML Attack（XML Bomb 等）対策。
- SSRF 防止:
  - URL スキーム検証（http/https のみ）。
  - プライベート/ループバックアドレスのブロック（直接 IP と DNS 解決の両方を検査）。
  - リダイレクト先の検証を含む安全な URLOpen 実装。
- 外部通信における最大レスポンスサイズチェック（メモリ DoS 対策）。
- .env 読み込み時に OS 環境変数を保護する `protected` 機構。

### パフォーマンス (Performance)
- API レート制限（120 req/min）を尊重する軽量なスロットリングで API 制限を回避。
- 再試行ロジックの指数バックオフで一時的障害に耐性を付与。
- news_collector のバルク INSERT（チャンク分割）により DB オーバーヘッドを削減。
- ページネーションでのトークン共有による効率化（id_token キャッシュ）。

### 既知の制限 / 注意点 (Known issues / Notes)
- `kabusys.strategy`, `kabusys.execution`, `kabusys.monitoring` は現時点では実装の雛形のみ。実行・戦略ロジックは今後追加予定。
- pipeline の `run_prices_etl` 等は ETL の主要フローを実装していますが、品質チェック（quality モジュール）や全ジョブの統合実行フローは別モジュール/追加実装が必要です。
- `run_prices_etl` の戻り値記述など実装上の細部は今後の拡張で明確化される予定（現状は取得件数/保存件数のレポートを行う骨組みを含む）。
- DuckDB への挿入時に SQL テキストを動的に構築している箇所があるため、プレースホルダ使用はしているものの、将来的により安全・効率的なパラメータバインディングへの改善余地あり。

---

今後は戦略/実行/監視の実装、品質チェック統合、テストカバレッジの拡充、ドキュメント整備を進める予定です。もし CHANGELOG の記載内容について補足・修正が必要であれば指示ください。