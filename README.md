# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集、データ品質チェック、監査ログ（発注→約定のトレース）など、運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持ったコンポーネントを集約したパッケージです。

- J-Quants API からの市場データ（株価日足、財務、マーケットカレンダー）取得
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集および記事と銘柄コードの紐付け
- マーケットカレンダー管理（営業日/半日/SQ判定、夜間更新ジョブ）
- 監査ログ（信号→発注要求→約定）を残すスキーマと初期化機能
- 設定は環境変数 / .env で管理（自動ロード機能あり）

設計上、API のレート制限やリトライ、Look-ahead bias の防止、冪等性（ON CONFLICT）などに配慮しています。

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - レート制御、リトライ、401 自動リフレッシュ、fetched_at 記録
- data.schema
  - DuckDB のスキーマ定義（raw / processed / feature / execution 層）
  - init_schema(db_path) による初期化
- data.pipeline
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新、バックフィル、品質チェック統合
- data.news_collector
  - RSS 取得（SSRF対策、サイズ制限、XML サニタイズ）
  - 記事IDの正規化（URL正規化→SHA-256）
  - raw_news / news_symbols への冪等保存
  - run_news_collection による一括収集ジョブ
- data.calendar_management
  - 営業日判定、前後の営業日取得、期間内の営業日リスト取得
  - calendar_update_job による夜間差分更新
- data.quality
  - 欠損、重複、スパイク（前日比）、日付不整合チェック
  - run_all_checks で一括実行し QualityIssue を返却
- data.audit
  - 監査ログ用テーブル（signal_events, order_requests, executions）と初期化関数
  - init_audit_schema / init_audit_db

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール  
   本リポジトリに pyproject.toml / requirements.txt がある前提で記載します。最低限必要な主要依存は以下です：
   ```
   pip install duckdb defusedxml
   ```
   その他、ログ周りや HTTP クライアントに応じて追加パッケージが必要になることがあります。

4. 環境変数を設定  
   必須環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD — kabuステーション用 API パスワード
   - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID — Slack のチャンネル ID

   標準ではプロジェクトルートの `.env` と `.env.local`（優先順）を自動で読み込みます（CWD ではなくソースファイル位置からプロジェクトルートを探索して読み込み）。自動ロードを無効化する場合は環境変数を設定してください：
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

   .env の例（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DB スキーマ初期化（DuckDB）
   Python REPL もしくはスクリプトで schema を初期化します（例）:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   conn.close()
   ```

6. 監査ログ用スキーマの初期化（任意）
   既存接続に追加する場合:
   ```python
   from kabusys.data import audit, schema
   conn = schema.get_connection("data/kabusys.duckdb")
   audit.init_audit_schema(conn)
   ```

---

## 使い方（基本例）

以下は代表的な利用例です。実運用ではエラーハンドリングやロギングを適切に追加してください。

- 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data import schema, pipeline

  conn = schema.init_schema("data/kabusys.duckdb")  # 初回は init_schema
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  conn.close()
  ```

- J-Quants の ID トークン直接取得（必要なら）
  ```python
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
  ```

- RSS ニュース収集ジョブ
  ```python
  from kabusys.data import schema, news_collector
  conn = schema.get_connection("data/kabusys.duckdb")

  # 収集を行い、戻り値は {source_name: 新規保存数}
  results = news_collector.run_news_collection(conn)
  print(results)
  ```

  銘柄抽出を行う場合は known_codes を渡す（既知の銘柄コードセット）。
  ```python
  known_codes = {"7203", "6758", "9984"}  # 例
  news_collector.run_news_collection(conn, known_codes=known_codes)
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import schema, calendar_management
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data import schema, quality
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date(2026, 1, 1))
  for i in issues:
      print(i)
  ```

---

## 環境変数 / 設定

主要な環境変数と説明:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API 接続パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するフラグ（任意）

注意: 必須変数が未設定の場合、config.Settings のプロパティアクセスで ValueError を投げます。

---

## ディレクトリ構成

（src 以下の主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 管理（自動ロード、Settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存ロジック
    - news_collector.py      — RSS 取得・前処理・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー判定・夜間更新ジョブ
    - audit.py               — 監査ログスキーマと初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連（空パッケージ／拡張ポイント）
  - execution/
    - __init__.py            — 発注/実行関連（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視関連（拡張ポイント）

主要な SQL テーブル（schema.py 参照）:
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- audit 用: signal_events, order_requests, executions

---

## 運用上の留意点 / ベストプラクティス

- API レート制限とリトライ: jquants_client は 120 req/min に合わせた RateLimiter と指数バックオフを備えています。大量取得は分割して行ってください。
- Look-ahead 防止: 外部データの取得時刻（fetched_at）や ETL の target_date の扱いを厳密にして、戦略実行時に未来情報を参照しないように注意してください。
- 冪等性: 保存処理は ON CONFLICT による上書き／無視を基本としています。外部からの DB 更新がある場合は競合を考慮してください。
- ニュース取得のセキュリティ: RSS 取得では SSRF 対策（スキーム検査、プライベート IP ブロック、リダイレクト検査）や XML のデフューズを行っています。
- 品質チェックは Fail-Fast しない設計です。ETL 後に検出した問題を監査ログやアラートへ渡す運用を推奨します。
- 本パッケージは基盤ライブラリであり、実際の売買ロジック（strategy 層）やブローカー接続（execution 層）は拡張して実装することを想定しています。

---

## 例: 最小スクリプト（ETL + ニュース）

```python
from datetime import date
from kabusys.data import schema, pipeline, news_collector

# DB 初期化（初回のみ）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL
res = pipeline.run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

# ニュース収集（既知銘柄セットを渡す例）
known_codes = {"7203", "6758", "9984"}
news_res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(news_res)

conn.close()
```

---

もし README に追加したい実行例、CI / デプロイ手順、より詳細な .env.example、あるいは strategy/execution 層のテンプレートなどがあれば教えてください。必要に応じて追補します。