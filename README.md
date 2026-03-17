# KabuSys

日本株向けの自動売買/データパイプライン基盤ライブラリ（KabuSys）。  
J-Quants からのマーケットデータ取得、RSS ニュース収集、ETL パイプライン、データ品質チェック、
マーケットカレンダー管理、監査ログ（トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株自動売買システム向けのデータプラットフォーム部分を実装した Python パッケージです。主に以下を目的としています。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御、リトライ、トークン自動リフレッシュ対応）
- DuckDB を用いたスキーマ（Raw / Processed / Feature / Execution / Audit）の定義と冪等的な保存
- RSS フィードからのニュース収集（SSRF 対策、XML 安全パース、トラッキングパラメータ除去）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・前後営業日の取得）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

パッケージは `src/kabusys` 以下に実装されています。バージョンは __version__ = "0.1.0"。

---

## 主な機能一覧

- J-Quants クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レート制御（120 req/min 固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx 対応）
  - 401 を受信した際の自動トークンリフレッシュ（1回のみ）
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードの収集と前処理（URL 除去、空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）
  - defusedxml による安全な XML パース
  - SSRF 対策（スキーム検査、リダイレクト先検査、プライベート IP 拒否）
  - レスポンスサイズ制限（デフォルト 10MB）
  - DuckDB への冪等保存（INSERT ... RETURNING を利用）

- ETL パイプライン
  - 差分更新（DB の最終取得日から未取得分のみ取得）
  - backfill による数日分の再取得で API の後出し修正を吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行

- カレンダー管理
  - market_calendar を用いた営業日判定、next/prev_trading_day、期間内営業日取得
  - 夜間バッチ更新ジョブ（calendar_update_job）

- 監査ログ / トレーサビリティ
  - signal_events, order_requests, executions などの監査テーブル
  - UTC タイムスタンプ、冪等キー（order_request_id, broker_execution_id など）

- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks で一括実行

---

## システム要件 / 依存関係

- Python 3.10 以上（コードは `|` 型合体など Python 3.10+ 構文を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```
pip install duckdb defusedxml
```

（パッケージ配布があれば `pip install .` や `pip install -e .` を推奨）

---

## 環境変数 / 設定

KabuSys は環境変数または `.env` / `.env.local` による設定をサポートします。プロジェクトルート（.git または pyproject.toml を探索）にある `.env` を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベース
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- システム
  - KABUSYS_ENV (development | paper_trading | live)（デフォルト development）
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

設定は `from kabusys.config import settings` によって取得できます（プロパティ経由）。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb defusedxml
   # またはパッケージ化されていれば:
   # pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成（`.env.example` を参考に）。
   - 必須項目を設定してください（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。

5. DuckDB スキーマ初期化
   Python REPL／スクリプトで以下を実行して DB ファイルを初期化します:

   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path オブジェクト
   conn.close()
   ```

   監査ログテーブルを追加したい場合:

   ```python
   from kabusys.data.audit import init_audit_schema
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   init_audit_schema(conn)
   conn.close()
   ```

---

## 使い方（主要 API / 例）

以下は主要な利用例です。実運用ではログ出力や例外処理、ジョブスケジューラ（cron / Airflow / systemd 等）と組み合わせて利用してください。

- 日次 ETL 実行（株価／財務／カレンダーの差分更新 + 品質チェック）:

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  conn.close()
  ```

- 市場カレンダー夜間更新ジョブ:

  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print("saved:", saved)
  conn.close()
  ```

- RSS ニュース収集（保存 + 銘柄抽出）:

  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  # known_codes = {"7203", "6758", ...}
  result = run_news_collection(conn, known_codes=set())  # known_codes を渡すと銘柄紐付けを行う
  print(result)
  conn.close()
  ```

- J-Quants から直接データを取得して保存（開発用途）:

  ```python
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  from kabusys.config import settings
  from datetime import date

  conn = init_schema(settings.duckdb_path)
  recs = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, recs)
  conn.close()
  ```

- データ品質チェック単体実行:

  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  conn.close()
  ```

注意点:
- J-Quants の認証トークンは refresh_token を設定し、ライブラリ内で id_token を自動取得・キャッシュします。401 発生時に自動リフレッシュし1回リトライします。
- NewsCollector は SSRF 対策やレスポンスサイズ制限を実装しており、安全に外部 RSS を取得できます。

---

## ディレクトリ構成

主要ファイル / モジュール一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（取得 & 保存ロジック）
    - news_collector.py         — RSS ニュース収集 / 前処理 / 保存
    - schema.py                 — DuckDB スキーマ定義・初期化
    - pipeline.py               — ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py    — マーケットカレンダー管理（営業日判定・更新ジョブ）
    - audit.py                  — 監査ログ（signal/events/order_requests/executions）
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py               — 発注/実行関連（拡張ポイント）
  - monitoring/
    - __init__.py               — 監視関連（拡張ポイント）

各モジュールは拡張可能な設計になっており、戦略・実行ロジック・モニタリングはプロジェクト固有の実装を追加して利用します。

---

## 開発・運用に関する補足

- 自動環境読み込み
  - `.env`（優先度低）および`.env.local`（優先度高）をプロジェクトルートから自動読み込みします。
  - OS環境変数が優先され、`.env.local` は既存環境変数を上書きできますが、OSの環境変数は保護されます。
  - 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB スキーマは冪等（IF NOT EXISTS / ON CONFLICT など）です。複数プロセスから同時初期化する際は注意してください（通常は単一プロセスで init を行います）。

- ニュース収集ではトラッキングパラメータ除去や URL 正規化を行い、記事 ID の冪等性を担保します。known_codes を渡して銘柄紐付けを行うことで、ニュース → 銘柄 の関連を保存します。

- 品質チェックは「全件収集」設計です。致命的な問題（error）を検出しても run_all_checks は結果を返します。呼び出し側で停止／通知等を行ってください。

---

## 貢献 / カスタマイズポイント

- strategy/ と execution/ はフレームワーク的な拡張ポイントです。独自の戦略実装や発注ロジックはここに追加してください。
- monitoring/ にアラートや Prometheus メトリクスのエクスポータを実装できます。
- ニュースのソースやトラッキング除去ルール、RSS パースの追加ルールは `news_collector.py` を拡張してください。

---

必要であれば、README にサンプル `.env.example`、CI/デプロイ手順、cron / systemd ユニット例、または Airflow DAG のサンプルを追加できます。どの情報を優先して追記しますか？