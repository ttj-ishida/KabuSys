# Changelog

すべての注目すべき変更点をこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に従っています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-17

初回リリース。

### 追加 (Added)
- パッケージ基本情報
  - パッケージルート（kabusys）を定義、バージョンを `0.1.0` に設定。
  - 公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルート（.git または pyproject.toml で判定）から `.env` と `.env.local` を自動読み込み。
    - OS 環境変数を保護する protected ロジックを実装。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - .env パーサを実装（export プレフィックス対応、シングル／ダブルクォートのエスケープ処理、インラインコメントの扱い等）。
  - 必須環境変数取得ヘルパ `_require` を提供（未設定時は ValueError を送出）。
  - 設定値プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - デフォルト値を持つ設定（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV）。
  - 環境切替ヘルパ（is_live / is_paper / is_dev）を提供。
  - KABUSYS_ENV と LOG_LEVEL の妥当性検証を実装。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API から株価日足、財務データ（四半期 BS/PL）、マーケットカレンダーを取得するクライアントを実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を保証する RateLimiter を実装。
  - リトライ戦略: 指数バックオフ（最大 3 回）、HTTP 408/429/5xx のリトライをサポート。429 の場合は Retry-After ヘッダを参照。
  - 認証: リフレッシュトークンからの id_token 取得（get_id_token）と、401 受信時の自動リフレッシュ（1 回のみ）を実装。モジュールレベルで id_token をキャッシュ。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）を実装。
  - データ保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）:
    - DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複を排除。
    - fetched_at を UTC 時刻で記録し、データ取得タイミングをトレース可能に（Look-ahead Bias 対策）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を取得して raw_news テーブルに保存する収集モジュールを実装。
  - セキュリティと堅牢性：
    - defusedxml を使用した XML パース（XML Bomb 等への対策）。
    - HTTP/HTTPS 以外のスキームを拒否し、SSRF 対策を実施。
    - リダイレクト時にスキームとホスト/IP を検証するカスタム RedirectHandler を実装。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定し遮断。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、gzip 解凍後もサイズ検査（Gzip bomb 対策）。
    - レスポンスの Content-Length の事前チェック。
  - URL 正規化:
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）を除去、スキーム・ホスト小文字化、フラグメント削除、クエリソートを行う。
    - 正規化済 URL の SHA-256（先頭32文字）を記事IDとして使用し冪等保存を担保。
  - テキスト前処理:
    - URL 除去、空白正規化、先頭末尾トリムを行う preprocess_text を実装。
  - DB 保存:
    - DuckDB に対してチャンク化されたバルク INSERT（INSERT ... ON CONFLICT DO NOTHING RETURNING id）を行い、実際に挿入された記事IDを返す（save_raw_news）。
    - 記事と銘柄の紐付けを news_symbols テーブルへ一括保存するヘルパ（_save_news_symbols_bulk / save_news_symbols）。
  - 銘柄抽出:
    - テキストから 4 桁数字候補を抽出し、与えられた known_codes セットに含まれるもののみを返す extract_stock_codes を実装。
  - run_news_collection によるソース毎の独立したエラーハンドリングと収集ワークフローを提供。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataPlatform 設計に基づく多層スキーマを定義・初期化するモジュールを追加。
  - Raw / Processed / Feature / Execution 層のテーブル定義を実装:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各列に型・制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
  - クエリ効率化のためのインデックス群を定義（例: idx_prices_daily_code_date, idx_signal_queue_status 等）。
  - init_schema(db_path) によりディレクトリ作成とテーブル/インデックスの冪等作成を実装。get_connection で既存 DB に接続可能。

- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新（差分取得）を想定した ETL ヘルパを実装。
  - ETLResult データクラスを実装し、取得数・保存数・品質問題・エラー一覧を保持。品質問題は辞書化可能。
  - 市場カレンダーの先読み日数、バックフィル日数の定数定義（デフォルト backfill_days=3, calendar lookahead=90）。
  - テーブル存在チェック、最大日付取得ユーティリティを実装。
  - trading day の補正ヘルパ（非営業日なら直近営業日に調整）を実装。
  - run_prices_etl の骨組みを導入（差分算出、fetch_daily_quotes 呼び出し、保存、ログ出力）。（注: ファイル末尾にて run_prices_etl の戻り値の構築途中で終了している箇所あり）

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- news_collector に複数の SSRF／XML／メモリ DoS 対策を実装：
  - defusedxml の利用、URL スキーム検証、プライベートアドレス拒否、リダイレクト時の検証、受信サイズ上限、gzip 解凍サイズ検査。
- .env 読み込み時のファイル読み込みエラーは warnings で通知し、クラッシュを防止。

### 既知の問題 / 注意点 (Known issues / Notes)
- run_prices_etl の戻り値組み立て部分がファイル末尾で途中になっている可能性（ソースの最後で `return len(records),` のように不完全に見える）。実行時に修正が必要になる場合があります。
- strategy / execution / monitoring パッケージはパッケージ化されているが、現時点では実装が含まれていない（プレースホルダ）。
- DuckDB の SQL 実行時に一部の動的 SQL（f-string による DDL/INSERT）で SQL インジェクションを考慮する必要がある箇所があるため、使用時は入力値の検証に注意してください（現在の実装は内部的に使用することを想定）。
- J-Quants API のリクエストで urllib を使用。高度な HTTP 機能（セッション管理やより細かなタイムアウト制御等）が必要な場合は追加の検討が必要。

---

参考: 本 CHANGELOG はソースコードからの実装内容を基に推測して作成しています。実際のリリースノートとして利用する際は、コミット履歴やリリースで意図した変更点と照合してください。