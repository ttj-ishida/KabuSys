Keep a Changelog
=================

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」仕様に従っています。

Unreleased
----------

注意・今後の作業予定 / 既知の問題
- run_prices_etl の戻り値が現状 len(records) のみを返しており、(fetched, saved) という意図されたタプルが不完全になっています。次リリースで修正予定。
- quality モジュール（ETL の品質チェック参照）は参照されていますが、本コードスナップショットに実装が含まれていません。品質チェックの統合・テストが必要です。
- execution/strategy パッケージは現状ほぼ空のプレースホルダになっているため、実取引ロジックや戦略コードは追加実装が必要です。
- モジュール内のグローバルトークンキャッシュ（_ID_TOKEN_CACHE）はプロセス状態に依存します。長期プロセスやマルチスレッド利用時の振る舞い確認が望まれます。

0.1.0 - 2026-03-18
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアライブラリを追加。
  - パッケージレイアウト:
    - kabusys.config: 環境変数・設定読み込みと Settings 抽象。
      - .env / .env.local 自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
      - 必須環境変数取得ヘルパー _require と各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH 等）。
      - KABUSYS_ENV と LOG_LEVEL の入力値検証（許容値チェック）。
  - kabusys.data:
    - jquants_client: J-Quants API クライアント実装。
      - レート制御: 120 req/min に対応する固定間隔スロットリング（_RateLimiter）。
      - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。
      - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token 取得用 get_id_token。
      - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements（pagination_key 処理）。
      - fetch_market_calendar（JPX カレンダー）取得。
      - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT DO UPDATE による上書き。
      - 型安全な変換ユーティリティ: _to_float, _to_int。
    - news_collector: RSS ニュース収集モジュール。
      - RSS フィード取得と記事正規化（URL 正規化、トラッキングパラメータ削除）。
      - defusedxml を利用した安全な XML パース（XML Bomb 等の防御）。
      - SSRF 対策: スキーム検証、プライベートアドレス検出、リダイレクト時の検査（_SSRFBlockRedirectHandler）、HTTP クライアントラッパー _urlopen（テスト用モック可能）。
      - 受信サイズ制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズ検査。
      - 記事ID生成: 正規化 URL の SHA-256 先頭32文字を使用して冪等性を保証。
      - DuckDB への保存: save_raw_news（チャンク / トランザクション / INSERT ... RETURNING により挿入済み ID を返す）、save_news_symbols、_save_news_symbols_bulk。
      - 銘柄コード抽出関数 extract_stock_codes（4 桁数字、known_codes フィルタ）。
      - 統合収集ジョブ run_news_collection（ソース毎に独立処理、エラーハンドリング）。
    - schema: DuckDB スキーマ定義と初期化。
      - Raw / Processed / Feature / Execution 層のテーブル定義を包括的に実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
      - 各種制約（PRIMARY KEY, CHECK 等）や外部キーを定義。
      - 頻出クエリ向けのインデックス群を作成（例: idx_prices_daily_code_date 等）。
      - init_schema(db_path) によるディレクトリ自動作成と DDL 実行（冪等）。
      - get_connection(db_path) による接続取得（スキーマ初期化は行わない注意）。
    - pipeline: ETL パイプライン基盤。
      - ETLResult dataclass（取得件数、保存件数、品質問題、エラー等を含む）。
      - 差分更新を支えるユーティリティ: テーブル存在確認、最終取得日の取得（get_last_price_date, get_last_financial_date, get_last_calendar_date）、取引日調整ヘルパー (_adjust_to_trading_day)。
      - run_prices_etl 実装（差分算出、backfill_days による再取得ロジック、jquants_client を用いた取得と保存）。※戻り値の不備は Unreleased に記載。
  - テスト・デバッグ支援:
    - id_token 注入可能な設計、_urlopen のモック差し替えが可能でユニットテスト容易性を考慮。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- RSS パーサーに defusedxml を採用し、XML 関連攻撃（XML Bomb 等）に対処。
- RSS/HTTP クライアントで SSRF 対策（スキーム検証、プライベートネットワークの検出、リダイレクト先検査）を導入。
- .env 読み込みでは既存の OS 環境変数を保護するため protected セットを使用。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。

Deprecated / Removed
- 初期リリースのため該当なし。

Migration / 注意事項
- 初回起動時は schema.init_schema() を呼んで DuckDB スキーマを作成してください（get_connection() はスキーマ初期化を行いません）。
- 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください。設定がない場合、Settings プロパティが ValueError を投げます。
- デフォルトの DuckDB パスは data/kabusys.duckdb です（settings.duckdb_path）。
- jquants_client は 120 req/min のレート制御を行います。大量取得時はレートに注意してください。
- news_collector の run_news_collection は既知銘柄コードセット（known_codes）を与えると news_symbols を構築しますが、known_codes の管理は呼び出し側で行ってください。

謝辞
- 本リリースはデータ取得・保存・ETL 基盤に重点を置いた初期実装です。戦略ロジック・実行エンジン・品質チェック等は今後のリリースで順次拡張予定です。