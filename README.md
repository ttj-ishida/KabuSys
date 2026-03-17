# KabuSys

日本株自動売買プラットフォーム用ライブラリ（KabuSys）のリポジトリ README。  
本ドキュメントはコードベースに含まれるモジュールの概要、セットアップ方法、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。以下の役割を持つコンポーネントを含みます。

- データ収集：J-Quants API や RSS フィードから株価・財務・ニュース・市場カレンダー等を取得
- データ保存：DuckDB をコアにしたスキーマ設計と冪等（idempotent）保存処理
- ETLパイプライン：差分取得・バックフィル・品質チェックを行う日次ETL
- 監査ログ：シグナルから約定までをトレースする監査スキーマ
- 戦略 / 発注 / 監視モジュールの骨組み（strategy, execution, monitoring パッケージ）

設計上の注力点：
- API レート制限とリトライ（指数バックオフ）への対応
- Look-ahead bias を防ぐための fetched_at / UTC保存
- DB 保存は ON CONFLICT を用いた冪等性
- ニュース収集における SSRF / XML Attack / Gzip bomb 対策
- 品質チェック（欠損・重複・スパイク・日付不整合）

---

## 機能一覧

主な機能（抜粋）:

- 環境変数管理（`.env`/`.env.local` 自動ロード、必要変数の検出）
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、市場カレンダー取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ
- RSS ニュース収集・前処理
  - URL 正規化、トラッキングパラメータ除去、ID生成（SHA-256）
  - SSRF対策、gzip制限、XML安全パース
  - DuckDB への冪等保存（raw_news / news_symbols）
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - スキーマ初期化ユーティリティ（init_schema）
- ETL パイプライン
  - 日次 ETL（run_daily_etl）でカレンダー・価格・財務を差分取得
  - バックフィル、品質チェック（quality モジュール）
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブル、トレーサビリティ設計

---

## 要件

- Python 3.10 以上（型注釈に `X | None` 構文を使用）
- 主要ライブラリ（例、以下を想定）
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, logging, datetime, pathlib 等）

実際のプロジェクトでは `pyproject.toml` / `requirements.txt` を用意して依存管理してください。

---

## 環境変数

自動ロード：パッケージはプロジェクトルート（`.git` または `pyproject.toml`）を探索し、`.env` → `.env.local` の順で環境変数を自動読み込みします。OS 環境変数は上書きされません（`.env.local` は上書き可）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時などに利用）。

主要な環境変数（必須）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

任意 / デフォルト:
- KABUSYS_ENV — 実行環境（development, paper_trading, live）。デフォルト: `development`
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）。デフォルト: `INFO`
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: `data/kabusys.duckdb`
- SQLITE_PATH — 監視用途の SQLite パス。デフォルト: `data/monitoring.db`

設定が不足している場合、Settings クラスのプロパティは例外を投げます（必須項目は `_require` によりチェック）。

---

## セットアップ手順

1. リポジトリをチェックアウト
   ```
   git clone <repository-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール（例）
   ```
   pip install duckdb defusedxml
   ```
   実際は `pyproject.toml` / `requirements.txt` を参照してインストールしてください。

4. 環境変数設定
   - リポジトリ直下に `.env`（および必要なら `.env.local`）を作成して必要なキーを設定します。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. DuckDB スキーマ初期化（Pythonコンソールまたはスクリプトで）
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
   監査ログのみ別DBにしたい場合:
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 基本的な使い方

ここでは主要なユースケースの例を示します。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定するとその日分を処理
  print(result.to_dict())
  ```

- ニュース収集（RSS）と保存
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は銘柄コードセット (例: {'7203', '6758', ...})
  stats = run_news_collection(conn, known_codes={'7203','6758'})
  print(stats)
  ```

- J-Quants トークン取得 / API 呼び出しの直接利用
  ```python
  from kabusys.data import jquants_client as jq

  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- ETL / API 呼び出しは network I/O を伴います。ログや例外を適切に処理してください。
- J-Quants のレート制限（120 req/min）をモジュール内で制御しますが、大量バッチ実行時はさらに注意してください。

---

## ディレクトリ構成（主なファイル）

以下はコードベースに含まれる主要ファイルとその説明です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と Settings クラス、自動 `.env` ロードロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、レートリミット・リトライ・保存ロジック
    - news_collector.py
      - RSS取得、前処理、DuckDB への保存、銘柄抽出（SSRF対策等）
    - schema.py
      - DuckDB の DDL 定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）
    - audit.py
      - 監査ログ用スキーマ初期化（signal_events, order_requests, executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py
    - （戦略モジュールを配置する想定）
  - execution/
    - __init__.py
    - （発注・約定管理・ブローカーインターフェースを実装する想定）
  - monitoring/
    - __init__.py
    - （監視・アラート用コードを実装する想定）

ドキュメント / 設計参照:
- DataPlatform.md（設計参照と記載箇所あり）
- README に示した各モジュールの docstring を参照すると詳細設計が読めます。

---

## 運用上の注意・ベストプラクティス

- 秘密情報（API トークン・パスワード）は `.env` で管理し、リポジトリに含めないでください。
- DuckDB ファイルは定期的にバックアップしてください。監査ログは削除しない前提の設計です。
- ETL は冪等に設計されていますが、外部からの手動操作でスキーマが壊れると想定外の挙動を招くので注意してください。
- ニュース収集では外部 RSS の妥当性を常に検証する（SSRF / 大容量レスポンスをブロック）。
- 本ライブラリは戦略実行・発注のコア基盤を提供します。実際のアルゴリズムやブローカー連携は別モジュールで実装してください（paper_trading/live 切り替え等）。

---

必要であれば、README に含めるサンプル .env.example、実行スクリプト（CLI ラッパー）や、CI / テストのセットアップ手順（KABUSYS_DISABLE_AUTO_ENV_LOAD を使ったテスト時の環境制御など）も作成します。どの追加情報がほしいか教えてください。