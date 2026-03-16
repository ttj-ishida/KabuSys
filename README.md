# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（ベータ）です。  
J-Quants / kabuステーション 等から市場データや財務データを取得して DuckDB に格納し、ETL（差分更新）・データ品質チェック・監査ログの基盤を提供します。

主な想定用途:
- 日次データパイプライン（株価・財務・マーケットカレンダー）の自動取得と保存
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（シグナル→発注→約定フロー）の永続化（DuckDB）

---

## 機能一覧

- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）および 401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 対策）
  - DuckDB への冪等な保存（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層を想定したテーブル群のDDL定義
  - 初期化ユーティリティ（init_schema, get_connection）

- ETL パイプライン
  - 差分更新（最終取得日 + バックフィル設定）
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェックを組み合わせた日次 ETL（run_daily_etl）

- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、主キー重複、日付不整合（未来日・非営業日）検出
  - QualityIssue オブジェクトで詳細を返す（severity: error/warning）

- 監査ログ（audit）
  - signal_events, order_requests, executions を含む監査スキーマ
  - 発注の冪等性（order_request_id）やタイムゾーン（UTC）運用指針を反映
  - init_audit_schema / init_audit_db を提供

- 設定管理
  - .env ファイル or 環境変数から設定自動ロード（プロジェクトルート検出）
  - 必須変数未設定時は明示的なエラー

---

## セットアップ手順

前提:
- Python 3.10 以降（typing の | 演算子を利用）
- pip が利用可能

1. リポジトリをクローン / ローカルに配置

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール  
   ※ 本コードで直接必要なのは duckdb（HTTP 標準ライブラリは標準で利用）。
   例:
   pip install duckdb

   （プロジェクトに pyproject.toml / requirements.txt があればそちらを利用してください）

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（少なくとも次を設定してください）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   .env の例:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

5. DB スキーマ初期化（DuckDB）
   Python REPL やスクリプトから以下を実行して DB を初期化します。

   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)  # ファイルがなければディレクトリも自動作成

6. 監査スキーマの初期化（任意）
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)

---

## 使い方（主な API）

以下は代表的な利用例です。実運用ではログ設定や例外ハンドルを追加してください。

- DuckDB スキーマ初期化（インメモリ DB 例）
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")

- run_daily_etl で日次 ETL を実行（デフォルトは本日を対象）
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)  # 既存 DB に接続
  result = run_daily_etl(conn)
  print(result.to_dict())  # ETL 結果（取得数・保存数・品質問題・エラー）

- 個別ジョブを実行（例: 株価のみ）
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  saved_info = run_prices_etl(conn, target_date=date.today())

- J-Quants クライアントを直接利用（ID トークンは自動管理）
  from kabusys.data import jquants_client as jq
  rows = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))

- データ品質チェックを個別実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- 自動環境読み込みを無効化する場合（テスト等）
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意点:
- run_daily_etl は複数ステップ（calendar → prices → financials → quality）を実行し、各ステップは独立して例外処理を行います。結果は ETLResult オブジェクトに集約されます。
- J-Quants API のレート制限を内部で守る仕組みがありますが、同時実行や外部からの大量呼び出しには注意してください。

---

## ディレクトリ構成

このリポジトリの主要ファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               # 環境変数・設定管理（.env 自動ロード）
    - data/
      - __init__.py
      - jquants_client.py     # J-Quants API クライアント（取得・保存ロジック）
      - schema.py             # DuckDB スキーマ定義 / 初期化
      - pipeline.py           # ETL パイプライン（差分更新・品質チェック）
      - audit.py              # 監査ログスキーマ初期化
      - quality.py            # データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py           # 戦略関連（拡張用）
    - execution/
      - __init__.py           # 発注 / ブローカ連携（拡張用）
    - monitoring/
      - __init__.py           # 監視・アラート関連（拡張用）

ドキュメントや設計資料（参照用）:
- DataPlatform.md, DataSchema.md（ソースには含まれていませんが、コードコメントで参照される設計方針が実装に反映されています）

---

## 開発・運用上の注意

- Python バージョンは 3.10 以上を推奨（型ヒントに | を使用）。
- DuckDB はローカルファイルで軽量に運用可能。大規模運用ではバックアップ/保全、同時接続ポリシーを検討してください。
- J-Quants の API 利用には利用規約・認証情報の管理を遵守してください。
- 本ライブラリはデータ取得・保存・品質チェックの基盤を提供しますが、発注ロジック（ブローカーへの実送信）やリスク管理の実装は別途必要です。
- all timestamps are handled with UTC for traceability（監査ログ等は UTC 保存を前提）。

---

## 追加情報 / 貢献

バグ報告・機能提案・プルリクエスト歓迎です。README の改善やドキュメント追加、戦略モジュール・execution モジュールの実装拡充などの貢献をお待ちしています。

---

必要であれば、README に使い方のより詳細なコード例（ETL のスケジューリング例、監査ログの使い方、テスト用のモック設定等）を追加します。どのトピックを優先して追加しますか？