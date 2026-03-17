# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。J-Quants / kabuステーション 等の外部APIからデータを取得して DuckDB に格納し、ETL・品質チェック・ニュース収集・監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を含みます。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に格納
- RSS ベースのニュース収集と記事 → 銘柄紐付け
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- DuckDB 上のスキーマ定義（Raw / Processed / Feature / Execution 層）
- 発注・約定の監査ログ（監査用スキーマの初期化）

設計上のポイント:
- API レート制限・リトライ・トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB への保存は冪等（ON CONFLICT）で実装
- RSS 収集は SSRF・XML Bomb・Gzip Bomb 等の防御を考慮
- ETL は差分更新と品質チェックを段階的に実行

---

## 主な機能一覧

- J-Quants クライアント
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - レートリミット、リトライ、トークン自動更新対応
- DuckDB スキーマ管理
  - init_schema(db_path), get_connection(db_path)
  - Raw / Processed / Feature / Execution 層のテーブルとインデックスを作成
- ETL パイプライン
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分 + backfill）
- データ品質チェック
  - check_missing_data(), check_spike(), check_duplicates(), check_date_consistency()
  - run_all_checks() によりまとめて実行
- ニュース収集
  - fetch_rss(), save_raw_news(), save_news_symbols(), run_news_collection()
  - URL 正規化・トラッキング除去・記事ID のハッシュ化、SSRF 対策、受信サイズ制限
- 監査ログ（監査スキーマ初期化）
  - init_audit_schema(conn), init_audit_db(db_path)

---

## 前提・依存

- 推奨 Python バージョン: 3.10+
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

プロジェクトに setup/requirements があればそちらを使用してください。手早く試すには:

pip install duckdb defusedxml

またはローカル開発時はパッケージを editable インストール:

pip install -e .

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。プロジェクトルートはこのパッケージファイルから上位ディレクトリを探索して `.git` または `pyproject.toml` を見つけて決定します。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

重要な環境変数:

- J-Quants / API
  - JQUANTS_REFRESH_TOKEN (必須)
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (省略可, デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- DB パス
  - DUCKDB_PATH (省略時: data/kabusys.duckdb)
  - SQLITE_PATH (省略時: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO

設定はコード内で `from kabusys.config import settings` 経由で取得できます（例: settings.jquants_refresh_token）。

---

## セットアップ手順

1. Python 環境を準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb defusedxml

3. パッケージをインストール（開発時）
   - pip install -e .

4. 環境変数を設定（`.env` を作成）
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD を使えば無効化可）。
   - 例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - KABUSYS_ENV=development

5. DuckDB スキーマ初期化
   - 以下を実行して DB を初期化します（ファイルパスは settings.duckdb_path を参照してもよい）:

Python 例:
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

この時、親ディレクトリがなければ自動作成されます。

---

## 使い方（サンプル）

- J-Quants トークンを手動で取得（テスト等）

from kabusys.data import jquants_client as jq
token = jq.get_id_token()  # settings.jquants_refresh_token を使って id_token を取得

- 日次 ETL 実行

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)
print(result.to_dict())  # ETL 結果の辞書化

- ニュース収集ジョブ実行

from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes に有効銘柄コードのセットを渡すと銘柄紐付けを試みます
res = run_news_collection(conn, known_codes={"7203","6758"})
print(res)  # {source_name: 新規保存件数, ...}

- 監査スキーマの初期化（既存の DuckDB 接続に追加）

from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)

- 品質チェックを個別に実行

from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)

注意点:
- run_daily_etl は内部で market_calendar を先に更新し、営業日判定の後で株価等を取得します。
- ETL は各ステップで例外を捕捉し、可能な限り残りの処理を継続します。ETLResult にエラー情報が格納されます。

---

## テスト・デバッグのヒント

- 環境変数の自動読み込みを無効化:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- テスト用にメモリ上の DuckDB を使う:
  - conn = init_schema(":memory:")
- news_collector 内のネットワーク呼び出しは _urlopen をモックして置き換え可能（ユニットテスト向け）

---

## ディレクトリ構成

リポジトリ（src 配下）の主要ファイル/モジュール:

- src/kabusys/
  - __init__.py  -- パッケージ初期化（__version__ = "0.1.0"）
  - config.py    -- 環境変数読み込み・Settings クラス（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py    -- RSS 取得・前処理・DB 保存・銘柄抽出
    - pipeline.py          -- ETL パイプライン（差分取得・backfill・品質チェック）
    - schema.py            -- DuckDB スキーマ定義と init_schema / get_connection
    - audit.py             -- 監査ログ（signal/order/execution）スキーマ初期化
    - quality.py           -- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py  -- 戦略関連のエントリポイント（現状空）
  - execution/
    - __init__.py  -- 発注/執行関連のエントリポイント（現状空）
  - monitoring/
    - __init__.py  -- モニタリング機能のエントリポイント（現状空）

---

## 追加ノート

- このリポジトリはデータ取得→保存→品質確認→監査ログまでの「データプラットフォーム」層を重視しています。実トレードの実行（kabuステーションとの注文送信・約定管理）は execution / strategy 層で拡張する想定です。
- セキュリティ上の配慮（トークン管理、SSRF対策、XML/圧縮爆弾対策等）を各モジュールで取り入れていますが、本番運用前に十分なレビューと実データでの検証を行ってください。

---

もし README に追加したい使用例（CLI スクリプト、Docker 構成、CI 設定など）があれば教えてください。必要に応じてサンプル .env.example も作成します。