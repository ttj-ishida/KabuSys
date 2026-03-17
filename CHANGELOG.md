# Changelog

すべての注目すべき変更を記録します。本ドキュメントは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-17

概要: 日本株自動売買システム「KabuSys」の初回リリース相当の実装。以下の主要コンポーネントと機能を含みます（コードベースから推測して作成）。

### Added
- パッケージ基礎
  - パッケージ名 kabusys を定義し、モジュール構成（data, strategy, execution, monitoring）を公開。バージョンは 0.1.0 に設定。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD に依存しない実装）。
  - .env パーサを独自実装（コメント行、export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント等に対応）。
  - Settings クラスを提供し、必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）やデフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH）を管理。
  - KABUSYS_ENV と LOG_LEVEL の値検証およびユーティリティプロパティ（is_live / is_paper / is_dev）を実装。

- データ取得クライアント / data/jquants_client.py
  - J-Quants API クライアントを実装。
    - レート制御: 固定間隔スロットリング（120 req/min）。
    - リトライ: 指数バックオフ、最大試行回数・対象ステータス（408, 429, 5xx）に対応。
    - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回まで）を実装。
    - ページネーション対応でデータを継続取得。
    - データ取得関数: fetch_daily_quotes（OHLCV）、fetch_financial_statements（四半期 BS/PL）、fetch_market_calendar（JPX カレンダー）。
    - 認証トークン取得関数 get_id_token（refreshtoken → idToken）。
  - DuckDB へ保存する関数を実装（冪等性確保）。
    - save_daily_quotes, save_financial_statements, save_market_calendar: ON CONFLICT DO UPDATE による上書き保持と fetched_at の付与。
    - 型変換ユーティリティ: _to_float, _to_int（厳密な int 変換ロジックを含む）。
    - 各保存処理で PK 欠損行のスキップとログ出力を行う。

- ニュース収集モジュール / data/news_collector.py
  - RSS フィードからニュースを収集し DuckDB に保存する ETL コンポーネントを実装。
    - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）。
    - セキュリティ対策:
      - defusedxml による XML パース（XML Bomb 等への対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルでないことをチェック、リダイレクト先の検査を行うカスタムリダイレクトハンドラを実装。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、Content-Length および実際の読み込みサイズでチェック。gzip 解凍後もサイズ検証。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）に基づく記事 ID の生成（正規化 URL の SHA-256 の先頭 32 文字）。
    - テキスト前処理（URL 除去・空白正規化）。
    - 保存処理:
      - save_raw_news: チャンク化（上限 _INSERT_CHUNK_SIZE）してトランザクションで INSERT INTO raw_news ... ON CONFLICT DO NOTHING RETURNING id を実行。実際に挿入された記事ID一覧を返す。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING RETURNING 1）し、挿入数を正確に返す。トランザクションとチャンク処理を採用。
    - 銘柄コード抽出: 正規表現で 4 桁数字を抽出し、known_codes セットでフィルタして重複除去。
    - run_news_collection: 複数ソース一括実行、ソース単位で独立したエラーハンドリング（1 ソース失敗で他を継続）、新規保存件数を返す。

- スキーマ管理 / data/schema.py
  - DuckDB 用のスキーマ定義を実装（Raw / Processed / Feature / Execution の多層構造）。
    - Raw 層: raw_prices, raw_financials, raw_news, raw_executions。
    - Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
    - Feature 層: features, ai_scores。
    - Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルに対して適切な型・チェック制約・主キー・外部キーを定義。
  - クエリ性能を考慮したインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) を提供し、親ディレクトリ自動作成、全テーブル・インデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB に接続（スキーマ初期化は行わない旨明記）。

- ETL パイプライン / data/pipeline.py
  - ETL の設計と一部実装。
    - 差分更新方針: DB の最終取得日を参照し、backfill_days を用いて多少遡って再取得して API の後出し修正を吸収する設計。
    - ETLResult データクラスを追加し、ETL 実行結果（取得数・保存数・品質問題・エラー等）を集約。品質問題を辞書化して出力可能。
    - 内部ユーティリティ: テーブル存在チェック、テーブルの最大日付取得（_get_max_date）、営業日補正ヘルパー（_adjust_to_trading_day）。
    - 差分用ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
    - run_prices_etl を実装（date_from 自動決定、J-Quants からの差分取得と保存を呼び出す）。（注: コードの末尾は一部切れているため、パイプラインの続きは別実装想定）

### Security & Reliability notes
- API クライアントと RSS 取得の両方で堅牢性を重視（レート制御、リトライ、トークン自動更新、SSRF/サイズ上限/defusedxml）。
- DuckDB 側は ON CONFLICT を活用して冪等性を確保しており、トランザクション管理（begin/commit/rollback）で一貫性を保持。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

注記:
- data/quality など参照されているモジュールの実装は本コード抜粋では示されていませんが、ETL 側はそれらと連携する設計になっています。
- pipeline モジュールの末尾が切れている箇所があり、run_prices_etl の戻り値や後続処理の完全実装はコード全体に依存します。将来的なリリースでパイプライン統合（品質チェック、バックフィル、他ジョブの連携）が進む想定です。