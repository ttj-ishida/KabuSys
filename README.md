# KabuSys

日本株自動売買プラットフォーム用の共通ライブラリ群です。  
データ収集（J-Quants / RSS）、ETL パイプライン、DuckDB スキーマ、マーケットカレンダー管理、ニュース集約、品質チェック、監査ログ等の機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のアルゴリズム取引基盤向けに設計されたモジュール群です。主に以下を目的とします。

- J-Quants API からの時系列データ（株価日足、財務、マーケットカレンダー）取得と DuckDB への格納（冪等保存）
- RSS ベースのニュース収集と記事→銘柄紐付け
- ETL（差分取得／バックフィル）パイプラインとデータ品質チェック
- マーケットカレンダーを用いた営業日判定・探索ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ初期化
- 環境設定管理（.env 自動読み込み、必須環境変数チェック）

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）対応（スロットリング）
- 冪等性を重視（ON CONFLICT / DO UPDATE / DO NOTHING を活用）
- リトライ・指数バックオフ、401 時はトークン自動リフレッシュ
- SSRF / XML Bomb 等に対する安全対策（news_collector）

---

## 主な機能一覧

- data/jquants_client.py
  - 株価日足（OHLCV）、財務（四半期）、マーケットカレンダー取得
  - DuckDB への保存（save_*）
  - レート制御・リトライ・トークン管理

- data/news_collector.py
  - RSS フィード取得、前処理、記事ID生成（normalized URL → SHA-256）
  - DuckDB への冪等保存（raw_news, news_symbols）
  - SSRF や応答サイズ制限などのセキュリティ対策

- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化

- data/pipeline.py
  - 差分取得・バックフィルを行う ETL（run_daily_etl）
  - 品質チェック（quality モジュール）と結果の ETLResult 出力

- data/calendar_management.py
  - market_calendar を用いた営業日判定・next/prev_trading_day 等
  - 夜間カレンダー更新ジョブ（calendar_update_job）

- data/quality.py
  - 欠損、スパイク、重複、日付不整合検出
  - run_all_checks で一括実行

- data/audit.py
  - 監査ログ用テーブル群の初期化（init_audit_schema / init_audit_db）

- config.py
  - 環境変数の読み込み（.env/.env.local 自動読み込み）
  - settings オブジェクト経由の設定取得（必須チェック・検証）

---

## 要求環境 / 依存

- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - defusedxml

pip での最低インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクト配布に合わせて requirements.txt / setup.py を参照
```

---

## セットアップ手順

1. レポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

3. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を配置できます。.env.local は .env を上書きします。
   - 自動読み込みはデフォルトで有効です（config.py がプロジェクトルートを探して .env / .env.local を読み込みます）。
   - 自動ロードを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - （任意）KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - データベースパス:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
   - 実行環境:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx...
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（代表的なコード例）

以下は Python から主要機能を呼び出す例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# :memory: でインメモリ DB も可能
```

- 日次 ETL 実行（J-Quants からの差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- ニュース収集ジョブ実行
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

- 監査ログスキーマの初期化（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# transactional=True を指定すると DDL をトランザクションで実行（init_audit_db は transactional=True）
init_audit_schema(conn, transactional=False)
```

- 設定値の参照（環境変数）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.kabu_api_base_url)
print(settings.is_live)
```

---

## 主要 API の注意点 / 運用上のポイント

- J-Quants API:
  - レート制限は 120 req/min。jquants_client は内部で固定間隔レート制御と指数バックオフを実装しています。
  - get_id_token はリフレッシュトークンから idToken を取得します。401 が返った場合は自動で1回リフレッシュして再試行します。
  - fetch_* 関数はページネーション対応。

- News Collector:
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で生成し、冪等性を担保します。
  - RSS のレスポンスサイズは MAX_RESPONSE_BYTES（10MB）で制限しています。
  - リダイレクトやホストは内部アドレスチェックをし、SSRF を防止します。

- ETL:
  - 差分取得を基本とし、backfill_days により直近数日分を再取得して API 側の後出し修正を吸収します。
  - 品質チェックは Fail-Fast ではなく、検出結果を収集して呼び出し元に返します。

- 環境変数自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）から .env / .env.local を自動で読み込みます。
  - OS 環境変数は保護され、.env の値は上書きされません（ただし .env.local は override=True で上書き可能）。
  - テスト時などに自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

主要なファイル/ディレクトリ構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / settings
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント、保存ユーティリティ
    - news_collector.py           -- RSS ニュース収集・前処理・保存
    - pipeline.py                 -- ETL パイプライン（run_daily_etl など）
    - schema.py                   -- DuckDB スキーマ定義 / 初期化
    - calendar_management.py      -- マーケットカレンダー管理・営業日ユーティリティ
    - audit.py                    -- 監査ログスキーマ初期化
    - quality.py                  -- データ品質チェック
  - strategy/
    - __init__.py                 -- 戦略層（拡張用）
  - execution/
    - __init__.py                 -- 発注/実行/ポジション管理（拡張用）
  - monitoring/
    - __init__.py                 -- 監視関連（拡張用）

この README はプロジェクトの概要と主要な利用方法をまとめたものです。詳細な API や設計ドキュメント（DataPlatform.md / DataSchema.md 等）が別途ある想定のため、実運用時はそれらのドキュメントも参照してください。

---

## 貢献・問い合わせ

バグ報告や機能改善提案は issue を通してお願いします。Pull Request の際はテスト・ドキュメントの追加をお願いします。

--- 

以上。必要であれば、README にサンプル .env.example や よくある運用コマンド（cron/airflow のサンプル）を追記します。どの情報を追加しますか？