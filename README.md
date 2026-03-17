# KabuSys

バージョン: 0.1.0

日本株向けの自動売買プラットフォームのコアライブラリです。データ取得（J-Quants）、ETLパイプライン、ニュース収集、データスキーマ／監査ログ、品質チェック、マーケットカレンダー管理などを提供します。戦略（strategy）や発注（execution）、監視（monitoring）はモジュール分割されています（実装はプロジェクトに応じて拡張）。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（サンプル）
- 環境変数一覧と自動ロード挙動
- ディレクトリ構成
- 開発・貢献メモ

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリ群です。外部データ取得（J-Quants API、RSS ニュース）、DuckDB を利用したスキーマ、ETL パイプライン、データ品質チェック、マーケットカレンダー管理、監査ログなど、戦略や実際の発注ロジックを乗せられる堅牢なレイヤーを提供します。

設計上のポイント:
- J-Quants の API レート制限遵守（120 req/min）やリトライ、トークン自動リフレッシュを備えたクライアント
- DuckDB による冪等なデータ保存（ON CONFLICT / DO UPDATE, DO NOTHING）
- ニュース収集での SSRF・XML 攻撃対策、受信サイズ制限、トラッキングパラメータ除去
- データ品質チェック・監査ログの充実
- 市場カレンダーを元にした営業日判定やバッチ更新

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、必須変数取得ヘルパ
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務諸表、マーケットカレンダー取得
  - レートリミティング、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、記事正規化、記事ID生成（SHA-256）と DuckDB への保存
  - SSRF 対策・XML 攻撃対策・受信サイズ制限・銘柄コード抽出
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - スキーマ初期化関数（init_schema）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（バックフィル対応）、保存、品質チェックの一括実行（run_daily_etl 等）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、カレンダー夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal / order_request / execution の監査スキーマと初期化ヘルパ
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出と QualityIssue レポート

---

## セットアップ手順

前提
- Python 3.10 以上を推奨（ソースの型注釈や構文に依存）
- DuckDB を利用

依存パッケージ（例）
- duckdb
- defusedxml

インストール（例）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 他に必要なライブラリがあれば requirements.txt を作成して pip install -r requirements.txt
```

環境ファイル
- プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると、自動的に読み込まれます。
- 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = schema.init_schema(":memory:")
```

監査ログ用スキーマ初期化（既存接続に追加）
```python
from kabusys.data import audit

# conn: duckdb connection を用意してから
audit.init_audit_schema(conn, transactional=True)
```

---

## 使い方（サンプル）

1) 環境設定を読み込み、設定値を参照する
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須変数が未設定だと ValueError
print(settings.duckdb_path)  # Path オブジェクト
```

2) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
```

3) 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) ニュース収集ジョブの実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使う有効銘柄コードのセット
known_codes = {"7203", "6758", "9432"}  # 例
out = run_news_collection(conn, known_codes=known_codes)
print(out)  # {source_name: 新規保存件数, ...}
```

5) マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

6) J-Quants のデータ取得のみ直接呼ぶ（テスト用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 環境変数一覧と自動ロード挙動

主要な環境変数（必須のものは README 上で明示）:

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルトあり）:
- KABUSYS_ENV: 環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...）。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- KABUSYS_* の他設定: KABUSYS に特化したものは settings を参照してください

データベースパス:
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用など）パス（デフォルト: data/monitoring.db）

自動ロード優先順位:
- OS 環境変数 > .env.local > .env
- パッケージは __file__ を起点に親ディレクトリを探索し、.git または pyproject.toml を検出したディレクトリをプロジェクトルートと見なします（CWD 依存しない）。もしプロジェクトルートが特定できない場合は自動ロードをスキップします。

必須変数未設定時:
- settings の必須プロパティを参照すると ValueError が送出されます（.env.example を基に .env を作成してください）。

---

## ディレクトリ構成

主要ファイル・モジュール（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py             — RSS ニュース収集・保存・銘柄抽出
    - schema.py                     — DuckDB スキーマ定義と init_schema()
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        — マーケットカレンダー管理
    - audit.py                      — 監査ログスキーマ（signal/order/execution）
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略モジュール向けパッケージ（拡張ポイント）
  - execution/
    - __init__.py                   — 発注・約定周りのパッケージ（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視・メトリクスモジュール（拡張ポイント）

補足:
- schema.py には Raw / Processed / Feature / Execution 層のテーブルがすべて定義されています。
- audit.py は監査用の専用スキーマ初期化を提供します（init_audit_db / init_audit_schema）。

---

## 開発・貢献メモ

- Python の型注釈（PEP 604 の | 型等）を使用しているため、Python 3.10 以上を推奨します。
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化すると isolation が取りやすいです。
- ネットワークを伴う部分（jquants_client.fetch_*、news_collector.fetch_rss など）はモックしやすい設計（id_token 注入、_urlopen を差し替え可能）になっています。
- DuckDB に対する変更はスキーマ整合性に注意してください。DDL はすべて init_schema / init_audit_schema で管理します。
- ニュース収集で外部 URL を扱う箇所は SSRF や XML Bomb を考慮した実装になっています。実装変更時はセキュリティ観点のレビューを推奨します。

---

必要であれば、README に含める具体的なコマンド（systemd / cron / Airflow 用のジョブ定義例）、テストの書き方、CI 設定テンプレートなども追加で作成します。どの情報を優先して追加しますか？