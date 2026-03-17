# Changelog

すべての注目すべき変更点をここに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠しています。

フォーマットの意味:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連の改善

## [Unreleased]

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア基盤を実装しました。以下の機能・設計方針を含みます。

### Added
- パッケージ基礎
  - パッケージ初期化 `kabusys.__init__` を導入し、バージョン情報 (`0.1.0`) と主要サブパッケージ (`data`, `strategy`, `execution`, `monitoring`) を公開。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを追加。
  - 自動ロード:
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を読み込み。
    - OS 環境変数を保護しつつ `.env.local` で上書き可能。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用）。
  - `.env` パーサーの強化:
    - コメント行、`export KEY=val` 形式、シングル・ダブルクォート内のエスケープ処理、インラインコメント処理に対応。
  - 必須設定取得ヘルパー `_require` と、J-Quants / kabuAPI / Slack / DB パス等のプロパティを提供。
  - `KABUSYS_ENV` と `LOG_LEVEL` の値検証（許容値チェック）と、`is_live`/`is_paper`/`is_dev` 判定プロパティを追加。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しの共通処理 `_request` を実装:
    - ベース URL とクエリ生成、JSON ボディサポート（POST）、JSON デコード検証。
    - レート制御: 固定間隔スロットリングで 120 req/min を遵守する `_RateLimiter` を導入。
    - リトライロジック: 指数バックオフ（最大 3 回）、HTTP ステータス 408/429 および 5xx に対する再試行。
    - 401（Unauthorized）発生時はトークンを自動リフレッシュして 1 回リトライ（無限再帰を防止）。
    - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間で共有。
  - 認証ヘルパー `get_id_token`（refresh token → id token）。
  - データ取得関数（ページネーション対応）:
    - `fetch_daily_quotes`（株価日足）
    - `fetch_financial_statements`（四半期財務）
    - `fetch_market_calendar`（JPX マーケットカレンダー）
    - 各関数は pagination_key によるページネーションをサポート。
  - DuckDB への保存関数（冪等設計: ON CONFLICT DO UPDATE）:
    - `save_daily_quotes`, `save_financial_statements`, `save_market_calendar`
    - 保存時に UTC の fetched_at を記録し、PK 欠損行のスキップとログ出力を行う。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装（堅牢な変換・空値処理・float 文字列の扱い等）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからのニュース収集機能を実装:
    - デフォルトソースに Yahoo Finance のカテゴリ RSS を設定。
    - フィード取得 (`fetch_rss`) → 前処理 → DB 保存 の一連処理を提供。
  - セキュリティ・堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定（DNS 解決 / IP 判定）、リダイレクト時の事前検証ハンドラ `_SSRFBlockRedirectHandler`。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - User-Agent と Accept-Encoding の取り扱い。
  - URL 正規化と記事 ID 生成:
    - トラッキングパラメータ（utm_* / fbclid / gclid 等）除去、クエリ整列、フラグメント削除の `_normalize_url`。
    - 正規化 URL の SHA-256 先頭32文字を記事IDにする `_make_article_id`（冪等性確保）。
  - テキスト前処理 `preprocess_text`（URL除去、空白正規化）。
  - RSS の pubDate パース `_parse_rss_datetime`（RFC 2822 → UTC へ変換。失敗時は現在時刻で代替）。
  - DuckDB への保存:
    - `save_raw_news`: チャンク INSERT、トランザクションでまとめて実行、INSERT ... RETURNING で新規挿入された記事IDを返す。
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄コードの紐付けを ON CONFLICT で冪等に保存し、実際に挿入された件数を返す。
  - 銘柄コード抽出 `extract_stock_codes`:
    - 正規表現で 4 桁数字 (日本株) を抽出し、既知コード集合と照合して重複除去して返す。
  - 統合ジョブ `run_news_collection`:
    - 複数ソースを個別に処理して DB に保存、銘柄紐付けを一括挿入。ソース単位でエラーハンドリングを行い、他ソースへの影響を抑止。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - DataSchema に基づくスキーマ定義（Raw / Processed / Feature / Execution 層）を実装。
  - テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）を含む DDL を定義。
  - 運用を考慮したインデックス群を定義（code/date スキャンや status 検索用）。
  - スキーマ初期化 API:
    - `init_schema(db_path)`：ディレクトリ作成、全 DDL とインデックスを実行して初期化済み DB 接続を返す（冪等）。
    - `get_connection(db_path)`：既存 DB への接続取得（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計方針と差分更新ロジックを実装:
    - 最小データ開始日 `_MIN_DATA_DATE`、カレンダー先読み `_CALENDAR_LOOKAHEAD_DAYS`、デフォルトバックフィル `_DEFAULT_BACKFILL_DAYS` を定義。
    - ETL 結果を表すデータクラス `ETLResult`（品質問題とエラー収集、シリアライズ用 to_dict）。
    - テーブル存在チェック `_table_exists` と最大日付取得 `_get_max_date`（汎用ユーティリティ）。
    - 直近営業日への調整 `_adjust_to_trading_day`（market_calendar を利用、最大 30 日遡る）を実装。
    - 最終取得日取得ヘルパー (`get_last_price_date`, `get_last_financial_date`, `get_last_calendar_date`) を追加。
    - 個別 ETL ジョブ (例: `run_prices_etl`) を実装する骨組みを追加（差分取得・backfill を考慮）。（注: run_prices_etl の戻り値の末尾が未完のままの箇所が存在します。）

### Security
- ニュース収集時の SSRF 対策、XML パースの堅牢化（defusedxml）、受信サイズ制限、gzip 解凍後のサイズ検査を導入。
- .env 読み込みで OS 環境変数を保護する機構を実装（`.env.local` における上書き制御含む）。

### Notes / Known issues
- pipeline.run_prices_etl の末尾に返却タプルが不完全（最後の return が途中で終わっている）箇所が見受けられます。ETL の完全な戻り値整備（prices_saved の返却）や他の ETL ジョブの実装継続が必要です。
- strategy / execution パッケージの __init__ は空実装であり、具体的な戦略・発注ロジックは未実装です。
- 一部 API 呼び出しで例外やリトライの挙動は仕様に基づくが、実運用での挙動検証（テスト・監視）が推奨されます。

---

（以降のリリースでは、各機能の追加/変更/修正点を日付つきで記録してください。）