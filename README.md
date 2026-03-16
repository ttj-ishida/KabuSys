# KabuSys

日本株の自動売買基盤向けライブラリ（軽量プロトタイプ）

このリポジトリは、J-Quants / kabuステーション 等の外部サービスからデータを取得し、
DuckDB に格納・監査・品質チェックを行うための基盤モジュール群を含みます。
主にデータプラットフォーム（ETL）、監査ログ、品質チェックの実装に重点を置いています。

バージョン: 0.1.0

## 主な特徴（機能一覧）

- 環境変数／.env 管理
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込み
  - 必須変数は Property 経由で取得し未設定時はエラーを出力

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダーを取得
  - レートリミット（120 req/min）遵守
  - リトライ（指数バックオフ）、401でのトークン自動リフレッシュ、ページネーション対応
  - 取得時刻（fetched_at）を UTC で記録

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマを定義・初期化
  - 各種インデックスを作成（検索パターンを想定）

- ETL パイプライン
  - 差分取得（最終取得日を元に差分・バックフィル）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 各ステップは独立してエラーハンドリング（1ステップ失敗でも全体を継続し問題点を収集）

- データ品質チェックモジュール
  - 欠損データ、主キー重複、スパイク（前日比閾値）、
    将来日付・非営業日データ検出を実施
  - 問題は QualityIssue オブジェクト群として返却

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 の一連のトレーサビリティを UUID ベースで保持
  - 発注の冪等キー（order_request_id）をサポート
  - UTC タイムスタンプ、ステータス管理、監査用インデックスを提供

## 動作環境・前提

- Python 3.10 以上（型注釈に `X | None` を使用）
- DuckDB（Python パッケージ: duckdb）
- 外部 API の利用には各種トークン／資格情報が必要（下記参照）

必要な Python パッケージはプロジェクトの packaging/requirements に依存します。最低限次をインストールしてください（例）:

pip install duckdb

パッケージ配布が整っている場合は:
pip install -e .

## 環境変数（必須 / 任意）

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client が使用）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

自動ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると `.env` 自動読み込みを無効化できます（テスト等で便利）。

.env の読み込み順:
1. OS 環境変数（優先）
2. .env.local（存在すれば上書き）
3. .env（初期値）

サンプル `.env`（README 用例）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## セットアップ手順

1. Python 3.10+ を用意する
2. 仮想環境を作成して有効化する（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - pip install duckdb
   - もしパッケージ化されている場合: pip install -e .
4. プロジェクトルートに `.env` を作成し、上記の必須環境変数を設定する
5. DuckDB スキーマを初期化する
   - 下記の「使い方」を参照

## 使い方（コード例）

以下は基本的な初期化と日次 ETL 実行の例です。

- DuckDB スキーマの初期化（ファイル DB を作る）

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

- 監査ログテーブルの初期化（既存接続に追加）

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

- J-Quants の ID トークンを取得（内部的に環境変数の refresh token を参照）

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用

- 単体の API 呼び出し例（株価取得）

from kabusys.data.jquants_client import fetch_daily_quotes
quotes = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

- 日次 ETL の実行（カレンダー・株価・財務・品質チェックを実行）

from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しないと今日で実行
# ETLResult には fetched/saved カウントや quality_issues, errors が含まれる
print(result.to_dict())

- 品質チェックのみ実行

from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2024,1,1))
for i in issues:
    print(i.check_name, i.severity, i.detail)

注意点:
- run_daily_etl は内部で market_calendar を先に取得して営業日調整を行います。
- ETL は各ステップを個別に try/except しているため、失敗しても残りの処理は続行され問題点を収集します。
- DuckDB の接続は thread-safe ではないため、並列処理する場合は接続ごとにインスタンスを作成してください。

## API のポイント（実装上の設計）

- jquants_client
  - レート制御: 固定間隔スロットリング（_RateLimiter）
  - リトライ: 最大 3 回、指数バックオフ。HTTP 429 の場合は Retry-After を優先
  - 401 を受けた場合はリフレッシュして 1 回リトライ
  - ページネーション対応（pagination_key）

- schema
  - Raw / Processed / Feature / Execution / Audit テーブルを用意
  - ON CONFLICT DO UPDATE による冪等保存設計

- pipeline
  - 差分更新ロジック（get_last_* で最終取得日を算出）
  - backfill_days により後出し修正を吸収
  - ETLResult に品質チェック結果とエラーメッセージを格納

- quality
  - 各チェックは QualityIssue のリストを返す
  - スパイク閾値や対象日をパラメータ化している

## ディレクトリ構成

以下はパッケージ内部の主要ファイル・モジュール構成（抜粋）です:

src/
  kabusys/
    __init__.py                  # パッケージ初期化（__version__ 等）
    config.py                    # 環境変数 / 設定管理
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント + 保存ロジック
      schema.py                  # DuckDB スキーマ定義・初期化
      pipeline.py                # ETL パイプライン（差分更新・品質チェック）
      audit.py                   # 監査ログ用スキーマ・初期化
      quality.py                 # データ品質チェック
    strategy/
      __init__.py
    execution/
      __init__.py
    monitoring/
      __init__.py

各ファイルの役割:
- config.py: .env 自動読み込みや必須環境変数の取得を行う Settings クラスを提供
- data/jquants_client.py: API 呼び出し、ページング、レスポンスの保存（DuckDB 用関数）
- data/schema.py: テーブル DDL と init_schema/get_connection を提供
- data/pipeline.py: 差分 ETL の実装と run_daily_etl を提供
- data/quality.py: 欠損・重複・スパイク・日付不整合などのチェック
- data/audit.py: signal/order_request/execution の監査テーブル定義と初期化

## 運用上の注意 / ベストプラクティス

- 本コードは API キー・トークンを扱います。`.env` は Git 管理しないように `.gitignore` に追加してください。
- KABUSYS_ENV の値により環境別の挙動を切り替えられます（development / paper_trading / live）。
  - 実際の発注や運用時には十分なテストとリスク管理を行ってください。
- DuckDB ファイルは定期的にバックアップすることを推奨します。
- ETL を定期実行する場合は外部ジョブキュー（cron/airflow 等）でスケジューリングし、
  実行ログおよび ETLResult を永続化して監査できるようにしてください。

---

この README はコードベース（src/kabusys）からの抽出情報に基づいて作成しています。  
追加の使い方や CLI、パッケージ配布設定（pyproject.toml / requirements.txt）がある場合は、
それらに合わせて README を拡張してください。