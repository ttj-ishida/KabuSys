# KabuSys

日本株自動売買システムのライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、DuckDB スキーマ定義、品質チェック、監査ログなどを提供します。

※ 本 README はリポジトリ内のソースコードに基づいて作成しています。

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集・前処理・銘柄紐付け（SSRF/サイズ制限/トラッキング除去 等の安全対策）
- DuckDB を利用した三層データレイヤ（Raw / Processed / Feature）と Execution / Audit 層のスキーマ定義・初期化
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上の特徴：
- API レート制限（J-Quants：120 req/min）を守る固定間隔スロットリング
- 401 時はリフレッシュトークンで ID トークンを自動更新して再試行
- ETL/保存処理は冪等性（ON CONFLICT DO UPDATE / DO NOTHING) を考慮
- DuckDB をメインの永続化として使用（ファイル / :memory: 両対応）

---

## 主な機能一覧

- 環境設定読み込み（`.env` / `.env.local` 自動読み込み、OS 環境変数保護）
- J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レートリミット、最大リトライ、トークン自動リフレッシュを実装
- DuckDB スキーマ初期化（data.schema.init_schema）
- ETL パイプライン（data.pipeline.run_daily_etl）:
  - 市場カレンダー取得、株価差分取得、財務差分取得、品質チェック
- ニュース収集（data.news_collector.run_news_collection）:
  - RSS 取得、XML パース（defusedxml）、記事 ID 生成（URL 正規化 + SHA-256）、raw_news 保存、銘柄抽出・紐付け
- カレンダー管理（data.calendar_management）:
  - 営業日判定、前後営業日の取得、夜間カレンダー更新ジョブ
- データ品質チェック（data.quality）:
  - 欠損、重複、スパイク、日付不整合の検出
- 監査ログスキーマ、監査 DB 初期化（data.audit）

---

## 要件

- Python 3.10+
- 主要依存（最小）:
  - duckdb
  - defusedxml
- （利用環境に応じて追加の HTTP/Slack/KabuStation クライアント等が必要）

インストール例（開発環境）:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトに requirements.txt があれば:
# pip install -r requirements.txt
```

パッケージを編集可能モードでインストールする場合:
```bash
pip install -e .
```

---

## 環境変数 / 設定

KabuSys は .env ファイル（プロジェクトルートの .git または pyproject.toml を基準に探索）または OS 環境変数から設定を読み込みます。.env 自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主要な環境変数（必須は _require によってチェックされます）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL、デフォルト: INFO）

.env の読み込み順:
1. OS 環境変数（既存キーは保護）
2. .env（プロジェクトルート）
3. .env.local（.env を上書きする）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. Python 3.10+ を用意する
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` を作成し、必要な環境変数を設定
4. DuckDB スキーマを初期化する

DuckDB スキーマ初期化の例:
```python
from kabusys.data.schema import init_schema
# ファイル DB を作成・初期化
conn = init_schema("data/kabusys.duckdb")
# またはインメモリ
# conn = init_schema(":memory:")
```

監査ログ用 DB 初期化の例:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（代表的な例）

日次 ETL の実行（最小構成）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

差分 ETL（個別）:
```python
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
# conn は init_schema / get_connection の戻り値
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

ニュース収集の実行:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出のための有効コード集合（省略可）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)
```

J-Quants の直接呼び出し例:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token を指定せずに呼べばモジュールキャッシュを利用（自動リフレッシュ対応）
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
```

品質チェックだけを実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date.today())
for issue in issues:
    print(issue)
```

注意点:
- J-Quants API は 120 req/min の制限を設けているため、jquants_client は内部でスロットリングを行います。
- ネットワークエラーや 5xx は指数バックオフで最大 3 回リトライします。401 の場合は ID トークンを自動更新して 1 回リトライします。

---

## 主要モジュール / ディレクトリ構成

リポジトリの主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数 / 設定管理（.env 自動読み込み）
  - data/                 — データ関連モジュール
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 + 保存ロジック）
    - news_collector.py   — RSS ニュース収集・前処理・保存
    - schema.py           — DuckDB スキーマ定義・初期化
    - pipeline.py         — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py            — 監査ログ（シグナル→発注→約定のトレーサビリティ）
    - quality.py          — データ品質チェック
  - strategy/             — 戦略層（パッケージ：実装場所）
  - execution/            — 発注実行層（パッケージ：実装場所）
  - monitoring/           — 監視（パッケージ：実装場所）

各モジュールは docstring / コメントで設計方針と制約を明記しています。strategy / execution / monitoring はパッケージとして用意されていますが、具体的な実装は個別に追加してください。

---

## 運用上の注意

- 環境変数にはシークレット（API トークン等）を設定します。`.env` をリポジトリに含めないでください。
- DuckDB のファイルパスはデフォルトで data/ 下に作成されます。バックアップや権限に注意してください。
- ニュース収集では外部 URL を扱うため、SSRF 対策（実装済み）や最大受信サイズ制限が適用されていますが、運用環境ではプロキシ等と組み合わせて安全性確認を行ってください。
- ETL のスケジューリングは cron / Airflow / 他のワークフロー管理ツールで行うことを想定しています。run_daily_etl は再入可能で各ステップで例外を捕捉して続行しますが、監査ログやモニタリングを組み合わせて運用監視を行ってください。

---

## 開発・貢献

- コードはモジュール単位でユニットテストを追加してください。
- .env 自動読み込みはテストの邪魔になる場合があるため、テスト実行中は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。
- 依存パッケージのバージョン管理は pyproject.toml / requirements.txt を用いて行ってください（この README 作成時点では最小限の依存のみ記載しています）。

---

## 最後に

この README はソースコードの公開 API と設計コメントに基づき作成しました。実際の運用では API キー管理、ログ出力/監視、バックアップ/リカバリ設計、証券会社 API（kabuステーション）との接続フローの追加実装が必要になります。必要に応じて各モジュールの docstring を参照して詳細を確認してください。