# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
当リポジトリはセマンティックバージョニングに従います。

## [Unreleased]
（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-17
Initial release

### Added
- パッケージの初期リリースを追加しました（kabusys v0.1.0）。
- 基本パッケージ構成を導入:
  - モジュール: kabusys.config, kabusys.data (jquants_client, news_collector, schema, pipeline), kabusys.strategy, kabusys.execution, kabusys.data パッケージ初期化。
- 環境設定管理（kabusys.config）を実装:
  - .env ファイルや環境変数からの自動読み込み機能を追加（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動でプロジェクトルートを探索。
  - .env のパース処理を実装（コメント、export プレフィックス、シングル/ダブルクォート、インラインコメントの扱いなどに対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須設定取得用ユーティリティ _require() と Settings クラスを提供。主なプロパティ:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN を必須)
    - kabu_api_password, kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token, slack_channel_id
    - duckdb_path (デフォルト: data/kabusys.duckdb)
    - sqlite_path (デフォルト: data/monitoring.db)
    - env (KABUSYS_ENV: development|paper_trading|live の検証)
    - log_level (LOG_LEVEL の検証)
    - is_live / is_paper / is_dev の便宜プロパティ
- J-Quants API クライアント（kabusys.data.jquants_client）を実装:
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用 API 呼び出し関数を追加:
    - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - 設計上の特徴:
    - API レート制限対応（120 req/min）: 固定間隔スロットリング RateLimiter 実装。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行）。
    - 401 受信時の自動トークンリフレッシュを 1 回だけ行い再試行。
    - ページネーション対応（pagination_key を利用）。
    - fetched_at を UTC で付与して取得時刻を記録（Look-ahead Bias 対策）。
    - DuckDB への保存関数（冪等性を担保する ON CONFLICT DO UPDATE を使用）:
      - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - 型変換ユーティリティ: _to_float(), _to_int()（安全な変換ルール）
- ニュース収集モジュール（kabusys.data.news_collector）を実装:
  - RSS フィード取得と raw_news 保存の ETL を提供:
    - fetch_rss(), save_raw_news(), save_news_symbols(), _save_news_symbols_bulk(), extract_stock_codes(), run_news_collection()
  - 設計上の特徴・安全対策:
    - RSS XML パースで defusedxml を使用し XML ベースの脆弱性を軽減。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時のスキーム＆ホスト検証を行うカスタム HTTPRedirectHandler を導入。
      - ホスト名を DNS 解決してプライベート/ループバック/リンクローカル/マルチキャストを拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip 解凍後もサイズ検査を実施。
    - トラッキングパラメータ（utm_*, fbclid 等）の削除と URL 正規化を行い、記事ID を正規化後 URL の SHA-256（先頭32文字）で生成。
    - テキスト前処理（URL 除去、空白正規化）を実装。
    - DB 保存はチャンク化して一つのトランザクションで行い、INSERT ... RETURNING により実際に挿入されたレコードを返す実装。
    - 銘柄コード抽出機能: 4桁数字を検出し known_codes でフィルタする extract_stock_codes() を提供。
    - HTTP クライアント処理はテスト容易性のため _urlopen を差し替え可能（モック可能）。
  - デフォルト RSS ソース: Yahoo Finance（news.yahoo.co.jp のビジネスカテゴリ RSS）。
- DuckDB スキーマ（kabusys.data.schema）を導入:
  - DataSchema.md に基づく多層スキーマを作成:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な型チェック制約（CHECK）や外部キーを定義。
  - 頻出クエリ向けのインデックスを追加（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - 初期化ユーティリティ:
    - init_schema(db_path) — ディレクトリ作成、DDL とインデックス実行、DuckDB 接続を返す（冪等）。
    - get_connection(db_path) — 既存 DB への接続取得（スキーマ初期化は行わない）。
- ETL パイプラインの基礎（kabusys.data.pipeline）を追加:
  - 差分更新、バックフィル、品質チェックを想定した実装骨格を提供。
  - ETLResult dataclass（実行結果の集約、品質問題とエラーの集計）を実装。
  - テーブル存在チェック、最終取得日の取得ユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）を提供。
  - run_prices_etl() による差分取得ロジック（最終取得日からの backfill を考慮）を実装（J-Quants クライアントとの連携）。
  - 市場カレンダー調整ヘルパー: _adjust_to_trading_day()（非営業日の調整）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS / XML 処理に defusedxml を採用して XML ベースの攻撃リスクを軽減。
- ニュース収集で SSRF を考慮したスキーム／ホスト検証、リダイレクト検査を導入。
- .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を導入し、意図しない上書きを回避。
- J-Quants クライアントでトークンリフレッシュ時の無限再帰を防ぐ allow_refresh フラグを実装。

### Notes / Implementation details
- DuckDB の INSERT 文は ON CONFLICT DO UPDATE / DO NOTHING を多用しており、ETL の冪等性（安全な再実行）を重視しています。
- news_collector の fetch_rss() は XML パースエラーや大きすぎるレスポンスを検出した場合は空リストを返し、run_news_collection() はソースごとに独立してエラーハンドリングを行うため、あるソースの失敗が他に波及しない設計です。
- pipeline モジュールは品質チェックモジュール（kabusys.data.quality）との連携を想定しています（品質チェックは致命的問題があっても ETL を継続する方針）。
- HTTP クライアントや外部 API 呼び出し部はテストのために差し替え／モック可能な実装を心がけています（例: _urlopen, id token の注入）。

---

（注）本 CHANGELOG はソースコードの実装内容から推測して作成したものであり、リリース日・バージョン番号はソース中の __version__ や現行日付に基づき記載しています。必要に応じて日付や細部を実際のリリースに合わせて更新してください。