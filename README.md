# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants API から市場データ（株価日足、財務データ、JPXカレンダー等）を取得して DuckDB に保存し、品質チェックや監査ログの初期化・管理を行うためのコンポーネントを提供します。

本リポジトリはライブラリ形式で、ETL パイプライン、データスキーマ、品質チェック、監査ログ（オーダー／約定のトレーサビリティ）を中心に設計されています。

---

## 特徴（機能一覧）

- 環境変数/`.env` 自動読み込みと型付き設定取得（kabusys.config）
  - 自動読み込み順序: OS 環境変数 > .env.local > .env
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
  - 必須項目は未設定時に ValueError を発生させる

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期）、JPXマーケットカレンダーを取得
  - レート制限（120 req/min）を守る固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 の場合はトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を軽減
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の層別テーブル定義
  - インデックス定義・テーブル作成順を管理
  - `init_schema()` で DB を初期化して接続を返す

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最後の取得日ベース、バックフィルオプション）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）との連携
  - 結果は `ETLResult` で返却（取得数、保存数、品質問題、エラー等）

- 品質チェック（kabusys.data.quality）
  - 欠損データ検出（OHLC）
  - 異常値（スパイク）検出（前日比閾値）
  - 主キー重複検出
  - 将来日付 / 非営業日データ検出
  - 各問題は `QualityIssue` オブジェクトで返却

- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティを保持するテーブル群を定義
  - 冪等キー（order_request_id / broker_execution_id 等）やステータス遷移を管理
  - `init_audit_schema()` / `init_audit_db()` を提供

---

## 要件

- Python 3.10 以上（Union types `X | Y` を使用）
- 依存パッケージ:
  - duckdb
- ネットワークアクセス（J-Quants API）

（運用上は J-Quants の利用登録・トークンが必要です）

---

## 環境変数（主な必須キー）

必須（アプリ起動時に設定する／`.env` に記載）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト有り）:
- KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 `.env` ロードを無効化する場合に `1` を設定

サンプル .env（README 用例）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン（例）
   - git clone ...

2. Python 仮想環境を作成 / 有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb
   - （将来的に requirements.txt を用意している場合は pip install -r requirements.txt）

4. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成
   - 必須キー（上記）を設定

5. データベーススキーマ初期化（例はローカルで DuckDB を使用する場合）
   - Python スクリプトや REPL から:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ（audit）を追加する場合:
     ```
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```
   - 監査専用 DB を作る場合:
     ```
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（代表的な例）

- 設定取得:
  ```
  from kabusys.config import settings
  token = settings.jquants_refresh_token  # 必須
  is_live = settings.is_live
  ```

- 日次 ETL を実行（最も基本的な例）:
  ```
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（初回のみ）
  conn = init_schema("data/kabusys.duckdb")

  # ETL 実行（今日を対象日として実行）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ETL を明示的にテストトークンで呼ぶ例:
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(":memory:")  # テスト用インメモリ DB
  # J-Quants の id_token を事前に取得して注入することも可能
  result = run_daily_etl(conn, id_token="...your_id_token...")
  ```

- 品質チェックだけを実行:
  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- J-Quants から日足を直接取得:
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes
  rows = fetch_daily_quotes(code="7203", date_from=..., date_to=...)
  ```

---

## 主要 API の説明（簡易）

- kabusys.config.Settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path など

- kabusys.data.jquants_client
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(conn, records), save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)

  主要設計点:
  - レート制限 120 req/min を内部で制御
  - リトライ（408/429/5xx）と 401 時のトークンリフレッシュ
  - DuckDB への保存は ON CONFLICT DO UPDATE による冪等性

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB 接続（テーブルをすべて作成）
  - get_connection(db_path) -> 既存 DB への接続（初期化は行わない）

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
    - カレンダー → 株価 → 財務データ → 品質チェック の順で実行
    - ETLResult を返す（保存数、品質問題、エラー等）

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
    - QualityIssue のリストを返す

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/            (発注ロジック用モジュール群の配置想定)
      - __init__.py
    - strategy/             (戦略ロジック用モジュール群の配置想定)
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py   (J-Quants API クライアント)
      - schema.py           (DuckDB スキーマ定義 & init_schema)
      - pipeline.py         (ETL パイプライン)
      - audit.py            (監査ログ定義 & init)
      - quality.py          (データ品質チェック)

主要 API は上記ファイルに実装されています。strategy, execution, monitoring ディレクトリは拡張用のプレースホルダです。

---

## 運用上の注意 / トラブルシューティング

- 環境変数が足りない場合、Settings のプロパティアクセスで ValueError が発生します。`.env.example` を参考に `.env` を用意してください。
- J-Quants API を叩くためのトークンは必ず安全に保管してください。token のリフレッシュや cache は jquants_client 内部で処理されます。
- DuckDB のファイルパスが指定した親ディレクトリが存在しない場合、init_schema() が自動作成します。
- 自動 `.env` ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用に便利です）。
- J-Quants のレート制限（120 req/min）を内部で守る設計ですが、分散的な複数プロセスからの同時アクセスがある場合は別途レート制御が必要です。

---

## 追加メモ（設計ポイント）

- データ取得時に fetched_at を UTC で保存することで「いつシステムがデータを知り得たか」をトレース可能にしています（Look-ahead Bias の軽減）。
- ETL は Fail-Fast ではなく各ステップを独立に実行し、問題は結果オブジェクトに集約され、呼び出し元が判断できるようになっています。
- データ品質チェックは SQL ベースで DuckDB 上で効率的に実行します。問題は QualityIssue オブジェクトにまとめられます。

---

この README はコードの現状（src 以下に示されたモジュール群）を基に作成しています。戦略ロジック（strategy）や実際のブローカー接続（execution）の実装は別途追加する想定です。必要ならば、README に含めるサンプル CLI、CI/CD 手順、より詳細な .env.example や運用チェックリストを追記します。どの情報を追加したいか教えてください。