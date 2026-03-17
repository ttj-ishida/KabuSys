# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の方針に従います。
なお、本ログはソースコードから推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-17

初期リリース — 日本株自動売買システム「KabuSys」の公開バージョン。

### 追加 (Added)
- パッケージ初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - モジュール公開: data, strategy, execution, monitoring
- 環境変数・設定管理モジュールを追加 (src/kabusys/config.py)
  - Settings クラスを公開し、J-Quants や kabuステーション、Slack、DB パス、実行環境、ログレベル等を環境変数から取得
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）を実装
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応
  - .env ファイルの行パースで export プレフィックス、クォート、インラインコメント等に対応する頑健な実装を追加
- J-Quants API クライアントを追加 (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得関数を実装（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）
  - ID トークン取得と自動リフレッシュ機能（get_id_token, トークンキャッシュ共有）
  - レート制限制御（固定間隔スロットリング: 120 req/min を守る _RateLimiter）
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx 対応、429 の Retry-After 優先）
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ (_to_float, _to_int)
  - fetched_at に UTC タイムスタンプを付与して Look-ahead Bias を防止
- ニュース収集モジュールを追加 (src/kabusys/data/news_collector.py)
  - RSS フィード収集 → 前処理 → raw_news への冪等保存 → 銘柄コード紐付け の一連処理を実装
  - URL 正規化とトラッキングパラメータ削除（_normalize_url, _make_article_id）
  - 記事 ID を SHA-256（先頭32文字）で生成して冪等性を確保
  - defusedxml を利用した安全な XML パース
  - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査用ハンドラ _SSRFBlockRedirectHandler）
  - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）
  - DB へのバルク挿入はチャンク化してトランザクション内で実行、INSERT ... RETURNING を用いて実際に挿入されたレコードのみを返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）
  - 銘柄コード抽出 (extract_stock_codes): 4桁数列のみを候補として既知コード集合でフィルタ
  - デフォルト RSS ソース定義（例: Yahoo Finance のカテゴリ RSS）
  - run_news_collection により複数ソースの収集をまとめて実行（ソース毎に独立してエラーハンドリング）
- DuckDB スキーマ定義・初期化モジュールを追加 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の3層に対応したテーブル定義を用意（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）
  - 制約（PRIMARY KEY、CHECK、FOREIGN KEY）やインデックスを明示
  - init_schema(db_path) でディレクトリ作成 → テーブル作成（冪等）し接続を返す
  - get_connection(db_path) で既存 DB への接続を取得
- ETL パイプラインモジュールを追加 (src/kabusys/data/pipeline.py)
  - 差分更新ロジック（DB の最終取得日を参照して date_from を自動算出、backfill_days により過去数日を再取得）
  - 市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS）や最小データ開始日定義
  - ETL 実行結果を表す ETLResult データクラス（品質問題一覧、エラー一覧、集計数を含む）
  - テーブル存在確認・最終日取得ユーティリティ（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）
  - run_prices_etl を含む個別 ETL ジョブ（差分取得 → 保存 → ログ出力）を実装（fetch/save の注入によりテスト容易性を確保）
- 複数の実装詳細に対するドキュメント相当の docstring を追加（設計方針・セキュリティ対策・ETL フロー等）

### 変更 (Changed)
- 初期リリースのためなし（新規実装中心）

### 修正 (Fixed)
- .env パースの堅牢化
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い、キー空白トリム等を実装（src/kabusys/config.py::_parse_env_line）
- DB 保存における重複処理を明示（ON CONFLICT DO UPDATE / DO NOTHING による冪等性確保）

### セキュリティ (Security)
- RSS XML パースに defusedxml を使用し XML-based の攻撃から保護（news_collector）
- SSRF 対策を多層で実装
  - URL スキーム検証（http/https のみ）
  - 初回とリダイレクト先両方でホストのプライベートアドレス判定（_is_private_host, _SSRFBlockRedirectHandler）
  - 不正スキームやプライベートアドレスへのアクセスを拒否
- レスポンスサイズ上限を設けることでメモリDoS / Gzip bomb を軽減（MAX_RESPONSE_BYTES）
- 外部 API 通信におけるタイムアウトとリトライ制御によりサービス拒否や悪質な応答変化に耐性を向上（jquants_client）

### パフォーマンス (Performance)
- API 呼び出しのレートリミット管理（固定間隔スロットリング）でレート制限違反とスロットリングを回避（jquants_client._RateLimiter）
- ページネーション取得でトークンキャッシュを共有して API 呼び出しを効率化（_ID_TOKEN_CACHE）
- DuckDB へのバルク挿入は executemany / チャンク化してオーバーヘッドを低減（news_collector, jquants_client）
- INSERT ... RETURNING による挿入結果の正確な把握

### 公開 API（主な関数・クラス）
- kabusys.config.Settings（settings インスタンス）
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live, is_paper, is_dev
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection, extract_stock_codes, preprocess_text
- kabusys.data.schema
  - init_schema, get_connection
- kabusys.data.pipeline
  - ETLResult, run_prices_etl, get_last_price_date, get_last_financial_date, get_last_calendar_date

### 既知の制約・注意点 (Known issues / Notes)
- J-Quants のレート・認証仕様に依存するため、API 側の仕様変更は追加対応が必要
- SQLite / DuckDB の実行環境や権限によってはファイル作成時に権限エラーが発生する可能性がある（init_schema は親ディレクトリを自動作成するが、OS 権限は考慮）
- News の銘柄コード抽出は「4桁数字かつ known_codes に存在する」方式のため、表記揺れや文脈依存の誤検出は存在し得る
- ETL の品質チェックモジュール (kabusys.data.quality) は本スナップショットに含まれておらず、品質判定ロジックは別途実装を想定

---

今後のリリースで予定している改善例:
- strategy / execution / monitoring の具象実装（現在はモジュールプレースホルダ）
- 品質チェック（quality モジュール）の追加と ETL パイプラインへの統合強化
- テストカバレッジ拡充とモック可能なインターフェイスの整理
- CLI / Supervisor 連携や運用向けメトリクス・アラート出力の実装

（以上）