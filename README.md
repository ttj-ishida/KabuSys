KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
概要
本プロジェクトは日本株を対象とした自動売買プラットフォームの基盤モジュール群です。  
主に以下を提供します：
- J-Quants API からの市場データ取得クライアント（株価日足、財務データ、マーケットカレンダー）
- DuckDB を用いたデータベーススキーマ定義と初期化
- ETL（差分取得・保存・品質チェック）パイプライン
- 監査（audit）テーブルの定義（シグナル→発注→約定のトレース用）
- 環境変数/設定管理

設計上のポイント
- J-Quants API のレート制限（120 req/min）に合わせたレートリミッタ、リトライ（指数バックオフ）実装
- 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
- DuckDB へは冪等（ON CONFLICT DO UPDATE）で保存
- ETL は差分更新（最終取得日から backfill を行う）と品質チェックを実行
- 監査用テーブルは UUID によるチェーンでトレース可能

主な機能一覧
- 環境設定: kabusys.config.Settings — 必須/任意の設定を環境変数から取得、自動 .env ロード（プロジェクトルート検出）
- J-Quants クライアント: kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
- DuckDB スキーマ: kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
  - テーブル: raw / processed / feature / execution 層を網羅
- ETL パイプライン: kabusys.data.pipeline
  - run_daily_etl(conn, target_date=..., ...) — 日次 ETL（一括でカレンダー・株価・財務取得と品質チェック）
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- 品質チェック: kabusys.data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 監査ログ初期化: kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

セットアップ手順（ローカル）
前提
- Python 3.9+（ソースは typing に | を使用しているため3.10相当での実行を想定）
- pip, virtualenv 等

1) 仮想環境作成（推奨）
- Unix/macOS:
  python3 -m venv .venv
  source .venv/bin/activate
- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

2) 依存パッケージのインストール
（プロジェクトの pyproject.toml / requirements.txt がある想定。最小限のランタイム依存は duckdb）
- 例:
  pip install duckdb

3) パッケージを開発モードでインストール（任意）
- プロジェクトルートで:
  pip install -e .

4) 環境変数の設定
必要な環境変数（主に config.Settings で参照される）:
- JQUANTS_REFRESH_TOKEN （必須） — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD （必須） — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN （必須） — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID （必須） — Slack チャンネル ID
- DUCKDB_PATH （任意、デフォルト: data/kabusys.duckdb）
- SQLITE_PATH （任意、デフォルト: data/monitoring.db）
- KABUSYS_ENV （任意、 default=development） — 有効値: development, paper_trading, live
- LOG_LEVEL （任意, default=INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD （任意） — 1 を設定すると自動 .env ロードを無効化

自動 .env 読み込み
- パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、
  OS 環境 > .env.local > .env の順で読み込みが行われます（OS 環境は上書きされません）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（基本例）
以下は Python スクリプトや REPL での基本的な使い方例です。

1) 設定の参照
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)

2) DuckDB スキーマ初期化
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path を使って DB を初期化（親ディレクトリを自動作成）
conn = init_schema(settings.duckdb_path)

3) 監査スキーマの初期化（監査テーブルを追加）
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

4) 日次 ETL の実行（最も一般的なエントリポイント）
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日を基準に処理
# 結果の確認
print(result.to_dict())  # ETLResult を辞書化してログ等に保存可能

run_daily_etl の主な引数
- target_date: ETL 対象日（省略時は今日）
- id_token: 明示的に J-Quants の id_token を渡してテスト可能
- run_quality_checks: 品質チェックを実行するか（デフォルト True）
- spike_threshold: スパイク検出閾値（デフォルト 0.5 = 50%）
- backfill_days: 差分更新時のバックフィル日数（デフォルト 3）
- calendar_lookahead_days: カレンダー先読み日数（デフォルト 90）

5) 個別にデータを取得・保存する
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
saved = jq.save_daily_quotes(conn, records)

6) 品質チェックだけを実行する
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=...)
for i in issues:
    print(i.check_name, i.severity, i.detail)

注意点・運用メモ
- J-Quants API 呼び出しはレート制限（120 req/min）を厳守する設計です。大量データ取得時は時間がかかることがあります。
- get_id_token() はリフレッシュトークンを使って id_token を取得します。jquants_client._request は 401 を検出すると自動でリフレッシュして再試行します（1 回）。
- DuckDB の初期化は init_schema() を最初に一度行ってください。get_connection() は既存 DB に接続するだけでスキーマ初期化は行いません。
- ETL は個々のステップで例外を捕捉して継続する設計（1 ステップ失敗でも他ステップは継続）。最終的な状態は ETLResult に集約されます。
- 監査テーブル（audit）は削除前提ではなく、すべての TIMESTAMP は UTC で保存されます。init_audit_schema() 実行時に SET TimeZone='UTC' が適用されます。

ディレクトリ構成（主要ファイル）
src/
  kabusys/
    __init__.py                 # パッケージメタ情報（__version__ 等）
    config.py                   # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py         # J-Quants API クライアント + 保存ロジック
      schema.py                 # DuckDB スキーマ定義・初期化
      pipeline.py               # ETL パイプライン（run_daily_etl 等）
      audit.py                  # 監査ログ（signal, order_request, executions）
      quality.py                # データ品質チェック
    strategy/
      __init__.py               # 戦略層（拡張ポイント）
    execution/
      __init__.py               # 実際の発注・ブローカー連携（拡張ポイント）
    monitoring/
      __init__.py               # 監視・アラート用（拡張ポイント）

補足: 追加の実装・拡張箇所
- strategy/ と execution/ には戦略実装やブローカー連携ロジックを追加する余地があります。
- Slack 通知等のモニタリングは monitoring モジュールや外部ツールで組み立ててください。
- production 環境（KABUSYS_ENV=live）では実資金を扱うため、十分なリスクチェックと稼働前の総合テストを実施してください。

ライセンス・貢献
（ここにプロジェクトのライセンス・貢献ガイドラインを追記してください）

以上がこのコードベースの README（日本語）です。必要であれば「環境変数の .env 例」「簡易デプロイ手順」「CI / cron による定期実行例」等を追加します。どの情報を追記しましょうか？