# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
J-Quants や kabuステーション 等からデータを取得し、DuckDB に格納、品質チェック・ETL を行い、監査ログ（発注→約定トレース）を提供します。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存（冪等）
- データの差分更新（バックフィル対応）と ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ
- kabuステーション / ブローカー接続、戦略、実行、監視のためのパッケージ分割（骨組み）

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を厳守する RateLimiter を実装
- リトライ、トークン自動リフレッシュ、Look-ahead-bias 防止のための fetched_at 記録
- DuckDB に対する INSERT は ON CONFLICT DO UPDATE で冪等化

---

## 主な機能一覧

- 環境・設定管理（自動で .env/.env.local を読み込み、Settings クラスで参照）
- J-Quants クライアント（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レートリミット制御、リトライ、401 時のトークン自動リフレッシュ対応
- DuckDB スキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化
- テストしやすい設計（id_token 注入、:memory: DB 利用可）

---

## 要件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
- ネットワークアクセス（J-Quants API 等）
- 任意: .env に認証情報を準備

（実際の requirements.txt / pyproject.toml は本リポジトリに合わせて導入してください）

---

## セットアップ手順

1. リポジトリをチェックアウト、仮想環境作成・有効化

   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージと依存関係をインストール

   - pyproject.toml/requirements.txt がある場合はそれに従ってください。開発時の例:

   ```
   pip install -U pip
   pip install duckdb
   pip install -e .
   ```

3. 環境変数（.env）を用意

   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（CWD に依存せずパッケージ位置からプロジェクトルートを探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須環境変数（README 用の代表例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

   任意／デフォルト:
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

---

## データベース初期化（DuckDB）

DuckDB スキーマを作成するには、`kabusys.data.schema.init_schema` を使います。例:

```
python - <<'PY'
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
print("initialized:", conn)
PY
```

監査ログ（order_requests / executions 等）のテーブルを既存接続に追加する場合:

```
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

※ `db_path=":memory:"` を指定するとインメモリ DB を利用できます（テスト向け）。

---

## 使い方（代表的な例）

- 日次 ETL 実行（市場カレンダー取得 → 株価 → 財務 → 品質チェック）

```
from datetime import date
from kabusys.data import schema, pipeline

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別ジョブ（価格データのみ差分 ETL）

```
from datetime import date
from kabusys.data import schema, pipeline
conn = schema.get_connection("data/kabusys.duckdb")
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- J-Quants から直接フェッチして保存（テスト用）

```
from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect(":memory:")
# スキーマ作成
from kabusys.data import schema
schema.init_schema(":memory:")
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
jq.save_daily_quotes(conn, records)
```

- 品質チェックを手動で実行

```
from kabusys.data import quality, schema
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i)
```

テスト時のヒント:
- id_token を外部から注入可能（jquants_client の fetch 系関数に id_token 引数を渡す）
- 自動.envロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 設定の詳細（Settings）

`kabusys.config.settings` から各種設定にアクセスできます。主なプロパティ:

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabuステーション API パスワード（必須）
- kabu_api_base_url: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token / slack_channel_id: Slack 通知用（必須）
- duckdb_path / sqlite_path: DB ファイルパス（デフォルト有り）
- env: KABUSYS_ENV（development|paper_trading|live）
- log_level: LOG_LEVEL（DEBUG, INFO, ...）
- is_live / is_paper / is_dev: env 判定ヘルパー

.env の自動読み込みの挙動:
- プロジェクトルート (.git または pyproject.toml が存在する場所) を起点に `.env` と `.env.local` を読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- .env.local の方が .env より優先され、override=True で上書きされます。
- テスト等で自動ロードを抑止するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 内部モジュール概要（主なファイル）

- kabusys/
  - config.py: 環境設定管理、.env の自動読み込み、Settings クラス
- kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ）
  - schema.py: DuckDB のスキーマ定義および初期化（Raw / Processed / Feature / Execution）
  - pipeline.py: ETL パイプライン（差分更新・バックフィル・品質チェック）
  - audit.py: 監査ログスキーマ（signal/events/order_requests/executions）の初期化
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys/strategy/: 戦略レイヤー（骨組み）
- kabusys/execution/: 発注・ブローカー連携（骨組み）
- kabusys/monitoring/: 監視・アラート（骨組み）

---

## ディレクトリ構成（抜粋）

src/
- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - schema.py
    - pipeline.py
    - audit.py
    - quality.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

---

## 注意事項 / 運用メモ

- J-Quants のレート制限（120 req/min）を厳守していますが、大量データ取得時は実行時間に注意してください。
- jquants_client は 401 を受信するとリフレッシュトークン経由で id_token を更新して 1 回だけリトライします。
- DuckDB の DDL は冪等（CREATE IF NOT EXISTS）になっているため、初回のみ init_schema を呼ぶ運用で問題ありません。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等を利用）で設計されています。
- 品質チェックは Fail-Fast ではありません。重大度に応じて呼び出し側で対応判断をしてください。

---

もし README に追加したいサンプルスクリプトや CI / デプロイ手順、あるいは .env.example のテンプレートなどがあれば、それに合わせて追記します。