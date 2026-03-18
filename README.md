# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ部分のみ）。  
データ収集、ETL、品質チェック、監査ログ、ニュース収集など、自動売買パイプラインの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの自動売買基盤のための内部ライブラリ群です。本リポジトリには主に以下の機能が含まれます。

- J-Quants API からの市場／財務データ取得（レート制御・リトライ・トークン自動更新）
- RSS からのニュース収集と DuckDB への冪等保存（SSRF／XML攻撃対策、トラッキング除去）
- DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損、重複、スパイク、未来日付等）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）

設計方針として、冪等性・トレース性・セキュリティ（SSRF/XML/サイズ制限）を重視しています。

---

## 機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパー（settings オブジェクト）
- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー
  - レートリミット（120 req/min）とリトライ（指数バックオフ）、401 時の自動トークン更新
  - DuckDB へ冪等に保存する save_* 関数
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理、記事ID生成（正規化 URL の SHA-256）、DuckDB へ冪等保存
  - SSRF 対策、gzip サイズ制限、defusedxml による XML 安全化
  - 銘柄コード抽出と news_symbols への紐付け
- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブルDDLを一括で作成する init_schema()
  - インデックス、外部キー依存を考慮した初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日を基に自動算出）、バックフィル、品質チェックを含む日次ETL
  - run_daily_etl() による一括実行
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間バッチでの calendar_update_job()
- 品質チェック（kabusys.data.quality）
  - 欠損 / 重複 / スパイク / 日付不整合を検出し QualityIssue リストを返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化する init_audit_schema / init_audit_db

---

## 必要条件（推奨）

- Python 3.10 以上（PEP 604 の記法（X | None）を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

必要に応じて追加で urllib (標準)、email、hashlib などの標準ライブラリを利用します。

---

## セットアップ手順

例: 仮想環境を作成して必要なパッケージをインストールする手順。

1. 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```

   （実際のプロジェクトでは requirements.txt / pyproject.toml に依存を追加してください）

3. 環境変数ファイル（.env）を作成
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 例: `.env.example` に基づく最低限のキー
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DuckDB スキーマ初期化（例）
   - Python REPL / スクリプトで:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査DB を分離して使う場合:
     ```python
     from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（主要 API とサンプル）

以下は主要な機能を簡単に使うためのサンプルコードです。

- 設定の利用
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema(settings.duckdb_path)
  ```

- J-Quants から株価を取得して保存（単体）
  ```python
  from kabusys.data import jquants_client as jq
  # get_id_token() は settings.jquants_refresh_token を使って自動で取得します
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)
  ```

- 日次 ETL 実行（推奨）
  ```python
  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)  # target_date を省略すると今日の処理を実行
  print(result.to_dict())
  ```

- RSS ニュース収集と保存
  ```python
  from kabusys.data import news_collector
  articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  new_ids = news_collector.save_raw_news(conn, articles)
  # 既知の銘柄コード集合があれば紐付け
  known_codes = {"7203", "6758", "9432"}  # 例
  # run_news_collection は fetch + save + symbols 紐付けをまとめて実行
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  ```

- マーケットカレンダー操作
  ```python
  from kabusys.data import calendar_management as cm
  from datetime import date
  is_trading = cm.is_trading_day(conn, date(2024,3,15))
  next_day = cm.next_trading_day(conn, date(2024,3,15))
  ```

- 品質チェックの実行
  ```python
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

ログレベルは環境変数 LOG_LEVEL を使って設定できます（例: INFO/DEBUG）。

---

## 自動環境変数読み込みについて

- kabusys.config モジュールは、プロジェクトルート（.git または pyproject.toml の位置）を起点に `.env` → `.env.local` の順で環境変数を自動読み込みします。
- OS 環境変数は `.env` の値で上書きされません。`.env.local` は既存の OS 環境変数を保護しつつ上書き可能です。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

リポジトリ内の主なファイル/ディレクトリ構成（抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                   -- 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py         -- J-Quants API クライアント & DuckDB 保存
      - news_collector.py         -- RSS ニュース収集・保存
      - schema.py                 -- DuckDB スキーマ定義・初期化
      - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
      - calendar_management.py    -- マーケットカレンダー管理・バッチ
      - audit.py                  -- 監査ログ（signal/order/execution）
      - quality.py                -- データ品質チェック
    - strategy/
      - __init__.py               -- 戦略層（拡張ポイント）
    - execution/
      - __init__.py               -- 発注/ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py               -- 監視周り（拡張ポイント）

上記のモジュールは、戦略層（strategy）・発注層（execution）・監視（monitoring）を組み合わせることで自動売買システム全体を構成することを想定しています。

---

## 注意点 / 運用上のヒント

- DuckDB はローカルファイルを想定した軽量 DB です。本番ではファイル排他やバックアップを考慮してください。
- J-Quants API のレート制限（120 req/min）に従うように実装されていますが、別の API を併用する場合は注意してください。
- news_collector は外部 URL を扱うため、タイムアウトや例外（URLError 等）を適切にハンドリングして運用してください。
- 日次 ETL は各ステップで例外を捕捉し継続する設計です。重大な問題は QualityIssue の severity="error" によって検出されます。運用側でアラートや停止判断を実装してください。
- すべてのタイムスタンプは UTC を想定して保存・扱う設計になっています（監査モジュール等で明示的に SET TimeZone='UTC' を実行します）。

---

この README はライブラリの概要・主要な利用方法をまとめたものです。戦略実装部（strategy）やブローカー連携（execution）についてはプロジェクト固有の要件に合わせて拡張してください。必要であればサンプルスクリプトや CI/CD、デプロイ手順のテンプレートも追加できます。