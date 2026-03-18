# KabuSys

バージョン: 0.1.0

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants API から市場データ・財務データ・マーケットカレンダーを取得し、DuckDB に冪等的に保存するETL、ニュース収集、データ品質チェック、監査ログ用スキーマなどを提供します。戦略・発注・監視のためのモジュール群（strategy / execution / monitoring）の骨組みも含んでいます。

主要な設計方針:
- データの冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）
- API レート制御・リトライ・自動トークン更新（J-Quants）
- ニュース収集に対する SSRF / XML Bomb / サイズ制限 等のセキュリティ対策
- DuckDB を中心としたローカルデータプラットフォーム
- 品質チェックで ETL の健全性を可視化
- 監査ログでシグナル→注文→約定のトレーサビリティを保証

機能一覧
- 環境変数 / .env の自動読み込みと設定ラッパー（kabusys.config）
- J-Quants クライアント（株価日足、財務、マーケットカレンダー取得）
  - レートリミット（120 req/min）と指数バックオフ、401時のトークン自動更新対応
  - ページネーション対応、取得時刻（fetched_at）の記録
  - DuckDB へ安全に保存する save_* 関数（冪等）
- RSS ニュース収集（news_collector）
  - URL 正規化・トラッキングパラメータ除去による記事ID生成（SHA-256）
  - defusedxml を使った安全な XML パース
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - レスポンスサイズ上限（デフォルト 10 MB）や gzip 対応
  - raw_news / news_symbols への冪等保存（INSERT ... RETURNING で挿入数を取得）
- DuckDB スキーマ定義・初期化（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを定義
  - インデックス作成、冪等な初期化 API
- ETL パイプライン（data.pipeline）
  - 市場カレンダー先読み、差分更新（バックフィル）、品質チェックの実行
  - run_daily_etl による一括実行と詳細な実行結果（ETLResult）
- マーケットカレンダー管理（data.calendar_management）
  - 営業日判定、前後営業日取得、一括更新ジョブ
- データ品質チェック（data.quality）
  - 欠損、スパイク、重複、日付不整合のチェックを提供（QualityIssue）
- 監査ログ向けスキーマ（data.audit）
  - signal_events / order_requests / executions 等、トレーサビリティ用テーブル群
  - 監査スキーマの初期化ヘルパー

セットアップ手順（ローカル開発向け）
1. 必要な Python バージョン
   - Python 3.10 以上（型ヒントの `X | None` 構文を使用）

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

3. 依存ライブラリのインストール
   - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt があればそれを使ってください）

4. 環境変数の設定
   - プロジェクトルートに .env を置くと自動的に読み込まれます（.env.local も上書き読み込み）。
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 主な環境変数（必須 / デフォルト）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
     - KABU_API_BASE_URL (任意) — デフォルト "http://localhost:18080/kabusapi"
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
     - SLACK_CHANNEL_ID (必須) — Slack チャンネルID
     - DUCKDB_PATH (任意) — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH (任意) — デフォルト "data/monitoring.db"
     - KABUSYS_ENV (任意) — "development" / "paper_trading" / "live"（デフォルト "development"）
     - LOG_LEVEL (任意) — "DEBUG","INFO","WARNING","ERROR","CRITICAL"（デフォルト "INFO"）

5. データベース初期化（DuckDB）
   - Python REPL やスクリプトで初期化できます。例:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を使う場合:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/audit.duckdb")

使い方（主要なユースケース例）
- 日次 ETL を実行して株価 / 財務 / カレンダーを取得・保存する
  - from kabusys.data.schema import init_schema
  - from kabusys.data.pipeline import run_daily_etl
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_daily_etl(conn)
  - print(result.to_dict())

- ニュース収集ジョブを実行する
  - from kabusys.data.schema import init_schema
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - conn = init_schema("data/kabusys.duckdb")
  - known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット（必要に応じて）
  - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  - print(results)

- J-Quants の ID トークンを直接取得する（テスト等）
  - from kabusys.data.jquants_client import get_id_token
  - token = get_id_token()  # settings.jquants_refresh_token を使用

- 市場カレンダー更新ジョブ（夜間バッチ向け）
  - from kabusys.data.calendar_management import calendar_update_job
  - conn = init_schema("data/kabusys.duckdb")
  - saved = calendar_update_job(conn)

- 品質チェックを個別に／一括で実行する
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn)
  - for i in issues: print(i)

実装・挙動の注意点
- J-Quants クライアントは内部で固定間隔のレートリミッタを持ち、最大試行回数と指数バックオフでリトライします。401 受信時はリフレッシュして 1 回だけ再試行します。
- news_collector は RSS を安全に扱うために多数の防御策を実装しています（URL 正規化、トラッキング除去、スキーム検査、プライベートIP拒否、gzip/サイズチェック、defusedxml）。
- DuckDB への保存は可能な限り冪等性を保つように設計されています。外部キー制約やチェック制約を多用しています。
- ETL は Fail-Fast ではなく、各ステップを独立して実行→問題は QualityIssue や errors に集約して返す設計です。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数と .env ロード
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得 + 保存）
    - news_collector.py       — RSS ベースのニュース収集・保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py  — カレンダー管理（営業日判定・更新ジョブ）
    - audit.py                — 監査ログスキーマ（signal/order/execution）
    - quality.py              — データ品質チェック
  - strategy/                  — 戦略層（骨組み）
    - __init__.py
  - execution/                 — 発注／ブローカー接続（骨組み）
    - __init__.py
  - monitoring/                — 監視関連（骨組み）
    - __init__.py

FAQ / よくある運用上の疑問
- Q: .env ファイルの自動読み込みはどう動く？
  - A: パッケージの config モジュールは .git または pyproject.toml を起点にプロジェクトルートを探索し、OS 環境変数 > .env.local > .env の順で読み込みます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: DuckDB の初期化は何度実行しても安全ですか？
  - A: はい。schema.init_schema() は CREATE TABLE IF NOT EXISTS を使用しており冪等です。

- Q: ニュース記事の重複はどう管理されていますか？
  - A: 記事IDは正規化URLの SHA-256（先頭32文字）を使用し、raw_news テーブルでは PK により重複挿入がスキップされます。news_symbols も ON CONFLICT DO NOTHING で冪等に保存します。

拡張 / 開発メモ
- strategy / execution / monitoring パッケージは拡張ポイントです。戦略の生成したシグナルを signal_events / signal_queue に保存し、order_requests → executions を経て監査ログでトレースする設計になっています。
- 単体テストでは、kabusys.config の自動 .env ロードを無効化し、id_token や HTTP 呼び出しをモックしてテストを行うことを想定しています（news_collector._urlopen を差し替え可能）。

ライセンスや貢献
- この README ではライセンスファイルや貢献ガイドは含めていません。リポジトリに LICENSE / CONTRIBUTING.md があれば準拠してください。

以上がこのコードベースの概要、セットアップ、使い方の手引きです。必要であれば、具体的なサンプルスクリプト（CI 用の実行例、systemd タイマーや cron による定期実行例、Dockerfile など）も作成しますので指示ください。