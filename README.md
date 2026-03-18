# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants や RSS などから市場データ・ニュースを取得し、DuckDB に保存して ETL・品質チェック・監査用スキーマを提供します。戦略・発注・監視モジュールの基盤実装を含み、後続の自動売買ロジックや監視ツールの土台として利用できます。

バージョン: 0.1.0

---

## 主な概要

- J-Quants API を用いた株価（OHLCV）、財務（四半期 BS/PL）、JPX カレンダーの取得
- RSS フィードからのニュース収集と記事の正規化・銘柄紐付け
- DuckDB ベースのスキーマ定義（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）スキーマ
- 環境変数 / .env からの設定ロード（自動読み込み機能あり）

設計のポイント:
- API レート制御、リトライ（指数バックオフ）、トークン自動リフレッシュ
- Look-ahead bias 防止のため fetched_at を UTC で記録
- DuckDB への保存は冪等（ON CONFLICT）で実装
- RSS 収集は SSRF / XML Bomb / gzip bomb 等の安全対策あり

---

## 機能一覧

- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - レートリミッタ、リトライ、トークンキャッシュ実装

- data.news_collector
  - RSS フィード取得（SSRF 対策、gzip 対応、受信サイズ制限）
  - URL 正規化・記事ID（SHA-256 ハッシュ）生成
  - raw_news / news_symbols への保存（トランザクション・チャンク挿入）
  - 銘柄コード抽出（4桁）と紐付け

- data.schema
  - DuckDB の全スキーマ（Raw / Processed / Feature / Execution / Audit）作成
  - init_schema / get_connection

- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー取得 → 株価 → 財務 → 品質チェック
  - 差分更新・バックフィル対応（既存最終日を基準に再フェッチ）

- data.calendar_management
  - 営業日判定・前後営業日の取得、カレンダー更新バッチ

- data.quality
  - 欠損 / スパイク / 重複 / 日付不整合のチェックと QualityIssue レポート

- data.audit
  - 監査用テーブル初期化（signal_events, order_requests, executions）
  - UTC 固定、インデックス定義

---

## 必要条件

- Python 3.10+
- 以下の主要依存パッケージ（例示）
  - duckdb
  - defusedxml
- 標準ライブラリの urllib, logging 等を利用

（実プロジェクトでは pyproject.toml / requirements.txt を用意して pip install してください）

---

## 環境変数（必須 / 任意）

アプリ設定は環境変数またはプロジェクトルートの .env / .env.local から自動読み込みされます（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須 (Settings._require により未設定だと例外):
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabuAPI の base URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH — DuckDB ファイルパス (default: data/kabusys.duckdb)
- SQLITE_PATH — SQLite（監視等）ファイルパス (default: data/monitoring.db)
- KABUSYS_ENV — 環境 (development | paper_trading | live, default: development)
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL, default: INFO)

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
2. 仮想環境作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （実プロジェクトでは pip install -e . または pip install -r requirements.txt を利用）
4. 環境変数を設定（.env をプロジェクトルートに配置）
5. DuckDB スキーマ初期化（次節参照）

※ 自動で .env を読み込む仕組みがありますが、テスト時に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## データベース初期化

DuckDB スキーマの初期化:

Python REPL またはスクリプトで:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可

監査ログ専用 DB の初期化:

from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")

既存 DB に接続するだけなら:

from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")

---

## 基本的な使い方（例）

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())

- J-Quants から株価を直接取得する例

from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
# DuckDB へ保存する場合は save_daily_quotes を使う

- RSS 収集・保存（ニュースコレクタ）

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に取得した有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}

- カレンダー操作例

from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
is_trading = is_trading_day(conn, date(2026, 3, 15))

- 品質チェックを個別に実行

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

---

## 開発向けメモ / 挙動の注意点

- 自動 env 読み込み:
  - package の import 時にプロジェクトルートを探索して .env, .env.local を読み込みます。
  - テストなどでこれを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み込み優先度: OS 環境 > .env.local > .env。.env.local は override=True のため OS の既存変数は保護されます。

- J-Quants クライアント:
  - レート制限は 120 req/min（固定間隔スロットリング）で制御されます。
  - 401 を受けた場合はリフレッシュトークンで自動で id_token を取得して 1 回だけリトライします。
  - ページネーション対応。取得時に fetched_at を UTC で付与して保存します。

- ニュース収集:
  - URL は正規化してトラッキングパラメータを削除。記事 ID は正規化 URL の SHA-256（先頭32文字）。
  - SSRF 対策としてリダイレクト先や最終ホストのプライベート IP をチェックします。
  - レスポンスサイズは MAX_RESPONSE_BYTES (10MB) で制限し、gzip 展開後も検査します。

- DuckDB スキーマ:
  - スキーマは冪等。init_schema は必要なテーブルとインデックスを作成します。
  - audit.init_audit_db は UTC に TimeZone を固定して監査スキーマを作成します。

---

## よくある操作コマンド（テンプレート）

- 仮想環境作成・依存インストール（例）

python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml

- スキーマ初期化と日次ETL（簡易スクリプト）

#!/usr/bin/env python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
conn = init_schema("data/kabusys.duckdb")
res = run_daily_etl(conn)
print(res.to_dict())

---

## ディレクトリ構成

プロジェクトの主要ファイル・ディレクトリ（抜粋）:

src/
  kabusys/
    __init__.py                 # パッケージ情報
    config.py                   # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py         # J-Quants クライアント（取得・保存）
      news_collector.py         # RSS ニュース収集・保存
      schema.py                 # DuckDB スキーマ定義・初期化
      pipeline.py               # ETL パイプライン（日次 ETL 等）
      calendar_management.py    # カレンダー管理（営業日判定・更新ジョブ）
      audit.py                  # 監査ログ（トレーサビリティ）初期化
      quality.py                # データ品質チェック
      pipeline.py
    strategy/                    # 戦略関連（未実装のエントリポイント）
      __init__.py
    execution/                   # 発注・ブローカー統合（未実装のエントリポイント）
      __init__.py
    monitoring/                  # 監視・アラート（未実装のエントリポイント）
      __init__.py

README.md（本ファイル）
pyproject.toml / setup.cfg（プロジェクト設定; 存在すればルート探索で自動 .env 読み込みに使われます）

---

必要があれば、README により具体的な使用例（cron や Airflow でのスケジューリング例、Slack 通知の統合方法、kabuステーション API 統合の実装例など）を追加できます。どの部分を詳しく書けばよいか教えてください。