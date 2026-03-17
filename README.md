# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants や RSS を利用したデータ収集、DuckDB によるスキーマ管理、ETL パイプライン、ニュース収集・銘柄紐付け、監査ログなどを備えます。

## 概要
KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主に以下を提供します。

- J-Quants API からの株価（日足）、財務データ、マーケットカレンダーの取得（レート制限・リトライ・トークン自動更新対応）
- RSS フィードからのニュース収集と DuckDB への冪等保存、記事と銘柄コードの紐付け
- DuckDB を用いたスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理、監査ログテーブル（シグナル→発注→約定のトレーサビリティ）

設計方針として、API レート制限遵守、冪等性、Look-ahead バイアス防止（fetched_at 記録）、メモリ/SSRF 対策などを重視しています。

## 主な機能一覧
- data.jquants_client
  - get_id_token / fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - RateLimiter、リトライ（指数バックオフ）、401 時の自動リフレッシュ対応
- data.news_collector
  - RSS 取得（SSRF 防止、gzip 対応、XML セーフパーサ）
  - 記事の正規化・ID 生成（URL 正規化→SHA-256）
  - raw_news / news_symbols への一括挿入（トランザクション・チャンク分割）
  - 銘柄コード抽出・一括紐付け
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution のテーブル・インデックス）
  - init_schema(db_path) による初期化
- data.pipeline
  - 差分更新 / backfill 対応の ETL（run_daily_etl）
  - 品質チェック（data.quality）との連携
- data.calendar_management
  - 営業日判定・next/prev_trading_day・カレンダー夜間更新ジョブ
- data.audit
  - 監査用テーブル（signal_events, order_requests, executions）と初期化関数
- data.quality
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）

## 必要要件
- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（標準ライブラリの urllib, datetime 等も使用しています。プロジェクト用の requirements.txt は本リポジトリに含まれていないため、pip で上記パッケージを追加してください。）

例:
pip install duckdb defusedxml

## 環境変数 / 設定
KabuSys は .env ファイルまたは環境変数から設定を読み込みます（自動ロード: OS env > .env.local > .env）。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG | INFO | WARNING | ERROR | CRITICAL

設定はコード上で kabusys.config.settings から取得できます。

## セットアップ手順（ローカル開発用）
1. Python を用意（推奨: 3.10+）
2. パッケージをインストール
   - 例: pip install duckdb defusedxml
   - 開発用にパッケージ化されている場合は pip install -e . も可能
3. 環境変数を作成
   - プロジェクトルートに `.env`（または `.env.local`）を作成。例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動読み込みは、config モジュールがプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を検出して行います。

## 初期化（DB スキーマ作成）
DuckDB にテーブルを作成する例:

Python REPL / スクリプト例:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection。以後 ETL 等で使用

監査ログ用（audit）テーブルを追加する:
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

あるいは監査専用 DB を作成:
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")

## 使い方（主要なユースケース）
- 日次 ETL を実行する（株価・財務・カレンダー・品質チェック）
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュース収集ジョブを実行する
  from kabusys.data.news_collector import run_news_collection
  # conn は init_schema で作成した接続
  # known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: set(['7203','6758'])）
  stats = run_news_collection(conn, sources=None, known_codes=None)
  print(stats)  # {source_name: new_count, ...}

- 市場カレンダー夜間更新（calendar_update_job）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)

- J-Quants から直接データを取得して保存する（細かな制御が必要な場合）
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes()
  saved = jq.save_daily_quotes(conn, records)

- 品質チェックを個別に実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)

## 自動環境ロードの動作
- 読み込み順: OS 環境変数 > .env.local（override=True）> .env（override=False）
- 自動ロードを無効にするには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- settings は実行時に環境変数の検証（必須チェック・列挙値チェック）を行います

## 実装上の注意点（開発者向け）
- J-Quants クライアントは 120 req/min のレート制限を守るため固定間隔でスロットリングしています。また 401 時はトークンを自動更新して1回のみリトライします。
- ニュース収集は RSS の XML を defusedxml で安全にパースし、SSRF 回避のためリダイレクト/ホスト検査を行っています。記事 ID は URL 正規化→SHA-256 のハッシュ先頭32文字で生成します。
- DuckDB の INSERT は ON CONFLICT を活用して冪等性を確保しています。ニュースや銘柄紐付けはチャンクサイズで分割してトランザクションで保存します。
- data.pipeline.run_daily_etl は各ステップを独立してエラーハンドリングするため、1ステップの失敗が他に波及しにくい設計です。
- audit の初期化関数はデフォルトで UTC タイムゾーンに固定します（SET TimeZone='UTC'）。

## ディレクトリ構成
リポジトリ内の主なファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                             -- 環境変数・設定読み込み
  - data/
    - __init__.py
    - schema.py                            -- DuckDB スキーマ定義と初期化
    - jquants_client.py                    -- J-Quants API クライアント（取得/保存）
    - pipeline.py                          -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py                    -- RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py               -- マーケットカレンダー管理
    - audit.py                             -- 監査ログ（signal/order/execution）初期化
    - quality.py                           -- データ品質チェック
  - strategy/
    - __init__.py                          -- 戦略用パッケージプレースホルダ
  - execution/
    - __init__.py                          -- 実行（発注）用パッケージプレースホルダ
  - monitoring/
    - __init__.py                          -- 監視用プレースホルダ

（README に示した以外にもユーティリティや補助モジュールが含まれます。）

## 例: 最小ワークフロー
1. 環境変数を準備（.env）
2. スキーマ初期化:
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
3. 日次 ETL 実行:
   from kabusys.data.pipeline import run_daily_etl
   res = run_daily_etl(conn)
   print(res.to_dict())
4. ニュース収集:
   from kabusys.data.news_collector import run_news_collection
   run_news_collection(conn, known_codes=set(['7203','6758']))

## 開発・貢献
- コードは型注釈・ドキュメント文字列を重視して実装されています。ユニットテストや CI を追加して品質を保つことを推奨します。
- セキュリティ面（シークレット管理、SSRF、XML パース等）に配慮した実装が施されていますが、運用時は接続先や権限設定・ネットワーク制限を再確認してください。

---

不明点や追加したい利用例があれば教えてください。README のチュートリアルやサンプルスクリプトを追記できます。