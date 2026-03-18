# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得・ETL、ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ（注文→約定トレーサビリティ）など、トレーディング基盤で必要になる基本機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、J-Quants や RSS 等の外部データソースから市場データ・財務データ・ニュースを収集し、DuckDB に格納・管理するためのモジュール群です。さらに、日次 ETL パイプライン、データ品質チェック、マーケットカレンダーの管理、監査ログ（発注／約定のトレース）機能を提供します。

設計上の主なポイント:
- J-Quants API に対してレート制限（120 req/min）とリトライ（指数バックオフ・401時自動リフレッシュ）を実装
- データの冪等性確保（DuckDB の ON CONFLICT / DO UPDATE、ON CONFLICT DO NOTHING 等）
- News Collector は SSRF / XML Bomb / 大容量レスポンス等の安全対策を実装
- ETL は差分更新・バックフィル・品質チェックを備え、障害耐性を重視

---

## 主な機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local 自動ロード（プロジェクトルートに基づく）、必須値チェック
  - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL 等

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務指標、JPX マーケットカレンダーの取得
  - レートリミット管理、リトライ、トークン自動リフレッシュ、取得時刻(fetched_at) 記録
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を収集し raw_news に保存、記事ID は正規化 URL の SHA-256（先頭32文字）
  - トラッキングパラメータ除去、コンテンツ前処理、SSRF 対策、gzip サイズチェック、XML の安全パーシング
  - 銘柄コード抽出 & news_symbols への紐付け

- データスキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema() により DuckDB の初期化（テーブル・インデックス作成）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: カレンダー取得 → 株価差分取得（バックフィル）→ 財務差分取得 → 品質チェック
  - 差分取得のヘルパー（最終取得日の検出など）

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - 夜間バッチ（calendar_update_job）で JPX カレンダー差分更新

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合（未来日・非営業日データ）を検出
  - QualityIssue 型で詳細を返す

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等、発注〜約定フローをトレースするためのテーブル群
  - init_audit_db / init_audit_schema による初期化、UTC タイムゾーン固定

---

## セットアップ手順

前提: Python 3.9+ を想定（コード上は型ヒントに Python 3.10 以降の表記が含まれている箇所があります）。必要に応じて仮想環境を作成してください。

1. リポジトリをクローン（またはプロジェクトのルートで作業）
   - 仮にプロジェクトルートがある想定

2. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - 他に必要なパッケージがある場合は requirements.txt を用意している想定であれば pip install -r requirements.txt

4. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を作成することで自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可）。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意（デフォルトあり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DB スキーマ初期化
   - Python REPL やスクリプトで以下を実行:
     ```
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")  # ファイルパスは settings.duckdb_path と合わせてください
     ```
   - 監査ログ専用 DB を分けて作る場合:
     ```
     from kabusys.data.audit import init_audit_db
     init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡易ガイド・コード例）

以下は最小限の利用例です。詳細は各モジュールを参照してください。

- 日次 ETL を実行する例:
  ```
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（まだ行っていなければ）
  conn = init_schema("data/kabusys.duckdb")

  # 日次 ETL 実行（target_date を指定しなければ今日）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する例:
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # sources を省略するとデフォルト RSS（Yahoo Finance 等）を使用
  results = run_news_collection(conn, known_codes={"7203","6758", ...})
  print(results)
  ```

- J-Quants から直接データを取得して保存する（テスト用）:
  ```
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  token = get_id_token()  # settings からリフレッシュトークンを使って id_token を取得
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print(saved)
  ```

- 監査 DB を初期化する:
  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

注意点:
- J-Quants API はレート制限（120 req/min）を守る必要があります。本クライアントは内部で固定間隔のスロットリングを行います。
- 自動的に環境変数を .env から読み込みますが、テスト時などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル・モジュール）

以下は本コードベースの主要ディレクトリ / ファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動読み込み、settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py
      - RSS 収集、前処理、DB保存、銘柄抽出
    - schema.py
      - DuckDB のスキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, ...）
    - calendar_management.py
      - マーケットカレンダーの判定・更新ロジック
    - audit.py
      - 監査ログ（signal_events, order_requests, executions 等）の初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py  （戦略関連の実装領域）
  - execution/
    - __init__.py  （発注・約定関連の実装領域）
  - monitoring/
    - __init__.py  （監視・メトリクス関連の実装領域）

---

## 運用・開発上の注意点

- 環境変数: 必須値が未設定だと settings プロパティで ValueError が発生します。 .env.example を用意して環境を整備してください。
- DB 初期化: init_schema() は冪等です。既存テーブルがあればスキップされます。
- テスト可能性: jquants_client は id_token を注入可能、news_collector の _urlopen などはテスト用にモックしやすい設計になっています。
- セキュリティ: news_collector は SSRF 対策、defusedxml の利用、レスポンスサイズ制限等を施していますが、実運用では追加のネットワーク制約（プロキシ、ファイアウォール）や認証周りの管理を強化してください。
- 運用環境: KABUSYS_ENV を `live` にすると実取引相当の挙動を期待するコード分岐を行う想定です。paper_trading / development と用途に応じて設定を切り替えてください。

---

もし README に追加したい内容（例: .env.example の完全なテンプレート、CI/CD 実行手順、詳細な API 使用例、ユニットテストの実行方法など）があれば教えてください。必要に応じて追記します。