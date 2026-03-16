# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
データ取り込み、データ品質チェック、監査ログ、DuckDBスキーマ定義、J-Quants API クライアントなど、アルゴリズム取引に必要な基盤機能を提供します。

---

## 概要

KabuSys は以下の目的で設計された小規模なライブラリ群です。

- J-Quants API から株価・財務データ・マーケットカレンダーを取得して DuckDB に保存する。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を実行する。
- 監査ログ（シグナル → 発注 → 約定のトレース）用テーブルを DuckDB に作成する。
- 設定は環境変数／`.env` ファイルで管理し、自動で読み込む（プロジェクトルート検出あり）。
- 発注・取引ロジックのためのスキーマ（Execution Layer）を定義する（出力・連携用インターフェースを想定）。

設計上のポイント: レート制限遵守、リトライ・トークン自動リフレッシュ、UTC タイムスタンプ保存、冪等性を考慮した DB 挿入。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（OS 環境変数を保護）
  - 必須環境変数チェック、環境種別（development/paper_trading/live）バリデーション

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - マーケットカレンダー（fetch_market_calendar）
  - レートリミッタ（120 req/min）・リトライ（指数バックオフ）・401 時の自動トークンリフレッシュ
  - DuckDB への保存関数（冪等な INSERT ... ON CONFLICT）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化
  - インデックス作成、init_schema() / get_connection()

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL と初期化（UTC タイムゾーン）
  - 冪等キー・ステータス遷移を考慮した設計

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合の検出
  - QualityIssue 型で問題を集約して返す（Fail-Fast ではなく全件収集）

---

## 前提・依存関係

- Python 3.10 以上（型ヒントで `|` 演算子を使用）
- 依存パッケージ（主に）
  - duckdb

必要に応じて pip でインストールしてください:

pip install duckdb

（プロジェクトをパッケージとしてインストールする場合は setup/pyproject に応じて pip install -e . 等を使用）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - pip install duckdb

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動で読み込まれます。
   - 読み込み順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

5. `.env` の例（`.env.example` を作成して使ってください）:

JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
KABU_API_PASSWORD=あなたの_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

---

## 使い方（コード例）

以下は主要な利用例です。実際は例外処理やログ管理を適切に追加してください。

- DuckDB スキーマ初期化

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 既存 DB に接続する場合:
# conn = schema.get_connection("data/kabusys.duckdb")

- J-Quants から日足を取得して保存する

from kabusys.data import jquants_client
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")

# 例: 7203（トヨタ）の日足を 2023-01-01 から 2023-12-31 まで取得
records = jquants_client.fetch_daily_quotes(
    code="7203",
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
)
saved = jquants_client.save_daily_quotes(conn, records)
print(f"Saved {saved} rows")

- 財務データ / マーケットカレンダーの取得・保存も同様

records_fin = jquants_client.fetch_financial_statements(code="7203")
jquants_client.save_financial_statements(conn, records_fin)

calendar = jquants_client.fetch_market_calendar()
jquants_client.save_market_calendar(conn, calendar)

- 監査ログテーブルを追加で初期化する（既存の conn に対して）

from kabusys.data import audit
audit.init_audit_schema(conn)
# または監査専用 DB を作る:
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

- データ品質チェックの実行

from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
    for row in i.rows:
        print("  ", row)

- Token の直接取得（通常は自動処理されます）

from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings から refresh_token を取得して POST

---

## 設定（環境変数）についての補足

- 自動 .env 読み込み
  - パッケージ import 時点でプロジェクトルートを探索し、`.env` と `.env.local` を読み込みます。
  - OS の環境変数は保護され、`.env` で上書きされません（ただし .env.local は override=True で上書きする仕様）。
  - テスト時などに自動読み込みを停止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 設定の参照
  - from kabusys.config import settings を介して各種設定を参照（例: settings.jquants_refresh_token）。

- 有効な KABUSYS_ENV:
  - development, paper_trading, live

- ログレベル:
  - DEBUG / INFO / WARNING / ERROR / CRITICAL

---

## ディレクトリ構成

以下はプロジェクト内の主要ファイル／モジュール構成（抜粋）です。

src/
  kabusys/
    __init__.py            -- パッケージ定義（__version__ 等）
    config.py              -- 環境変数 / 設定管理
    data/
      __init__.py
      jquants_client.py    -- J-Quants API クライアント（取得・保存ロジック）
      schema.py            -- DuckDB スキーマ定義と init_schema / get_connection
      audit.py             -- 監査ログ（signal/events/order/exec）定義と初期化
      quality.py           -- データ品質チェック（欠損・スパイク・重複・日付不整合）
      (その他: news, executions 等のスキーマ要素)
    strategy/
      __init__.py          -- 戦略関連のプレースホルダ
    execution/
      __init__.py          -- 発注 / 実行関連のプレースホルダ
    monitoring/
      __init__.py          -- 監視・メトリクス関連のプレースホルダ

注意: strategy / execution / monitoring の実装は現状プレースホルダです（拡張前提）。

---

## 実装上の注意点・設計メモ

- J-Quants クライアントはレート制限（120 req/min）を守るために内部でスロットリングします。大量リクエストを行う際はこの制約に留意してください。
- リトライは 3 回まで、408/429/5xx を対象に指数バックオフを行います。429 の場合は Retry-After ヘッダを優先します。
- 401 Unauthorized を受け取った際は、リフレッシュトークンから ID トークンを自動で再取得して1回だけリトライします。
- DuckDB への保存は ON CONFLICT ... DO UPDATE を利用して冪等化しています。
- すべての TIMESTAMP は原則 UTC で記録されます（監査ログ等は init_audit_schema() が TimeZone='UTC' を設定します）。
- データ品質チェックは Fail-Fast ではなく全ての問題を収集して返します。呼び出し元で重大度に応じて処理を止めるかログ出力するか判断してください。

---

## 開発・貢献

- コードの拡張ポイント:
  - strategy / execution / monitoring モジュールに実戦用ロジックを追加
  - Slack 通知・監視ダッシュボード用の統合
  - 単体テスト・CI の追加（.env 自動読み込みを無効化する環境変数が用意されています）

---

必要であれば、README に以下を追記できます:
- CI/CD 手順
- よくあるトラブルシューティング
- 詳細な DB スキーマドキュメント（DataSchema.md 参照を想定）
- サンプルデータを使ったハンズオン手順

追加で入れたい項目やサンプルを指定してください。