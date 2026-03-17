# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）。  
J-Quants / kabuステーション 等の外部データソースからデータを収集・保存し、ETL・品質チェック・市場カレンダー・ニュース収集・監査ログを提供するモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。主に以下を提供します。

- J-Quants API クライアント（株価日足・財務・マーケットカレンダー）
  - レート制御、リトライ、トークン自動リフレッシュ、ページネーション対応
- RSS ベースのニュース収集（正規化・SSRF対策・トラッキング除去）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev/trading_days）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）

設計上、冪等性・トレーサビリティ・セキュリティ（SSRF/XML攻撃対策）を重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - RateLimiter、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
- data/news_collector.py
  - RSS 取得（gzip対応）、URL 正規化（utm 等削除）、ID 発行（SHA-256）、SSRF 対策、DuckDB へ保存（INSERT ... RETURNING）
  - 銘柄コード抽出（4桁数字／known_codes フィルタ）
- data/schema.py
  - 全テーブルの DDL 定義（Raw / Processed / Feature / Execution）
  - init_schema / get_connection
- data/pipeline.py
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェックの実行
  - 差分取得・バックフィル・品質チェック統合
- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチでカレンダー更新）
- data/quality.py
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data/audit.py
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化関数
- config.py
  - .env 自動読み込み（プロジェクトルート検出）、Settings クラス（環境変数を型安全に取得）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

---

## 前提 / 依存関係

- Python 3.10 以上（型ヒントの union 文法などを利用）
- 必要パッケージ（主なもの）
  - duckdb
  - defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt を参照してインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

2. 依存パッケージをインストール
   ※ 実際のプロジェクトに応じて requirements を使ってください。例:
   ```bash
   pip install duckdb defusedxml
   # またはプロジェクトが提供する依存ファイル経由で
   # pip install -r requirements.txt
   ```

3. パッケージを開発モード（任意）
   ```bash
   pip install -e .
   ```

4. 環境変数を設定（.env）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すれば無効化）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: 通知先チャネル ID
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH: デフォルト `data/monitoring.db`

   例 `.env`（サンプル）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な呼び出し例）

以下は簡単な Python スニペット例です。実行前に環境変数を設定してください。

- DuckDB スキーマの初期化
  ```python
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  # 以降 conn を ETL や保存関数に渡す
  ```

- 監査ログスキーマの初期化（既存の conn に追加）
  ```python
  from kabusys.data import audit

  audit.init_audit_schema(conn)
  ```

- J-Quants の株価を取得して保存（ETL を使わない単発実行）
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  ```

- 日次 ETL の実行（推奨）
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data import news_collector, schema
  import duckdb
  conn = schema.init_schema("data/kabusys.duckdb")
  # デフォルト RSS ソースを使用
  res = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
  print(res)  # {source_name: saved_count}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.init_schema("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved={saved}")
  ```

- 設定値の取得
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.env)  # development / paper_trading / live
  ```

ヒント:
- 自動で .env を読み込む仕組みはプロジェクトルート（.git か pyproject.toml を基準）から探します。
- 自動ロードを無効化したい場合は環境変数を設定してください:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

主要ファイル・モジュールは以下のとおりです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py  — マーケットカレンダー管理
    - audit.py                — 監査ログスキーマ初期化
    - quality.py              — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現状の実装ファイル群の抜粋です。strategy / execution / monitoring は将来的な拡張を想定したパッケージです。）

---

## 注意事項 / 実運用に関するメモ

- 認証情報（J-Quants トークン、kabu API パスワード、Slack トークン等）は絶対にソース管理にコミットしないでください。`.env.example` を利用してローカルのみで管理してください。
- J-Quants API のレート制限（120 req/min）を遵守する実装になっていますが、運用によってはさらに調整してください。
- DuckDB のファイルバックアップやスキーママイグレーション戦略は運用設計により追加してください。
- news_collector は外部 RSS を取得するため、ネットワークの信頼性やプロキシ設定、タイムアウト設定（timeout 引数）に注意してください。
- Python バージョンは 3.10 以上を推奨します（typing の union 型 | を使用しているため）。

---

## 貢献 / 開発

- バグ報告や機能要望は Issue を立ててください。
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境の自動読み込みを止めるとテストが容易です。
- 単体テスト、統合テスト、CI の追加を推奨します（DuckDB の :memory: を使ったテストが可能）。

---

以上が本リポジトリの README です。必要であれば導入手順のスクリーンショットや具体的な CI / デプロイ手順、.env.example のテンプレート等も作成します。どの部分を詳しく書くか指示ください。