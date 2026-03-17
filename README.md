# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants や RSS など外部データを取得して DuckDB に格納し、ETL・品質チェック・マーケットカレンダー管理・ニュース収集・監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを安全に取得・保存する
- RSS フィードからニュース記事を収集し、銘柄コードと紐付ける
- DuckDB を用いたスキーマ（Raw / Processed / Feature / Execution / Audit）の初期化・管理
- ETL（差分取得、バックフィル、品質チェック）を実行可能なパイプラインを提供
- マーケットカレンダー（営業日判定、前後営業日の取得）を扱うユーティリティ
- 監査ログ（シグナル→発注→約定のトレース）用スキーマの初期化

設計上の特徴（抜粋）:
- API レート制御・リトライ（指数バックオフ）・トークン自動リフレッシュを備えた J-Quants クライアント
- DuckDB への冪等保存（ON CONFLICT / DO UPDATE / DO NOTHING）
- RSS 収集での SSRF 対策・XML 脆弱性防御（defusedxml）・受信サイズ制限
- 品質チェック（欠損・スパイク・重複・日付不整合）を集約して報告

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（fetch / save 関数、レート制御、リトライ、トークン管理）
  - news_collector: RSS 取得・前処理・DB 保存、銘柄抽出機能
  - schema: DuckDB スキーマ定義と init_schema()
  - pipeline: 日次 ETL（差分取得・保存・品質チェック）の実行（run_daily_etl）
  - calendar_management: market_calendar の更新と営業日判定ユーティリティ
  - audit: 監査ログ用のテーブル初期化（init_audit_db / init_audit_schema）
  - quality: 品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
- config: 環境変数管理（.env 自動読み込み、Settings クラス）
- strategy / execution / monitoring パッケージのためのプレースホルダ

---

## 必要条件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（その他、標準ライブラリの urllib 等を使用。実際の運用では追加で Slack 等の SDK が必要になることがあります。）

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb defusedxml
# 開発パッケージを setup.py/pyproject.toml によって管理している場合は `pip install -e .` など
```

---

## 環境変数（主なもの）

config.Settings で参照する主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。

- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード。

- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン（運用時）。

- SLACK_CHANNEL_ID (必須)  
  通知先の Slack チャンネル ID。

- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb

- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db

- KABUSYS_ENV (任意)  
  有効値: development, paper_trading, live  
  デフォルト: development

- LOG_LEVEL (任意)  
  有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL  
  デフォルト: INFO

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると、.env 自動読み込みを無効化できます。

.env ファイル自動読み込みの順序:
- OS 環境変数 > .env.local > .env
- プロジェクトルートはこのパッケージファイルから親ディレクトリを上へ探索し、.git または pyproject.toml があるディレクトリをルートと判定します。見つからない場合は自動ロードをスキップします。

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. 仮想環境の作成・有効化（推奨）
3. 依存パッケージをインストール（duckdb, defusedxml 等）
4. プロジェクトルートに .env（または .env.local）を置く。例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xxxx
   SLACK_CHANNEL_ID=XXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
5. DuckDB スキーマの初期化:
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
     ```
6. 監査ログ用スキーマを追加（任意、監査用 DB を別にすることも可能）:
   ```python
   from kabusys.data.audit import init_audit_db
   init_audit_db("data/kabusys_audit.duckdb")
   # または既存の DuckDB 接続に追加:
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（主要 API と実行例）

- DuckDB スキーマ作成
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL を実行（パイプライン）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集（raw_news に保存）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  # sources を省略すると DEFAULT_RSS_SOURCES を使用
  results = run_news_collection(conn)
  print(results)  # {source_name: new_saved_count, ...}
  ```

- J-Quants からデータ取得のみ（例: 日足を直接フェッチ）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックを個別に実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

- 注意: これらはライブラリ API の呼び出し例です。運用環境ではログ設定・例外ハンドリング・定期実行（cron / Airflow 等）を追加してください。

---

## 運用例（cron 例）

- 日次 ETL（平日夜に実行）:
  - 例: 毎日 1:00 に run_daily_etl を実行（cron や CI/CD、ジョブスケジューラで Python スクリプトを呼ぶ）

- マーケットカレンダー更新（夜間）
  - calendar_update_job を毎日実行（lookahead_days を適宜調整）

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル構成の抜粋です:

- src/
  - kabusys/
    - __init__.py
    - config.py                  -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py        -- J-Quants API クライアント（fetch/save）
      - news_collector.py        -- RSS 収集・前処理・保存・銘柄抽出
      - schema.py                -- DuckDB スキーマ定義 / init_schema
      - pipeline.py              -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py   -- 市場カレンダー管理ユーティリティ
      - audit.py                 -- 監査ログスキーマ初期化
      - quality.py               -- データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（フルツリーはリポジトリ内の src/kabusys 以下を参照）

---

## 注意点 / 運用上のヒント

- Python バージョンは 3.10 以上を想定しています（型ヒントで | を使用）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時などは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- J-Quants API はレート制限（120 req/min）があるため、jquants_client 内でスロットリングを行っています。並列リクエストは注意してください。
- RSS 取得時は SSRF / XML Bomb 対策を行っていますが、外部の未検証フィードを運用環境で追加する際は監視を行ってください。
- DuckDB ファイルはバックアップやロックに注意して運用してください（複数プロセスからの同時書き込みなど）。

---

## ライセンス / 貢献

本リポジトリのライセンスや貢献ガイドはリポジトリのトップレベルに置いてください（このコードベースの README には含めていません）。

---

必要であれば、README に次の追加を作成できます:
- 詳細な .env.example サンプル
- 実行スクリプト（systemd / cron 用のサンプル）
- CI/テストの実行方法
ご希望があれば、それらを追記します。