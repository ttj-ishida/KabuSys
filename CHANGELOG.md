# CHANGELOG.md

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
初期リリースはコードベースから推測して作成しています。

現在のバージョンは 0.1.0（パッケージ定義: kabusys.__version = "0.1.0"）です。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買プラットフォームのコア機能を実装しています。主な追加点は以下のとおりです。

### Added
- パッケージ基盤
  - src/kabusys/__init__.py
    - パッケージ名とバージョン定義（0.1.0）。
    - 公開モジュール一覧: data, strategy, execution, monitoring（strategy と execution は空のパッケージとして用意）。
- 設定管理
  - src/kabusys/config.py
    - .env または環境変数から読み込む設定管理。
    - プロジェクトルート自動検出（.git または pyproject.toml を探索）により、CWD に依存しない自動 .env 読み込み。
    - .env/.env.local の読み込み優先順位（OS 環境変数 > .env.local > .env）とオーバーライド制御。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - 必須環境変数を取得する _require() と Settings クラス（J-Quants、kabuステーション、Slack、DB パス、環境・ログレベル判定など）。
    - KABUSYS_ENV、LOG_LEVEL の検証（許容値チェック）。
- データアクセス（J-Quants）
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアント実装。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時にリフレッシュトークンで id_token を自動リフレッシュして 1 回だけ再試行。
    - ページネーション対応の取得関数:
      - fetch_daily_quotes (株価日足、OHLCV)
      - fetch_financial_statements (四半期 BS/PL)
      - fetch_market_calendar (JPX カレンダー)
    - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - データ型変換ユーティリティ (_to_float, _to_int) と fetched_at の UTC タイムスタンプ記録による Look-ahead バイアス対策。
- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を収集して raw_news に保存するモジュール。
    - デフォルト RSS ソース（例: Yahoo Finance）。
    - セキュリティ/堅牢性のための実装:
      - defusedxml を使った XML パース（XML Bomb 対策）。
      - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバック/リンクローカルかのチェック、リダイレクト先の検証（カスタム HTTPRedirectHandler）。
      - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - トラッキングパラメータ除去、URL 正規化、記事IDは正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL 除去・空白正規化）、RSS pubDate のパース（UTC に正規化）等。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING と RETURNING を用いた新規挿入IDの返却、トランザクションとチャンク挿入による効率化。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING, RETURNING）。
    - 銘柄コード抽出機能: テキスト中の 4 桁数字候補から既知銘柄セットと照合して抽出（重複除去）。
    - 統合ジョブ run_news_collection: 複数 RSS ソースを安全に収集し、失敗したソースはスキップして他を継続。known_codes が与えられれば銘柄紐付けを実行。
- データベーススキーマ / 初期化
  - src/kabusys/data/schema.py
    - DuckDB 向けスキーマ定義（Raw / Processed / Feature / Execution 層）。
    - 主なテーブル:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）とインデックスの定義（頻出クエリ向け）。
    - init_schema(db_path) によりディレクトリ作成 -> DuckDB 接続 -> DDL/インデックス適用（冪等）。
    - get_connection(db_path) で既存 DB 接続取得（スキーマ初期化は行わない）。
- ETL / パイプライン
  - src/kabusys/data/pipeline.py
    - 差分更新を中心とした ETL パイプラインの骨格を提供。
    - 差分取得ロジック（DB の最終取得日を確認し backfill_days に基づき再取得期間を決定）。
    - 市場カレンダーの先読み、バックフィルデフォルト、品質チェック呼び出し（quality モジュールと連携する想定）。
    - ETLResult データクラスにより ETL のメトリクス・品質問題・エラーを集約して返却。
    - ヘルパー: テーブル存在チェック、最大日付取得、営業日調整、get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - run_prices_etl の実装骨子（差分ロジック・fetch->save フロー）。（未完の戻り値組立等はコードから推測）
- その他
  - 空のパッケージ初期化ファイルを用意:
    - src/kabusys/data/__init__.py
    - src/kabusys/execution/__init__.py
    - src/kabusys/strategy/__init__.py

### Security
- ニュース収集における SSRF 対策や defusedxml による XML 攻撃対策を実装。
- J-Quants クライアントは API レート制限とリトライ（429 の Retry-After 優先）を尊重するよう実装。

### Notes / Migration / 運用上の注意
- .env 自動ロードはデフォルトで有効。テストや特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルト DB パス:
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可能）
  - SQLite (monitoring 用): data/monitoring.db（環境変数 SQLITE_PATH）
- KABUSYS_ENV の許容値は development / paper_trading / live。LOG_LEVEL は標準的なログレベルのみ許容。
- jquants_client の get_id_token は内部で _request を呼び出します。allow_refresh=False を渡して無限再帰を防ぐ実装になっています。
- news_collector の fetch_rss は非 http(s) スキームやプライベートホストを拒否します。RSS ソースの URL は公開 reachable な http(s) を指定してください。
- DuckDB スキーマは init_schema() により初期化可能。既存テーブルは CREATE IF NOT EXISTS により上書きせず残すため、安全に呼び出せます。

### Fixed
- （なし）

### Changed
- （なし）

---

今後のリリースでは、strategy / execution の具体的な取引ロジック、モニタリング機能、品質チェックモジュール（quality）の統合、テストカバレッジおよびドキュメントの拡充が想定されます。必要があれば、この CHANGELOG を元により詳細なリリースノートや移行手順を作成します。