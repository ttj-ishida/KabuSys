# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群です。J-Quants や RSS フィードからのデータ収集、DuckDB によるデータ格納・スキーマ管理、日次 ETL パイプライン、ニュース収集・銘柄紐付け、監査ログ用スキーマなど、データ基盤とトレース機能を中心に提供します。

-------------------------------------------------------------------------------

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のためのデータ基盤コンポーネント群です。主に以下を提供します。

- J-Quants API クライアント（株価日足 / 財務 / カレンダー取得）  
  - レート制限（120 req/min）とリトライ、トークン自動リフレッシュを内蔵
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑止
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit）
- ETL パイプライン（日次 ETL、差分取得、品質チェック）
- ニュース収集モジュール（RSS 収集・前処理・重複防止・銘柄抽出）
  - SSRF 対策、XML インジェクション対策、受信サイズ制限等の安全対策を実装
- 監査ログ（signal → order_request → execution のトレーサビリティ）

-------------------------------------------------------------------------------

## 機能一覧

- data/jquants_client.py
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- data/news_collector.py
  - RSS の取得（fetch_rss）、記事の正規化、ID 生成、DuckDB への保存（save_raw_news）、
    銘柄紐付け（save_news_symbols / _save_news_symbols_bulk）、テキスト前処理、銘柄抽出
- data/schema.py
  - DuckDB のスキーマ（DDL）一括作成（init_schema）、既存 DB への接続（get_connection）
- data/pipeline.py
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
- data/calendar_management.py
  - 営業日判定、前後の営業日取得、カレンダー夜間更新ジョブ（calendar_update_job）
- data/quality.py
  - 欠損/重複/スパイク/日付不整合チェック（check_missing_data / check_duplicates / check_spike / check_date_consistency / run_all_checks）
- data/audit.py
  - 監査ログ用テーブルの定義・初期化（init_audit_schema / init_audit_db）
- config.py
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）および Settings オブジェクトによる環境変数管理

-------------------------------------------------------------------------------

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型ヒントに `X | Y` を使用）
- duckdb, defusedxml などが必要

1. リポジトリをクローンしてワークディレクトリに移動
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - pyproject.toml / requirements.txt がある想定の場合:
     ```
     pip install -e .
     ```
     または最小限:
     ```
     pip install duckdb defusedxml
     ```
   - ログ送信や Slack 連携等を使う場合は追加ライブラリ（requests, slack-sdk 等）が必要になるかもしれません。

4. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) (デフォルト: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで schema.init_schema を実行して DB を初期化します。
   ```
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

6. 監査ログ用スキーマ初期化（任意）
   ```
   from kabusys.data import audit
   conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

-------------------------------------------------------------------------------

## 使い方（主な例）

以下はライブラリの主要な使い方例です。実際のアプリケーションではエラーハンドリングやログ出力を適切に追加してください。

- 日次 ETL を実行する（最も一般的な利用）:
  ```python
  from kabusys.data import schema, pipeline
  # DB 初期化（初回のみ）
  conn = schema.init_schema("data/kabusys.duckdb")

  # 日次 ETL 実行（target_date を指定しなければ今日）
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュース収集ジョブの実行
  ```python
  from kabusys.data import schema, news_collector
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続

  # ソースをカスタマイズ可。known_codes を渡すと銘柄紐付けも実行
  result = news_collector.run_news_collection(
      conn,
      sources={"yahoo": "https://news.yahoo.co.jp/rss/categories/business.xml"},
      known_codes={"7203", "6758", "9984"},
  )
  print(result)
  ```

- 市場カレンダーの夜間更新ジョブ
  ```python
  from kabusys.data import schema, calendar_management
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved: {saved}")
  ```

- J-Quants API から直接データ取得して保存
  ```python
  from kabusys.data import jquants_client as jq
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  jq.save_daily_quotes(conn, records)
  ```

- 品質チェックの実行
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- jquants_client は API レート・リトライ・トークンリフレッシュを内蔵していますが、実運用では API 利用制限と課金に注意してください。
- news_collector は外部 URL へのアクセスを行うため、ネットワーク制約やセキュリティポリシーに従ってください。

-------------------------------------------------------------------------------

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知に使用
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env 読み込みを無効化

-------------------------------------------------------------------------------

## ディレクトリ構成

主要ファイルとモジュール構成の概略（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数管理・Settings
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント & DuckDB 保存
    - news_collector.py         — RSS ニュース収集・前処理・DB 保存
    - schema.py                 — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー判定・更新ジョブ
    - audit.py                  — 監査ログテーブル定義・初期化
    - quality.py                — データ品質チェック
  - strategy/                    — 戦略層（未実装部分のエントリ）
  - execution/                   — 発注・実行層（未実装部分のエントリ）
  - monitoring/                  — 監視関連（エントリ）

簡易ツリー:
```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   ├─ execution/
   └─ monitoring/
```

-------------------------------------------------------------------------------

## 設計上の注意点・セキュリティ

- jquants_client:
  - API レート制限（120 req/min）を守るため固定間隔スロットリングを実装
  - 408/429/5xx に対して指数バックオフでリトライ（最大 3 回）
  - 401 を受信した場合はリフレッシュトークンを使って id_token を再取得して1回リトライ
  - 取得時刻（fetched_at）を UTC ISO 形式で保存して Look-ahead Bias を抑止

- news_collector:
  - defusedxml を使い XML の脆弱性対策
  - SSRF 対策: リダイレクト先のスキーム検査、プライベート IP/ループバック拒否
  - レスポンスサイズ制限（デフォルト 10MB）や Gzip 解凍後のサイズチェック
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で冪等性を確保
  - トラッキングパラメータ除去、URL 正規化を実施

- DB スキーマ:
  - 多くのテーブルで PRIMARY KEY / CHECK を設けて不整合を防止
  - raw 層は ON CONFLICT DO UPDATE / DO NOTHING を適用して冪等性を担保

-------------------------------------------------------------------------------

## 開発・貢献

- 型アノテーションを多用しているため型チェック（mypy 等）を入れると品質向上に役立ちます。
- 単体テストや統合テストはネットワーク依存が多いため、外部呼び出しをモックして実行してください（news_collector._urlopen の差し替えなどを想定）。

-------------------------------------------------------------------------------

問題や不明点があれば、どの部分を詳しく知りたいか（例: ETL の挙動、スキーマ詳細、API 呼び出しの例、.env の例など）教えてください。必要に応じて README を拡張します。