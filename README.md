# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants API / RSS 等からデータを取得して DuckDB に蓄積し、ETL・品質チェック・カレンダー管理・監査ログ等の基盤機能を提供します。

バージョン: kabusys.__version__ = 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API からの市場データ（株価日足・四半期財務・JPX カレンダー）取得と保存
- RSS からのニュース収集と銘柄紐付け
- DuckDB によるデータスキーマ（Raw / Processed / Feature / Execution / Audit）の初期化
- ETL パイプライン（差分取得・バックフィル・品質チェック）の実装
- 市場カレンダー管理（営業日判定・前後営業日取得など）
- 監査ログ（シグナル→発注→約定のトレース）用スキーマ

設計上のポイント:
- API のレート制限・retry（指数バックオフ）・トークン自動リフレッシュを備えたクライアント
- データの冪等保存（ON CONFLICT）を前提とした実装
- Look-ahead bias 回避のため取得日時を UTC で記録
- RSS 収集時の SSRF 対策・XML 脆弱性対策・受信サイズ制限

---

## 主な機能一覧

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - API レート制御（120 req/min）、リトライ、401時トークンリフレッシュ対応
- data.news_collector
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化、トラッキングパラメータ除去、SSRF 対策、データ大小チェック
- data.schema
  - init_schema(db_path) / get_connection(db_path)
  - Raw / Processed / Feature / Execution 各層のテーブル作成
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
  - 差分更新・バックフィル・品質チェック統合
- data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - QualityIssue 型による問題収集（error / warning 判定）
- data.audit
  - init_audit_schema / init_audit_db（監査ログ用スキーマ）

その他:
- 環境設定管理: kabusys.config.settings（.env の自動読み込みをサポート）
- パッケージルート検出に基づく .env / .env.local 自動ロード（必要に応じ無効化可）

---

## 必要条件（推奨）

- Python 3.10+（型注釈に Union | を利用）
- 依存主要ライブラリ（例）
  - duckdb
  - defusedxml

推奨インストール例:
```bash
python -m pip install duckdb defusedxml
# またはプロジェクトとして配布する場合:
pip install -e .
```

（実際の requirements.txt はプロジェクトルートに追加してください）

---

## 環境変数 / .env

kabusys は .env（および .env.local）を自動で読み込みます（優先度: OS 環境 > .env.local > .env）。  
自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト用途など）。

必須となる環境変数（Settings クラスで参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

その他（デフォルトあり）:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用データベース）パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読込を無効化（値があると無効）

例 (.env):
```
JQUANTS_REFRESH_TOKEN="hogehoge_refresh_token"
KABU_API_PASSWORD="kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # または
   pip install -e .
   ```
3. .env を作成して必要な環境変数を設定
4. DuckDB スキーマ初期化
   - Python から:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     ```
   - またはメモリ DB でテスト:
     ```python
     conn = init_schema(":memory:")
     ```

5. 監査スキーマを追加する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（代表例）

最低限の ETL 実行フロー例:

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# DB 初期化（初回）
conn = init_schema(settings.duckdb_path)

# 日次 ETL を実行（id_token を注入することも可能）
result = run_daily_etl(conn)
print(result.to_dict())
```

ニュース収集ジョブ（RSS → raw_news 保存）:

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 既知銘柄コードセットを渡すと、抽出した4桁コードで紐付けも行う
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: new_saved_count, ...}
```

カレンダーの夜間更新ジョブ:

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
saved = calendar_update_job(conn)
print("saved:", saved)
```

J-Quants トークン取得（例: テストで直接取得）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

品質チェック（ETL 実行後）:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

監査ログスキーマ初期化（audit 専用 DB）:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 注意点 / 実装上の留意事項

- J-Quants クライアントは 120 req/min のレート制限を想定しており、内部的にスロットリングを行います。長時間の大量リクエストは考慮してください。
- HTTP エラー（408/429/5xx）は指数バックオフで最大 3 回リトライします。401 は refresh token による自動リフレッシュを一度試行します。
- データ保存処理は冪等（ON CONFLICT DO UPDATE / DO NOTHING）です。再実行での上書きを基本に設計されています。
- RSS の XML パースには defusedxml を使い XML 関連の脆弱性を軽減しています。HTTP/リダイレクト先の検査や受信バイト数制限も実装されています。
- DuckDB の日付/タイムスタンプの取り扱いに注意してください（UTC での取得日時保存等）。
- settings の .env 自動読み込みはプロジェクトルート (.git または pyproject.toml を基準) を探します。CI/テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       - 環境変数 / 設定管理
    - data/
      - __init__.py
      - schema.py                     - DuckDB スキーマ定義・初期化
      - jquants_client.py             - J-Quants API クライアント
      - pipeline.py                   - ETL パイプライン
      - news_collector.py             - RSS ニュース収集・保存
      - calendar_management.py        - マーケットカレンダー管理
      - quality.py                    - データ品質チェック
      - audit.py                      - 監査ログスキーマ
    - strategy/
      - __init__.py                    # 戦略関連モジュール（拡張箇所）
    - execution/
      - __init__.py                    # 発注/ブローカ連携モジュール（拡張箇所）
    - monitoring/
      - __init__.py                    # 監視・通知周り（拡張箇所）

この README はプロジェクトの概要と主要な利用方法をまとめたものです。各モジュールの詳細な API や追加の運用手順（cron/jupyter/コンテナ化・CI での運用等）は、別ドキュメントやコード内の docstring を参照してください。質問や補足があればお知らせください。