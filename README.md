# KabuSys

日本株の自動売買／データ基盤ライブラリ（KabuSys）。  
J-Quants から市場データを取得して DuckDB に保存し、品質チェック・監査ログ・ETL パイプラインを提供します。

※ この README はソースコード構成（src/kabusys 以下）に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォーム兼自動売買基盤のコンポーネント群です。主な目的は以下です。

- J-Quants API から株価（日足）・財務情報・市場カレンダーを取得
- DuckDB に対するスキーマ定義・初期化および冪等な保存
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注〜約定の監査ログ（監査テーブル群）の初期化

設計上の特徴：
- API レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
- DuckDB への挿入は ON CONFLICT DO UPDATE を用いた冪等処理
- すべてのタイムスタンプは UTC を想定（監査テーブル等）

---

## 機能一覧

- J-Quants クライアント
  - get_id_token（リフレッシュトークンから id_token を取得）
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（財務データ、ページネーション対応）
  - fetch_market_calendar（JPX マーケットカレンダー）
  - 保存関数（save_*）で DuckDB に冪等保存
- DuckDB スキーマ管理
  - init_schema(db_path) — 全テーブルを作成（Raw / Processed / Feature / Execution 層）
  - get_connection(db_path)
- 監査ログ初期化
  - init_audit_schema(conn) / init_audit_db(db_path)
- ETL パイプライン
  - run_daily_etl(conn, target_date=..., ...) — 市場カレンダー→株価→財務→品質チェックの一括実行
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- 品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks(conn, ...) — すべてのチェックを実行して QualityIssue の一覧を返す
- 環境設定管理
  - settings（環境変数経由で設定値を取得。自動的に .env / .env.local をプロジェクトルートからロード）

---

## 前提（動作環境）

- Python >= 3.10（型ヒントに `X | None` を利用しているため）
- 必要な Python パッケージ（最低限）:
  - duckdb
  - そのほか標準ライブラリ（urllib 等）を使用

依存はプロジェクトのパッケージ管理ファイルに合わせて導入してください（例: poetry / pip）。

例（pip）:
```bash
pip install duckdb
# プロジェクトを editable インストールする場合
pip install -e .
```

---

## セットアップ手順

1. リポジトリを取得し、Python 環境を準備する。

2. 依存パッケージをインストール
   - duckdb 等をインストールしてください。

3. 環境変数を設定
   - .env または環境変数に以下を設定してください（必須は下記参照）。

必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能使用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能使用時）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知機能使用時）

任意 / デフォルトあり:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

自動 .env ロードを無効にする場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定

プロジェクトルートは .git または pyproject.toml を基準に自動検出され、その下の .env / .env.local を読み込みます。

4. DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

5. （監査ログを別途利用する場合）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
# または専用 DB を作る場合
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（サンプル）

基本的な ETL（日次）を実行する例：

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DuckDB 初期化（存在しなければ作成）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（target_date を指定しなければ今日）
result = run_daily_etl(conn)

# 結果確認
print(result.to_dict())
if result.has_errors:
    print("ETL 中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックでエラーが検出されました")
```

個別ジョブを直接実行する例（株価だけ）:

```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

J-Quants の API を直接使う例:

```python
from kabusys.data import jquants_client as jq
# トークンは settings.jquants_refresh_token から自動取得されます
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# DuckDB へ保存する場合:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

品質チェックだけ実行する例:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

ログレベルや環境は環境変数で制御します（例: LOG_LEVEL=DEBUG）。

---

## 注意事項 / Tips

- Python の型注釈や演算子（例: Path | None）に依存しているため Python 3.10 以上を推奨します。
- J-Quants API はレート制限（120 req/min）に従う必要があります。本クライアントは内部で固定間隔スロットリングとリトライを実装しています。
- get_id_token のような認証取得は再帰を避けるため allow_refresh を制御しています。通常は明示的な操作は不要です。
- DuckDB のテーブルは init_schema() で作成します。既存のスキーマがあれば冪等的にスキップされます。
- ETL の差分取得ロジックは最終取得日を参照し、backfill_days（デフォルト3日）分さかのぼって再取得します。これにより API の後出し修正を吸収します。
- 自動で .env を読み込む機能はプロジェクトルート (.git や pyproject.toml) を基準に行われます。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得＋保存）
  - schema.py                    — DuckDB スキーマ定義・初期化
  - pipeline.py                  — ETL パイプライン（差分取得・品質チェック含む）
  - audit.py                     — 監査ログ（発注→約定トレース）初期化
  - quality.py                   — データ品質チェック群
- execution/
  - __init__.py                   — 発注・執行関連（未実装のエントリプレースホルダ）
- strategy/
  - __init__.py                   — 戦略層（未実装のエントリプレースホルダ）
- monitoring/
  - __init__.py                   — 監視関連（未実装のエントプレースホルダ）

主なファイル:
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- src/kabusys/data/quality.py
- src/kabusys/data/audit.py

---

## 追加情報 / 今後の拡張

- execution / strategy / monitoring パッケージはプレースホルダとして用意されています。発注ロジックや戦略実装、モニタリング連携（Slack 等）はここに実装してください。
- 監査ログは `order_requests.order_request_id` を冪等キーとして二重発注を防ぎつつ、signal → order → execution のフローを完全にトレースできます。
- 品質チェックの出力は QualityIssue オブジェクトのリストで返るため、アラート送信やダッシュボードへの連携が可能です。

---

必要があれば、README にサンプル .env.example やより詳細な API 使用例（ページネーション・エラー処理等）を追加します。どの情報を追記しましょうか？