# KabuSys

日本株向け自動売買・データプラットフォームライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。  
主に以下を提供します：

- J-Quants API からの市場データ（株価・財務・マーケットカレンダー）取得および DuckDB への永続化（冪等保存）
- RSS からのニュース収集とニュース⇄銘柄紐付け
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（営業日判定・前後営業日取得など）
- ETL（差分取得、バックフィル、品質検査）をまとめた日次パイプライン
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ初期化

設計上の重点は「安全性（SSRF対策、XMLパースの安全化）」「冪等性」「トレーサビリティ」「API レート制御・リトライ」などにあります。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存（save_daily_quotes 等、ON CONFLICT DO UPDATE）
- data/news_collector.py
  - RSS 取得・XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256）
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - raw_news / news_symbols への冪等保存
- data/schema.py / audit.py
  - DuckDB のスキーマ定義および初期化（Raw/Processed/Feature/Execution/Audit）
  - 監査ログ用スキーマ（信頼性の高いトレーサビリティ）
- data/pipeline.py
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分取得／バックフィル／品質チェックの組合せ
- data/calendar_management.py
  - 営業日判定、前後営業日取得、期間内営業日取得、夜間カレンダー更新ジョブ
- data/quality.py
  - 欠損・重複・スパイク・日付不整合チェック（QualityIssue を返す）
- config.py
  - .env（プロジェクトルートの .env / .env.local 自動読み込み）や環境変数管理
  - 必須値チェック（トークン類）や環境フラグ（KABUSYS_ENV 等）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法に `X | None` を使用しているため）
- duckdb, defusedxml などの依存パッケージ

例: 仮想環境作成と依存インストール

```bash
# 仮想環境作成（任意）
python -m venv .venv
source .venv/bin/activate

# pip アップデート
pip install -U pip

# 必要パッケージ（最低限）
pip install duckdb defusedxml
```

このリポジトリをプロジェクトとして使う場合（ソースを直接使う）
- プロジェクトルートに `src` がある構成なので、開発インストールが可能なら次を実行してください（setup 配置があれば）：
  ```
  pip install -e .
  ```
- もしパッケージ化されていない場合は、実行時に PYTHONPATH を設定するかプロジェクトルートからスクリプトを実行してください:
  ```
  PYTHONPATH=src python your_script.py
  ```

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動読み込みされます（テスト等で無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード
  - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
  - SLACK_CHANNEL_ID: Slack チャンネル ID
- 任意（デフォルトあり）:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/...
  - DUCKDB_PATH: データベースパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

注意: 秘密情報（トークン等）は .env を含めてバージョン管理に含めないでください。

---

## 使い方（簡単な例）

各例は Python REPL や小スクリプトとして実行できます。`src` を PYTHONPATH に含めるかパッケージインストール後に実行してください。

1) DuckDB スキーマ初期化

```python
from kabusys.data import schema

# ファイル DB を初期化
conn = schema.init_schema("data/kabusys.duckdb")
# or メモリ DB
# conn = schema.init_schema(":memory:")
```

2) 監査ログ専用 DB 初期化（audit 専用）

```python
from kabusys.data import audit

conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) J-Quants トークン取得（自動的に Settings からリフレッシュトークンを使用）

```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
print(id_token)
```

4) 日次 ETL 実行（市場カレンダー → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# 事前に init_schema() を呼んでおくこと（初回）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL（省略時は今日）
result = run_daily_etl(conn)
print(result.to_dict())
```

5) RSS ニュース収集ジョブ実行（既知銘柄セットがある場合は紐付け可能）

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")

# sources を省略するとデフォルトの RSS ソースを使用
# known_codes は銘柄コードセット（例: {"7203", "6758", ...}）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: 新規保存件数}
```

6) カレンダー夜間更新ジョブ

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved", saved)
```

7) 品質チェックを個別に実行

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

推奨 / 任意:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env の自動読み込みを無効化

.env.example を用意することで初期設定が容易になります（プロジェクトルートに配置）。

---

## セキュリティ上の注意

- .env ファイルにトークンを平文で保存する場合は取り扱いに注意してください。レポジトリにコミットしないでください。
- news_collector は SSRF 対策、XML の安全パース、レスポンスサイズ制限など多重防御を実装していますが、外部データを扱う点から運用時はログと例外監視を行ってください。
- J-Quants や証券会社 API の利用については各サービスの利用規約に従ってください（API レート制限に注意）。

---

## ディレクトリ構成

（src 配下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数と設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント / 保存ユーティリティ
    - news_collector.py            — RSS 取得・記事保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義と初期化
    - pipeline.py                  — ETL パイプライン（差分更新・バックフィル・品質チェック）
    - calendar_management.py       — マーケットカレンダー管理（営業日判定など）
    - audit.py                     — 監査ログスキーマ初期化
    - quality.py                   — データ品質チェック
  - strategy/
    - __init__.py                  — 戦略関連（拡張用のエントリ）
  - execution/
    - __init__.py                  — 発注/ブローカー連携のためのプレースホルダ
  - monitoring/
    - __init__.py                  — 監視・メトリクス関連（拡張用）

上記ファイルはモジュール単位で責務を分離しており、運用ツール（ETL ジョブ、ニュース収集バッチ、発注エンジン、監査 DB 初期化など）を個別に組み合わせて利用できます。

---

## 開発者向けメモ

- Python 型注釈は 3.10+ 構文を使用しています（X | None 等）。
- DuckDB を用いるため、大量データの分析や検索が速く、SQLite より分析処理に向きます。
- jquants_client は内部で固定間隔のレートリミッタとリトライロジックを持っています（120 req/min を想定）。
- テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます。
- 単体テスト時は jquants_client._urlopen / news_collector._urlopen 等をモックすることで外部通信を遮断できます。

---

必要であれば、README に以下を追加できます：
- .env.example のサンプル
- 実運用時の Systemd / cron / Airflow によるスケジューリング例
- 具体的な CI/CD / テストの実行手順

追加したい内容があれば教えてください。