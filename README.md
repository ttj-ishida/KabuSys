# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。J-Quants API から市場データや財務データを取得して DuckDB に保存し、品質チェック・監査ログ・ETL パイプラインを備えた堅牢なデータプラットフォームと、戦略／発注レイヤを支援するための基盤機能を提供します。

## 特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）に従う固定間隔レートリミッタ
  - 再試行（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ
  - ページネーション対応、取得時刻（fetched_at）の記録（Look-ahead Bias 対策）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層に分けたスキーマ定義
  - 発注／約定／ポジション／監査ログ用テーブルを含む詳細な DDL
  - インデックス定義によるクエリ最適化

- ETL パイプライン
  - 差分更新（最終取得日を参照）、バックフィルにより後出し修正を吸収
  - カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損、スパイク、重複、日付不整合）の実行と集約
  - 各ステップは独立してエラーハンドリング（1 ステップの失敗で他を中断しない）

- データ品質チェック
  - 欠損（OHLC の NULL）、前日比スパイク、主キー重複、将来日付／非営業日の検出
  - 問題は QualityIssue オブジェクト一覧で返却。重大度（error / warning）で分類

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の UUID ベースのチェーンで完全追跡
  - 発注の冪等キー（order_request_id）管理
  - 全テーブルに created_at / updated_at 等を付与して監査可能に保存

- 環境設定管理
  - .env / .env.local 自動ロード（OS 環境変数 > .env.local > .env）
  - 必須環境変数は例外で通知
  - テスト等のために自動ロード無効化フラグあり（KABUSYS_DISABLE_AUTO_ENV_LOAD）

## セットアップ

前提:
- Python 3.9+（コード内では typing の型注釈に Python 3.9+ 構文を使用）
- DuckDB が必要（Python パッケージとして duckdb をインストール）

1. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール（最低限: duckdb）
   pipenv/poetry/requirements.txt が無い場合は手動で:
   ```bash
   pip install duckdb
   ```

3. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を配置します（自動ロードされます）。
   必要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
   - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            : SQLite パス（監視DB 等、デフォルト: data/monitoring.db）
   - KABUSYS_ENV            : development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL              : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   .env の簡単な例:
   ```
   JQUANTS_REFRESH_TOKEN=your-refresh-token
   KABU_API_PASSWORD=your-kabu-password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. 自動環境読み込みの無効化（テスト時）
   環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードをスキップできます。

## 使い方（基本）

以下は Python REPL やスクリプトから利用する例です。

- DuckDB スキーマの初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も利用可
  ```

- 監査ログ（audit）スキーマの追加
  ```python
  from kabusys.data import audit
  # 既存 conn に監査テーブルを追加
  audit.init_audit_schema(conn)

  # または監査専用 DB を初期化
  audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- J-Quants API を直接呼んでデータ取得
  ```python
  from kabusys.data import jquants_client as jq
  # トークンは settings から自動取得されるため通常は省略可
  daily = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
  ```

- ETL 日次パイプライン実行
  ```python
  from datetime import date
  from kabusys.data import pipeline, schema

  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

主な API:
- data.jquants_client
  - get_id_token(refresh_token: str | None) -> str
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- data.schema
  - init_schema(db_path) -> duckdb connection
  - get_connection(db_path)
- data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data.quality
  - run_all_checks(conn, target_date=None, ...)

ログレベルや実行環境は `KABUSYS_ENV` と `LOG_LEVEL` で制御します。
- KABUSYS_ENV の有効値: development, paper_trading, live
- is_live / is_paper / is_dev プロパティが settings にあります。

## ディレクトリ構成

（プロジェクトの src ディレクトリを基準にした主要ファイル一覧）

- src/kabusys/
  - __init__.py       - パッケージ定義（__version__ = "0.1.0"）
  - config.py         - 環境変数／設定読み込みと Settings クラス
  - data/
    - __init__.py
    - jquants_client.py - J-Quants API クライアントと DuckDB 保存ロジック
    - schema.py         - DuckDB スキーマ定義と初期化関数
    - pipeline.py       - ETL パイプライン（差分取得、backfill、品質チェック）
    - quality.py        - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py          - 監査ログ（signal/order_request/execution）DDL と初期化
    - audit/ (なし)     - （将来的な追加想定）
  - strategy/
    - __init__.py       - 戦略層用のエントリ（実装は各戦略で追加）
  - execution/
    - __init__.py       - 発注・ブローカー連携用のエントリ（実装は追加）
  - monitoring/
    - __init__.py       - 監視用モジュール（実装は追加）

## 運用上の注意 / 実装上のポイント

- 環境自動読み込み:
  - パッケージは .env/.env.local をプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から自動的に読み込みます。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効にできます。
  - 読み込み優先度: OS 環境 > .env.local > .env

- 冪等性:
  - 保存処理は ON CONFLICT DO UPDATE を使っているため複数回実行してもデータの上書きによる差分問題を防ぎます。

- 品質チェック:
  - run_daily_etl は品質チェックの結果を収集して返しますが、ETL 自体は品質エラーで自動停止しない設計です（呼び出し元で判断してください）。

- レート制御:
  - J-Quants のレート制限（120 req/min）に合わせて固定間隔で待機します。大量データ取得時はレート制限に注意してください。

- タイムゾーン:
  - 監査ログなどでは UTC を使用する設計になっています（audit.init_audit_schema で SET TimeZone='UTC' を実行）。

## 参考／拡張

- 戦略（strategy）・発注（execution）・監視（monitoring）モジュールはインターフェイスを整備してあるため、実際のトレードロジックやブローカー連携、監視ダッシュボードはこの基盤上に実装していく想定です。
- CI/CD や定期実行（cron / GitHub Actions / Airflow など）で ETL をスケジュールし、監視（Slack 通知等）を組み合わせると運用が容易になります。

---

不明点や README に追加したい具体的な使い方（例: 実際の ETL スケジュール例、戦略テンプレート、CI 設定 など）があれば教えてください。README を用途に合わせて拡張して作成します。