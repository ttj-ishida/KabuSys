CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
この CHANGELOG は「Keep a Changelog」仕様に準拠しています。  

注: 本ドキュメントの内容はリポジトリ内のコードから推測して作成しています。実装・設計の意図に基づく要約であり、実際のコミット履歴に基づくものではありません。

Unreleased
----------

- 既知の問題:
  - data.pipeline.run_prices_etl() の戻り値処理が途中で切れており（return が不完全）タプルを正しく返しません。短期的に修正が必要です。

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージルート: src/kabusys/__init__.py にてバージョンと公開モジュールを定義。

- 環境変数/設定管理モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して検出（CWD 非依存）。
    - 読み込み順: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export プレフィックス、クォート、インラインコメント等に対応。
    - 既存 OS 環境変数を保護する protected セットによる上書き制御。
  - Settings クラスを公開（settings インスタンス）:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供。
    - KABUSYS_ENV（development | paper_trading | live）と LOG_LEVEL の検証を実装。
    - デフォルトの DB パス（DuckDB/SQLite）や KABU_API_BASE_URL のデフォルトを設定。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しユーティリティ:
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装（_RateLimiter）。
    - リトライ（指数バックオフ）処理: 最大 3 回、HTTP 408/429/5xx を対象。
    - 401 受信時にリフレッシュトークンから id_token を自動更新して 1 回リトライ（再帰防止フラグ allow_refresh）。
    - ページネーション対応（pagination_key）。
    - JSON デコードエラーハンドリング。
  - 認証: get_id_token(refresh_token=None) を実装（POST /token/auth_refresh）。
  - データ取得関数:
    - fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を実装。
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
    - ON CONFLICT Do UPDATE による上書きで冪等性を確保。
    - fetched_at に UTC タイムスタンプを付与。
  - 型変換ユーティリティ: _to_float(), _to_int()（堅牢なパース）

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからのニュース収集と DuckDB への保存機能を実装。
  - セキュリティ/堅牢性機能:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証、ホストがプライベートアドレスかの検査、リダイレクト時の検証ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査。
    - URL 正規化（トラッキングパラメータ削除、クエリ整列）と記事ID生成（SHA-256 の先頭32文字）。
    - URL を除去・空白正規化する前処理関数 preprocess_text。
  - DB 保存:
    - save_raw_news(): INSERT ... ON CONFLICT DO NOTHING と RETURNING を使い、実際に挿入された記事IDを返す（チャンク挿入、トランザクション）。
    - save_news_symbols(), _save_news_symbols_bulk(): 記事と銘柄コードの紐付け（ON CONFLICT DO NOTHING、チャンク、トランザクション）。
  - 銘柄抽出:
    - extract_stock_codes(): 正規表現で4桁銘柄コードを抽出し、既知銘柄セットでフィルタ。
  - 統合収集ジョブ:
    - run_news_collection(): 複数 RSS ソースを処理し、記事保存 → 新規 ID の銘柄紐付けまで実行。各ソースは独立してエラーハンドリング。

- DuckDB スキーマと初期化（src/kabusys/data/schema.py）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブル定義を実装。
  - 主なテーブル（一部抜粋）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PRIMARY KEY, FOREIGN KEY, CHECK）や列型を細かく定義（数値精度や非負チェックなど）。
  - インデックス定義（頻出クエリを想定した複数の CREATE INDEX）。
  - init_schema(db_path) による冪等的なテーブル作成と親ディレクトリ自動生成、get_connection() を提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult dataclass による ETL 実行結果の集約（品質問題・エラー一覧を含む）。
  - 差分更新のヘルパー:
    - _table_exists(), _get_max_date() 汎用ヘルパー。
    - 市場カレンダーに基づく取引日調整: _adjust_to_trading_day().
    - get_last_price_date(), get_last_financial_date(), get_last_calendar_date().
  - run_prices_etl(): 差分更新ロジック（最終取得日 - backfill_days による再取得、J-Quants からの取得 → 保存のフロー）を実装。
    - 注意: 現状のソースコード上で戻り値が途中で切れているため修正が必要（Known issue）。

- パッケージ構造の初期化
  - 空のパッケージ初期化ファイルを追加: src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py

Security
- ニュース収集に関する SSRF 対策、XML パース保護、レスポンスサイズ制限などセキュリティに配慮した実装を導入。

Performance / Reliability
- J-Quants API クライアントにレート制御とリトライ/バックオフ、トークン自動リフレッシュを導入。
- DuckDB 側はチャンク挿入・トランザクション・ON CONFLICT を多用して冪等性と挿入効率を向上。

Fixed
- （初期リリースにつき該当なし）

Changed
- （初期リリースにつき該当なし）

Removed
- （初期リリースにつき該当なし）

Known issues / TODO
- data.pipeline.run_prices_etl() の戻り値が不完全（return 文の修正が必要）。
- テストカバレッジ: ネットワーク依存ロジック（SSRF ハンドラ、gzip 解凍、ID トークン自動更新、ページネーション等）に対するユニットテスト・統合テストを整備する必要あり。
- 外部 API（J-Quants / kabuステーション）とのエンドツーエンド検証、Slack/Execution 関連の実装（execution モジュール）はまだ未実装/空（実装予定）。
- マイグレーション: スキーマ変更時のデータ移行戦略（バージョニング・マイグレーションツール）は未定義。

導入/移行メモ
- 初回セットアップ:
  - .env.example を参考に .env を用意し、JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD 等を設定してください。
  - デフォルトの DuckDB パスは data/kabusys.duckdb（設定は DUCKDB_PATH 環境変数で上書き可能）。
- 自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

貢献
- 初期実装のため、各モジュール（特に data/*）の単体テスト、エンドツーエンドテスト、ドキュメント化（DataPlatform.md, DataSchema.md 等の参照箇所）へのリンク整備を歓迎します。

以上。