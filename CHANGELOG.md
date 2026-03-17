# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog の慣習に従って記載しています。

## [Unreleased]


## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: KabuSys — 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py にて設定）

- 環境設定・自動.envローダー（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする仕組みを追加。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパースは export プレフィックス、クォート文字（シングル/ダブル）、エスケープ、インラインコメント（クォートあり/なしの違い）などに対応。
  - .env.local は .env の上書き（override）として扱い、OS 環境変数は保護（protected）される。
  - 必須設定取得ヘルパー _require と Settings クラスを提供。J-Quants、kabu API、Slack、DB パス等の設定プロパティを用意。
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL のバリデーションを実装。
  - デフォルト DB パス（DuckDB: data/kabusys.duckdb、SQLite: data/monitoring.db）を設定。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出し用ユーティリティ _request を実装。JSON デコード、タイムアウト、クエリパラメータ、POST ボディ対応。
  - レート制限制御（固定間隔スロットリング）を実装（120 req/min）。_RateLimiter により呼び出し間隔を管理。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大 3 回）。HTTP 408/429 と 5xx をリトライ対象に含む。429 の場合は Retry-After ヘッダーを優先。
  - 401 Unauthorized 受信時は自動でリフレッシュトークンから id_token を更新して1回だけリトライする仕組みを追加（再帰防止のため allow_refresh フラグ実装）。
  - id_token キャッシュ（モジュールレベル）を実装し、ページネーション間でトークンを共有。
  - データ取得関数を実装:
    - fetch_daily_quotes: 株価日足（OHLCV）のページネーション対応取得。
    - fetch_financial_statements: 四半期財務データの取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB へ冪等に保存する関数を追加（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ (_to_float, _to_int) を実装。空値や不正値は None に変換。_to_int は "1.0" のような float 文字列を考慮し、小数部が非ゼロの場合は None を返す仕様。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し DuckDB に保存する ETL ロジックを追加。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時にスキームとホストを検証する _SSRFBlockRedirectHandler、ホストがプライベート/ループバック/リンクローカル/マルチキャストでないことを検査する _is_private_host を実装。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍後のサイズ検証（Gzip bomb 対策）。
  - その他の機能:
    - URL 正規化とトラッキングパラメータ除去（_normalize_url、_TRACKING_PARAM_PREFIXES）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成する方式（冪等性担保）。
    - テキスト前処理（URL 除去、空白正規化）preprocess_text。
    - RSS pubDate のパース（_parse_rss_datetime、UTC 変換、フォールバック日時ロジック）。
    - fetch_rss: 名前空間対応やフォールバックを含む RSS 取得関数（gzip 対応、最終 URL 再検証、XML パース失敗時は空リストを返す）。
    - DB 保存関数:
      - save_raw_news: INSERT ... RETURNING を使って新規挿入記事 ID を返す（チャンク単位、トランザクションで実行）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING で実際に挿入された件数を返す）。
    - 銘柄コード抽出ロジック: テキスト中の 4 桁数字パターンを既知銘柄セットでフィルタ（extract_stock_codes）。
    - run_news_collection: 複数 RSS ソースを順次処理し、ソース単位でエラーを隔離（1 ソースの失敗で他ソースは継続）。新規保存数の集計と既知銘柄への紐付け処理をまとめて実行。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - DataPlatform に基づく 3 層（Raw / Processed / Feature）および Execution 層のテーブル定義を追加。
  - 代表的なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに PRIMARY KEY / CHECK 制約や外部キー制約を付与。
  - クエリ性能を考慮したインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status など）。
  - init_schema(db_path) を実装し、ファイルの親ディレクトリ自動作成、DDL の逐次実行でスキーマを冪等に初期化する。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラスを追加し、ETL 実行結果・品質問題・エラーの概観を保持・辞書化できるようにした。
  - 差分更新ヘルパー:
    - _table_exists, _get_max_date による最終取得日の取得ユーティリティ。
    - get_last_price_date, get_last_financial_date, get_last_calendar_date を公開。
  - 市場カレンダ補助: _adjust_to_trading_day（非営業日の調整ロジック）。
  - run_prices_etl の骨組みを追加:
    - 差分更新のデフォルト動作（最終取得日から backfill_days 前を date_from とする）を実装。
    - J-Quants からの取得と保存（fetch_daily_quotes, save_daily_quotes）を呼び出すフローを実装（戻り値は取得件数と保存件数を返す設計）。
  - ETL 設計方針として、backfill（日次の再取得で API 後出し修正を吸収）・品質チェックを想定する実装になっている（quality モジュール連携は外部に依存）。

- テスト・開発向けフック
  - news_collector の _urlopen をモック差し替え可能にしてテスト容易性を確保。
  - jquants_client の id_token を注入可能にすることで単体テストが容易。

### Changed
- （初回リリースにつき変更履歴はありません。）

### Fixed
- （初回リリースにつき修正履歴はありません。）

### Security
- RSS パーサーに defusedxml を使用し、SSRF・XML Bomb・不正スキーム等の対策を明記。
- HTTP レスポンスサイズ制限や gzip 解凍後の上限チェックを実装してメモリ DoS を軽減。

### Notes / Developer hints
- 自動 .env ロードはテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化可能。
- jquants_client の再試行・トークン更新ロジックは id_token の自動リフレッシュを行うため、get_id_token の呼び出し先で無限再帰しないよう allow_refresh フラグを使用。
- DuckDB のスキーマ初期化は init_schema() を推奨。既存 DB に接続する場合は get_connection() を使用し、初回のみ init_schema() を呼ぶこと。
- NewsCollector の記事 ID は正規化後の URL ハッシュに依存するため、URL 正規化ロジック変更は重複検出に影響します。

--- 

今後のリリースでは以下のような点が想定されます:
- pipeline の品質チェック（quality モジュール）との統合強化と異常対応ポリシーの自動化。
- execution 層（kabu API を用いた発注・約定処理）の実装・テスト。
- モニタリング・Slack 通知連携の実装（設定は既に Settings で用意済み）。