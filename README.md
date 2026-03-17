# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants API や RSS フィードからデータを取得して DuckDB に格納し、ETL・データ品質チェック・マーケットカレンダー管理・監査ログなどを提供します。

## プロジェクト概要
KabuSys は以下の目的を持つモジュール群です。
- J-Quants API から株価（OHLCV）・財務データ・JPX カレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集し、記事と銘柄の紐付けを行う
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）を提供
- マーケットカレンダーの管理（営業日判定・前後営業日取得）
- 監査ログ（シグナル → 発注 → 約定 のトレーサビリティ）を実現する監査DB初期化機能
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴:
- J-Quants API のレート制限（120 req/min）遵守（固定間隔スロットリング）
- リトライ（指数バックオフ、最大3回）、401 受信時はトークン自動リフレッシュ
- DuckDB への保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）
- RSS 収集は SSRF 対策・サイズ制限・XML ハードニング（defusedxml）を実装

---

## 主な機能一覧
- data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（refresh token から id token 取得）
  - save_* 系メソッドで DuckDB に冪等保存
- data.news_collector
  - RSS 取得（URL 正規化、トラッキング除去、SSRF 防止、gzip 対応）
  - raw_news への一括保存（INSERT ... RETURNING を使用）
  - 記事から銘柄コード抽出・news_symbols への紐付け
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution レイヤ）
  - init_schema(db_path) で初期化
- data.pipeline
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 部分的 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
- data.calendar_management
  - 営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job
- data.audit
  - 監査ログ用テーブルの初期化（init_audit_schema / init_audit_db）
- data.quality
  - check_missing_data／check_spike／check_duplicates／check_date_consistency
  - run_all_checks（品質問題の集計）

---

## セットアップ手順（開発環境向け）
前提: Python 3.10+ を想定（型ヒントで | を使用）。適宜バージョンを調整してください。

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <repo>

2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)

3. 必要なパッケージをインストール
   (プロジェクトに requirements.txt がない場合は少なくとも以下を入れてください)
   pip install duckdb defusedxml

   （その他、ログや HTTP 周りの拡張を使う場合は適宜追加してください）

4. パッケージを開発モードでインストール（任意）
   pip install -e .

5. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (オプション, default: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (オプション, default: data/kabusys.duckdb)
   - SQLITE_PATH (オプション, default: data/monitoring.db)
   - KABUSYS_ENV (development / paper_trading / live, default: development)
   - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（抜粋例）
以下はライブラリ API の代表的な利用例です。実運用ではエラーハンドリング・ログ設定を追加してください。

1. DuckDB スキーマ初期化
   Python REPL / スクリプト内で:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査DBを別ファイルに作る場合:
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

2. 日次 ETL 実行（全体）
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection, init_schema

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

   run_daily_etl は以下を順に行います:
   - カレンダー ETL（先読み）
   - 株価（差分 + backfill）
   - 財務（差分 + backfill）
   - 品質チェック（run_quality_checks=True なら実行）

3. RSS ニュース収集の実行
   from kabusys.data.news_collector import run_news_collection
   conn = init_schema("data/kabusys.duckdb")
   known_codes = {"7203", "6758", "9432"}  # 既知銘柄コードセット
   results = run_news_collection(conn, known_codes=known_codes)
   print(results)  # {source_name: 新規保存件数}

4. カレンダー夜間更新ジョブ
   from kabusys.data.calendar_management import calendar_update_job
   conn = init_schema("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"saved: {saved}")

5. J-Quants から直接データ取得して保存
   from kabusys.data import jquants_client as jq
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)

注意点:
- J-Quants API のレート制限（120 req/min）を内部で遵守しますが、並列化する場合は注意してください。
- get_id_token は refresh token を元に id token を取得し、401 時は 1 回自動リフレッシュして再試行します。
- RSS 収集は URL スキーム検証 / プライベートIP 検査を行います（SSRF 対策）。

---

## ディレクトリ構成（抜粋）
以下は主要なモジュール／ファイル構成です（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                         # 環境変数・設定の読み込み/検証
  - data/
    - __init__.py
    - schema.py                        # DuckDB スキーマ定義・初期化
    - jquants_client.py                # J-Quants API クライアント（取得・保存）
    - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
    - news_collector.py                # RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py           # マーケットカレンダー管理・判定ロジック
    - audit.py                         # 監査ログスキーマ（signal/order/execution）
    - quality.py                       # データ品質チェック
  - strategy/
    - __init__.py                       # 戦略関連用のプレースホルダ
  - execution/
    - __init__.py                       # 発注・ブローカー連携プレースホルダ
  - monitoring/
    - __init__.py                       # 監視系プレースホルダ

README に載せていない追加モジュール（例: Slack 通知、kabuステーション接続、実際の戦略実装、監視用 DB）を別途用意できます。

---

## 補足 / 運用上の注意
- 自動環境読み込み: config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- データベースファイルのデフォルト: DUCKDB_PATH は `data/kabusys.duckdb`、SQLITE_PATH は `data/monitoring.db`（Settings で確認可能）。
- テスト容易性: 多くの関数は id_token を注入可能／HTTP 周りのオープナーをモック置換可能に設計されています。
- セキュリティ: RSS は defusedxml を利用、URL 検証・プライベートIP検査・レスポンスサイズ制限を実施しています。

---

ご不明な点や README の拡張（例: CI での ETL 実行例、cron/scheduler 連携、実運用の監視設計など）が必要であれば、用途に合わせて追記できます。