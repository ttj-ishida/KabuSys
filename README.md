# KabuSys

日本株向け自動売買基盤（データ収集・ETL・監査・実行基盤の骨組み）  
このリポジトリは J-Quants や RSS 等からデータを取得して DuckDB に保存し、戦略層・実行層のためのデータ基盤を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買システムのデータ基盤とユーティリティを集めたパッケージです。主な目的は以下です。

- J-Quants API から株価日足・財務データ・マーケットカレンダーを取得して DuckDB に保存
- RSS からニュース記事を収集し前処理して保存、銘柄紐付け
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ定義
- 実行（kabuステーション等）や戦略を差し込むための基盤モジュール群

設計方針としては「冪等性」「リトライとレート制御」「Look-ahead Bias の防止」「SSRF や XML bomb 等のセキュリティ対策」を重視しています。

---

## 主な機能一覧

- J-Quants API クライアント（認証・リトライ・レートリミット・ページネーション対応）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークンからの ID トークン取得）
  - 保存用ユーティリティ（DuckDB へ ON CONFLICT DO UPDATE で保存）
- RSS ニュース収集モジュール
  - fetch_rss：SSRF/大容量対策・gzip 解凍・XML パース安全化
  - save_raw_news / save_news_symbols：DuckDB へ冪等保存（INSERT ... RETURNING）
  - 記事 ID の正規化（URL 正規化 → SHA-256 先頭 32 文字）
  - 銘柄抽出（テキスト中の 4 桁銘柄コード抽出）
- DuckDB スキーマ定義・初期化（data.schema.init_schema）
  - Raw / Processed / Feature / Execution / Audit の各レイヤー
- ETL パイプライン（差分取得・バックフィル・品質チェック）
  - run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ（signal_events / order_requests / executions）初期化ユーティリティ
- 環境設定（.env/.env.local 自動読み込み、Settings クラス）

---

## 動作要件

- Python 3.9+（型注釈に union 演算子等を使用）
- 必要な主なパッケージ:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）
- J-Quants リフレッシュトークンや証券 API の資格情報

（実際の pyproject.toml/requirements.txt に合わせて依存を追加してください）

---

## インストール（開発環境）

例:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Unix/macOS) / .venv\Scripts\activate (Windows)

2. インストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - pip install -e .  # パッケージ化されている場合

※ pyproject.toml / setup.cfg がある前提。無ければ必要なモジュールを個別に pip install してください。

---

## 環境変数 / .env

パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（優先順位: OS 環境 > .env.local > .env）。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

例 `.env.example`（README 用サンプル）:

KABUSYS_DISABLE_AUTO_ENV_LOAD=0
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（DB 初期化）

DuckDB スキーマを初期化するには data.schema.init_schema を使います。Python REPL やスクリプトで実行できます。

例:

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

監査ログテーブルだけ別に初期化する場合:

from kabusys.data import schema, audit
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)

既存 DB に接続するだけなら:

from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")

---

## 使い方（主要 API の例）

1) 設定にアクセスする

from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)

2) J-Quants トークン取得 / データ取得

from kabusys.data import jquants_client as jq

# id_token を自動で取得（内部でリフレッシュ・キャッシュされる）
id_token = jq.get_id_token()  # または settings.jquants_refresh_token を利用

# 日足取得（ページネーション対応）
records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)

# DuckDB に保存（init_schema で作成した conn を渡す）
import duckdb
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)

3) ニュース収集（RSS）

from kabusys.data import news_collector as nc
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# 単一ソースのフェッチ
articles = nc.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = nc.save_raw_news(conn, articles)

# まとめて収集 + 銘柄紐付け（known_codes は set('7203', '6758', ...)）
results = nc.run_news_collection(conn, sources=None, known_codes=known_codes_set)

4) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）

from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())

5) 品質チェックを個別に実行

from kabusys.data import quality
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)

---

## 注意・設計上のポイント

- J-Quants: API レート制限 120 req/min を内部で固定間隔スロットリング（RateLimiter）で守ります。
- 認証: get_id_token はリフレッシュトークンを使い ID トークンを取得。401 受信時は自動リフレッシュして再試行します（1 回のみ）。
- ETL: 差分更新と backfill（デフォルト 3 日）を組み合わせ、後出し修正に対処します。
- ニュース収集: URL 正規化、トラッキングパラメータ除去、SSRF 対策、XML 安全パーサ defusedxml を使用しています。大きなレスポンスは拒否（最大 10 MB）。
- DuckDB 保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を使います。
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。CI やテストで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ディレクトリ構成

src/kabusys/
- __init__.py
- config.py                — 環境設定・Settings クラス（.env 自動ロード等）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（取得/保存ロジック）
  - news_collector.py      — RSS 取得・前処理・保存・銘柄抽出
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - schema.py              — DuckDB スキーマ定義・初期化
  - audit.py               — 監査ログ（signal/events/orders/executions）初期化
  - quality.py             — データ品質チェック
  - pipeline.py
- strategy/
  - __init__.py            — (戦略実装のプレースホルダ)
- execution/
  - __init__.py            — (発注周りのプレースホルダ)
- monitoring/
  - __init__.py            — (監視/メトリクス用プレースホルダ)

主要なファイル:
- src/kabusys/data/jquants_client.py
- src/kabusys/data/news_collector.py
- src/kabusys/data/schema.py
- src/kabusys/data/pipeline.py
- src/kabusys/config.py

---

## テスト・デバッグのヒント

- 環境変数読み込みをスキップしたいとき:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- DuckDB をメモリ上で使いたい:
  - schema.init_schema(":memory:")
- news_collector の外部ネットワーク呼び出しをテストで差し替えるには、kabusys.data.news_collector._urlopen をモックしてください（ドキュメント内で想定）。
- ログレベルは LOG_LEVEL 環境変数で制御します。

---

この README はコードベース（src/kabusys 以下）の現状を要約したものです。実運用の前にセキュリティ・認証・エラーハンドリング・監査要件を必ずレビューし、必要に応じて証券会社の API 実装（execution 層）を追加してください。質問や追加したい説明があれば教えてください。