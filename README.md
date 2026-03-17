# KabuSys

日本株向けの自動売買データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS などから市場データ・ニュースを収集し、DuckDB に保存、ETL（品質チェック含む）を実行するためのモジュール群を提供します。  
（戦略・発注・監視の骨組みを含む設計になっています）

---

## プロジェクト概要

KabuSys は次の目的で設計されています。

- J-Quants API から株価（日足）・財務データ・市場カレンダーを安全に取得する。
- RSS フィード等からニュース記事を収集し、記事と銘柄コードの紐付けを行う。
- 取得データを DuckDB に冪等（idempotent）に保存するためのスキーマ／保存関数を提供する。
- ETL パイプライン（差分取得、バックフィル、品質チェック）を実行する。
- 監査ログ（signal → order → execution のトレーサビリティ）を保持するためのテーブル群を用意する。

設計上の特徴:

- API レート制御（120 req/min）の遵守
- リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
- Look-ahead bias 防止のため fetched_at を UTC で記録
- RSS/HTTP の SSRF／XML 攻撃対策（スキーム検証、プライベートIPチェック、defusedxml、受信サイズ制限）
- DuckDB での冪等保存（ON CONFLICT ...）とトランザクション管理
- 品質チェック（欠損・スパイク・重複・日付不整合）

---

## 主な機能一覧

- 環境設定管理（自動でプロジェクトルートの `.env` / `.env.local` をロード、設定取得用 `settings`）
- J-Quants クライアント
  - get_id_token (リフレッシュトークンからIDトークン取得)
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar
- RSS ニュース収集
  - fetch_rss : RSS 取得・XML パース（安全対策内蔵）
  - save_raw_news, save_news_symbols : DuckDB への保存・銘柄紐付け
  - run_news_collection : 複数ソースの一括収集ジョブ
- DuckDB スキーマ管理
  - init_schema(db_path) : 全テーブル・インデックスを作成
  - get_connection(db_path)
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl : 日次 ETL の統合実行（品質チェック含む）
- マーケットカレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
- 監査（audit）テーブル生成・初期化（init_audit_schema, init_audit_db）
- 品質チェック（quality モジュール）：欠損・スパイク・重複・日付不整合検出

---

## セットアップ手順

前提:
- Python 3.10 以上（組み合わせ型記法 `X | None` を使用しているため）
- git, pip 等が利用可能

1. リポジトリをクローン
   ```
   git clone <your-repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール  
   本コードベースで直接使用している外部パッケージは最小で以下です:
   - duckdb
   - defusedxml

   pip でインストール:
   ```
   pip install duckdb defusedxml
   ```

   （プロダクション用途では requirements.txt / Poetry で依存管理してください）

4. 環境変数の設定  
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（変数名は下記参照）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な環境変数（少なくとも以下を設定してください）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意・デフォルト:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読込を無効化
   - KABUSYS_LOG_LEVEL / LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_DUCKDB_PATH / DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB 等で使う SQLite パス（デフォルト data/monitoring.db）

---

## 使い方（コード例）

以下は主要な利用例です。パッケージは `src` 配下にある想定で、Python パスに追加するかパッケージとしてインストールして利用してください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は Path を返す
conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL を実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブを実行（既存 DuckDB 接続を渡す）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に有効銘柄一覧を用意
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

4) J-Quants API を直接利用（トークン取得・日足取得）
```python
from kabusys.data import jquants_client as jq

id_token = jq.get_id_token()  # settings から refresh_token を使用
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
# 保存
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

5) 監査スキーマの初期化（signal/order/execution 用）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
init_audit_schema(conn)
```

注意点:
- run_daily_etl 等は内部で品質チェック（quality.run_all_checks）を呼びます。品質問題は結果に含まれますが、デフォルトでは ETL を中断しません（呼び出し元で判断してください）。
- RSS フェッチは SSRF 対策やレスポンスサイズ制限を行います。外部URLの扱いに注意してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト "http://localhost:18080/kabusapi")
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト "data/kabusys.duckdb")
- SQLITE_PATH (任意、デフォルト "data/monitoring.db")
- KABUSYS_ENV (任意、 "development" | "paper_trading" | "live")
- LOG_LEVEL (任意、 "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意、"1" で .env 自動ロードを無効化)

---

## ディレクトリ構成（抜粋）

以下はコードベースの主要ファイルとディレクトリの構成です（src 配下）。実際のリポジトリでは追加ファイルやドキュメントがある可能性があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                   # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得・保存）
      - news_collector.py         # RSS ニュース収集・保存・銘柄紐付け
      - pipeline.py               # ETL パイプライン（run_daily_etl 等）
      - schema.py                 # DuckDB スキーマ定義と初期化
      - calendar_management.py    # 市場カレンダー管理 / 夜間更新ジョブ
      - audit.py                  # 監査ログ（signal/order/execution）スキーマ初期化
      - quality.py                # データ品質チェック
    - strategy/                    # 戦略層（未実装骨組み）
    - execution/                   # 発注実行層（未実装骨組み）
    - monitoring/                  # 監視モジュール（未実装骨組み）

---

## 運用上の注意 / ベストプラクティス

- 秘密情報（API トークンなど）は .env.local 等のローカルファイルやシークレット管理により保護してください。`.env.example` を参照して `.env` を作成する運用を想定しています。
- DuckDB ファイルは定期的にバックアップしてください。大容量データや並列書き込みに注意が必要です（DuckDB の特性に依存）。
- J-Quants API の利用制限（レートや利用規約）を遵守してください。モジュールは 120req/min に合わせた固定間隔スロットリングを実装していますが、さらに運用側の注意が必要です。
- run_daily_etl などはバッチジョブとして cron / Airflow / GitHub Actions 等でスケジュール運用するのが良いでしょう。
- テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って環境変数の自動ロードを抑制できます。

---

## ライセンス / 貢献

（この README にはライセンス情報が含まれていません。実際のリポジトリに LICENSE を追加してください。）  
バグ報告・機能提案・プルリクエストは歓迎します。コード変更時はユニットテストと静的解析を追加してください。

---

この README はソースコードの説明をもとに作成しています。実運用時は `.env.example`、運用手順（デプロイ / ローテーション / バックアップ）や CI/CD の設定ドキュメントを追加してください。