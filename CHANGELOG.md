# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
安定版リリースのタグ付け・バージョニングには semver を想定しています。

## [Unreleased]

### 注意 / 既知の問題
- run_prices_etl 関数の戻り値の組み立てがソース上で途中になっている（保存件数を返すべき箇所の記述が未完）。リリース前に修正・テストが必要。
- ユニットテスト・統合テストの追加が必要（外部 API 呼び出しやネットワーク関連処理はモック化しての検証推奨）。
- DuckDB スキーマを変更する場合は init_schema の実行・マイグレーション方針を検討すること。

---

## [0.1.0] - 2026-03-17

初回リリース (v0.1.0)。日本株自動売買プラットフォームの基盤機能を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。__version__ = "0.1.0"。
  - モジュール分割: data, strategy, execution, monitoring を公開。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に .env ファイルを探索して自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env の詳細なパース実装: コメント処理、export プレフィックス、クォートやエスケープの扱いなどに対応。
  - 必須設定取得時に未設定なら ValueError を投げる _require ユーティリティを提供。
  - 環境 (development / paper_trading / live) およびログレベルの検証ロジックを実装。
  - デフォルト DB パス (DuckDB / SQLite) の取得ユーティリティ。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティ _request を実装（JSON デコードエラーハンドリング、タイムアウト、パラメータ化）。
  - レート制御: 固定間隔スロットリングによる 120 req/min 制御（_RateLimiter）。
  - 冪等性を考慮したデータ保存: DuckDB へ ON CONFLICT DO UPDATE を使った save_* 関数を提供。
  - リトライロジック: 指定ステータス（408/429/5xx）に対する指数バックオフリトライ、最大試行回数設定。
  - 401 Unauthorized 受信時にリフレッシュトークン経由で id_token を自動更新して再試行する仕組みを実装。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期 BS/PL 等)
    - fetch_market_calendar (JPX マーケットカレンダー)
  - DuckDB 保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar（各 save_* はスキップログ・保存件数ログを出力）
  - 型変換ユーティリティ (_to_float / _to_int) を実装（不正値は None に変換）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を取得し raw_news テーブルへ冪等保存する機能を実装。
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を担保。
  - URL 正規化: スキーム・ホストの小文字化、追跡用クエリパラメータ（utm_* 等）の削除、フラグメント除去、クエリキーのソートなどを実装。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト検査ハンドラ (_SSRFBlockRedirectHandler) によるリダイレクト先スキーム・プライベートアドレス検査。
    - ホスト名を DNS 解決してプライベート / ループバック / リンクローカルを検出するロジック。
  - セキュリティ・堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等への対策）。
    - レスポンス最大読み取りサイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - HTTP ヘッダ Content-Length の事前チェック。
  - RSS パースのフォールバックと前処理:
    - content:encoded を優先、なければ description を利用。
    - URL 除去・空白正規化を行う preprocess_text。
    - pubDate の RFC 2822 パースと UTC 正規化。
  - DB への保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を使い、新規挿入された記事IDのリストを返す（チャンク挿入、1 トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（ON CONFLICT DO NOTHING + RETURNING を利用、チャンク処理）。
  - 銘柄抽出:
    - テキスト中から 4 桁数字候補を抽出し known_codes セットでフィルタする extract_stock_codes を実装。
  - 統合ジョブ:
    - run_news_collection: 複数 RSS ソースから収集→保存→（known_codes 指定時）銘柄紐付けを行う。ソース単位で独立したエラーハンドリング。

- DuckDB スキーマ (kabusys.data.schema)
  - DataSchema.md に基づく多層テーブル定義を追加（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols などの Processed テーブルを定義。
  - features, ai_scores 等の Feature 層テーブルを定義。
  - signal_queue, orders, trades, positions, portfolio_performance 等の Execution 層テーブルを定義。
  - 主キー・チェック制約・外部キーを可能な限り定義してデータ整合性を強化。
  - 頻出クエリ向けの INDEX 定義を追加（code/date、ステータス検索等）。
  - init_schema(db_path) を実装し、必要に応じて親ディレクトリ作成→全 DDL と INDEX を順に実行して初期化する（冪等）。
  - get_connection(db_path) による既存 DB への接続ユーティリティ。

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass: ETL 実行の結果集約（取得数・保存数・品質問題・エラー等）を格納するデータ構造を実装。
  - 差分更新ロジック補助:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date：各 raw テーブルの最終取得日を取得。
    - _adjust_to_trading_day: 非営業日の場合に最も近い過去の営業日に調整するユーティリティ。
  - run_prices_etl: 差分取得（バックフィル日数指定可能）→ J-Quants から取得 → 保存、というワークフローを実装（差分起算の既定は最終取得日から backfill して再取得）。
  - 設計方針として品質チェックモジュール（quality）との連携を想定しており、ETL は品質エラーがあっても継続収集する方針。

### セキュリティ (Security)
- ニュース収集での SSRF 対策を実装（スキーム検証、プライベートIP検出、リダイレクト検査）。
- XML パースに defusedxml を採用し XML 関連攻撃を防止。
- ネットワーク応答サイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後チェックによりメモリ DoS / Gzip Bomb 対策。
- .env 読み込み時に OS 環境変数を保護するため protected セットを使用（上書き制御）。

### 変更 / 修正 (Changed / Fixed)
- 初版のため大きな変更履歴はありません（初回実装）。

---

## マイグレーション / 利用上の注意
- 初回利用時は必ず init_schema(db_path) を実行して DuckDB スキーマを作成してください。
- J-Quants や Slack 等の必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を .env に設定するか OS 環境変数で提供してください。
- 自動で .env を読み込む動作は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト環境で便利）。
- run_news_collection や run_prices_etl の実行は、外部 API のレート制限・認証情報管理に注意してスケジューリングしてください。
- 既知の未完了点（run_prices_etl の戻り値など）はリリース前に修正してください。

---

（補足）今後の予定（提案）
- 単体テスト・統合テストの整備（HTTP や DB 操作をモックするテスト群）。
- quality モジュールの実装・ETL 連携の充実。
- strategy / execution / monitoring モジュールの実装（現状はパッケージ公開のみ）。
- CLI / サービス化・ジョブスケジューラ統合（Airflow / cron など）や運用監視の導入。