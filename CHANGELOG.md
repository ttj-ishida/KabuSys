# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを使用します。

## [Unreleased]

### Added
- 開発の初期実装を追加（ベースパッケージ構成、データ取得・保存・ETL 基盤の実装）。
  - パッケージメタ:
    - `kabusys.__version__ = "0.1.0"` を設定。
    - パッケージの公開 API: data, strategy, execution。
  - 環境設定管理 (`kabusys.config`):
    - .env ファイルおよび環境変数からの自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）。
    - `.env.local` を上書き読み込みする優先度ロジック、OS 環境変数保護。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - 詳細な .env 行パーサ（クォート／エスケープ／インラインコメントの扱い）を実装。
    - 必須設定取得ヘルパ (`_require`) と `Settings` クラス（J-Quants トークン、kabu API、Slack、DB パス、環境・ログレベル検証、便利な is_live/is_paper/is_dev プロパティ）。
  - J-Quants API クライアント (`kabusys.data.jquants_client`):
    - 日足（OHLCV）、財務データ、マーケットカレンダー取得関数を実装（ページネーション対応）。
    - レート制御（固定間隔スロットリング）で 120 req/min を遵守する RateLimiter 実装。
    - リトライ（指数バックオフ、最大 3 回、408/429/5xx 対象）、429 の Retry-After 優先処理。
    - 401 受信時はリフレッシュトークンを使って id_token を自動更新して1回だけ再試行する仕組み。
    - ページネーション間で共有するモジュールレベルの id_token キャッシュ。
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`：fetched_at を UTC で記録、PK 欠損行スキップ、ログ出力。
    - 型変換ユーティリティ `_to_float`, `_to_int`。
  - ニュース収集モジュール (`kabusys.data.news_collector`):
    - RSS フィード収集、XML パース（defusedxml 使用）および前処理（URL 除去・空白正規化）。
    - トラッキングパラメータ除去／URL 正規化・ハッシュによる記事ID生成（SHA-256 先頭32文字）。
    - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト事前検査）、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）、gzip 解凍時のサイズ検証（Gzip bomb 対策）。
    - DuckDB への冪等保存（トランザクション、チャンク分割、INSERT ... RETURNING を利用）:
      - `save_raw_news`, `save_news_symbols`, `_save_news_symbols_bulk`。
    - テキストからの銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁数字 + known_codes フィルタ）。
    - 統合ジョブ `run_news_collection`：各ソース独立で回し、失敗を他ソースに影響させない実装。
  - スキーマ/初期化 (`kabusys.data.schema`):
    - DuckDB 用 DDL を定義（Raw / Processed / Feature / Execution レイヤー）。
    - 各種テーブル（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, features, ai_scores, signals, orders, trades, positions, 等）および関連インデックスを実装。
    - `init_schema(db_path)` によりディレクトリ作成とテーブル初期化（冪等）を実行、`get_connection` を提供。
  - ETL パイプライン基盤 (`kabusys.data.pipeline`):
    - 差分更新の考え方を実装（最終取得日判定、backfill_days による再取得）。
    - ETL 実行結果を格納する dataclass `ETLResult`（品質問題・エラーの集約とシリアライズ）。
    - テーブル存在チェック、最大日付取得ヘルパ、取引日調整ヘルパを実装。
    - 個別 ETL ジョブ: `run_prices_etl`（差分取得 → 保存の流れ）を実装（J-Quants クライアントを使用）。
  - ドキュメント文字列：各モジュールに設計方針や振る舞いを明記。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Security
- news_collector で defusedxml を使用し、XML Bomb 等への対策を実装。
- RSS フェッチで SSRF 対策（ホストのプライベートアドレス検出、スキーム検証、リダイレクト検査）を導入。
- .env 読み込みで OS 環境変数を保護する設計。

## [0.1.0] - 2026-03-17

初回公開（Unreleased と同内容をスナップショットとして記載）。

- 上記「Added」項目を含む初期機能セットをリリース。
- パッケージバージョンを 0.1.0 に設定。

---

## 既知の問題 / 注意点
- pipeline.run_prices_etl の戻り値
  - 実装中の関数 `run_prices_etl` の末尾が不完全で、現在は (len(records), ) のようにタプルが不完全に返される可能性があります（保存件数 saved を含むべきところ）。ETL 呼び出し側での期待値と整合させる必要があります。
- strategy と execution パッケージはプレースホルダ（__init__.py が空）であり、戦略ロジックや実発注ロジックは未実装です。
- quality モジュールの実装（品質チェック）の詳細がこのスナップショットに含まれていない場合があります（pipeline から参照しているため、実装またはモックの存在を確認してください）。
- J-Quants のリフレッシュトークンが未設定の場合、get_id_token は ValueError を投げます。運用前に必須環境変数を設定してください。
- DuckDB スキーマの DDL は多くの CHECK 制約を含みます。既存データを移行する場合はデータ整合性を事前に確認してください。

## マイグレーション / 設定メモ
- 環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須。
  - DUCKDB_PATH, SQLITE_PATH はデフォルト値あり（必要に応じて上書き）。
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。
  - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか。
  - 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB 初期化:
  - 初回は `kabusys.data.schema.init_schema(db_path)` を呼び出してテーブルを作成してください。
  - 既存 DB に接続するだけなら `get_connection` を使用。

---

貢献・フィードバック歓迎。重大なバグやセキュリティ問題が見つかった場合は issue を作成してください。