# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（データ取得・ETL・スキーマ・監査・品質チェックの基盤）。  
このリポジトリは主に以下を提供します。

- J-Quants API からのデータ取得クライアント（株価日足、四半期財務、マーケットカレンダー）
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得・バックフィル・保存・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

この README はコードベース（src/kabusys 以下）の機能と使い方をまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（導入例）
- 環境変数と .env の取り扱い
- 主要モジュールの説明
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買のデータ基盤・ETL・監査の基礎機能を提供する Python パッケージです。
- データ取得は主に J-Quants API を用い、取得した生データを DuckDB に保存します。
- データは Raw → Processed → Feature → Execution の多層スキーマで管理され、監査ログ（signal / order_request / executions）も別途管理できます。
- 設計方針として「冪等性」「Look-ahead Bias の回避（fetched_at 等の記録）」「API レート制限遵守」「リトライ/トークン自動更新」「品質チェックによる健全性確認」を重視しています。

---

機能一覧
- J-Quants クライアント
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（四半期財務）
  - fetch_market_calendar（JPX カレンダー）
  - get_id_token（リフレッシュトークンから id_token 取得、401 発生時自動リフレッシュ）
  - レート制限（120 req/min）、指数バックオフ・リトライ、401 自動リフレッシュ対応
- DuckDB スキーマ管理
  - init_schema(db_path)：全テーブル（Raw/Processed/Feature/Execution）を作成
  - get_connection(db_path)：既存 DB に接続
  - init_audit_schema(conn) / init_audit_db(db_path)：監査ログ用テーブルの初期化
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(conn, target_date=None, ...)：市場カレンダー取得→株価・財務 ETL→品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
  - 差分更新（DB の最終取得日を参照）、バックフィル（デフォルト 3 日）
- 品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks：まとめて実行し QualityIssue のリストを返す
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルを定義
  - 冪等キー（order_request_id, broker_execution_id 等）を想定した設計

---

セットアップ手順（ローカル開発）
前提: Python 3.10+（パッケージ内で | 型注釈を使用しているため）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - duckdb 等が必要です。セットアップはプロジェクトの pyproject.toml / requirements.txt に従ってください。
   - 例（最小）:
     - pip install duckdb

   開発中は編集を反映するために editable install することが多いです:
   - pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に .env および .env.local を置くと自動読み込みされます（後述の自動読み込みルールを参照）。
   - テスト時など自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

環境変数（主要）
以下はコード内で参照される主な環境変数です（.env に設定する想定）。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。get_id_token() により id_token を取得します。
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意, 有効値: development, paper_trading, live)（settings.env）
- LOG_LEVEL (任意, 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL)

.env のパースルール（主なポイント）
- 空行と先頭が # の行は無視
- export KEY=val 形式に対応
- 値にクォート（' or "）がある場合はエスケープ処理を行い、対応する閉じクォートまでを値として扱う
- クォートなしの場合は '#' が現れ、その直前がスペースまたはタブであればコメントとみなす
- 自動ロード順: OS 環境 > .env.local (override=True) > .env (override=False)
- 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行う。見つからない場合はスキップ。

---

使い方（簡単な導入例）
以下は最小限の Python スニペット例です。

1) DuckDB スキーマの初期化
- 永続 DB を作成してスキーマを初期化する例:

from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返す

- インメモリ DB:
conn = schema.init_schema(":memory:")

2) 監査ログスキーマを既存接続に追加
from kabusys.data import audit
audit.init_audit_schema(conn)

3) 日次 ETL の実行
from kabusys.data import pipeline

result = pipeline.run_daily_etl(conn)
# ETLResult の概要:
print(result.to_dict())

4) 個別 ETL を実行（例: 株価のみ）
from datetime import date
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())

5) J-Quants API を直接呼ぶ（id_token の自動管理あり）
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
# 保存:
jq.save_daily_quotes(conn, records)

ログと環境
- settings.log_level によりログレベルを制御できます（環境変数 LOG_LEVEL）。
- settings.is_live / is_paper / is_dev で環境モードを判定できます（KABUSYS_ENV）。

---

主要モジュールの説明（役割）
- kabusys.config
  - 環境変数の読み込みと settings オブジェクトを提供
  - 自動 .env ロード、必須キーチェック（_require）
  - settings から DB パスや API トークン等を取得
- kabusys.data.jquants_client
  - J-Quants API の HTTP 呼び出しラッパー
  - rate limiting（120 req/min、固定間隔スロットリング）
  - リトライ（最大 3 回）・指数バックオフ・401 時の id_token 自動更新
  - fetch_* / save_* 関数群（保存は DuckDB への ON CONFLICT DO UPDATE による冪等性）
- kabusys.data.schema
  - DuckDB の DDL（Raw / Processed / Feature / Execution テーブル）を定義
  - init_schema() で一括作成、get_connection() で既存 DB に接続
- kabusys.data.pipeline
  - ETL の Orchestrator（差分取得、backfill、品質チェック）
  - run_daily_etl() が主要入口
  - ETL の各段階は独立して例外処理され、1 ステップ失敗でも他は継続
- kabusys.data.quality
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - QualityIssue を返し、呼び出し元で重大度に応じた判断をする
- kabusys.data.audit
  - 監査ログテーブル（signal_events, order_requests, executions）の定義と初期化
  - トレーサビリティと冪等性を考慮した設計

---

設計上の重要ポイント（簡潔に）
- API レート制限（120 req/min）を厳守するため内部で RateLimiter を使用
- リトライ戦略: 408 / 429 / 5xx に対して指数バックオフ（最大 3 回）
- 401 はトークン期限切れとみなし自動的にリフレッシュ（1 回のみ）
- データ取得時間（fetched_at）は UTC で保存して Look-ahead Bias を回避可能に
- DuckDB への保存は ON CONFLICT DO UPDATE により冪等に実施
- ETL は差分更新（最終取得日から backfill 日数分再取得）を行う

---

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（取得 & 保存）
      - schema.py          — DuckDB スキーマ定義・init_schema / get_connection
      - pipeline.py        — ETL パイプライン（run_daily_etl 等）
      - audit.py           — 監査ログスキーマと初期化
      - quality.py         — データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要テーブル（抜粋）
- Raw 層: raw_prices, raw_financials, raw_news, raw_executions
- Processed 層: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- Feature 層: features, ai_scores
- Execution 層: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- Audit 層: signal_events, order_requests, executions

---

開発・テスト時のヒント
- 自動で .env を読み込むため、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部に影響を与えないようにできます。
- ETL の単体テストでは pipeline の関数に id_token を注入してテストしやすく設計されています。
- init_schema(":memory:") でインメモリ DB を用いて高速なユニットテストが可能です。

---

ライセンス / 貢献
- 本 README にライセンス情報は含まれていません。実際のリポジトリに LICENSE ファイルがあればそちらを参照してください。  
- バグ修正・機能追加は PR ベースで歓迎します。変更前に設計方針（冪等性・トレーサビリティ・UTC タイムスタンプ等）を確認してください。

---

追加の質問・使い方の詳細（例: ストラテジー層との連携、broker API との統合、監視周りの実装例など）が必要であれば、実際に行いたいユースケースを教えてください。具体的なコード例やワークフロー図を用意します。