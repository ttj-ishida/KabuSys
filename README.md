# KabuSys

日本株向け自動売買プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、ニュース収集、データ品質チェック、DuckDB スキーマ定義、監査ログなどを提供し、戦略・発注層と連携して売買フローを構成できます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主に以下を目的としています。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- RSS ベースのニュース収集と記事の正規化・DB保存（SSRF / XML 攻撃対策、トラッキング除去）
- DuckDB によるデータスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）

設計上の特徴として、冪等性（ON CONFLICT での更新・INSERT DO NOTHING）、Look-ahead バイアス対策（fetched_at の記録）、および堅牢なネットワーク処理（リトライ・指数バックオフ・RateLimiter）を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存: save_daily_quotes, save_financial_statements, save_market_calendar
  - API レート制限（120 req/min）およびリトライ処理、401 時の自動トークン更新
- data/news_collector.py
  - RSS フィード取得（gzip 対応）、URL 正規化、トラッキング除去、SSRF 対策
  - raw_news / news_symbols への冪等保存（チャンク挿入、INSERT ... RETURNING）
  - 銘柄コード抽出、統合収集ジョブ（run_news_collection）
- data/schema.py
  - DuckDB のテーブル DDL（Raw / Processed / Feature / Execution 層）とインデックス定義
  - init_schema(db_path) で DB 初期化を実行
- data/pipeline.py
  - 日次 ETL の実装（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得、backfill 設定、ETLResult を返却
- data/quality.py
  - 欠損・スパイク・重複・日付不整合のチェック（複数チェックをまとめて実行）
- data/audit.py
  - 監査ログ用テーブル群（signal_events / order_requests / executions）と初期化補助

設定は環境変数（.env / .env.local を自動読み込み）から取得します（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 要件

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, logging, datetime 等）

pip パッケージはプロジェクトの pyproject.toml / requirements.txt に従ってください。最低限動かすには duckdb と defusedxml をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンしてローカルへ
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要なパッケージをインストール
   ```
   pip install -U pip
   pip install duckdb defusedxml
   # またはプロジェクトに同梱の依存ファイルがあればそれを使う
   # pip install -e .
   ```

4. 環境変数設定（.env を作成）
   プロジェクトルートに `.env` を置くと、自動で読み込まれます（.env.local があれば優先して上書き）。
   主要な環境変数例（.env.example を参考にしてください）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 必要に応じて
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

5. DB 初期化（DuckDB スキーマの作成）
   Python REPL やスクリプトから:
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   監査ログを別 DB に分けたい場合:
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/kabusys_audit.duckdb")
   ```
   あるいは既存の接続に監査テーブルを追加:
   ```py
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（基本例）

- 日次 ETL（市場カレンダー・株価・財務の差分取得と品質チェック）
  ```py
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定することも可
  print(result.to_dict())
  ```

- ニュース収集（RSS）を実行して raw_news に保存
  ```py
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # sources をカスタマイズしたい場合は dict を渡す
  results = run_news_collection(conn)
  print(results)  # {source_name: saved_count, ...}
  ```

- J-Quants から日足を直接フェッチして保存
  ```py
  from kabusys.data.schema import init_schema
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- データ品質チェック単体実行
  ```py
  from kabusys.data.schema import init_schema
  from kabusys.data.quality import run_all_checks

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- 環境変数の取得
  ```py
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live
  ```

---

## 自動環境読み込みについて

- 実行時、プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` があれば自動で読み込みます。
- 自動ロードを停止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須環境変数が未設定の場合、Settings のプロパティアクセス時に ValueError が発生します。

必須となる主な環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

（上記はコード内で _require により必須扱いされています）

---

## 注意点 / 設計上の挙動

- J-Quants クライアントは API レート制限（120 req/min）を守るため固定間隔スロットリングを実装しています。
- リトライ: ネットワークエラーや 408/429/5xx に対して指数バックオフで最大 3 回リトライします。401 は自動トークン更新を試みて 1 回リトライします。
- ニュース収集は SSRF、XML Bomb、トラッキングパラメータ等に対する対策を施しています。
- DuckDB の DDL は冪等であり、init_schema は既存テーブルがあってもスキップします。
- ETL は Fail-Fast ではなく、各ステップを独立して実行し、発生したエラーを ETLResult に集約して返します。呼び出し側で停止/通知等の対応を行ってください。

---

## ディレクトリ構成

リポジトリ（抜粋）:
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      schema.py
      audit.py
      quality.py
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py
```

主要モジュール:
- kabusys.config: 環境変数と設定の管理（Settings）
- kabusys.data.schema: DuckDB スキーマ定義と初期化
- kabusys.data.jquants_client: J-Quants API クライアント（取得 + 保存）
- kabusys.data.news_collector: RSS ニュース収集と DB 保存
- kabusys.data.pipeline: ETL の Orchestrator（run_daily_etl など）
- kabusys.data.quality: 品質チェック
- kabusys.data.audit: 監査ログスキーマ

---

## 運用例（高度な利用法）

- ETL を Cron / Airflow / Prefect 等で毎朝実行し、結果を Slack に通知する（SLACK_BOT_TOKEN を使用）。
- run_daily_etl の戻り値（ETLResult）を監査ログやモニタリング DB に格納して運用アラート判定に利用。
- ニュース収集で抽出した銘柄と features/ai_scores を組み合わせ、シグナル生成→order_requests→発注フローへ繋ぐ。

---

## 貢献・拡張

- strategy/ と execution/ パッケージは拡張ポイントです。新しい戦略を strategy 配下に実装し、execution にブローカー連携を追加してください。
- DuckDB スキーマは DataPlatform.md に基づく想定です。運用に合わせてフィールド追加やインデックス調整を行ってください。
- テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使い、環境依存を排除します。

---

必要であれば README にサンプル .env.example、実行スクリプト（CLI）やユニットテスト手順、CI の設定例も追加できます。どの情報を追記しますか？