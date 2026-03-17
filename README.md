# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。  
J-Quants / JPX の市場データや RSS ニュースを収集し、DuckDB に蓄積、ETL・品質チェック・監査ログの管理までを行うコンポーネントを提供します。戦略・発注・監視層の基盤機能を含むプロジェクトのコア部分です。

## 概要
- J-Quants API を用いた株価（日足）・財務データ・マーケットカレンダーの取得と保存
- RSS フィードからのニュース収集と記事→銘柄の紐付け
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取り込み、バックフィル、品質チェック）
- 監査ログ（signal → order_request → executions のトレースを保証）
- セキュリティ・信頼性面の配慮（API レート制御、リトライ、SSRF対策、XMLパースの安全化 等）

本 README はコードベース（src/kabusys 以下）の主要機能と使い方をまとめたものです。

---

## 機能一覧
- 環境変数/設定管理
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
  - 必須値の取得とバリデーション（KABUSYS_ENV, LOG_LEVEL 等）
- J-Quants クライアント（kabusys.data.jquants_client）
  - ID トークン取得（refresh token から）
  - 日足（OHLCV）、財務四半期データ、マーケットカレンダー取得（ページネーション対応）
  - レートリミッタ（120 req/min）・リトライ（指数バックオフ、401 時トークン自動更新）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事 ID は SHA-256（先頭32文字）
  - SSRF 防止（スキーム検証、リダイレクト時のホストチェック、プライベートIP拒否）
  - 受信サイズ制限・gzip 解凍後サイズチェック、DuckDB へ一括挿入（INSERT ... RETURNING）
  - テキストからの銘柄コード抽出（既知コードとの突合）
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス作成、init_schema(db_path) による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（market calendar → prices → financials → 品質チェック）
  - 差分更新・backfill・品 質チェック統合
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job による夜間差分更新
- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を収集
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のテーブルとインデックス
  - init_audit_schema / init_audit_db による初期化（UTC 時刻固定）

---

## セットアップ手順

前提:
- Python 3.10+ を想定（コードは型ヒントに Union 型などを使用）
- DuckDB ライブラリが必要
- defusedxml が必要

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール  
   （プロジェクトに requirements.txt が無い場合の最小例）
   pip install duckdb defusedxml

   実際の環境では以下のようなパッケージが必要になる可能性があります:
   - duckdb
   - defusedxml
   - （ロギングや HTTP クライアントを使う場合は追加パッケージ）

4. 環境変数設定  
   プロジェクトルートに `.env` を作成します。自動で読み込まれます（ただしテスト時などに無効化可）。
   必須の環境変数（一例）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_station_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>

   任意・デフォルト:
   - KABUSYS_ENV=development | paper_trading | live  （デフォルト: development）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db
   - LOG_LEVEL=INFO

   サンプル `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

   自動読み込みを無効にする場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. スキーマ初期化（DuckDB）
   python -c "from kabusys.data.schema import init_schema; from kabusys.config import settings; init_schema(settings.duckdb_path)"

---

## 使い方（主なコード例）

- DuckDB スキーマの初期化

  ```
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  ```

- 監査ログ用 DB（別ファイル）を初期化

  ```
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL の実行（デフォルトは今日）

  ```
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- カレンダー夜間更新ジョブ

  ```
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集（既知銘柄セットを与えて紐付けを行う例）

  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  result = run_news_collection(conn, known_codes=known_codes)
  print(result)  # {source_name: 新規保存件数}
  ```

- J-Quants から直接データ取得（テストやデバッグ）

  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックの実行

  ```
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 設定/運用上の注意
- 環境（KABUSYS_ENV）は "development", "paper_trading", "live" のいずれかのみ許容されます。
- LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のいずれか。
- J-Quants のレート制限（120 req/min）を尊重するためモジュール内部でスロットリングが行われます。大量取得を行う際は注意してください。
- news_collector は SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクト時検証）や XML 安全化（defusedxml）を組み込んでいますが、外部 URL を扱う際は常に注意してください。
- DuckDB はファイル単位のロックや並行アクセスの制約があるため、複数プロセスからの同時書き込み等は運用設計に注意してください。
- audit テーブルは UTC タイムゾーンでの保存を前提としています（init_audit_schema が TimeZone を UTC に設定します）。

---

## ディレクトリ構成
（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（取得 & 保存）
    - news_collector.py                — RSS ニュース取得・保存・銘柄抽出
    - schema.py                        — DuckDB スキーマ定義・init_schema
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py           — カレンダー管理・営業日ユーティリティ
    - audit.py                         — 監査ログスキーマ（signal/order_request/execution）
    - quality.py                       — データ品質チェック
  - strategy/
    - __init__.py                       —（戦略層のプレースホルダ）
  - execution/
    - __init__.py                       —（発注/実行層のプレースホルダ）
  - monitoring/
    - __init__.py                       —（監視・メトリクスのプレースホルダ）

例（ツリー）:
```
src/kabusys/
├── __init__.py
├── config.py
├── data
│   ├── __init__.py
│   ├── audit.py
│   ├── calendar_management.py
│   ├── jquants_client.py
│   ├── news_collector.py
│   ├── pipeline.py
│   ├── quality.py
│   └── schema.py
├── execution
│   └── __init__.py
├── monitoring
│   └── __init__.py
└── strategy
    └── __init__.py
```

---

## 追加情報 / 貢献
- ドキュメント（DataPlatform.md 等）や依存管理ファイルがある場合、それに準拠して使用してください。
- 新機能やバグ修正は PR ベースでの貢献を想定しています。ユニットテストと型チェック（mypy 等）を含めると保守性が向上します。

---

必要であれば、この README に「requirements.txt」の推奨内容、より具体的な運用手順（cron による nightly ETL、Docker 化の方針、Slack 通知の例など）を追加できます。どの部分を拡張しますか？