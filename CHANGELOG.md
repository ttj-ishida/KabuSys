# Changelog

すべての注目すべき変更点をここに記載します。  
このファイルは Keep a Changelog の形式に準拠しています。  

注意: 以下は提示されたコードベースの内容から推測して作成した変更履歴です。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: `kabusys`（日本株自動売買システムの基礎実装）
  - パッケージメタ: `src/kabusys/__init__.py` にバージョン `0.1.0` と公開APIを定義。

- 環境設定/ロード機能（`kabusys.config`）
  - `.env` / `.env.local` の自動読み込み（プロジェクトルートの自動検出: .git または pyproject.toml を基準）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応（テスト用途など）。
  - 強化された `.env` パース (`export KEY=val`、クォート付き文字列のエスケープ処理、インラインコメント処理など)。
  - 環境変数取得ヘルパー `_require` と `Settings` クラスを実装。以下の設定プロパティを提供:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`, `sqlite_path`
    - システム: `env`, `log_level`, `is_live`, `is_paper`, `is_dev`
  - `env` / `log_level` の値検証（許容値チェック）。

- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - ベース機能:
    - 株価日足（OHLCV）取得: `fetch_daily_quotes`（ページネーション対応）
    - 財務データ（四半期BS/PL）取得: `fetch_financial_statements`（ページネーション対応）
    - JPX マーケットカレンダー取得: `fetch_market_calendar`
  - 認証: リフレッシュトークンから ID トークンを取得する `get_id_token` 実装。
  - レート制御: 固定間隔スロットリングによるレートリミット実装（120 req/min 相当） (`_RateLimiter`)。
  - リトライロジック: 指数バックオフ、最大3回リトライ、408/429/5xx をリトライ対象、429 に対して Retry-After を尊重。
  - 401 (Unauthorized) 受信時にトークン自動リフレッシュを 1 回行ってリトライする実装（無限再帰を回避）。
  - DuckDB への冪等保存用ユーティリティ:
    - `save_daily_quotes` / `save_financial_statements` / `save_market_calendar`：ON CONFLICT DO UPDATE を用いた更新、PK欠損行のスキップ、fetched_at を UTC で記録。
  - 型変換補助: `_to_float`, `_to_int`（安全に None を扱う、"1.0" などの float 文字列ハンドリング）。

- ニュース収集モジュール（`kabusys.data.news_collector`）
  - RSS フィード取得と記事保存の実装:
    - `fetch_rss`: RSS フィードの取得・パース（defusedxml を利用して XML 攻撃対策）。
    - `save_raw_news`: DuckDB の `raw_news` にチャンク単位でトランザクション挿入（INSERT ... RETURNING を使用して実際に挿入した記事IDを返す）。
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄コードの紐付け保存（ON CONFLICT DO NOTHING、チャンク挿入）。
    - `extract_stock_codes`: テキストから 4 桁銘柄コードを抽出（既知コードセットでフィルタ・重複除去）。
    - `run_news_collection`: 複数RSSソースを横断し収集 → raw_news 保存 → 銘柄紐付けまでの統合ジョブ（各ソースを独立してエラーハンドリング）。
  - 安全性・堅牢性:
    - URL 正規化とトラッキングパラメータ除去 (`_normalize_url`)、記事ID は正規化URLの SHA-256 (先頭32文字)。
    - URL スキーム検証（http/https のみ許可）および SSRF 対策（プライベートIP/ループバック/リンクローカルを拒否）。
    - リダイレクト時にもスキーム/プライベートアドレス検査するカスタムハンドラ `_SSRFBlockRedirectHandler`。
    - レスポンスサイズ上限（10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - 受信時の Content-Length 事前チェック、不正値の無視。
    - テキスト前処理（URL 除去、連続空白正規化）。
    - XML パース失敗やその他の問題に対するログ出力とフォールバック。

- DuckDB スキーマ定義と初期化（`kabusys.data.schema`）
  - 3 層（Raw / Processed / Feature）＋ Execution レイヤーのテーブル DDL を定義:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）と用途に応じたデータ型を定義。
  - 頻出クエリを想定したインデックス群を定義。
  - スキーマ初期化関数 `init_schema(db_path)`（親ディレクトリ自動作成、冪等的にテーブル作成）と既存接続取得 `get_connection` を提供。

- ETL パイプライン基礎（`kabusys.data.pipeline`）
  - ETL 結果を表す `ETLResult` dataclass（品質検査結果やエラー一覧を保持、辞書化メソッドあり）。
  - 差分更新のためのユーティリティ:
    - テーブル存在チェック `_table_exists`、最大日付取得 `_get_max_date`、最終取得日取得用ヘルパー (`get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`)。
    - 市場カレンダーに基づく営業日補正 `_adjust_to_trading_day`。
  - 個別 ETL ジョブ雛形（差分更新 / バックフィル対応）:
    - `run_prices_etl`（差分取得、backfill_days に基づく再取得、jquants_client の fetch / save を組み合わせる）を実装。

### Changed
- （初回リリース）該当なし。

### Fixed
- （初回リリース）該当なし。

### Security
- RSS XML のパースに defusedxml を採用し XML 関連攻撃を緩和。
- news_collector における SSRF 対策:
  - スキーム検証（http/https 限定）
  - ホスト/IP のプライベートアドレス検出と拒否
  - リダイレクト先検査
- RSS レスポンスサイズ上限と gzip 解凍後の検査により DoS/Decompression bomb を軽減。
- 環境変数の取り扱いで OS 環境変数を保護する設計（`.env.local` の上書き制御など）。

### Performance
- API 呼び出しに対する固定間隔スロットリング（120 req/min 想定）を導入してレート制限を順守。
- ニュース保存はチャンク化してバルクINSERTを行い、トランザクションをまとめてオーバーヘッドを低減。
- DuckDB 側での ON CONFLICT を利用して冪等性と更新コストを抑制。

### Notes / Known issues (推測)
- 提示された `run_prices_etl` の末尾が途中で切れている（return の直後でファイルが終了しているように見える）。実際のリポジトリでは完全な戻り値と他の ETL ジョブ（financials, calendar など）や品質チェック（`kabusys.data.quality`）の統合が必要と推測される。
- `execution` と `strategy` パッケージはパッケージ初期化ファイルのみ存在し、具象実装はまだ追加されていない（今後の実装予定）。
- DuckDB スキーマ中の一部外部キー制約（例: news_symbols → news_articles）が存在するため、データ挿入順序に注意が必要。

---

以上がこのコードベース（presented files）から推測される初期リリースの CHANGELOG です。必要であれば、各変更点をさらにファイル/行レベルでマッピングした詳細なリリースノート（例: 主要関数のシグネチャ一覧、例外ハンドリング方針、既知の TODO）も作成します。どのレベルの詳細が必要か教えてください。