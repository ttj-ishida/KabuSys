# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。J-Quants API からマーケットデータ・財務データ・カレンダーを取得して DuckDB に保存する ETL、データ品質チェック、監査ログ（発注から約定までのトレーサビリティ）などを提供します。

---

## 概要

- J-Quants API を用いたデータ取得（株価日足、四半期財務、JPX マーケットカレンダー）
- DuckDB ベースの 3 層データモデル（Raw / Processed / Feature）と実行/監査テーブル
- 差分更新・バックフィルを考慮した ETL パイプライン（run_daily_etl）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal / order_request / execution）による完全なトレーサビリティ
- Rate limiter、リトライ（指数バックオフ）、401 の自動トークンリフレッシュ、冪等性（ON CONFLICT）などを考慮した実装

設計上のポイント:
- API レート制限（120 req/min）を厳守
- 取得時刻（fetched_at）や全 TIMESTAMP を UTC で記録
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で二重挿入を防止

---

## 機能一覧

- 環境変数/.env の自動読み込み（プロジェクトルートを検出）
- J-Quants API クライアント
  - get_id_token（リフレッシュトークンからIDトークン取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- DuckDB スキーマ定義と初期化（data.schema.init_schema）
- 監査ログスキーマ初期化（data.audit.init_audit_schema / init_audit_db）
- ETL パイプライン（data.pipeline）
  - 差分取得、backfill、先読みカレンダー処理
  - 品質チェック呼び出し（data.quality.run_all_checks）
  - ETL 実行結果を表す ETLResult
- 品質チェック（data.quality）
  - 欠損（missing_data）、スパイク（spike）、重複（duplicates）、日付不整合（future_date / non_trading_day）
  - 各チェックは QualityIssue を返す
- 監視 / 実行 / 戦略用のプレースホルダモジュール（strategy, execution, monitoring）

---

## 動作環境 / 前提

- Python 3.10+
- duckdb（DuckDB Python パッケージ）
- （API 呼び出しは標準ライブラリ urllib を使用しているため追加 HTTP ライブラリは不要）

必要な Python パッケージの例:
pip install duckdb

（プロジェクトに pyproject.toml / requirements.txt があればそちらを使用してください）

---

## 環境変数

以下は必須 / 任意の主要な環境変数です。プロジェクトでは .env（および .env.local）をプロジェクトルートから自動で読み込みます。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系で利用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必要なら）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL。デフォルト: INFO）

テスト・CI 等で自動読み込みを無効にする場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb
   - （必要に応じてその他パッケージを追加）

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成して必要なキーを設定
     例:
       JQUANTS_REFRESH_TOKEN=your_refresh_token
       KABU_API_PASSWORD=your_kabu_password
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C12345678
       DUCKDB_PATH=data/kabusys.duckdb
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定

5. DuckDB スキーマの初期化
   - Python から data.schema.init_schema() を呼び出して DB を初期化
   - 例（次節の使い方参照）

---

## 使い方（簡単なコード例）

以下は基本的な使用例です。Python スクリプト内で実行します。

1) スキーマ初期化（DuckDB を作成・テーブル作成）
```python
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 個別データ取得（J-Quants クライアント）
```python
from kabusys.data import jquants_client as jq

# 1) ID トークン取得（任意） - 通常は内部キャッシュを利用するため不要
id_token = jq.get_id_token()

# 2) 銘柄コード 7203 (例) の日足を取得
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

# DuckDB に保存する場合は save_daily_quotes を使用
import duckdb
conn = duckdb.connect(str("data/kabusys.duckdb"))
jq.save_daily_quotes(conn, records)
```

4) 監査スキーマ初期化（ETL で作成した接続に追記）
```python
from kabusys.data import audit, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
audit.init_audit_schema(conn)  # 監査テーブルを追加
```

5) 品質チェックだけ実行する
```python
from kabusys.data import quality
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

注意:
- run_daily_etl 等は例外を個別に捕捉して処理を継続する設計です。戻り値の ETLResult で詳細を確認してください。
- すべてのタイムスタンプは UTC で扱われます（監査スキーマは明示的に SET TimeZone='UTC' を実行）。

---

## 主要 API（概要）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.is_live 等

- kabusys.data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(id_token: str | None, code: str | None, date_from: date | None, date_to: date | None) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path) -> duckdb connection (初期化はしない)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...) -> ETLResult
  - run_prices_etl, run_financials_etl, run_calendar_etl（個別 ETL）

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5) -> list[QualityIssue]

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## 注意事項 / 実運用メモ

- API レート制限: J-Quants は 120 req/min。クライアントは内部でスロットリングを行いますが、実行環境によっては追加の制御が必要になる場合があります。
- リトライ/バックオフ: ネットワークエラーや 5xx、429 等に対して指数バックオフで最大 3 回リトライします。429 の場合は Retry-After が使われます。
- トークンリフレッシュ: 401 を受けた場合は内部でリフレッシュを行い 1 回だけリトライします（無限再帰は防止）。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を用いるため、再実行しても上書きで整合を保ちます。
- ETL の差分ロジック: stock/fundamental は DB の最終取得日を参照して差分のみ取得します。バックフィル日数（デフォルト 3 日）で後出し修正を吸収します。
- 時刻・タイムゾーン: 監査用タイムスタンプは UTC 保存が前提です。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/                (発注・ブローカー関連：プレースホルダ)
      - __init__.py
    - strategy/                 (戦略ロジック：プレースホルダ)
      - __init__.py
    - monitoring/
      - __init__.py
    - data/
      - __init__.py
      - jquants_client.py       (J-Quants API クライアント)
      - schema.py               (DuckDB スキーマ定義・初期化)
      - pipeline.py             (ETL パイプライン)
      - audit.py                (監査ログスキーマ)
      - quality.py              (データ品質チェック)

---

## ライセンス・貢献

このリポジトリのライセンスやコントリビュートルールはリポジトリ内の LICENSE / CONTRIBUTING を参照してください（存在しない場合は管理者に問い合わせてください）。

---

README は以上です。必要であれば、.env.example の雛形や具体的な CI ワークフロー（スケジューリング・監視・Slack 通知等）のサンプルを追加します。どの情報を補足しましょうか？