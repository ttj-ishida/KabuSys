# KabuSys

日本株向け自動売買・データプラットフォーム（ライブラリ）  
このリポジトリは、J‑Quants API から市場データを取得して DuckDB に保存し、データ品質チェック・監査ログ・ETL パイプラインを提供する基盤コンポーネント群を含みます。戦略（strategy）や発注（execution）モジュールと組み合わせて自動売買システムを構築できます。

---

## プロジェクト概要

主な目的：
- J‑Quants API から株価（日足）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
- DuckDB に対して冪等（idempotent）にデータを保存
- ETL（差分取得／バックフィル）パイプラインの提供
- データ品質チェック（欠損・スパイク・重複・日付不整合）の実行
- 監査ログ（signal → order_request → executions のトレーサビリティ）スキーマの初期化

設計上のポイント：
- API レート制限（120 req/min）を固定間隔スロットリングで遵守
- リトライ（指数バックオフ、最大 3 回）、401 受信時はトークン自動リフレッシュ
- データ取得日時（fetched_at）を UTC で記録し、Look‑ahead Bias を防止
- DuckDB への INSERT は ON CONFLICT DO UPDATE により冪等に保存

---

## 機能一覧

- 環境設定管理（.env 自動読み込み／環境変数）
- J‑Quants クライアント
  - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar
  - 取得データの DuckDB への保存（save_*）
- DuckDB スキーマ定義・初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
- 監査ログスキーマ（data.audit.init_audit_schema / init_audit_db）
- ETL パイプライン（data.pipeline.run_daily_etl）
  - カレンダー、株価、財務の差分取得、保存、品質チェックの一括実行
- データ品質チェック（data.quality）
  - 欠損データ、スパイク（急騰・急落）、重複、日付整合性チェック
- ロギング、構成（環境変数によるログレベルなど）

---

## セットアップ手順

前提
- Python 3.10 以上（コード内で | 型アノテーションなどを使用）
- DuckDB が必要（Python パッケージとして duckdb を利用）

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合は .venv\Scripts\activate）

2. 必要パッケージのインストール
   - pip install duckdb

   （プロジェクトで追加の依存がある場合は適宜 requirements.txt / pyproject.toml に従ってください）

3. 環境変数（.env）の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` および必要に応じて `.env.local` を配置すると自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで使用）。

必須環境変数（少なくとも開発で使う場合）：
- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabu ステーション API のパスワード（発注機能を使う場合）
- SLACK_BOT_TOKEN : Slack 通知を使う場合の Bot Token
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID

任意（デフォルトあり）：
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH : DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite path（デフォルト data/monitoring.db）

例（.env の最小例）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なコード例）

以下は基本的な初期化と日次 ETL 実行の例です。

1) DuckDB スキーマを初期化して接続を取得
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH を反映
conn = init_schema(settings.duckdb_path)
```

2) 監査ログ（audit）スキーマを追加で初期化する
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

3) 日次 ETL を実行（カレンダー／株価／財務を差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

4) J‑Quants の ID トークンを直接取得する（テスト等で利用）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()
```

5) 個別の品質チェックを実行する
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

補足：
- ETL 実行はログを確認してください。エラーや品質問題は ETLResult に収集されます。
- jquants_client は内部でレート制限・リトライ・トークンキャッシュを行います。

---

## 環境変数と設定（Settings API）

コード内では `kabusys.config.settings` を通して設定を参照できます。主なプロパティ：
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path オブジェクト)
- settings.sqlite_path (Path)
- settings.env (development / paper_trading / live)
- settings.log_level
- settings.is_live / is_paper / is_dev

自動 .env 読み込みの仕組み：
- プロジェクトルートを __file__ の親から探し、.git または pyproject.toml があるディレクトリをプロジェクトルートとする。
- 読み込み順は OS 環境 > .env.local > .env（.env.local が .env を上書き）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

.env のパースはシェルライクな簡易パーサで、クォートや export 形式、行末コメント等に対応しています。

---

## 主要モジュール（簡単な説明）

- kabusys.config
  - 環境変数・設定の取得、.env 自動ロード
- kabusys.data.jquants_client
  - J‑Quants API 呼び出し、レート制限、リトライ、取得 & DuckDB 保存用ユーティリティ
- kabusys.data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）と初期化
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化
- kabusys.data.pipeline
  - 差分 ETL（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.strategy, kabusys.execution, kabusys.monitoring
  - 戦略、発注、監視のための名前空間（拡張用）

---

## ディレクトリ構成

（リポジトリ内の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/
      - __init__.py
    - strategy/
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py

DuckDB スキーマは data/schema.py 内に記述されています。監査ログ（audit）DDL は data/audit.py にあります。

---

## 運用上の注意

- API レート制限とリトライ:
  - J‑Quants は 120 req/min を想定。内部で固定間隔スロットリングを行います。
  - HTTP 408/429/5xx はリトライ対象。429 の場合は Retry‑After ヘッダを尊重します。
  - 401 受信時はリフレッシュトークンで ID トークンを再取得して 1 回だけリトライします。

- 時刻関連:
  - 取得時刻（fetched_at）や監査ログの TIMESTAMP は UTC で記録することを想定しています。
  - audit.init_audit_schema() は DuckDB 接続に対して "SET TimeZone='UTC'" を実行します。

- データ保存:
  - save_* 関数は ON CONFLICT DO UPDATE を使用して冪等性を担保します。

- テスト:
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - get_id_token などは id_token を引数注入できるためテストが容易です。

---

## 今後の拡張案（参考）

- strategy / execution 層の実装（シグナル生成、ポートフォリオ最適化、ブローカー API 実装）
- Slack や Prometheus など監視・アラート連携の拡充
- ETL のスケジューリング（Airflow / Prefect 等との統合）
- テスト用のモック HTTP サーバー／VCR の導入

---

質問や README の追加内容（例: pyproject.toml、CI/CD、詳細な .env.example）を希望する場合はお知らせください。