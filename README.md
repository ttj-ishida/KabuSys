# KabuSys — 日本株自動売買システム

バージョン: 0.1.0

KabuSys は日本株の自動売買プラットフォームに必要なデータ収集・ETL・スキーマ管理・監査（トレーサビリティ）などの基盤機能を提供する Python パッケージです。J-Quants API や RSS フィード等からデータを取得し、DuckDB に冪等（idempotent）に保存、品質チェックや市場カレンダー管理、ニュース収集、監査ログなどの機能を備えています。

主な設計方針の例：
- API レート制限（J-Quants: 120 req/min）を守る制御
- 冪等性（ON CONFLICT で INSERT/UPDATE）
- リトライ、トークン自動リフレッシュ
- SSRF/XML Bomb 等のセキュリティ対策（news_collector）
- DuckDB を用いたローカルデータレイヤ（Raw/Processed/Feature/Execution）
- 監査用テーブル（order_requests / executions / signal_events）によるトレーサビリティ

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期）、マーケットカレンダー取得
  - レートリミット、再試行、401時の自動トークンリフレッシュ
  - ページネーション対応
  - DuckDB への保存（冪等）

- ETL パイプライン
  - 差分取得（最終取得日ベース）＋バックフィル
  - 市場カレンダー先読み
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集
  - RSS フィード取得、前処理、URL 正規化（トラッキング除去）
  - SSRF 対策、gzip サイズ制限、XML の安全なパース
  - DuckDB への冪等保存（raw_news, news_symbols）

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト取得
  - カレンダー夜間バッチ更新ジョブ

- スキーマ管理
  - DuckDB の全テーブル（Raw / Processed / Feature / Execution）とインデックスの作成
  - 監査ログテーブル（signal_events, order_requests, executions）の初期化

- データ品質チェック
  - 欠損、スパイク（前日比閾値）、重複、日付不整合などを検出し QualityIssue を返却

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型表現（X | None）を利用しているため）
- pip が利用可能

1. リポジトリをクローン（パッケージ配布前想定）
   - git clone ...

2. 依存ライブラリをインストール
   - 必要最低パッケージ（例）
     - duckdb
     - defusedxml
   - 例:
     ```
     python -m pip install duckdb defusedxml
     ```
   - （プロジェクトに requirements.txt があればそちらを利用してください）

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と/または `.env.local` を配置すると、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（コードで _require() されているもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite (monitoring 用)（デフォルト: data/monitoring.db）
   - `.env` の例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース（DuckDB）の初期化
   - Python から schema を初期化します（親ディレクトリがなければ自動作成されます）。
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査スキーマ（別モジュール）を追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（主要な使用例）

以下はパッケージ内 API を直接呼び出す最小の例です。実運用ではスクリプトやジョブ管理（cron, systemd, Airflow など）に組み込んでください。

- 日次 ETL を実行する（株価・財務・カレンダーと品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 既存ファイルならスキップされる
  result = run_daily_etl(conn)  # target_date を省略すると今日
  print(result.to_dict())
  ```

- 市場カレンダーを夜間バッチで更新する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved", saved)
  ```

- RSS からニュース収集を実行する
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # known_codes: 銘柄抽出に使用する有効な銘柄コードセット（None なら紐付けスキップ）
  results = run_news_collection(conn, known_codes={"7203", "6758"})
  print(results)  # {source_name: new_saved_count}
  ```

- J-Quants トークン取得 / データ取得（個別）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # settings.jquants_refresh_token を利用して ID トークンを取得
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- データ品質チェックを手動で実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点:
- run_daily_etl 等は内部でエラーハンドリングを行い、個別ステップが失敗しても可能な限り続行します。戻り値（ETLResult）や品質チェックの結果を参照して運用判断を行ってください。
- news_collector はデフォルトで MAX_RESPONSE_BYTES による制限、SSRF の防止、gzip 解凍後のサイズチェック等を行います。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルト:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — set to "1" to disable auto .env loading

.env / .env.local の自動読込について:
- 読み込み順: OS 環境 > .env.local (override=True) > .env (override=False)
- 自動読込を無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋；実際は src/ 以下にパッケージが配置されています）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント／保存ロジック
    - news_collector.py      — RSS ニュース収集 / 前処理 / DB 保存
    - schema.py              — DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー管理（is_trading_day など）と calendar_update_job
    - audit.py               — 監査ログ用スキーマ初期化（signal_events / order_requests / executions）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略層（未実装箇所のプレースホルダ）
  - execution/
    - __init__.py            — 発注実行層（未実装箇所のプレースホルダ）
  - monitoring/
    - __init__.py            — モニタリング（未実装プレースホルダ）

---

## 実運用上の注意 / 運用チェックリスト

- J-Quants API のレート制限（120 req/min）を厳守すること。モジュール内部で制御がありますが、運用ジョブの同時実行数には注意してください。
- DuckDB ファイルのバックアップとローテーション（特に監査ログが大きくなる点）。
- Slack / kabu API 等の機密情報は適切に管理し、CI/CD に平文で含めないこと。
- news_collector の外部 HTTP 呼び出しは SSRF 対策済みですが、プロキシ／ネットワークルールの確認を行ってください。
- 環境（KABUSYS_ENV）を適切に設定して、paper_trading / live を切り替える運用フローを整備してください。

---

## 貢献 / 開発

- コードは src/kabusys 以下に実装されています。新機能は該当モジュールに追加し、DB スキーマ変更がある場合は schema.py の DDL を更新してください。
- テストや CI のセットアップは任意ですが、API 呼び出しは外部依存が大きいためモック可能な設計（id_token 注入、_urlopen の差し替えなど）を利用してください。

---

以上。必要があれば README に含める具体的なコマンド、例 .env.example、あるいはサンプルスクリプト（cron/airflow 用 DAG）などを追加で作成します。どの部分を詳しく書き足しますか？