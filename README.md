# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys のREADMEです。  
このドキュメントはリポジトリ内の主要モジュールをもとに、概要、機能、セットアップ方法、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムおよびデータ基盤（ETL・品質管理・監査ログ）を構築するためのライブラリ群です。主な目的は以下です。

- J-Quants API からの市場データ（株価日足、四半期財務、JPX カレンダー）の取得と DuckDB への保存
- RSS からのニュース収集と記事→銘柄紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ定義
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計のポイント:
- API レート制限とリトライ処理を備えた堅牢なクライアント実装
- DuckDB を用いた冪等保存（ON CONFLICT を活用）
- SSRF や XML Bomb 等を考慮した安全設計（ニュース収集）
- 品質チェックは「全件収集」方針、呼び出し元で重症度に応じた対応を行う

---

## 機能一覧

- 環境変数・設定管理（自動 .env ロード、必須項目チェック）
- J-Quants API クライアント
  - ID トークン自動リフレッシュ
  - レート制限（120 req/min）と指数バックオフ・リトライ
  - fetch / save: 日足、財務、カレンダー
- DuckDB スキーマ定義と初期化（データレイヤ：Raw/Processed/Feature/Execution）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、翌営業日/前営業日取得など）
- ニュース収集モジュール（RSS → raw_news、記事IDによる冪等性、銘柄抽出）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal/events, order_requests, executions）

---

## 必要環境・依存

- Python 3.10 以上（型ヒントで `X | Y` を使用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリのみで実装されている部分が多いですが、プロジェクトで必要な追加依存があれば pyproject.toml 等を参照してください）

インストール例（pip）:
```bash
python -m pip install -U pip
python -m pip install duckdb defusedxml
# 開発中はローカル editable install
python -m pip install -e .
```

---

## 環境変数（主なもの）

KabuSys は .env / .env.local / OS 環境変数から設定を読み込みます（プロジェクトルートの検出に .git / pyproject.toml を使用）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings 参照）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- kabuステーション API
  - KABU_API_PASSWORD: kabu API のパスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- Slack（通知用）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- データベースパス
  - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
  - SQLITE_PATH: 監視用 SQLite データベース（デフォルト `data/monitoring.db`）
- システム
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG|INFO|...

.env の簡易例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: Settings の必須変数が未設定だと ValueError が発生します。

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 環境を作成（推奨: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate     # Windows: .venv\Scripts\activate
   ```
3. 依存をインストール
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 他の依存があれば追加
   ```
4. .env を作成
   - リポジトリルートに .env を作り、上記必須変数を設定
5. DuckDB スキーマを初期化
   - Python スクリプトや REPL で以下を実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # パスは DUCKDB_PATH に合わせる
     ```
6. 監査DB（必要なら）
   ```python
   from kabusys.data import audit
   conn_audit = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下は代表的な利用例です。実運用ではログ周りや例外ハンドリング、ジョブスケジューラ（cron, Airflow 等）から呼ぶ想定です。

- DuckDB スキーマ初期化（既述）
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL の実行（差分取得・品質チェック）
  ```python
  from kabusys.data import pipeline
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema している場合
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  pipeline.run_daily_etl は以下を実行します:
  1. 市場カレンダー取得（先読み）
  2. 株価日足の差分 ETL（バックフィルあり）
  3. 財務データの差分 ETL（バックフィルあり）
  4. 品質チェック（run_quality_checks=True で実行）

- ニュース収集ジョブ（RSS）
  ```python
  from kabusys.data import news_collector
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # sources を渡すかデフォルトを使用
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count}
  ```

- J-Quants からのデータ取得（低レベル）
  ```python
  from kabusys.data import jquants_client as jq

  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date.today())
  ```

- 市場カレンダー操作
  ```python
  from kabusys.data import calendar_management as cm
  conn = schema.get_connection("data/kabusys.duckdb")
  is_trade = cm.is_trading_day(conn, date(2026,3,18))
  next_day = cm.next_trading_day(conn, date(2026,3,18))
  ```

- 監査スキーマ初期化（既述）
  ```python
  from kabusys.data import audit
  conn = audit.init_audit_db("data/audit.duckdb")
  ```

---

## 実装上の注意点 / 動作仕様

- J-Quants クライアント:
  - レート制限: 120 req/min を守るため内部でスロットリング（固定間隔）を行います。
  - リトライ: 最大 3 回（408/429/5xx に対して指数バックオフ）。429 の場合は Retry-After ヘッダを優先。
  - 401 の場合はリフレッシュトークンから ID トークンを再取得して 1 回リトライします。
  - 取得したデータには fetched_at（UTC）が付与され、いつデータが取得されたかをトレースできます。
- NewsCollector:
  - RSS の XML パースに defusedxml を使用（XML Bomb 防御）。
  - レスポンスサイズ上限（デフォルト 10MB）を超える場合は取得を中止。
  - URL 正規化を行い、記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性を確保。
  - SSRF 対策としてリダイレクト先の検証やプライベートIPアクセス防止を実装。
- DuckDB スキーマ:
  - 各テーブルは CREATE TABLE IF NOT EXISTS で定義され、初期化は冪等です。
  - raw → processed → feature → execution の各レイヤを想定したスキーマ構成。
- 品質チェック:
  - check_missing_data / check_spike / check_duplicates / check_date_consistency を実装。
  - run_all_checks は検出した QualityIssue リストを返します（呼び出し元で評価）。

---

## ディレクトリ構成

（リポジトリ src 配下の主要ファイル/モジュール）

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（fetch/save）
      - news_collector.py      -- RSS ニュース収集
      - schema.py              -- DuckDB スキーマ定義・初期化
      - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py -- マーケットカレンダー管理（営業日判定等）
      - audit.py               -- 監査ログスキーマ（signal/order/exec）
      - quality.py             -- データ品質チェック
    - strategy/
      - __init__.py            -- 戦略関連（将来拡張）
    - execution/
      - __init__.py            -- 発注 / 約定処理（将来拡張）
    - monitoring/
      - __init__.py            -- 監視関連（将来拡張）

---

## 開発・運用時のヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB ファイルの配置ディレクトリは自動作成されます（init_schema / init_audit_db が親ディレクトリを作成）。
- ETL は各ステップが独立して例外を捕捉するため、片方の失敗で他が中断されることはありません。ログ（及び ETLResult.errors）を確認して運用判断を行ってください。
- ニュース収集では既知銘柄コード（known_codes）を与えることで記事→銘柄紐付けを行えます。巨大な RSS ソースを扱う場合は sources を分割して実行してください。

---

## 参考（APIサマリ: 主要関数）

- kabusys.config.settings: 各種設定プロパティ（jquants_refresh_token, kabu_api_password, duckdb_path 等）
- kabusys.data.schema.init_schema(db_path)
- kabusys.data.schema.get_connection(db_path)
- kabusys.data.jquants_client.get_id_token(refresh_token=None)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
- kabusys.data.news_collector.fetch_rss(url, source, timeout=30)
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)
- kabusys.data.calendar_management.is_trading_day(conn, d), next_trading_day, prev_trading_day
- kabusys.data.audit.init_audit_db(db_path)
- kabusys.data.quality.run_all_checks(conn, target_date=None, reference_date=None)

---

README は以上です。実際の運用スクリプトや CI/CD、デプロイ手順などは用途に合わせて追加してください。必要であればサンプルスクリプトや runbook のテンプレートも作成します。