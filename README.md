# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買に向けたデータ基盤・ETL・監査・実行レイヤを含むライブラリです。J-Quants API から市場データ・財務データ・カレンダーを取得して DuckDB に保存し、品質チェック・監査ログ・発注トレースを行うためのモジュール群を提供します。

主な設計方針:
- API レート制限（J-Quants: 120 req/min）を尊重する設計
- 冪等性（ON CONFLICT DO UPDATE）を前提とした保存ロジック
- ETL は差分更新・バックフィル対応
- 監査ログ（signal → order → execution）を UUID 連鎖でトレース可能に保存
- 品質チェックは全件収集型（Fail-Fast ではない）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・財務（四半期）・マーケットカレンダー取得
  - レートリミッタ、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存ユーティリティ（save_* 関数）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化関数 init_schema(db_path)
  - 既存 DB への接続 get_connection(db_path)
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベース）、バックフィル、カレンダーの先読み
  - run_daily_etl() による一括 ETL + 品質チェック
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付整合性チェック
  - QualityIssue オブジェクトで問題を集約
- 監査ログ初期化（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルを初期化する init_audit_schema
  - すべての TIMESTAMP を UTC で保存

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の | 型表記を使用）
- duckdb 等の依存パッケージ

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要ライブラリをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 最低限 duckdb が必要:
     ```
     pip install duckdb
     ```

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（起動時に自動読み込み）。
   - 自動読み込みを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - オプション（デフォルトあり）:
     - KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite path for monitoring（デフォルト: data/monitoring.db）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方

以下は代表的な利用例です。

1) DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数に基づくデフォルトパスを返します
conn = init_schema(settings.duckdb_path)
```
- db_path に ":memory:" を渡すとインメモリ DB を使用できます。

2) 監査ログスキーマの追加
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # 既存の conn に監査テーブルを追加
```

3) J-Quants API からデータを取得して保存（個別）
```python
from kabusys.data import jquants_client as jq

# トークンを明示的に取得
id_token = jq.get_id_token()

# 日足を取得（特定銘柄・日付範囲）
records = jq.fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2023,1,1), date_to=date(2023,3,31))
saved = jq.save_daily_quotes(conn, records)
```

4) 日次 ETL を一括実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)            # 今日を target_date として実行
# または特定日:
# result = run_daily_etl(conn, target_date=date(2023,3,31))
print(result.to_dict())
```
- run_daily_etl は市場カレンダー、株価、財務の順に差分取得と保存を行い、品質チェック（デフォルトで有効）を実行します。
- backfill_days を指定して後出し修正を吸収するための再取得窓を調整できます（デフォルト 3 日）。

5) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

6) 簡単な接続取得（スキーマ初期化を行わない場合）
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

---

## 重要な挙動・運用上の注意

- 自動 .env 読み込み:
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を起点）を探して `.env` / `.env.local` を自動読み込みします。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
  - テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます。

- J-Quants API:
  - レート制限はモジュール内の RateLimiter で制御されます（120 req/min）。
  - リトライは最大 3 回、408/429/5xx を対象に指数バックオフを行います。429 の場合は Retry-After ヘッダを優先します。
  - 401 が返された場合、自動的にリフレッシュトークンから id_token を再取得して 1 回だけ再試行します。

- データ保存:
  - save_* 関数は冪等（ON CONFLICT DO UPDATE）で実装されています。外部からの挿入やスキーマ変更がある場合に備え品質チェックを実施してください。

- 品質チェック:
  - チェック結果は QualityIssue オブジェクトのリストで返されます。呼び出し側で severity に応じた対応（停止・警告通知等）を実装してください。

- 環境（KABUSYS_ENV）:
  - 有効値: development / paper_trading / live。値が不正な場合は Settings が ValueError を投げます。
  - log レベルは LOG_LEVEL 環境変数で制御（DEBUG/INFO/...）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                     - パッケージエントリ（version 等）
  - config.py                       - 環境変数/設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（取得・保存）
    - schema.py                     - DuckDB スキーマ定義・init_schema / get_connection
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - audit.py                      - 監査ログテーブル定義・初期化
    - quality.py                    - データ品質チェック（欠損/スパイク/重複/日付不整合）
    - pipeline.py
  - strategy/
    - __init__.py                    - 戦略関連（未実装箇所のエントリ）
  - execution/
    - __init__.py                    - 発注・約定管理（未実装箇所のエントリ）
  - monitoring/
    - __init__.py                    - 監視周り（未実装箇所のエントリ）

---

## 開発・拡張のヒント

- テストしやすさ
  - jquants_client の関数は id_token を注入可能に設計されています。テスト時はモックの id_token を渡すか、KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境依存を切り離してください。
  - DuckDB の ":memory:" を使えばインメモリ DB で高速にユニットテスト可能です。

- ETL の観察
  - run_daily_etl は ETLResult を返します。result.to_dict() で監査や通知に使える構造化データが取得できます。

- 監査設計
  - order_request_id を冪等キーに用いたり、created_at/updated_at を必ず付与する方針は実運用でのトレーサビリティに役立ちます。外部ブローカー連携を実装する際は broker_order_id / broker_execution_id の取り扱いに注意してください。

---

必要であれば、README にサンプル .env.example、CI／デプロイ手順、より詳しい例（ETL スケジュール cron / Airflow など）を追加できます。どの情報を優先的に追記しますか？