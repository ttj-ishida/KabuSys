# KabuSys

日本株向けの自動売買システム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、DuckDB スキーマ／監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集と記事→銘柄紐付け（SSRF対策・トラッキング除去・gzip上限）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（戦略→シグナル→発注→約定のトレーサビリティ用テーブル群）

設計上、API レート制限や再試行、冪等性（ON CONFLICT）等を考慮してあり、運用/テストしやすいように id_token の注入や自動 .env ロードの無効化なども可能です。

---

## 主な機能一覧

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - 取得結果の DuckDB への冪等保存（save_* 関数）
  - レートリミット、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ

- ETL（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：市場カレンダー → 株価 → 財務 → 品質チェック
  - 差分更新、backfill、営業日調整

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応、XML パース防御、SSRF 対策）
  - URL 正規化、記事ID（SHA-256先頭32文字）生成、raw_news への冪等保存
  - 銘柄コード抽出（4桁）と news_symbols への紐付け

- スキーマ＆監査（kabusys.data.schema / kabusys.data.audit）
  - DuckDB 用の包括的な DDL 定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema / init_audit_schema で初期化可能

- データ品質チェック（kabusys.data.quality）
  - 欠損データ / スパイク（前日比） / 重複 / 日付不整合の検出
  - QualityIssue オブジェクトの集合として結果を返す

- 設定管理（kabusys.config）
  - .env ファイル自動読み込み（プロジェクトルート検出）
  - 環境変数経由の設定（必須・任意をプロパティで提供）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

---

## 要件

- Python 3.10 以上（typing の | などの記法を使用）
- 必要なパッケージ（少なくとも下記）
  - duckdb
  - defusedxml

（追加でロギングや Slack 連携等を行う場合は該当ライブラリを導入してください）

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発中パッケージとしてローカルインストールする場合
pip install -e .
```

---

## 環境変数（設定）

kabusys.config.Settings 経由で以下の環境変数を参照します。パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効）。

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション/デフォルトあり:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live、デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 設定で .env 自動ロードを無効化)

例 .env:

```
JQUANTS_REFRESH_TOKEN=xxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境の作成と依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   # 開発用にローカルインストール
   pip install -e .
   ```

3. 環境変数を設定（.env をプロジェクトルートに配置）
   - 上記の .env 例を参照してください。

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで実行:

   ```python
   from kabusys.data import schema
   from kabusys.config import settings

   # settings.duckdb_path は Settings が参照する環境変数に基づく
   conn = schema.init_schema(settings.duckdb_path)
   ```

   init_schema は冪等なので既存テーブルがあればスキップされます。

5. （監査ログを別 DB に分ける場合）
   ```python
   from kabusys.data import audit, schema
   conn = schema.init_schema(settings.duckdb_path)
   audit.init_audit_schema(conn)
   # または専用 DB
   audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（主要なサンプル）

1. 日次 ETL を実行する（デフォルトは今日）
   ```python
   from kabusys.data import pipeline, schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)
   result = pipeline.run_daily_etl(conn)
   print(result.to_dict())
   ```

   オプション:
   - target_date を指定して過去日分を処理
   - id_token を注入してテスト可能
   - run_quality_checks=False で品質チェックをスキップ

2. ニュース収集ジョブの実行
   ```python
   from kabusys.data import news_collector, schema
   from kabusys.config import settings

   conn = schema.init_schema(settings.duckdb_path)

   # 既知の銘柄コードセット（抽出時に利用）
   known_codes = {"7203", "6758", "9984"}  # 例

   results = news_collector.run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: 新規保存数, ...}
   ```

3. J-Quants の生データ取得 & 保存（個別実行）
   ```python
   from kabusys.data import jquants_client as jq
   from kabusys.data import schema
   from kabusys.config import settings
   import datetime

   conn = schema.init_schema(settings.duckdb_path)
   today = datetime.date.today()
   records = jq.fetch_daily_quotes(date_from=today - datetime.timedelta(days=7), date_to=today)
   saved = jq.save_daily_quotes(conn, records)
   print(f"fetched={len(records)} saved={saved}")
   ```

4. 品質チェック単体の実行
   ```python
   from kabusys.data import quality, schema
   import datetime

   conn = schema.init_schema("data/kabusys.duckdb")
   issues = quality.run_all_checks(conn, target_date=datetime.date.today())
   for i in issues:
       print(i)
   ```

---

## 注意点 / 運用上のポイント

- .env 自動読み込み
  - パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索して `.env` と `.env.local` を読み込みます。OS 環境変数が優先され、`.env.local` は `.env` の上書きに使用されます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

- レート制御とリトライ
  - J-Quants API は 120 req/min に制限されます。jquants_client は固定間隔のレートリミターとリトライロジック（408/429/5xx を対象）を実装しています。
  - 401 はトークン期限切れとみなし、1 回だけ自動でリフレッシュして再試行します。

- 冪等性
  - save_* 関数（DuckDB への保存）は ON CONFLICT（DO UPDATE / DO NOTHING）を使って冪等性を担保しています。ETL が途中で再実行されても基本的に安全です。

- セキュリティ
  - news_collector は SSRF 対策（スキーム検証、リダイレクト先のプライベートアドレス検査）、受信サイズ上限、defusedxml による XML パース防御を行います。

---

## ディレクトリ構成

パッケージソース（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定読み込みロジック
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存）
      - news_collector.py      # RSS ニュース収集・保存・銘柄紐付け
      - schema.py              # DuckDB スキーマ定義・初期化
      - pipeline.py            # ETL パイプライン（差分取得・品質チェック）
      - quality.py             # データ品質チェック
      - audit.py               # 監査ログ（戦略→注文→約定 トレーサビリティ）
      - audit.py
    - strategy/                 # 戦略関連（空のパッケージ / 実装を追加）
      - __init__.py
    - execution/                # 発注・実行管理（空のパッケージ / 実装を追加）
      - __init__.py
    - monitoring/               # 監視関連（空のパッケージ / 実装を追加）
      - __init__.py

---

## 今後の拡張案（参考）

- strategy / execution / monitoring の実装（戦略のプラグイン化、証券会社ブリッジ）
- Slack / メトリクス送信などの運用アラート統合
- テスト用 fixtures（DuckDB の in-memory 利用、ネットワークコールのモック）
- Docker イメージ化 & 定期実行（cron / scheduler）

---

不明点や README に追加したい運用手順（例: CI / デプロイ方法、Slack通知の実装例など）があればお知らせください。README をその用途に合わせて拡張します。