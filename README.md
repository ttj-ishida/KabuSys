# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants や RSS などから市場データ／ニュースを取得して DuckDB に保存し、ETL、品質チェック、マーケットカレンダー、監査ログ（発注→約定のトレース）などを提供します。

---

## プロジェクト概要

このパッケージは以下の目的で構成されています。

- J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを取得して DuckDB に保存するクライアント／ETL。
- RSS フィードからニュースを収集し前処理したうえで DuckDB に保存するニュース収集器（SSRF・サイズ制限・XML 攻撃対策あり）。
- DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。
- マーケットカレンダー管理（営業日判定・前後営業日計算・夜間バッチ更新）。
- 監査ログ（signal → order_request → executions のトレーサビリティ）を初期化するモジュール。
- 設定は環境変数／.env で管理。自動ロード機能あり。

設計上の注意点：
- J-Quants API はレート制限（120 req/min）とリトライ（指数バックオフ）に対応。
- トークン自動リフレッシュ（401 受信時）を行う。
- ETL／保存は冪等性を考慮（ON CONFLICT 句）している。
- ニュース収集は SSRF 対策、gzip 解凍制御、トラッキングパラメータ除去、記事IDは正規化 URL の SHA-256 先頭 32 文字で生成。

---

## 機能一覧

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート判定、CWD 非依存）
  - 必須環境変数取得（例: JQUANTS_REFRESH_TOKEN など）
- kabusys.data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミッタ、リトライ、トークンキャッシュ
  - DuckDB への保存用関数（save_daily_quotes 等）
- kabusys.data.news_collector
  - RSS フィード取得（SSRF・gzip・XML 対策）
  - テキスト前処理、記事ID 正規化、DuckDB への冪等保存
  - 銘柄コード抽出 / 一括紐付け処理
- kabusys.data.schema
  - DuckDB の全テーブル定義（Raw / Processed / Feature / Execution）
  - init_schema() で初期化
- kabusys.data.pipeline
  - 差分 ETL（prices / financials / calendar）と日次 ETL のエントリポイント run_daily_etl
  - backfill 対応、品質チェック統合
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - 夜間カレンダー更新ジョブ calendar_update_job
- kabusys.data.audit
  - 監査用テーブルの定義と初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks で総合実行

（execution / strategy / monitoring ディレクトリはインターフェース用の空パッケージとして配置されています）

---

## 必要条件（依存）

- Python 3.10+
- duckdb
- defusedxml

インストール例（pip）:
```bash
pip install duckdb defusedxml
```

プロジェクト固有の追加依存があれば pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. リポジトリをクローン／配置。

2. 必要パッケージをインストール:
   pip install -r requirements.txt
   （requirements.txt がない場合は少なくとも duckdb, defusedxml をインストール）

3. 環境変数を設定（.env をプロジェクトルートに配置するのが簡便）。主な変数：
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabu API パスワード（必須）
   - KABU_API_BASE_URL : kabu API の base URL（任意、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN : Slack 通知用トークン（必須）
   - SLACK_CHANNEL_ID : Slack チャンネルID（必須）
   - DUCKDB_PATH : DuckDB ファイルパス（任意、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（任意、デフォルト: data/monitoring.db）
   - KABUSYS_ENV : 環境（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL : ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env 自動ロードを無効化（テスト用）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマ初期化:
   - Python から実行する例:
   ```python
   from kabusys.data.schema import init_schema
   init_schema("data/kabusys.duckdb")
   ```
   - 監査ログ専用 DB を分ける場合:
   ```python
   from kabusys.data.audit import init_audit_db
   init_audit_db("data/kabusys_audit.duckdb")
   ```
   init_schema は親ディレクトリがなければ自動で作成します。

---

## 使い方（簡易ガイド）

以下は主要機能の使い方サンプルです。実際にはロギング設定やエラーハンドリングを適切に行ってください。

- 設定の取得:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
```

- 日次 ETL を実行する（DuckDB 接続を渡す）:
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

# 初回のみスキーマを作成
conn = init_schema("data/kabusys.duckdb")  # 既存ならスキップして接続を返す

# 日次 ETL（デフォルトは当日）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 個別 ETL ジョブを呼ぶ（例: 株価 ETL）:
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- カレンダー夜間更新ジョブ:
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved {saved} records")
```

- RSS ニュース収集と保存:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- 監査ログの初期化（既存接続にテーブルを追加）:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 品質チェックの実行:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

テスト・開発時のヒント:
- 自動 .env 読み込みを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- jquants_client の関数は id_token を引数注入できるため、テストではモックトークンを渡して動作確認が可能です。

---

## ディレクトリ構成

パッケージルート（src/kabusys）をベースに主要ファイルを抜粋すると以下のような構成です。

- src/
  - kabusys/
    - __init__.py
    - config.py            # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py  # J-Quants API クライアント（取得・保存・レート制御・リトライ）
      - news_collector.py  # RSS ニュース収集、前処理、DB 保存
      - schema.py          # DuckDB スキーマ定義・初期化
      - pipeline.py        # ETL パイプライン（差分取得・バックフィル・日次 ETL）
      - calendar_management.py  # マーケットカレンダーの管理
      - audit.py           # 監査ログ（signal/order_request/executions）定義・初期化
      - quality.py         # データ品質チェック
    - strategy/
      - __init__.py        # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py        # 発注・ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py        # 監視・メトリクス（拡張ポイント）

この README はコードベースに含まれる設計・API をベースに作成しています。実際の運用ではログ設定、例外処理、シークレットの安全管理、証券会社 API の実装（execution）や戦略の実装（strategy）を追加してください。

---

もし README に追記してほしい内容（例: CI / テストの実行方法、より詳しい .env.example、実運用の注意点など）があれば教えてください。