# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants や kabuステーション 等の外部 API からデータを収集し、DuckDB で管理、ETL・品質チェック・ニュース収集・監査ログなどの機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持ったモジュール群です。

- J-Quants API から株価（日足）・財務データ・マーケットカレンダーを取得して DuckDB に保存
- RSS からニュースを収集して正規化・DB保存、銘柄との紐付け
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定など）
- 監査ログ（シグナル→発注→約定のトレース用テーブル群）
- 設定は環境変数／.env により管理

設計上のポイント：
- API レート制限や再試行（リトライ）を考慮
- レコード保存は冪等（ON CONFLICT）で二重保存を防止
- ニュース収集は SSRF・XML Bomb 等の攻撃対策を実装
- 品質チェックで欠損・スパイク・重複・日付不整合を検出

---

## 主な機能一覧

- jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_daily_quotes / save_financial_statements / save_market_calendar
  - レート制限・指数バックオフ・401 自動リフレッシュ対応
- data.schema
  - DuckDB のスキーマ定義と初期化（raw / processed / feature / execution 層）
  - init_schema(db_path) で初期化
- data.pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次 ETL の一括実行 run_daily_etl
- data.news_collector
  - RSS 取得・前処理・記事保存（save_raw_news）・銘柄紐付け（save_news_symbols）
  - SSRF 対策、受信サイズ制限、記事IDは正規化 URL の SHA-256（先頭32文字）
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチでカレンダー差分更新）
- data.quality
  - 欠損・スパイク・重複・日付不整合チェック（run_all_checks）
- data.audit
  - 監査ログ用テーブル群と初期化（init_audit_schema / init_audit_db）

---

## 動作環境 / 必要パッケージ

（実プロジェクトでは requirements.txt を用意してください。ここでは主要依存を示します）

- Python 3.10+
- duckdb
- defusedxml

pip 例:
```
pip install duckdb defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／展開

2. Python 仮想環境を作成・有効化（任意）
```
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

3. 必要パッケージをインストール
```
pip install duckdb defusedxml
```

4. 環境変数を用意する（.env 推奨）
- プロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化します）。
- 必須の環境変数（Settings で `_require` されるもの）:

例 `.env`:
```
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=あなたの_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
# 任意:
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO           # DEBUG|INFO|WARNING|ERROR|CRITICAL
```

5. DB スキーマ初期化（DuckDB）
Python REPL やスクリプトで:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH の値または default を参照
conn = init_schema(settings.duckdb_path)
```

6. 監査ログテーブルの初期化（必要に応じて）
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema で得た接続
init_audit_schema(conn, transactional=True)
# または独立した監査用DB
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な例）

- J-Quants トークン取得（内部で settings の JQUANTS_REFRESH_TOKEN を使用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

- 指定期間の株価取得（API からの生データ取得、返り値は dict リスト）
```python
from kabusys.data.jquants_client import fetch_daily_quotes
from datetime import date
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 取得データを DuckDB に保存（init_schema で作成した conn を渡す）
```python
from kabusys.data.jquants_client import save_daily_quotes
saved_count = save_daily_quotes(conn, records)
```

- 日次 ETL を一括実行（カレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS からニュースを収集して保存・銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection
known_codes = {"7203", "6758"}  # 既知の銘柄コードセット
res = run_news_collection(conn, sources=None, known_codes=known_codes)
# res は {source_name: 新規保存件数} の辞書
```

- カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_trading = is_trading_day(conn, date(2026, 3, 17))
next_day = next_trading_day(conn, date(2026, 3, 17))
```

- 品質チェック（ETL 後に run_daily_etl 内で実行されるが個別にも可能）
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None, reference_date=None)
for i in issues:
    print(i)
```

---

## 設定（環境変数）

主要な環境変数一覧（Settings クラスにより取得）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（1 を設定）

.env の読み込み順: OS 環境 > .env.local > .env（プロジェクトルートは .git または pyproject.toml を基準に探索）

---

## ディレクトリ構成

（主要ファイル・モジュールの一覧と簡単な説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロードの実装と検証）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
    - news_collector.py
      - RSS 収集、前処理、記事保存、銘柄抽出と紐付け
    - schema.py
      - DuckDB スキーマ定義（Raw / Processed / Feature / Execution）と init_schema
    - pipeline.py
      - ETL パイプライン（差分取得、バックフィル、品質チェック、run_daily_etl）
    - calendar_management.py
      - マーケットカレンダー管理、営業日判定 / update_job
    - audit.py
      - 監査ログ（signal / order_request / executions）テーブル初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - strategy/
    - __init__.py  （戦略関連の拡張ポイント）
  - execution/
    - __init__.py  （発注・約定・ポジション管理の拡張ポイント）
  - monitoring/
    - __init__.py  （監視・アラート用の拡張ポイント）

---

## 開発上の注意点 / 実運用に向けて

- settings.env の管理は慎重に（シークレットは直接コミットしない）
- DuckDB はスキーマ変更に注意。テーブルは既存のデータを前提に設計されているため、DDL 変更時のマイグレーションを計画すること
- J-Quants API のレート制限（120 req/min）を順守する実装が組み込まれていますが、長時間のバックフィルなどは運用で調整してください
- ニュース収集は外部 URL を扱うため SSRF/大容量攻撃に対する保護を実装していますが、運用ネットワークポリシーにも注意してください
- ETL は部分的失敗を許容してログに記録する設計です。重要なエラーはログ／通知で監視してください

---

README のサンプル利用例や追加の使い方が必要であれば、利用シナリオ（例: 定期バッチの systemd / cron 設定、Slack 通知の統合、戦略の雛形）を教えてください。必要に応じてサンプルスクリプトを提供します。