# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株のデータ取り込み・品質管理・監査・ETL を中心とした基盤ライブラリです。J-Quants API や RSS フィードからデータを収集し、DuckDB に冪等的に保存、品質チェックやカレンダー管理、監査ログを提供します。自動売買ロジック（strategy）や証券会社発注（execution）、監視（monitoring）はこの基盤上で構築できます。

## 主な特徴

- データ取得
  - J-Quants からの株価日足（OHLCV）、財務指標、JPX マーケットカレンダーの取得（ページネーション対応、レート制限遵守）
  - RSS フィードからのニュース収集（SSRF対策、トラッキングパラメータ除去、gzip／サイズ制限）
- データ保存
  - DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
  - 保存は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で重複や再実行に強い
- ETL（差分更新）
  - 差分取得・バックフィル・先読み（カレンダー）を考慮した日次 ETL パイプライン
  - 品質チェック（欠損、重複、スパイク、日付不整合）を統合
- カレンダー管理
  - JPX カレンダーの夜間更新ジョブ、営業日/前後営業日の判定ユーティリティ
- ニュース処理
  - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成、raw_news に冪等保存
  - 記事→銘柄コードの紐付け（news_symbols）
- 監査（Audit）
  - signal → order_request → executions までトレース可能な監査スキーマ
  - order_request_id を冪等キーとして二重発注を防止
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（パッケージルート判定）
  - 必須環境変数がない場合は明確な例外を投げる

---

## 機能一覧（抜粋）

- kabusys.config
  - 自動 .env ロード（.git/pyproject.toml を基準にプロジェクトルートを検出）
  - settings オブジェクトによる環境変数アクセス（必須チェック）
- kabusys.data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - レートリミッタ、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
- kabusys.data.news_collector
  - RSS 取得（XML パースは defusedxml、gzip 対応、受信サイズ制限）
  - URL 正規化・トラッキングパラメータ除去、記事ID生成、raw_news / news_symbols 保存
  - SSRF 対策（スキーム検証、プライベート IP チェック、リダイレクト検査）
- kabusys.data.schema
  - DuckDB 用スキーマ定義（各レイヤのテーブル作成、インデックス）
  - init_schema(db_path) による初期化
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 日次 ETL の統合エントリーポイント（品質チェックオプションあり）
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.data.audit
  - 監査スキーマ初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks

（strategy / execution / monitoring はパッケージを提供。実装はアプリ側で追加）

---

## 要件

- Python 3.10+
- 主要依存（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API、RSS）

（実プロジェクトでは Poetry / pipenv / requirements.txt 等で依存を管理してください）

---

## セットアップ手順

1. リポジトリをクローンして開発環境を用意
   - 例:
     ```
     git clone <repo-url>
     cd <repo>
     ```

2. 仮想環境を作成して依存をインストール
   - pip の例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb defusedxml
     ```
   - 実際はプロジェクトの requirements.txt / pyproject.toml を使ってください。

3. 環境変数（.env）の準備
   - プロジェクトルートに .env（および必要なら .env.local）を置くと自動で読み込まれます。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:
     ```
     python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"
     ```
   - 監査ログ専用 DB を作る場合:
     ```
     python -c "from kabusys.data import audit; audit.init_audit_db('data/audit.duckdb')"
     ```

---

## 使い方（基本例）

- 日次 ETL を実行する（簡易例）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  # DB 初期化（初回のみ）
  conn = schema.init_schema('data/kabusys.duckdb')

  # ETL 実行（今日を対象）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- J-Quants から株価を手動取得して保存:
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  print(f'saved: {saved}')
  ```

- RSS ニュース収集の実行:
  ```python
  from kabusys.data import news_collector as nc
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  # sources を省略すると内部デフォルト（Yahoo Finance のビジネスカテゴリ等）を使用
  results = nc.run_news_collection(conn, known_codes={'7203','6758','9984'})
  print(results)  # {source_name: new_saved_count, ...}
  ```

- カレンダー更新ジョブ:
  ```python
  from kabusys.data import calendar_management as cm
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  saved = cm.calendar_update_job(conn)
  print('saved calendar rows:', saved)
  ```

- 品質チェックを個別に実行:
  ```python
  from kabusys.data import quality
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略時 localhost のスタブを使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — environment（development, paper_trading, live）
- LOG_LEVEL — ログレベル（INFO 等）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定

settings は kabusys.config.settings からアクセスできます。必須環境変数が不足していると ValueError が発生します。

---

## ディレクトリ構成

（ソース抜粋に基づく主要ファイル/ディレクトリ）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数管理・自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - news_collector.py — RSS 収集と raw_news 保存、銘柄抽出
    - schema.py — DuckDB スキーマ定義と init_schema
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — JPX カレンダー管理・営業日計算
    - audit.py — 監査ログスキーマ（signal/events/order_requests/executions）
    - quality.py — データ品質チェック群
  - strategy/
    - __init__.py — 戦略層（拡張向けに空パッケージ）
  - execution/
    - __init__.py — 発注層（拡張向けに空パッケージ）
  - monitoring/
    - __init__.py — 監視関連（拡張向けに空パッケージ）

---

## 設計上の注意点 / 動作ポリシー（要点）

- J-Quants API のレート制限（120 req/min）を守るため、固定間隔の RateLimiter を使用しています。
- API リクエストは指数バックオフでリトライ（最大 3 回）し、408 / 429 / 5xx を対象に再試行します。401 受信時は自動でトークンを再取得して 1 回リトライします。
- DuckDB への保存は原則冪等（ON CONFLICT を利用）です。ETL の再実行や重複イレージでも安全です。
- ニュース取得では SSRF／XML Bomb 等の攻撃に配慮（defusedxml、プライベート IP 検査、応答サイズ制限、gzip 解凍後サイズチェック）。
- 品質チェックは Fail-Fast させず、発見された全問題を集めて呼び出し元に返します。呼び出し元で重大度に応じたアクションを取ってください。
- カレンダーが未取得時は曜日によるフォールバック（平日を営業日とみなす）により機能を維持しますが、正確性のため calendar 層の初期取得を推奨します。

---

## 開発・拡張について

- strategy / execution / monitoring は空パッケージとして存在します。各アプリケーションに合わせて具体的な戦略ロジックやブローカー接続、および稼働監視を実装してください。
- テスト容易性のため、jquants_client の id_token を注入できる設計や、news_collector._urlopen をモックで差し替えることが想定されています。
- DB 操作は基本的に conn.execute / executemany を使っています。トランザクション管理（begin/commit/rollback）は一部の関数で明示的に行われます（ニュースの一括挿入や監査の初期化等）。

---

もし README に含めたい追加項目（例: CI 実行方法、Docker コンテナ化手順、サンプル .env.example のテンプレート、より詳しい API 使用例）があれば教えてください。必要に応じて README を拡張します。