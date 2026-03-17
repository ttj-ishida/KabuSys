CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース。パッケージメタ情報:
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート対象: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: .git または pyproject.toml を基準に検索（cwd に依存しない）。
    - 自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント判定等をサポート。
  - _load_env_file による上書き制御（override）と保護キー(protected)の扱い。
  - Settings クラスでアプリケーション設定を提供:
    - J-Quants / kabu ステーション / Slack / データベース (DuckDB, SQLite) 等のプロパティ。
    - KABUSYS_ENV の許容値検証 (development, paper_trading, live) と LOG_LEVEL 検証。
    - is_live / is_paper / is_dev のヘルパー。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 提供機能:
    - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得。
  - 設計上の注目点:
    - API レート制御（120 req/min）を守る固定間隔スロットリングの _RateLimiter を実装。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。再試行対象は HTTP 408/429/5xx。
    - 401 受信時は IDトークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で実装する save_* 関数を提供:
      - save_daily_quotes (raw_prices)
      - save_financial_statements (raw_financials)
      - save_market_calendar (market_calendar)
    - データ取得時刻 (fetched_at) を UTC 形式で保存して Look-ahead Bias 防止。
    - 入力値変換ユーティリティ: _to_float, _to_int（文字列/float の扱いやエラー耐性に注意）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュース記事を収集し DuckDB に保存する機能を実装。
  - デフォルト RSS ソースに Yahoo Finance を設定。
  - セキュリティ / ロバストネス:
    - defusedxml を用いた XML パースで XML Bomb 等に対処。
    - SSRF 対策: http/https 限定のスキーム検証、プライベートアドレス判定(_is_private_host)、リダイレクト時の検査を行う _SSRFBlockRedirectHandler。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10 MB) と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - URL 正規化 (_normalize_url)、トラッキングパラメータ除去（utm_* 等）。
    - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
  - フロー:
    - fetch_rss: RSS を取得して NewsArticle リストを返却（pubDate パース、content:encoded 優先、URL 検証、前処理）。
    - preprocess_text: URL 除去・空白正規化。
    - save_raw_news: チャンク分割・トランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用して新規挿入 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（重複除去、トランザクション、RETURNING により実挿入数を正確に返す）。
    - extract_stock_codes: テキスト中の 4 桁数字を候補とし、known_codes に従って抽出（重複除去）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層に対応したテーブル定義を実装。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY、CHECK、FOREIGN KEY）を定義。
  - パフォーマンス用インデックスを作成。
  - init_schema(db_path) によりディレクトリ作成→DDL実行→インデックス作成を行い接続を返す（冪等）。
  - get_connection で既存 DB への接続を取得。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass: ETL の実行結果（取得/保存件数、品質問題、エラー等）を表現。品質問題を辞書化する to_dict を提供。
  - ユーティリティ:
    - テーブル存在チェック、指定カラムの最大日付取得ヘルパー(_table_exists, _get_max_date)。
    - 取引日調整ヘルパー (_adjust_to_trading_day)。
    - 最終取得日取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - 個別 ETL ジョブ（例: run_prices_etl）:
    - 差分更新ロジック（DB の最終取得日に基づく date_from の算出、バックフィル指定）。
    - J-Quants クライアントを用いた取得と save_* による冪等保存。
    - 定数: データ開始日 _MIN_DATA_DATE (2017-01-01), カレンダー先読み日数、デフォルト backfill_days = 3。
    - 品質チェックモジュールとの連携を想定（quality モジュール参照）。

- その他
  - モジュール雛形: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を含む（将来的な拡張ポイント）。

### Changed
- なし

### Fixed
- なし

### Security
- RSS/XML 周りにおける複数のセキュリティ対策を追加（defusedxml、SSRF 検査、応答サイズ制限、リダイレクト検査）。

Notes
-----
- 全体設計は「冪等性」「外部 API への優しいアクセス（レート制御・リトライ）」「データ品質追跡（fetched_at 等）」を重視しています。
- ETL や収集ジョブは例外をロギングして継続する方針（Fail-Fast ではなく全件収集）。呼び出し元がエラー判定・リトライ方針を決定する設計です。
- 今後のバージョンでは strategy / execution / monitoring 周りの実装、品質チェックルールの実装、より細かなテスト・運用機能（ロギング設定・メトリクス等）の追加を想定しています。

---
このファイルはプロジェクトの初期リリースに関する要点をコードベースから推測してまとめたもので、実際の変更履歴やリリースノート用途に応じて追記・修正してください。