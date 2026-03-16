# KabuSys

日本株自動売買のためのデータ基盤・ETL・監査ライブラリ集合です。  
このリポジトリは、J-Quants から市場データを取得して DuckDB に保存し、品質チェック・監査ログを備えたデータパイプラインを提供します。

主な目的:
- J-Quants API から OHLCV・財務・市場カレンダーを取得して永続化
- 冪等な保存（ON CONFLICT DO UPDATE）と差分更新（バックフィル対応）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注・約定フローの監査ログ（UUIDベースのトレーサビリティ）

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境変数
  - DB 初期化
  - 日次 ETL 実行例
  - 監査ログ初期化
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API を使って日本株データ（株価日足、四半期財務、JPX マーケットカレンダー）を取得します。
- 取得したデータは DuckDB に保存され、スキーマは「Raw / Processed / Feature / Execution（監査含む）」の階層で設計されています。
- データ取得はレート制限（120 req/min）を尊重し、リトライ・トークン自動リフレッシュ等の堅牢な実装が施されています。
- ETL パイプラインは差分更新（最終取得日ベース）とバックフィルをサポートし、品質チェックを行います。
- 発注〜約定の監査トレースを別途保持するための監査テーブルも提供します。

---

機能一覧
- 環境変数／設定読み込み（.env / .env.local の自動読み込み、無効化フラグあり）
- J-Quants クライアント
  - 株価日足、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レートリミット制御（120 req/min）、指数バックオフによるリトライ、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録することで Look-ahead Bias の抑止
- DuckDB スキーマ定義 & 初期化（init_schema）
  - Raw / Processed / Feature / Execution（orders/trades/positions 等）テーブル
  - 頻出クエリのためのインデックス定義
- ETL パイプライン（run_daily_etl 等）
  - 差分取得（最終取得日を基に自動算出）、バックフィル、カレンダー先読み
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 各処理は独立してエラーハンドリング（1 ステップ失敗でも他は継続）
- 品質チェックモジュール（quality）
  - QualityIssue データクラスによる問題収集（error / warning）
- 監査ログ（audit）
  - signal_events、order_requests、executions 等の監査テーブル
  - UUID ベースの冪等性とトレーサビリティ
- その他
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
  - ETL の結果を ETLResult オブジェクトで取得可能

---

セットアップ手順

前提:
- Python 3.9+（コードでは型ヒントで Union 型を | で使っています）
- pip が使用可能

1) リポジトリをクローン / 配置
   git clone <repository>

2) 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3) パッケージのインストール
   - 依存パッケージ（例: duckdb）をインストールします。
   - setuptools / pyproject を整備している場合は pip install -e . などでインストール可能です。

   例:
   pip install duckdb
   pip install -e .

   （プロジェクト配布で requirements.txt や pyproject.toml があればそちらを利用してください）

4) 環境変数設定
   プロジェクトルートの .env または OS 環境変数に必要な値を設定します（下記参照）。
   本ライブラリの config モジュールは自動的にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env を読み込みます。
   自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot Token
  - SLACK_CHANNEL_ID      : Slack チャンネル ID
  - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注機能を使う場合）

- 任意 / デフォルトあり
  - KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
  - LOG_LEVEL   : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動ロードを無効化

.env の例ファイル（.env.example を参考に作成してください）:
# .env
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
KABU_API_PASSWORD=...

---

使い方（コード例）

1) DuckDB スキーマ初期化
Python REPL またはスクリプトで DuckDB の初期化を行います。

例:
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

これにより必要なテーブル・インデックスが作成されます。

2) 日次 ETL を実行する（単発実行）
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を与えなければ当日が対象

# ETLResult の確認
print(result.to_dict())

主要パラメータ:
- target_date: ETL 対象日（date オブジェクト）
- run_quality_checks: 品質チェックを実行するか（デフォルト True）
- backfill_days: 最終取得日の何日前から再取得するか（デフォルト 3）
- calendar_lookahead_days: カレンダー先読み日数（デフォルト 90）

3) J-Quants データを個別に取得・保存する
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)

4) 監査ログの初期化（audit テーブルを追加）
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)  # 既存接続に監査テーブルを追加

注記:
- jquants_client は内部でレートリミット（120 req/min）とリトライ（最大 3 回、指数バックオフ）を行います。
- 401 が返ると自動でリフレッシュトークンを使って id_token を再取得し一度リトライします（get_id_token からの呼び出し時は無限ループしないよう設計）。
- save_* 関数は ON CONFLICT DO UPDATE により冪等です。

---

品質チェック（quality モジュール）
- check_missing_data: OHLC 欠損（error）
- check_duplicates: 主キー重複（error）
- check_spike: 前日比スパイク（warning、閾値はデフォルト 50%）
- check_date_consistency: 将来日付・非営業日データ（error/warning）
- run_all_checks: 上記をまとめて実行し QualityIssue のリストを返す

ETL の中では run_daily_etl が最後に品質チェックを呼び出し、問題を ETLResult.quality_issues に格納します。呼び出し元は重大度に応じて通知・停止などのアクションを決定してください。

---

運用メモ / 推奨
- 定期実行: cron / systemd timer / Airflow 等で毎営業日実行する想定。run_daily_etl はカレンダー先読みやバックフィルを組み合わせて堅牢に更新します。
- ロギング: 環境変数 LOG_LEVEL でログレベルを調整してください。
- テスト時: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと .env の自動読み込みを無効化できます。
- DuckDB のバックアップ・永続化を検討してください（ファイルベースです）。

---

ディレクトリ構成
（主なファイル・モジュール）

src/
  kabusys/
    __init__.py               # パッケージ定義（__version__ 等）
    config.py                 # 環境変数 / 設定読み込みロジック
    data/
      __init__.py
      jquants_client.py       # J-Quants API クライアント（取得 + DuckDB 保存）
      schema.py               # DuckDB スキーマ定義 & init_schema / get_connection
      pipeline.py             # ETL パイプライン（run_daily_etl 等）
      quality.py              # データ品質チェック
      audit.py                # 監査ログ用テーブル定義 & 初期化
      pipeline.py             # ETL ロジック（差分取得 / バックフィル / 結果オブジェクト）
    strategy/
      __init__.py
      (戦略関連モジュールはここに配置)
    execution/
      __init__.py
      (発注・証券会社インタフェースはここに配置)
    monitoring/
      __init__.py
      (監視用コード等)

---

ライセンス / 貢献
- (プロジェクトに合わせてライセンスを明記してください)
- バグ報告・機能提案は Issue へお願いします。

---

補足（設計上の要点）
- API 呼び出しはモジュールレベルで id_token をキャッシュし、ページネーション間で共有して効率化します。
- DuckDB へは可能な限り SQL 側で効率的にチェック・集計を行い、品質チェックは全件収集で Fail-Fast を避ける方針です。
- 監査ログは削除せず永続的に保存する前提で設計されています（FK は ON DELETE RESTRICT、タイムスタンプは UTC）。

---

問題や実装拡張（例）
- kabuステーション連携（execution 層）や Slack 通知の具体的な実装は別モジュールで実装してください（Slack トークン等は config で供給されます）。
- ETL の並列化や増分処理の最適化は将来的な改善ポイントです。

---

必要であれば README にサンプル .env.example、より詳細な API 使用例、cron/systemd の設定例、または運用フロー図を追加します。どの情報がさらに必要か教えてください。