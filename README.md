# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。J-Quants や kabuステーション 等の外部 API からデータを取得して DuckDB に保存し、ETL（差分取得・品質チェック）、ニュース収集、監査ログ管理、実行・戦略層の土台となる機能群を提供します。

主な設計方針は「冪等性」「トレーサビリティ」「安全な外部通信（SSRF 対策等）」「API レート制御」「テスト容易性」です。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境変数（設定）
- 使い方（クイックスタート）
  - DB スキーマ初期化
  - 日次 ETL 実行
  - ニュース収集ジョブ
  - 監査ログ初期化
  - J-Quants API の利用（トークン取得・データ取得）
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤向けに設計された Python ライブラリです。  
主な目的は以下です。

- J-Quants API からの市場データ（株価日足・財務・マーケットカレンダー）取得と DuckDB への保存（冪等）。
- RSS からのニュース収集と記事の正規化・DB 保存、銘柄コード抽出による紐付け。
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）の提供。
- 監査ログ（シグナル → 発注 → 約定 のトレース）用スキーマとユーティリティ。
- 実行（execution）と戦略（strategy）層のための名前空間（拡張用）。

---

## 機能一覧

- 環境設定の自動ロード（.env / .env.local、プロジェクトルート検出）
- J-Quants クライアント
  - id_token の自動リフレッシュ
  - レート制御（120 req/min の固定間隔スロットリング）
  - リトライ（指数バックオフ、特定ステータスでの再試行）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（save_*、ON CONFLICT を用いた冪等保存）
- ニュース収集モジュール
  - RSS 取得・XML パース（defusedxml による安全処理）
  - URL 正規化・トラッキングパラメータ除去
  - SSRF 回避（スキーム検証／リダイレクト先のプライベートアドレス検出）
  - 保存（raw_news, news_symbols）でのトランザクション管理、INSERT ... RETURNING による実際の挿入結果取得
- DuckDB スキーマ（Raw / Processed / Feature / Execution 層）
  - テーブル定義・インデックス定義、init_schema による初期化
- ETL パイプライン
  - 差分取得（最終取得日をもとに自動で date_from を決定）
  - backfill による後出し修正吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - run_daily_etl による一括実行
- カレンダー管理（営業日判定、次/前営業日の取得、夜間更新ジョブ）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## 前提・依存関係

- Python 3.10 以上（型記法で | が使われているため）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging, hashlib, re, socket, ipaddress など

インストールは環境に応じて requirements を用意して実行してください。最低限の例:

pip install duckdb defusedxml

（プロジェクト配布パッケージがある場合は pip install -e . を想定）

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements があれば）
   - もしくは最低限: pip install duckdb defusedxml
4. 環境変数を設定（.env または OS 環境変数）
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（デフォルト）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. DuckDB スキーマを初期化（下記クイックスタート参照）

---

## 環境変数（設定項目）

kabusys.config.Settings で取得される主な環境変数：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 値: development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

注意:
- .env の自動読み込みはプロジェクトルート（.git か pyproject.toml の存在）を基準に行われます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動読み込みを無効化するには: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（クイックスタート）

以下は基本的な操作例です。Python REPL やスクリプトから実行できます。

1) スキーマ初期化（DuckDB にテーブルを作成）
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイル DB。":memory:" でインメモリ可
```

2) 日次 ETL の実行（市場カレンダー、株価、財務、品質チェックを順に実行）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS 取得 → raw_news へ保存 → 銘柄紐付け）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄コードのセット（例: {"7203", "6758", ...}）
known_codes = {"7203", "6758"}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # ソース名 -> 新規保存件数
```

4) 監査ログスキーマの初期化（既存 connection に監査テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

5) J-Quants API を直接使う例（id_token 取得・日足取得）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN が必要
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

---

## 主要モジュールの説明（簡易）

- kabusys.config
  - 環境変数読み込み、Settings クラスを通じた取得。
  - 自動 .env ロード、必須チェック（_require）。
- kabusys.data.jquants_client
  - J-Quants API 通信（認証、自動リフレッシュ、リトライ、レート制御）。
  - fetch_* 系、save_* 系（DuckDB への冪等保存）。
- kabusys.data.news_collector
  - RSS 取得、記事正規化、ID 生成、SSRF 対策、DuckDB への保存と銘柄紐付け。
- kabusys.data.schema
  - データベース DDL（Raw / Processed / Feature / Execution 層）と init_schema。
- kabusys.data.pipeline
  - 差分 ETL、日次パイプライン（run_daily_etl）と各 ETL ジョブ実装。
- kabusys.data.calendar_management
  - market_calendar を利用した営業日判定や夜間更新ジョブ。
- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）。
- kabusys.data.audit
  - 監査ログ用スキーマ定義と初期化。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - schema.py
      - calendar_management.py
      - quality.py
      - audit.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

---

## 注意事項 / 設計上のポイント

- 冪等性
  - API からの取得は重複保存を許容しない設計（ON CONFLICT DO UPDATE / DO NOTHING）。
- トレーサビリティ
  - 監査テーブル群でシグナル→発注→約定まで追跡可能に設計。
- セキュリティ
  - RSS の XML パースは defusedxml を使用。
  - ニュース収集ではスキーム検証、リダイレクト先のプライベートホスト拒否、受信サイズ上限など SSRF や DoS 緩和を実装。
- API レート制御
  - J-Quants へのリクエストは固定間隔でスロットリング（120 req/min 相当）する RateLimiter を搭載。
- 自動 .env ロード
  - プロジェクトルート（.git か pyproject.toml が目印）から .env を自動読み込みします。テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用。
- 環境（KABUSYS_ENV）に応じた挙動
  - development / paper_trading / live を区別するフラグがあり、実行時に挙動を分けられます。

---

貢献・開発
- 追加機能（戦略の実装、実注文送信の execution 層、モニタリング機構など）は strategy/ と execution/ に実装してください。
- テストでは .env 自動読み込みを無効にして、必要な環境変数を注入することを推奨します。

---

問題・質問があれば、実行したいユースケース（ETL のスケジュール化、監査ログの扱い、実注文フロー等）を教えてください。具体的なサンプルやスクリプト例を提供します。