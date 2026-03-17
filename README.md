# KabuSys

日本株自動売買システムのライブラリ群（KabuSys）。  
データ収集・ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログ用スキーマなどを提供します。

---

## プロジェクト概要

KabuSys は主に以下を目的とした内部ライブラリです。

- J-Quants API からの市場データ（株価、財務、マーケットカレンダー）取得と DuckDB への冪等保存
- RSS ベースのニュース収集と銘柄（4桁コード）紐付け
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー（JPX）管理・営業日判定ロジック
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ

設計上のポイント：
- API レート制限順守（J-Quants は 120 req/min）とリトライ（指数バックオフ、401 時のトークン自動更新）
- DuckDB への保存は冪等（ON CONFLICT）で安全
- ニュース収集は SSRF/XML-Bomb 対策や受信サイズ制限を実装
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- kabusys.config
  - .env 自動読み込み（プロジェクトルート基準） / 環境変数ラッパー（必須値チェック）
- kabusys.data.jquants_client
  - ID トークン取得、日次株価・財務・カレンダーの取得、DuckDB への保存ロジック
  - レートリミッタ、リトライ、トークンキャッシュ
- kabusys.data.news_collector
  - RSS 取得、テキスト前処理、記事ID生成（正規化URL→SHA256）、DuckDB 保存、銘柄抽出
  - SSRF 対策、gzip 制限、defusedxml を利用
- kabusys.data.schema / audit
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）と初期化関数
- kabusys.data.pipeline
  - run_daily_etl などの ETL エントリポイント（差分取得、バックフィル、品質チェック）
- kabusys.data.calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job
- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks

---

## 要件（推奨）

- Python 3.10+
- 依存パッケージ（主なもの）
  - duckdb
  - defusedxml
- （ネットワーク経由で J-Quants / RSS にアクセスするため適切なネットワーク環境）

実際の `pyproject.toml` / `requirements.txt` がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します（例: venv, poetry 等）。
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要なパッケージをインストールします（例: pip）。
   - pip install duckdb defusedxml
   - またはプロジェクトのパッケージを編集インストール:
     - pip install -e .

3. 環境変数の準備
   - プロジェクトルートに `.env`（およびローカル専用は `.env.local`）を作成することで、自動的にロードされます（起動時）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 必要な環境変数

少なくとも以下は設定しておく必要があります（`kabusys.config.Settings` が参照します）。

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

例（.env）:
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb

---

## 初期化（DB スキーマ）

DuckDB スキーマを初期化する例:

- メイン DB（全テーブル）を初期化:
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 監査ログ専用 DB を初期化:
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

注意: init_schema は親ディレクトリが存在しない場合に自動作成します。

---

## 使い方（簡単なコード例）

- 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）:

```python
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ実行（デフォルト RSS ソース）:

```python
from kabusys.data import schema
from kabusys.data import news_collector as nc

conn = schema.init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードのセット
res = nc.run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ:

```python
from kabusys.data import schema, calendar_management as cm

conn = schema.init_schema("data/kabusys.duckdb")
saved = cm.calendar_update_job(conn)
print("saved:", saved)
```

- 監査スキーマ追加（既存の conn に）:

```python
from kabusys.data.audit import init_audit_schema
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

- 直接 J-Quants クライアント関数を使う（テストや細かい取得に）:

```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

---

## 動作モード・ログレベル

- KABUSYS_ENV: development / paper_trading / live（Settings.env で検証）
  - Settings.is_dev / is_paper / is_live で判定可能
- LOG_LEVEL でログ出力レベルを制御（INFO など）

---

## セキュリティと運用上の注意

- jquants_client は API レート制限を守るよう実装されていますが、運用上のスケジューリング（cron/airflow 等）は別途考慮してください。
- news_collector は SSRF 対策（リダイレクト検証、プライベートアドレス拒否）や XML パース安全化（defusedxml）を実装しています。外部から与えられた RSS URL の扱いには注意してください。
- 環境変数やトークンは安全に管理してください（シークレット管理、アクセス制御）。

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアントと DuckDB 保存
    - news_collector.py         — RSS 収集・保存・銘柄抽出
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー管理・営業日判定
    - audit.py                  — 監査ログスキーマ（signal/order/execution）
    - quality.py                — データ品質チェック
  - strategy/                    — 戦略関連（空の __init__ が存在）
  - execution/                   — 発注・実行関連（空の __init__ が存在）
  - monitoring/                  — 監視用モジュール（未実装のパッケージ空間）

---

## 貢献・拡張

- 新しい ETL ジョブや戦略、実際のブローカ連携は `strategy/`、`execution/` 配下に実装してください。
- テストはネットワークアクセスを伴う部分が多いため、外部 API をモックするように設計してください（モジュール内部の `_urlopen` などはテスト時に差し替え可能です）。
- コード変更時は既存の DuckDB スキーマやマイグレーションを考慮してください（DDL は冪等に設計済みです）。

---

README は以上です。運用や拡張について詳細が必要であれば、利用想定のワークフロー（スケジューラ、権限、監視）や具体的なサンプルスクリプトを追記できます。どの部分を優先して詳述しましょうか？