# KabuSys — 日本株自動売買基盤 (README)

本リポジトリは「KabuSys」と呼ばれる日本株向けの自動売買・データ基盤の実装群です。J-Quants や RSS を使ったデータ取得、DuckDB を用いたスキーマ設計、ETL パイプライン、ニュース収集、監査ログ等の主要機能を含みます。

---

## プロジェクト概要

KabuSys は次の目的を持つライブラリ／ミニプラットフォームです。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得して DuckDB に保存する。
- RSS フィードからニュースを収集して前処理・DB保存、銘柄コードとの紐付けを行う。
- ETL（差分更新・バックフィル・品質チェック）を実行する日次パイプラインを提供する。
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマを提供する。
- マーケットカレンダーや営業日判定、品質チェックなどのユーティリティを備える。

設計上のポイント：
- API レート制限とリトライ（指数バックオフ）を実装
- トークン自動リフレッシュ（401 時に一度リトライ）
- DuckDB への冪等保存（ON CONFLICT を利用）
- SSRF や XML Bomb/メモリDoS 対策を意識した実装（news_collector）

---

## 機能一覧

- J-Quants クライアント
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - レートリミット制御、再試行、ID トークン自動更新
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化（init_schema）
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（差分取得・バックフィル・品質チェック）
- ニュース収集
  - RSS の取得・パース・前処理（URL除去・空白正規化）・ID生成・DB保存（save_raw_news）
  - 銘柄コード抽出・紐付け（extract_stock_codes, save_news_symbols）
- 品質チェック
  - 欠損データ、スパイク（急騰・急落）、重複、日付不整合の検出（quality.run_all_checks）
- マーケットカレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間差分更新ジョブ）
- 監査・トレーサビリティ
  - signal_events, order_requests, executions 等の監査スキーマ初期化（init_audit_schema / init_audit_db）
- 環境変数管理
  - .env 自動読み込み（プロジェクトルート検出）、必須 env の取得ラッパ（Settings）

---

## 前提（Prerequisites）

- Python 3.9+
- 必要パッケージ（例、pip 経由でインストール）
  - duckdb
  - defusedxml
  - （必要に応じて他のライブラリを追加）
- J-Quants のリフレッシュトークン、および kabu（kabuステーション）や Slack 用の認証情報

（環境によっては virtualenv / venv を利用することを推奨します）

---

## セットアップ手順

1. リポジトリをクローン／配置

   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（任意）

   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存ライブラリをインストール（例）

   pip install duckdb defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml に依存をまとめてください。

4. 環境変数設定（.env ファイル or OS 環境変数）

   プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須（Settings 参照）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   オプション（デフォルト値あり）:
   - KABUSYS_ENV (development | paper_trading | live)  — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 env ロードを無効化（テスト時に使用）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 初期化 / 使い方（簡単な手順とサンプル）

以下は Python スクリプトや REPL からの利用例です。

- DuckDB スキーマ初期化

  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
  ```

- 監査ログ（audit）スキーマを追加

  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # 既存の conn に監査テーブルを追加
  ```

- J-Quants トークン取得（手動）

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # Settings の JQUANTS_REFRESH_TOKEN を使用
  ```

- 日次 ETL 実行（市場カレンダー→株価→財務→品質チェック）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行（RSS 収集と DB 保存）

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes があれば銘柄抽出と紐付けを行う（例: {'7203', '6758', ...}）
  stats = run_news_collection(conn, known_codes=set(['7203','6758']))
  print(stats)  # {source_name: saved_count, ...}
  ```

- マーケットカレンダー夜間更新ジョブ

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- 品質チェック（個別実行または全チェック）

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None, reference_date=None)
  for issue in issues:
      print(issue)
  ```

---

## 重要な設計／動作上の注意

- J-Quants API は 120 req/min のレート制限に合わせたスロットリングを実装しています。過度な並列リクエストは避けてください。
- HTTP リクエストで 401 を受け取った場合、ID トークンを自動リフレッシュして 1 回だけリトライします。
- news_collector は XML / HTTP に対するセキュリティ対策（defusedxml、SSRF 防止、レスポンスサイズ制限等）を行っています。
- DuckDB の初期化関数（init_schema）は冪等（存在しないテーブルのみ作成）です。
- ETL は Fail-Fast ではなく「各ステップごとにエラーを収集して継続」する設計です。run_daily_etl の戻り値（ETLResult）で品質異常やエラーを確認してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（取得・保存）
    - news_collector.py        — RSS ニュース収集・保存ロジック
    - schema.py                — DuckDB スキーマ定義と初期化
    - pipeline.py              — ETL パイプラインとユーティリティ
    - calendar_management.py   — マーケットカレンダー管理ロジック
    - audit.py                 — 監査ログ（signal/order/execution）スキーマ
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は実装ファイルの抜粋です。strategy, execution, monitoring の実装は別途展開されます。）

---

## 環境変数（要約）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルトあり:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — default: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

settings オブジェクトからこれらにアクセスできます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 追加メモ / 開発者向けヒント

- テスト時に .env の自動読み込みを無効にしたい場合、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ニュース記事の重複防止は、正規化 URL の SHA-256（先頭32文字）を記事 ID として利用しています。
- DuckDB を用いるため、分析や SQL ベースの ETL が高速に実行できます。
- ETL の差分計算は DB に格納された最終日付を基準に自動算出します（バックフィル日数設定あり）。

---

必要ならば README に「インストール手順（pyproject.toml に基づく）」「より詳細な API リファレンス」「運用手順（cron / Airflow 等での日次実行例）」を追記できます。どの部分を拡張したいか教えてください。