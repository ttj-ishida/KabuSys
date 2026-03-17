# Changelog

すべての重要な変更はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に従います。  
安定版にしたい場合は Semantic Versioning を使用します。

※この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。以下の主要コンポーネントを含みます。

### Added
- パッケージ基盤
  - パッケージエントリポイント: kabusys.__init__（version = 0.1.0）。
  - モジュール分割: data, strategy, execution, monitoring を想定したパッケージ構成（空の __init__ を含む）。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスで各種設定値をプロパティとして提供:
    - J-Quants / kabuステーション / Slack トークン等の必須値チェック（未設定時は ValueError を投げる）。
    - DB パスのデフォルト（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）。
    - 環境（KABUSYS_ENV）のバリデーション（development, paper_trading, live）。
    - ログレベル（LOG_LEVEL）のバリデーション。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しの共通実装:
    - ベース URL とエンドポイントラッパー。
    - 固定間隔のレートリミッタ（120 req/min を守る _RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ保証）とモジュールレベルの id_token キャッシュ。
    - JSON デコードエラーやネットワーク例外の扱いを明確化。
  - 認証ヘルパー get_id_token（refreshtoken から idToken を取得）。
  - データ取得 API（ページネーション対応）:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存（冪等性を考慮）:
    - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT DO UPDATE を用いた挿入/更新で重複を排除。
    - fetched_at に UTC タイムスタンプを記録して「データをいつ知り得たか」をトレース可能に。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news / news_symbols へ保存するフローを実装。
  - セキュリティ対策と堅牢性:
    - defusedxml を用いた XML パース（XML bomb 等の対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、プライベート/ループバック/リンクローカル/マルチキャストアドレスを拒否（DNS 解決結果も検査）。
    - リダイレクト先の事前検査用ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）と圧縮解凍後のサイズチェック（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding の設定。
  - フィード処理:
    - URL 正規化（トラッキングパラメータの除去、クエリソート、スキーム/ホスト小文字化、フラグメント除去）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパース（RFC 2822 形式を UTC に正規化、失敗時は現在時刻で代替）。
  - DB 保存:
    - save_raw_news: チャンク単位のバルク INSERT（ON CONFLICT DO NOTHING）で INSERT ... RETURNING を使用し、実際に挿入された記事 ID を返す。1 トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存、ON CONFLICT で重複をスキップ、INSERT ... RETURNING を用いて挿入数を正確に返す。
  - 銘柄コード抽出:
    - extract_stock_codes: テキスト中の 4 桁数字候補を正規表現で抽出し、既知の銘柄セットでフィルタ。重複除去済みリストを返す。
  - 集約ジョブ:
    - run_news_collection: 複数 RSS ソースから独立に記事を取得・保存し、既知銘柄が与えられた場合は新規挿入記事に対して銘柄紐付けを実行。各ソースは独立してエラーハンドリング（1 ソースの失敗は他に影響しない）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema.md 想定に基づく 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）と型チェックを整備。
  - インデックス定義（頻出クエリ向け）を用意。
  - init_schema(db_path) による冪等的なスキーマ初期化と接続取得を提供。親ディレクトリ自動作成、":memory:" 対応。
  - get_connection(db_path) で既存 DB への接続を返す（初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスで ETL の結果（取得数、保存数、品質問題、エラー等）を一元管理。
  - 差分更新の考え方を導入:
    - DB の最終取得日から差分のみ取得し、backfill_days により数日前から再取得して API の後出し修正を吸収。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS）。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date: DB の最終日取得ユーティリティ。
  - 個別 ETL ジョブ（例: run_prices_etl）:
    - 差分計算、fetch -> save の流れを実装（jquants_client の save_* を使用して冪等保存）。
    - 品質チェックモジュール（quality）との統合ポイントを想定（重大度の概念をサポート）。  

### Security
- RSS パーサーで defusedxml を使用し XML による攻撃を緩和。
- SSRF 対策: URL スキーム制限、プライベートアドレス判定（IP/ホスト名 DNS 解決チェック）、リダイレクト時の再検証を実装。
- 最大レスポンスサイズと Gzip 解凍後チェックによりメモリ DoS 防御を実装。
- .env 読み込み時に OS 環境変数を保護するための protected 機構を導入。

### Performance / Reliability
- API クライアントに固定間隔のレートリミッタを実装し J-Quants のレート制限（120 req/min）を順守。
- リトライ（指数バックオフ）と 429 の Retry-After 対応により一時障害耐性を向上。
- DuckDB へのバルク挿入（チャンク処理）とトランザクションまとめによる IO/オーバーヘッド削減。
- INSERT ... RETURNING を多用し、実際に挿入された件数を正確に取得。

### Changed
- 初版のため以前のリリースからの変更はありません。

### Deprecated
- なし

### Removed
- なし

### Fixed
- 初版のため既知の修正はありません。

### Known limitations / Notes
- 現在の実装は主要なデータ入出力・スキーマ・ETL の基盤を提供しますが、戦略（strategy）、発注実行（execution）、監視（monitoring）といった上位モジュールはパッケージ構成は用意されていますが、このバージョンのコード内では実装が最小化（空の __init__ 等）されています。
- quality モジュール（品質チェック）の具体的実装は参照されているが、このスナップショット内での詳細実装状況に依存します（ETL は品質チェックを参照する設計）。
- 本 CHANGELOG はコードから推測して作成しているため、実際のリリースノートと差異がある可能性があります。

---

（以降のリリースでは Unreleased セクションに変更を記録し、リリース時に日付入りのバージョンセクションに移動してください。）