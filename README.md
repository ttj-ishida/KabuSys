# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群（KabuSys）。  
J-Quants / kabuステーション 等の外部APIからデータを取得し、DuckDBに蓄積、ETL、品質チェック、ニュース収集、監査ログ等の基盤機能を提供します。

---

## 主要な機能（概要）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ、Look-ahead バイアス対策（fetched_at）
  - DuckDB への冪等保存（ON CONFLICT による更新）

- ETL パイプライン
  - 差分取得（最終取得日ベース）、バックフィル調整、カレンダー先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集
  - RSS フィードの安全な取得（SSRF 対策、gzip 上限、XML 攻撃対策）
  - 記事の前処理・正規化・ID 生成（URL の正規化 → SHA-256）
  - DuckDB への冪等保存（INSERT ... RETURNING により挿入数を取得）
  - 銘柄コード抽出と紐付け（known_codes を利用）

- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、期間内営業日取得
  - カレンダーの夜間差分更新ジョブ

- 監査ログ（Audit）
  - シグナル → 注文 → 約定の完全トレーサビリティ（UUID 階層）
  - 監査用テーブル初期化ユーティリティ（UTC タイムゾーン固定）

- データ品質チェック（quality モジュール）
  - 欠損データ、スパイク（急騰・急落）、重複、将来日付・非営業日データの検出

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（パッケージ化時に requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを配置）

2. 仮想環境作成・アクティベート（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存インストール
   例: requirements.txt がある場合
   ```bash
   pip install -r requirements.txt
   ```
   主要なものだけ手動で入れる場合:
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（優先順: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須の環境変数（config.Settings 参照）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意 / デフォルトあり:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite ファイルパス（デフォルト: data/monitoring.db）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベーススキーマ初期化
   - DuckDB スキーマ（データ層）を初期化:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
     ```
   - 監査ログ用スキーマを追加する（必要に応じて）:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```
   - 監査専用 DB を別に作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主なユースケースとコード例）

- 日次 ETL（株価・財務・カレンダー取得＋品質チェック）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9432"}  # 事前に取得した有効コード集合
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: 新規保存件数, ...}
  ```

- カレンダー差分更新（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- J-Quants の個別 fetch / save（テストやデバッグ用）
  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

ログレベルや実行スケジュールは外部のスケジューラ（cron / Airflow / systemd timer）やコンテナで管理してください。

---

## 自動環境変数読み込みの挙動

- パッケージ読み込み時に、プロジェクトルート（.git または pyproject.toml がある親ディレクトリ）を探索し `.env` と `.env.local` を自動で読み込みします（OS 環境変数を上書きしない/`.env.local` は上書き）。  
- 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント（fetch/save）
      - news_collector.py            # RSS ニュース収集・保存
      - schema.py                    # DuckDB スキーマ定義・初期化
      - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       # マーケットカレンダー管理
      - audit.py                     # 監査ログテーブル初期化
      - quality.py                   # データ品質チェック
    - strategy/
      - __init__.py                  # 戦略層（拡張ポイント）
    - execution/
      - __init__.py                  # 発注・実行関連（拡張ポイント）
    - monitoring/
      - __init__.py                  # モニタリング（拡張ポイント）

---

## 開発メモ / 設計上のポイント

- データ取得は「いつシステムがそのデータを知り得たか」を記録するため fetched_at を UTC で記録します（Look-ahead 防止）。
- API はレート制御、リトライ、トークン自動リフレッシュを備え冪等に保存します。
- ニュース取得は SSRF・XML 攻撃・Gzip bomb 等の攻撃を考慮した堅牢設計です。
- DuckDB によるスキーマは Raw / Processed / Feature / Execution（監査含む） の多層で設計されています。
- 品質チェックは Fail-Fast ではなく、問題を列挙して呼び出し元で判断できるようにしています。

---

## 今後の拡張案（参考）

- strategy / execution / monitoring の具象実装（戦略ロジック、kabuステーションとの注文送信、Slack 通知等）
- CI / tests の追加（ユニットテスト、統合テスト）
- Docker イメージ化と運用用コンテナ構成（cron / systemd の代替）
- メトリクス収集（Prometheus 等）や可視化パイプライン

---

必要であれば README に含める追加のコマンド例（systemd ユニット、cron エントリ、Dockerfile、pyproject.toml / setup.cfg の雛形）や、具体的な .env.example を作成します。どの内容を追加しますか？