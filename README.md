# KabuSys

日本株自動売買システムのライブラリ群（データ収集・ETL・品質チェック・監査ログ・カレンダー管理等）。

このリポジトリは主に以下を提供します：
- J-Quants からの株価 / 財務 / 市場カレンダー取得クライアント
- RSS ベースのニュース収集器とニュース → 銘柄紐付け処理
- DuckDB スキーマ定義と初期化ユーティリティ
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）

バージョン: 0.1.0

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動リフレッシュ）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ冪等保存する save_* 関数

- data/news_collector.py
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ削除・記事ID生成（SHA-256）
  - SSRF 対策・レスポンスサイズ制限・DuckDB へトランザクション保存

- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema(db_path) による初期化（冪等）

- data/pipeline.py
  - run_daily_etl() による日次 ETL（カレンダー → 価格 → 財務 → 品質チェック）
  - 差分更新・backfill・品質チェック（quality モジュール）

- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job()：夜間で JPX カレンダーを差分更新

- data/audit.py
  - 監査ログ用テーブル定義（signal_events / order_requests / executions）
  - init_audit_schema()/init_audit_db()

- data/quality.py
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
  - run_all_checks()

- config.py
  - .env / 環境変数読み込み（自動ロード機能）
  - Settings（必須環境変数取得用ヘルパ）

---

## セットアップ手順

前提: Python 3.10+（コード内で型注釈に union types などを利用）

1. リポジトリをクローン
   ```
   git clone <このリポジトリのURL>
   cd <リポジトリ>
   ```

2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール
   - プロジェクトの配布設定がある場合は requirements.txt / pyproject.toml に従ってください。
   - 最低限必要なパッケージ:
     - duckdb
     - defusedxml
   例:
   ```
   pip install duckdb defusedxml
   ```
   またはプロジェクトを開発モードでインストールする場合:
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を利用できます（config.py が自動でロードします）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（Settings で _require により参照されるもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
   - LOG_LEVEL   : DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
   - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）

   簡易の `.env.example`（README 用サンプル）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトから schema.init_schema() を呼び出して DB を初期化します。

   例:
   ```python
   from pathlib import Path
   import kabusys.data.schema as schema

   db_path = Path("data/kabusys.duckdb")
   conn = schema.init_schema(db_path)
   ```

6. 監査ログ用スキーマ初期化（必要な場合）
   ```python
   import kabusys.data.audit as audit
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主なユースケース例）

- J-Quants のトークンを直接取得（ID トークン）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  import kabusys.data.pipeline as pipeline
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行（既存の DuckDB 接続と known_codes を渡す）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は検出対象の銘柄コードセット（例: {"7203", "6758", ...}）
  stats = run_news_collection(conn, known_codes={"7203", "6758"})
  print(stats)  # {source_name: 新規保存件数}
  ```

- マーケットカレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved {saved} records")
  ```

- 品質チェック（個別実行）
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=date.today())
  for issue in issues:
      print(issue)
  ```

- news_collector の個別 RSS 取得（例）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"])
  ```

---

## 設定と挙動のポイント

- .env 自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）から `.env` を自動で読み込みます。
  - 読み込み順序: OS 環境 > .env.local (override=True) > .env (override=False)
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 環境名 / ログレベル検証
  - KABUSYS_ENV は {development, paper_trading, live} のみ有効です。
  - LOG_LEVEL は {DEBUG, INFO, WARNING, ERROR, CRITICAL} のみ有効です。

- J-Quants API の設計
  - 120 req/min のレート制限をモジュール内で管理
  - リトライ（408/429/5xx）と指数バックオフ、401 時は自動でトークンリフレッシュして再試行
  - 取得したデータには fetched_at（UTC）を付与し、いつデータを知り得たかをトレース可能にする

- NewsCollector のセキュリティ設計
  - defusedxml による安全な XML パース
  - SSRF 対策（スキームチェック、ホストがプライベートアドレスかを検証）
  - レスポンスサイズ制限（デフォルト 10MB）と gzip 解凍後の再検査

---

## ディレクトリ構成

以下は主要ファイルのツリー（抜粋）です。実際のプロジェクトルートは src/kabusys 配下にパッケージが存在します。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - calendar_management.py
      - quality.py
      - audit.py
    - strategy/
      - __init__.py
      - (戦略関連実装を配置)
    - execution/
      - __init__.py
      - (発注/ブローカー連携ロジックを配置)
    - monitoring/
      - __init__.py

主に data パッケージが ETL・DB・外部 API 連携を担当し、strategy / execution / monitoring は上位層の実装が入る想定です。

---

## 開発上の注意点

- DuckDB をデータレイヤーに使用しており、スキーマ初期化は init_schema() を通して行ってください。
- audit.init_audit_schema は UTC タイムゾーン設定（SET TimeZone='UTC'）を行います。
- ETL / カレンダー等のジョブは外部 API に依存するため、テスト時は get_id_token やネットワーク呼び出しをモックしてください（設計上注入可能）。
- news_collector._urlopen 等はテスト用に差し替え可能な実装になっています。

---

もし README に追加してほしい「具体的な実行スクリプト例」や「CI / デプロイ手順」があれば教えてください。必要に応じてサンプル .env.example や systemd / cron の例も提供します。