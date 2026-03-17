# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants / RSS 等から市場データやニュースを収集・品質検査して DuckDB に保存し、戦略・発注・監査ログの基盤を提供します。

バージョン: 0.1.0

---

## 概要

- J-Quants API を使った株価（日足）・財務・マーケットカレンダーの取得と DuckDB への冪等保存。
- RSS フィードからニュース記事を収集し、記事と銘柄コードの紐付けを行うニュースコレクタ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- ETL パイプライン（日次差分更新・バックフィル・カレンダー先読み）。
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ。
- 環境変数経由の設定管理（.env 自動読み込み、プロジェクトルート自動検出）。

設計上のポイント:
- API レート制限やリトライ（指数バックオフ）、ID トークン自動リフレッシュを考慮。
- DuckDB へは ON CONFLICT を使った冪等な保存。
- RSS 取得では SSRF / XML Bomb 等のセキュリティ対策を実装。

---

## 主な機能一覧

- config
  - 環境変数の読み込み（.env / .env.local、自動ロードの有効/無効切替）
  - 必須設定の取得（例: JQUANTS_REFRESH_TOKEN 等）
  - 環境（development / paper_trading / live）とログレベルの検証

- data
  - jquants_client: J-Quants API との通信、ページネーション、保存用ユーティリティ
  - news_collector: RSS 取得、前処理、DuckDB への保存、銘柄抽出
  - schema: DuckDB のスキーマ（Raw / Processed / Feature / Execution 層）定義と初期化
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）の実装
  - calendar_management: 市場カレンダーの管理と営業日判定ロジック
  - audit: 監査ログ用テーブル（signal_events, order_requests, executions）初期化
  - quality: データ品質チェック群（欠損・スパイク・重複・日付不整合）

- strategy / execution / monitoring
  - パッケージプレースホルダ（戦略ロジック、発注実装、監視機能を配置する想定）

---

## 必要条件（Prerequisites）

- Python 3.10 以上（型注釈に Python 3.10 の union 型記法を利用）
- 主要依存パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```
（実プロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動

2. 依存パッケージをインストール
   - 例: pip install duckdb defusedxml

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` を配置すると自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)

`.env` の簡易例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 初期化（DuckDB スキーマ）

DuckDB のスキーマを初期化して接続を取得します。

Python 例:
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
```

監査ログ用スキーマを追加する場合:
```python
from kabusys.data import audit
# 既存の conn に監査テーブルを追加
audit.init_audit_schema(conn)
# または専用DBとして初期化
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主な API とサンプル）

- J-Quants の ID トークン取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得
```
設計により、HTTP エラーに対してリトライ・指数バックオフ、401 での自動リフレッシュに対応します。レート制限は 120 req/min（モジュール内で自動スロットリング）です。

- 日次 ETL 実行:
```python
from kubusys.data import schema, pipeline
conn = schema.get_connection("data/kabusys.duckdb")  # 事前に init_schema を実行しておくこと
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```
run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェックの順で実行します。各ステップは独立してエラーハンドリングされます。

- 個別ジョブ例（価格 ETL / カレンダー更新）:
```python
from kabusys.data import pipeline, calendar_management
# prices ETL（特定日まで）
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
# カレンダー夜間バッチ
saved = calendar_management.calendar_update_job(conn)
```

- ニュース収集（RSS）:
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出に使う有効な銘柄コード集合（例: 上場銘柄のコードセット）
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203","6758"]))
```
news_collector は RSS のスキーム検証、リダイレクト時のプライベートIP遮断、gzip サイズチェック、XML パースの安全対策を行います。保存は冪等で、INSERT ... RETURNING により実際に挿入された記事の数を返します。

- データ品質チェックの実行（個別 / 全チェック）:
```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

---

## 環境変数 / 設定の詳細

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境 > .env.local > .env
  - 既存 OS 環境のキーはデフォルトで保護されます。
  - 自動読み込みを停止する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings API（利用例）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.duckdb_path)
print(settings.env)  # development | paper_trading | live
```

---

## ディレクトリ構成

以下は本コードベースに含まれる主要ファイル・モジュールの構成です（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - news_collector.py      -- RSS 収集・前処理・保存・銘柄抽出
    - schema.py              -- DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py            -- ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py -- 市場カレンダー管理（営業日判定・更新ジョブ）
    - audit.py               -- 監査ログ（signal/order_request/execution）スキーマ
    - quality.py             -- データ品質チェック実装
  - strategy/
    - __init__.py            -- 戦略ロジックの配置場所（プレースホルダ）
  - execution/
    - __init__.py            -- 発注実装の配置場所（プレースホルダ）
  - monitoring/
    - __init__.py            -- 監視・メトリクスの配置場所（プレースホルダ）

---

## 運用上の注意 / セキュリティ

- J-Quants のレート制限（120 req/min）を尊重してください。jquants_client は固定間隔でスロットリングしますが、運用側でも同様の配慮をすること。
- 秘密情報（refresh token, kakbu API password, Slack トークン）は `.env` に平文で置く場合、アクセス制御を厳重にしてください。可能なら OS 環境変数やシークレット管理ツールを利用してください。
- news_collector は SSRF / XML 攻撃対策を実装していますが、未知のフィードの追加は慎重に行ってください。
- DuckDB ファイルのバックアップ・ローテーションを検討してください（データ量や監査ログの保持方針による）。

---

## 参考・補足

- KABUSYS_ENV: development / paper_trading / live のいずれかを設定して実行モードを切替可能。settings.is_live / is_paper / is_dev プロパティで判定できます。
- ログレベルは LOG_LEVEL 環境変数で調整してください（デフォルト INFO）。
- テストや CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、自動で .env を読み込まないようにできます。

---

必要であれば、README に以下を追加できます:
- 具体的な CLI / サービス起動手順（systemd / Docker / Docker Compose 等）
- pyproject.toml / requirements.txt のテンプレート
- サンプル運用スクリプト（cron で日次 ETL を回す例）
- 戦略・発注の実装ガイドライン

追加したい項目があれば教えてください。