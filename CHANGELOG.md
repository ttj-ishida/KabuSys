KEEP A CHANGELOG
すべての重要な変更点をここに記録します。  
このファイルは「Keep a Changelog」形式に準拠します。

注: 下記は提供されたコードベースから推測して作成した初回リリース向けの変更履歴です。

Unreleased
---------
（なし）

0.1.0 - 2026-03-17
-----------------
Added
- 初期リリース: KabuSys 日本株自動売買システムの基礎機能を追加。
  - パッケージ構成:
    - kabusys (トップレベル): data, strategy, execution, monitoring を公開。
  - 環境設定:
    - kabusys.config
      - .env / .env.local を自動で読み込む仕組みを実装（プロジェクトルートは .git または pyproject.toml で検出）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能。
      - 環境変数のパースロジックを独自実装（コメント処理、クォート・エスケープ対応、export プレフィックス対応）。
      - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなどの設定プロパティを公開。必須値未設定時は ValueError を発生。
      - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL のバリデーションを実装。
  - データ取得クライアント:
    - kabusys.data.jquants_client
      - J-Quants API クライアントを実装。
      - レート制限（120 req/min）を固定間隔スロットリングで保護（_RateLimiter）。
      - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象。429 は Retry-After ヘッダを尊重。
      - 401 受信時に自動でリフレッシュトークンから id_token を再取得して一度だけリトライ。
      - ページネーション対応の fetch_* 関数を提供:
        - fetch_daily_quotes（株価日足）
        - fetch_financial_statements（四半期財務）
        - fetch_market_calendar（JPX カレンダー）
      - DuckDB へ冪等に保存する save_* 関数を提供（INSERT ... ON CONFLICT DO UPDATE を利用）:
        - save_daily_quotes / save_financial_statements / save_market_calendar
      - データの fetched_at を UTC で記録（Look-ahead bias 対策）と型変換ユーティリティ（_to_float/_to_int）。
  - ニュース収集:
    - kabusys.data.news_collector
      - RSS フィード収集と前処理パイプラインを実装。
      - セキュリティ対策:
        - defusedxml を使った XML パース（XML bomb 等の対策）。
        - SSRF 対策: リダイレクト先のスキームチェック、ホストがプライベートアドレスかどうか検査する仕組み（DNS 解決・IP チェック）。
        - URL スキームは http/https のみ許可。
        - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査。
      - URL 正規化（トラッキングパラメータ削除・クエリソート・フラグメント削除）と記事ID生成（正規化URL の SHA-256 の先頭32文字）。
      - テキスト前処理（URL除去、空白正規化）。
      - DuckDB への保存処理:
        - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING を利用し新規挿入IDを返す。チャンク分割・単一トランザクションで挿入。
        - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で保存。ON CONFLICT で重複排除。
      - 銘柄コード抽出ロジック（4桁数字を候補にして既知コードセットでフィルタ）。
      - run_news_collection: 複数 RSS ソースを巡回してフェッチ→保存→銘柄紐付けまで一連で実行。各ソースは独立してエラーハンドリング（1ソース失敗でも継続）。
  - スキーマ管理:
    - kabusys.data.schema
      - DuckDB 用のスキーマ定義を実装（Raw / Processed / Feature / Execution の多層）。
      - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
      - features, ai_scores 等の Feature テーブル。
      - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
      - 運用上想定されるインデックスを作成（頻出クエリを想定）。
      - init_schema(db_path) でディレクトリ作成→全DDL適用→接続を返す。get_connection(db_path) ではスキーマ初期化は行わない点に注意。
  - ETL パイプライン基盤:
    - kabusys.data.pipeline
      - ETL 実行結果を表す ETLResult データクラス（品質チェック結果やエラー一覧を保持、辞書化可能）。
      - 差分更新ヘルパー（テーブル存在チェック、最終取得日の取得）。
      - 市場カレンダーを考慮した取引日調整ロジック（_adjust_to_trading_day）。
      - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
      - run_prices_etl（株価差分 ETL）を実装: 最終取得日 - backfill_days を考慮した差分取得→保存の流れを実現（backfill デフォルト 3 日、データ開始日 2017-01-01 を考慮）。
  - その他
    - ロギングを適切に行い、処理の進捗や警告（PK 欠損スキップ、レスポンスサイズ超過、XMLパース失敗等）を出力。

Security
- defusedxml、SSRF 検出、レスポンスサイズ上限などを導入して外部入力（RSS/XML/HTTP）の扱いを安全化。
- 環境変数の管理は .env/.env.local の読み込みロジックと protected set により OS 環境変数の上書きを制御。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Migration
- 初回導入時:
  - DuckDB スキーマを使用する前に kabusys.data.schema.init_schema(db_path) を呼び出してテーブルを作成してください。
  - 必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定する必要があります。未設定時は Settings のプロパティアクセスで ValueError が発生します。
  - 自動で .env/.env.local を読み込みますが、テスト時などで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API 利用:
  - rate limit（120 req/min）を順守するためクライアント側でスロットリングします。大量リクエスト時は注意してください。
  - トークン期限切れ時は自動リフレッシュ→1回リトライする設計ですが、リフレッシュ失敗や再度401が返ってきた場合は例外になります。
- NewsCollector:
  - RSS の最終 URL がプライベートアドレスにリダイレクトされる場合は取得を拒否します。
  - レスポンスや解凍後が MAX_RESPONSE_BYTES を超える場合はスキップします。

今後の予定（推測）
- pipeline の品質チェック（quality モジュール）統合や各種品質ルールの実装・拡充。
- strategy / execution / monitoring の具象実装（現状はパッケージ名のみ定義）。
- テストカバレッジの拡充と CI/CD の整備。

Contact
- 問い合わせやバグ報告はリポジトリの Issue を使用してください。

----- 
（注）上記 CHANGELOG は提供されたソースコードから機能・設計方針を推測して作成しています。実際の履歴やリリースノートが必要な場合は、コミット履歴や開発者の意図に基づいて調整してください。