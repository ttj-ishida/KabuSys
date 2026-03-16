# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得、ETL、データ品質チェック、DuckDB スキーマ定義、監査ログなど、自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を主目的とした Python パッケージです：

- J-Quants API からの市場データ（株価日足、四半期財務、JPX カレンダー）取得
- DuckDB によるデータ永続化（Raw → Processed → Feature → Execution の多層スキーマ）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 発注/監査ログ（order_request / executions 等）のスキーマおよび初期化

設計上のポイント：

- API レート制御（120 req/min）とリトライ（指数バックオフ）を実装
- トークンの自動リフレッシュ（401 を受けた場合の自動再取得）
- データ取得時刻（fetched_at）を UTC で記録して Look-ahead bias を抑制
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）を前提

---

## 機能一覧

- settings（環境変数ラッパー）
  - 必須/オプション設定の取得、検証（KABUSYS_ENV / LOG_LEVEL の検証含む）
  - .env/.env.local の自動読み込み（プロジェクトルート検出）
- data/jquants_client
  - get_id_token（リフレッシュトークンから id_token を取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_* 関数で DuckDB に冪等保存
- data/schema
  - DuckDB のスキーマ定義（raw/processed/feature/execution）と初期化関数 init_schema
  - get_connection（既存 DB へ接続）
- data/pipeline
  - 差分 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - 日次 ETL エントリポイント run_daily_etl（品質チェック統合）
- data/quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（すべての品質チェックを実行）
- data/audit
  - 監査用テーブル定義（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db（監査用初期化）
- その他
  - execution, strategy, monitoring パッケージ（プレースホルダ）

---

## セットアップ手順

※ プロジェクトは src レイアウトを採用しています。開発環境での例を示します。

1. Python 仮想環境（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 必要パッケージをインストール

   pip install duckdb

   （他に必要な依存がある場合は requirements.txt / pyproject.toml に従ってください）

3. ソースを editable インストール（任意）

   pip install -e .

4. 環境変数設定

   プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（.git または pyproject.toml を基準にプロジェクトルートを検出）。自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（抜粋）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite ファイルパス（監視/モニタリング用、省略時: data/monitoring.db）
   - KABUSYS_ENV: environment（development / paper_trading / live、省略時: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、省略時: INFO）

   例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
   KABU_API_PASSWORD="your_kabu_password"
   SLACK_BOT_TOKEN="xoxb-..."
   SLACK_CHANNEL_ID="C01234567"
   DUCKDB_PATH="data/kabusys.duckdb"
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化

   DuckDB スキーマを作成します（data/schema.init_schema を使用）:

   Python REPL / スクリプト例:

   from kabusys.data.schema import init_schema
   from kabusys.config import settings
   conn = init_schema(settings.duckdb_path)

   または:

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

---

## 使い方

以下は主要ユースケースの例です。

- DuckDB スキーマの初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 監査ログ（audit）テーブルの初期化（既存接続へ追加）

  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)

- J-Quants からデータを直接取得（単体呼び出し）

  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って id_token を得る
  records = fetch_daily_quotes(id_token=token, code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))

- ETL 日次実行（run_daily_etl）

  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルト: target_date=今日, 品質チェック実行
  print(result.to_dict())

  run_daily_etl は市場カレンダー→株価→財務→品質チェックの順で実行し、各ステップは独立してエラーハンドリングされます。結果は ETLResult オブジェクトで返り、has_errors / has_quality_errors 等のプロパティがあります。

- 品質チェックのみ実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- トークン更新や低レベル API 呼び出しは jquants_client の get_id_token, _request を使って行います（基本的には公開関数を利用してください）。API 呼び出しは内部でレート制御とリトライを行います。

---

## 注意点・運用メモ

- 自動環境読み込み
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を自動検出して `.env` と `.env.local` を読み込みます。OS 環境変数は保護され、`.env.local` は OS 環境変数を上書きしない（ただし override=True の挙動で環境変数以外は上書き可）。
  - 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 環境の検証
  - KABUSYS_ENV は development / paper_trading / live のいずれかでないとエラーになります。
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかでないとエラーになります。

- DuckDB
  - init_schema は冪等で、存在しない親ディレクトリを自動作成します。
  - 監査ログは init_audit_schema で追加できます（UTC タイムゾーン設定を行います）。

- API レートとリトライ
  - J-Quants API は 120 req/min に制限されています。jquants_client はこれに合わせた固定間隔スロットリングを行います。
  - リトライは最大 3 回、408/429/5xx 等は再試行の対象になります。429 時は Retry-After を尊重します。
  - 401 が返ってきた場合は id_token を自動リフレッシュして 1 回だけ再試行します。

---

## ディレクトリ構成

（プロジェクトルートに `src/` 配下の典型的な構成）

- src/
  - kabusys/
    - __init__.py
    - config.py              # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py    # J-Quants API クライアント（取得/保存）
      - schema.py           # DuckDB スキーマ定義・初期化
      - pipeline.py         # ETL パイプライン（差分更新・日次 ETL）
      - audit.py            # 監査ログ用 DDL / 初期化
      - quality.py          # データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py         # 戦略関連（プレースホルダ）
    - execution/
      - __init__.py         # 発注・実行関連（プレースホルダ）
    - monitoring/
      - __init__.py         # 監視・メトリクス（プレースホルダ）

README / ドキュメント想定ファイル（別途）:
- DataSchema.md
- DataPlatform.md

---

もし README に追加したい内容（CI やデプロイ方法、詳細なテーブル定義ドキュメント、実運用時の注意点、サンプル ETL 定期実行（cron/systemd）例など）があれば指示してください。必要に応じて README を拡張して、より具体的なコマンドやコード例を追加します。