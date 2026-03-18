README — KabuSys (日本語)
========================

概要
----
KabuSys は日本株向けの自動売買・データ基盤ライブラリです。本リポジトリは主に以下を提供します。

- J-Quants API からの市場データ（株価、財務、JPX カレンダー）取得クライアント
- RSS ベースのニュース収集器とテキスト前処理
- DuckDB を用いたデータスキーマ定義・初期化・ETL パイプライン
- データ品質チェック、カレンダー管理、監査ログ用スキーマ
- 発注・戦略・モニタリング用の名前空間（拡張ポイント）

設計上のポイント:
- API レート制限厳守（J-Quants: 120 req/min）とリトライ（指数バックオフ、401 のトークン自動更新対応）
- データの冪等保存（DuckDB 側で ON CONFLICT を使用）
- Look-ahead Bias 対策として取得時刻（fetched_at / created_at）を記録
- セキュリティ考慮（RSS の SSRF 対策、defusedxml を使用した XML パース等）

機能一覧
--------
主要モジュールと機能の概要:

- kabusys.config
  - .env / 環境変数読み込み（プロジェクトルート自動検出）
  - 環境設定のラッパー（settings オブジェクト）
- kabusys.data.jquants_client
  - J-Quants API クライアント（株価・財務・カレンダー取得）
  - レートリミット、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等的に保存する save_* 関数
- kabusys.data.news_collector
  - RSS 取得、前処理、記事ID生成（URL 正規化 + SHA-256）
  - SSRF 防止、レスポンスサイズ制限、Gzip 解凍安全対策
  - raw_news / news_symbols への冪等保存
- kabusys.data.schema
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) で DB 初期化
- kabusys.data.pipeline
  - 日次 ETL パイプライン（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新（最終取得日からバックフィル）、ETLResult の返却
- kabusys.data.calendar_management
  - 営業日判定・前後営業日取得・カレンダー更新ジョブ
- kabusys.data.audit
  - 監査ログ用スキーマ（signal / order_request / execution 等）と初期化
- kabusys.data.quality
  - 欠損・スパイク・重複・日付不整合などの品質チェック
- kabusys.strategy / kabusys.execution / kabusys.monitoring
  - 戦略・発注・監視向けの名前空間（実装拡張ポイント）

セットアップ手順
----------------

前提
- Python 3.10 以上（| 型演算子や型指定のため）
- pip が利用可能

推奨パッケージ (最低限)
- duckdb
- defusedxml

インストール例（開発環境）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （将来的に requirements.txt / pyproject を用意している場合はそちらを利用してください）

3. ローカル開発インストール（任意）
   - pip install -e .

環境変数 (.env)
- プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主な環境変数（settings で参照）:

  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: environment ("development" | "paper_trading" | "live")
  - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

例 (.env)
  JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（主要な操作例）
---------------------

1) DuckDB スキーマ初期化
Python REPL もしくはスクリプトで:

from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path を返します
conn = init_schema(settings.duckdb_path)
# 監査スキーマを追加する場合
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

2) 日次 ETL を実行する（市場データ取得 → 保存 → 品質チェック）
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

ETLResult には取得件数や品質チェック結果、エラー一覧が含まれます。

3) 個別データ取得・保存（J-Quants）
from kabusys.data import jquants_client as jq
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)

注意: get_id_token() 等は settings.jquants_refresh_token を利用して自動的にトークンを取得・リフレッシュします。

4) RSS ニュース収集ジョブ
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection(settings.duckdb_path)
# known_codes は銘柄コード抽出に使う有効コードの集合（例: {'7203','6758',...}）
results = run_news_collection(conn, sources=None, known_codes=None)

run_news_collection はソースごとにエラーを捕捉し、各ソースの挿入件数を返します。

5) マーケットカレンダー更新ジョブ（夜間バッチ向け）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)

6) 品質チェックのみ実行
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i)

注意事項・運用上のポイント
------------------------
- 自動 env 読み込み: パッケージはプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込みします。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API のレート制限・リトライ: jquants_client は 120 req/min を満たすよう内部でスロットリングし、リトライとトークン自動更新を実装しています。過度な並列呼び出しは避けてください。
- DuckDB の接続管理: init_schema は必要なディレクトリを作成した上でテーブルを作成します。運用では常に接続を共有するか適切にクローズしてください。
- セキュリティ: news_collector は SSRF / XML Bomb 等を考慮していますが、外部 URL を扱う際はホワイトリストや追加の制約を検討してください。
- 実運用（ライブ発注）を行う際は KABUSYS_ENV を "live" に設定し、十分な検証を行ってください。

ディレクトリ構成
----------------
（主要なファイル・モジュール抜粋）

src/
  kabusys/
    __init__.py
    config.py                     # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py           # J-Quants API クライアント + 保存ロジック
      news_collector.py           # RSS ニュース収集器
      schema.py                   # DuckDB スキーマ定義・初期化
      pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      calendar_management.py      # カレンダー管理・営業日判定
      audit.py                    # 監査ログスキーマ・初期化
      quality.py                  # データ品質チェック
    strategy/
      __init__.py                 # 戦略モジュール（拡張ポイント）
    execution/
      __init__.py                 # 発注・ブローカー連携（拡張ポイント）
    monitoring/
      __init__.py                 # モニタリング用（拡張ポイント）

ライセンス・貢献
----------------
本 README 内では明記していません。実際のリポジトリには LICENSE を設置してください。バグ報告・機能提案は Issue を立ててください。

補足
----
本 README はコードベースの現状（主要モジュールの実装）に基づく概要説明です。strategy / execution / monitoring などは名前空間のみ用意されており、実装はプロジェクト方針に従って拡張してください。必要であれば README に運用手順や CI/CD、Cron ジョブ例（ETL / calendar_update_job の定期実行）を追加できます。