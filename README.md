# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群／ライブラリ群です。  
データ取得（J-Quants）、ニュース収集、DuckDB スキーマ定義、ETL パイプライン、品質チェック、マーケットカレンダー管理、監査ログの初期化など、システム全体の基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は、日本株自動売買システムの基盤となるモジュール群です。主に以下の機能を持ち、DuckDB をデータ格納先として想定した設計になっています。

- J-Quants API を使った市場データ取得（株価日足、財務情報、マーケットカレンダー）と保存（冪等性）
- RSS ベースのニュース収集（SSRF 対策・トラッキングパラメータ除去・gzip 対応）と保存
- DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定や次営業日検索）
- 監査ログ（注文→約定のトレーサビリティ）用スキーマ初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の主な配慮点:
- API レート制限・リトライ・トークン自動リフレッシュ
- Look-ahead バイアス防止のため fetched_at を UTC で記録
- DuckDB への保存は ON CONFLICT を用いた冪等操作
- RSS の XML パースに defusedxml を利用し XML 攻撃を抑止
- SSRF / 内部ネットワークアクセスの防止

---

## 主な機能一覧

- 環境変数管理
  - .env / .env.local の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数チェック（settings オブジェクト経由）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レートリミッタ、リトライ（指数バックオフ）、401 によるトークン自動更新

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応）
  - URL 正規化とトラッキングパラメータ除去
  - SSRF 対策（スキーム検証、プライベート IP 判定、リダイレクト検査）
  - raw_news への冪等保存と news_symbols への銘柄紐付け

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema / get_connection

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー更新 → 株価差分取得 → 財務差分取得 → 品質チェック
  - 差分更新ロジック（最終取得日に基づく自動算出、backfill 対応）
  - 品質チェック結果を ETLResult として返却

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチ用）

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化
  - init_audit_schema / init_audit_db（UTC タイムゾーン固定）

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返却

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型合成 (|) を使用）
- Git が利用できる環境（.env 自動ロードのため、プロジェクトルート検出で .git または pyproject.toml を探します）

1. リポジトリをクローン / プロジェクトディレクトリに移動

2. 仮想環境作成（推奨）
   - Unix/macOS
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell)
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt または pyproject.toml がある場合はそちらを使用）

4. 環境変数の設定
   - プロジェクトルート（.git のある位置）に .env または .env.local を配置可能。
   - 自動ロードの無効化（テスト等）:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN  （J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD      （kabuステーション API パスワード）
     - SLACK_BOT_TOKEN        （Slack ボットトークン）
     - SLACK_CHANNEL_ID       （通知先 Slack チャンネルID）
   - 任意（デフォルト値あり）:
     - KABUSYS_ENV            （development / paper_trading / live、デフォルト development）
     - LOG_LEVEL              （DEBUG / INFO / ...、デフォルト INFO）
     - DUCKDB_PATH            （デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            （デフォルト data/monitoring.db）

   - .env の例:
     - JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C01234567
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

---

## 使い方（基本例）

ここではライブラリをインポートして簡単に利用する例を示します。実運用では各関数をアプリケーションのジョブスケジューラや CLI から呼び出してください。

- DuckDB スキーマ初期化（ファイル DB）
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- DuckDB インメモリでの初期化（テスト）
  - conn = schema.init_schema(":memory:")

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定しなければ今日を基準に実行
  - print(result.to_dict())

- ニュース収集ジョブ実行
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  - print(results)  # {source_name: 新規保存件数}

- J-Quants から株価を直接取得して保存
  - from kabusys.data import jquants_client as jq
  - records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  - saved = jq.save_daily_quotes(conn, records)

- 監査スキーマの初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")

- マーケットカレンダーの夜間更新ジョブ（例）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- 品質チェック単体実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=None)
  - for i in issues: print(i)

注意点:
- settings（環境変数）は kabusys.config.settings から取得します。ETL や API 呼び出しの一部は必須環境変数が未設定だと例外になります。テスト時は環境変数をモックするか KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動 .env 読み込みを制御してください。
- run_daily_etl などは内部で例外を捕捉して処理を継続する設計ですが、result.errors や result.quality_issues を確認して異常を検知してください。

---

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                - 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      - J-Quants API クライアント（取得 / 保存）
    - news_collector.py      - RSS ニュース収集・保存
    - schema.py              - DuckDB スキーマ定義 / init_schema
    - pipeline.py            - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py - マーケットカレンダー管理
    - audit.py               - 監査ログ（トレーサビリティ）スキーマ初期化
    - quality.py             - データ品質チェック
  - strategy/                 - 戦略用モジュール（雛形）
    - __init__.py
  - execution/                - 発注・実行関連（雛形）
    - __init__.py
  - monitoring/               - 監視用モジュール（雛形）
    - __init__.py

その他:
- pyproject.toml（存在する場合、プロジェクトルート検出に利用）
- .env / .env.local（任意、環境変数自動ロード用）

---

## 設計上の注意点 / ベストプラクティス

- 環境毎（development / paper_trading / live）で KABUSYS_ENV を適切にセットしてください。is_live/is_paper/is_dev でランタイム挙動を切り替えられます。
- J-Quants の API レート制限（120 req/min）回避のため、jquants_client は内部でレートリミッタを持ちます。大量の並列リクエストは避け、モジュールの提供 API を活用してください。
- DuckDB のトランザクション管理に注意してください。audit.init_audit_schema は transactional 引数で BEGIN/COMMIT を制御できますが、DuckDB はネストトランザクション非対応なので呼び出し時のトランザクション状態に注意してください。
- RSS 収集では外部 URL の処理を行います。SSRF 対策・コンテンツサイズ制限（MAX_RESPONSE_BYTES）などが組み込まれていますが、追加のセキュリティ要件があればカスタマイズしてください。
- ETL の品質チェックで severity="error" の問題が検出された場合、運用フロー側で ETL を停止するかアラートを上げるかを決めてください（run_daily_etl はチェック結果を返す設計です）。

---

## 参考 / よくある質問

- Q: 環境変数 .env の自動ロードを無効化したい  
  A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Q: DuckDB スキーマだけ初期化して ETL を後で実行したい  
  A: kabusys.data.schema.init_schema(db_path) を呼んで接続を保持してください。

- Q: J-Quants の認証トークンはどこで設定する？  
  A: JQUANTS_REFRESH_TOKEN 環境変数にリフレッシュトークンを設定してください。get_id_token がリフレッシュを行います。

---

README の内容は随時拡張してください。実運用に合わせたエラーハンドリング、ロギング設定、監視／アラート連携（Slack 送信等）を実装して統合運用を行ってください。