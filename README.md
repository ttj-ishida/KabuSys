# KabuSys — 日本株自動売買システム

このリポジトリは「KabuSys」と呼ばれる日本株向けの自動売買／データ基盤ライブラリです。  
主に J-Quants API からの時系列・財務・カレンダーの取得、RSS によるニュース収集、DuckDB を使ったデータスキーマと ETL パイプライン、品質チェック、監査ログ用スキーマなどを提供します。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数（設定項目）
- 使い方（主要 API の例）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からのデータ取得（株価日足、財務四半期、JPX マーケットカレンダー）
- RSS フィードからのニュース収集と DuckDB への保存（冪等・SSRF対策・トラッキング除去）
- DuckDB を用いたデータスキーマの初期化 / 接続管理
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログスキーマ（signal → order → execution のトレーサビリティ）

設計の重点:
- 冪等性（ON CONFLICT / RETURNING 等を活用）
- API レート制限と堅牢なリトライ（ID トークン自動リフレッシュ含む）
- セキュリティ対策（RSS取得のSSRF対策・defusedxml利用・受信サイズ制限）
- テスト容易性（id_token 注入や .env 自動読み込みの無効化オプション等）

---

## 機能一覧

主な機能（モジュール毎）:

- kabusys.config
  - 環境変数を読み込み、Settings オブジェクトを提供
  - .env / .env.local の自動ロード（必要に応じて無効化可能）
  - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL の検証

- kabusys.data.jquants_client
  - get_id_token（リフレッシュトークンから idToken 取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - 内部で固定間隔の RateLimiter（120 req/min）・リトライ・401 自動リフレッシュ対応

- kabusys.data.news_collector
  - fetch_rss（RSS 取得、XML パース、前処理）
  - preprocess_text、URL 正規化・トラッキング除去、SHA-256 による記事ID生成
  - SSRF 対策（リダイレクト検査、プライベートIP拒否）、gzip/サイズ上限対策
  - save_raw_news / save_news_symbols（DuckDB へチャンク挿入・トランザクション）
  - run_news_collection（複数ソースの統合収集 + 銘柄抽出と紐付け）

- kabusys.data.schema
  - DuckDB 用の DDL をまとめて作成する init_schema / get_connection
  - Raw / Processed / Feature / Execution 層のテーブル・インデックス定義

- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル）
  - run_daily_etl（市場カレンダー取得 → 株価ETL → 財務ETL → 品質チェックの統合）
  - ETLResult クラスで結果を集約（品質問題・エラーの収集）

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチでJPXカレンダーを差分更新）

- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - QualityIssue データクラスを返す（severity: error / warning）

- kabusys.data.audit
  - 監査用スキーマ（signal_events, order_requests, executions）と初期化関数
  - 監査トレーサビリティのための制約・インデックス定義

---

## セットアップ手順

前提:
- Python 3.9+（型注釈や一部の標準挙動に依存）
- DuckDB（Python パッケージで利用）

1. リポジトリをクローン / 配布パッケージを取得
   - git clone …（省略）

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - 最低限必要な外部依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトで requirements.txt / pyproject.toml が提供されている場合はそれに従ってください）
   - 開発用には logging 等の設定やテスト用ツールを追加してください。

4. 環境変数設定
   - プロジェクトルートに `.env`（および任意で `.env.local`）を置くと、自動的に読み込まれます。
   - 自動読み込みを無効化する場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマ初期化
   - Python から init_schema() を呼んで DB を初期化します（例は次節）。

---

## 環境変数（設定項目）

主要な環境変数（Settings 経由で参照）:

必須:
- JQUANTS_REFRESH_TOKEN
  - J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（注文実行周りで利用想定）
- SLACK_BOT_TOKEN
  - Slack 通知に使う Bot トークン
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化

.example .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- .env の読み込みはプロジェクトルート（.git または pyproject.toml のある階層）を探索して行います。
- .env.local は .env の上書き用として優先度が高く扱われますが、OS 環境変数は保護されます。

---

## 使い方（主要 API と実行例）

以下は代表的な初期化 / ETL / ニュース収集の Python スニペット例です。

- DuckDB スキーマの初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 毎日の ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 省略時は今日が target_date、id_token はキャッシュを自動使用
print(result.to_dict())
```

- ニュース収集（RSS）を実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
# 既存の known_codes セットを渡して銘柄抽出を行うことが推奨
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # 各ソースごとの新規保存件数
```

- 監査ログスキーマを初期化（監査専用または既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema, init_audit_db
from kabusys.data.schema import init_schema
from kabusys.config import settings

# 既存 DB に監査テーブルを追加
conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)

# または監査専用 DB を作る
audit_conn = init_audit_db("data/audit.duckdb")
```

- J-Quants クライアントを直接使う（テストで id_token を注入する等）
```python
from kabusys.data import jquants_client as jq

# id_token を明示的に取得
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
prices = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB に保存する場合は save_daily_quotes(conn, prices)
```

注意点:
- jquants_client は内部でレート制御（120 req/min）とリトライを行います。
- 401 受信時は自動でリフレッシュトークンから id_token を再取得して 1 回リトライします。
- news_collector は defusedxml、SSRF対策、受信サイズ上限等の防御を組み込んでいます。

---

## ディレクトリ構成

リポジトリ内の主要なファイル / モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（fetch/save）
      - news_collector.py            — RSS ニュース収集・前処理・保存
      - schema.py                    — DuckDB スキーマ定義 / 初期化
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - calendar_management.py       — マーケットカレンダー管理関数
      - quality.py                   — データ品質チェック
      - audit.py                     — 監査ログスキーマ
    - strategy/                       — 戦略レイヤ（骨格）
      - __init__.py
    - execution/                      — 発注/実行レイヤ（骨格）
      - __init__.py
    - monitoring/                     — 監視関連（骨格）
      - __init__.py

上記以外にプロジェクトルートに .env.example / pyproject.toml / README.md（本ファイル）等を置く想定です。

---

## 開発上の注意・運用メモ

- DB 初期化は init_schema() を 1 回実行しておくこと（既存テーブルがある場合はスキップされる）。
- ETL は差分更新を行うため、最終取得日を DB から判定して余分な再取得を抑えます。バックフィルはデフォルトで直近数日を再取得して API の後出し修正を取り込みます。
- news_collector は記事 ID を正規化後の SHA256（先頭32文字）で生成し、冪等性を担保します。
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml により探索するため、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使うと便利です。
- ログレベルや KABUSYS_ENV による挙動差（live/paper_trading/development）に注意してください（Settings.is_live 等で判定可能）。

---

必要があれば以下も提供します:
- requirements.txt / pyproject.toml の推奨内容
- 具体的なサンプルスクリプト（cron 用・Dockerfile 用・CI 用）
- ETL 実行時のログ出力サンプルや品質チェックの出力例

ご希望があれば README に追記・拡張します。どの部分をより詳しく載せたいか教えてください。