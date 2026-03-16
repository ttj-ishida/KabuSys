# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（データパイプライン・スキーマ・品質チェック・監査ログなどを含む）

> 小規模なサマリ:
> - J-Quants API から株価・財務・市場カレンダー等を取得し、DuckDB に保存する ETL パイプラインを提供します。  
> - データの品質チェック、監査ログ用スキーマ、監査テーブル初期化、発注/実行ログ用のスキーマも備えています。

---

## 主要な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）のページネーション取得
  - 財務諸表（四半期 BS/PL）の取得
  - JPX マーケットカレンダーの取得
  - レート制限（120 req/min）を守る内部 RateLimiter
  - 再試行（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ対応
  - 取得タイムスタンプ（fetched_at）で Look-ahead bias をトレース可能に保存

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマを DDL で定義
  - インデックス定義付きで初期化・接続を提供（冪等：既存テーブルは上書きしない）

- ETL パイプライン
  - 差分更新ロジック（DBの最終取得日から未取得分のみ取得）
  - backfill を含めた再取得（APIの後出し修正対策）
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実行して問題を収集

- データ品質チェック（quality モジュール）
  - 欠損データ検出（OHLC の欠損）
  - 主キー重複検出
  - スパイク（前日比の急変）検出
  - 将来日付 / 非営業日のデータ検出

- 監査ログ（audit モジュール）
  - シグナル／発注要求／約定をトレースする監査テーブル定義
  - order_request_id による冪等キー設計
  - UTC タイムゾーン強制、TIMESTAMP 管理

- 設定管理
  - .env / .env.local / OS 環境変数の読み込み（プロジェクトルート自動検出）
  - 必須環境変数チェックを行う Settings オブジェクトを提供

---

## 前提条件

- Python 3.10 以上（型ヒントに `|` 記法を使用）
- 主要依存:
  - duckdb
- ネットワークアクセス（J-Quants API）
- （必要に応じて）Slack 等の通知ライブラリ（本コードベースでは token の扱いのみ）

インストール例（仮に pyproject / setup がある場合）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# プロジェクトインストール（存在する場合）
pip install -e .
# 直接依存のみ入れる場合
pip install duckdb
```

もしくは、ソースをそのまま使う場合は PYTHONPATH に `src` を追加して実行できます：

```bash
export PYTHONPATH=$(pwd)/src:${PYTHONPATH}
```

---

## 環境変数 / .env

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、自動で `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには:

```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な必須環境変数:

- JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD … kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN … Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID … Slack チャンネル ID（必須）

その他（任意）:

- KABUSYS_ENV … development / paper_trading / live（デフォルト: development）
- LOG_LEVEL … DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH … 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 `.env`:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 基本的な使い方

以下は典型的なワークフローのサンプルです。まず DuckDB スキーマの初期化、その後日次 ETL を実行します。

例: スキーマ初期化（ファイル DB）

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# 必要に応じて監査ログを追加
from kabusys.data import audit
audit.init_audit_schema(conn)
```

例: 日次 ETL 実行

```python
from datetime import date
from kabusys.data import pipeline, schema

# DB 接続（事前に init_schema を呼んでおくことを推奨）
conn = schema.get_connection("data/kabusys.duckdb")

# 今日の ETL を実行（id_token を省略するとキャッシュ/自動リフレッシュを使用）
result = pipeline.run_daily_etl(conn)

print(result.to_dict())
if result.has_errors:
    print("ETL 実行中にエラーが発生しました:", result.errors)
if result.has_quality_errors:
    print("品質チェックでエラーが検出されました。")
```

ETL の詳細制御:
- pipeline.run_daily_etl の引数で target_date, id_token, run_quality_checks, spike_threshold, backfill_days, calendar_lookahead_days を調整可能。
- 個別処理を行う場合は run_calendar_etl / run_prices_etl / run_financials_etl を呼べます。

J-Quants API を直接操作する例:

```python
from kabusys.data import jquants_client as jq
# id_token を自分で取得して渡すことも可能
id_token = jq.get_id_token()
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,1,31))
```

品質チェックを単独で実行:

```python
from kabusys.data import quality
issues = quality.run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## API のポイント（実装上の注意）

- jquants_client:
  - _request は内部で指数バックオフの再試行を実行。408/429/5xx でリトライ、429 の場合は Retry-After ヘッダを考慮。
  - 401 受信時は get_id_token を使って一度だけ自動リフレッシュして再試行。
  - ページネーション対応（pagination_key）で全件を取得。
  - save_* 関数は DuckDB に対して ON CONFLICT DO UPDATE を使い冪等に保存。

- schema:
  - init_schema(db_path) で全テーブル（Raw/Processed/Feature/Execution）とインデックスを作成。
  - init_audit_schema(conn) により監査テーブルを追加（UTC タイムゾーンを強制）。

- pipeline:
  - 差分更新ロジックを提供。DB の最終取得日から不足分だけ取得し、backfill_days で数日前から再取得して API の後出し修正を吸収。
  - ETL 実行は個別ステップが独立して例外処理され、1 ステップ失敗でも残りのステップを継続する（結果に errors を蓄積）。

- quality:
  - 各チェックは QualityIssue のリストで結果を返す（エラー/警告の区別あり）。
  - SQL を用いた効率的なチェックで、対象日はパラメタで絞り込み可能。

---

## ディレクトリ構成（該当コードベース）

以下はソース内の主要ファイル一覧（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み / Settings
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義・初期化
    - audit.py               — 監査ログテーブル定義・初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（strategy / execution / monitoring は現状インターフェースのプレースホルダになっています）

---

## 運用上の注意

- 秘密情報（トークン・パスワード）は .env として管理し、バージョン管理に含めないでください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD をセットすると自動 .env の読み込みを無効化できます（テスト等で有用）。
- DuckDB ファイルはローカルファイルとして扱う設計になっています。運用ではバックアップ・永続化を検討してください。
- J-Quants API レート制限を守る設計になっていますが、並列で大量のリクエストを送る実装を追加する場合は十分注意してください。

---

## 付録: よく使う関数一覧（抜粋）

- 設定:
  - kabusys.config.settings

- DB スキーマ:
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.schema.get_connection(db_path)

- 監査ログ:
  - kabusys.data.audit.init_audit_schema(conn)
  - kabusys.data.audit.init_audit_db(db_path)

- J-Quants クライアント:
  - kabusys.data.jquants_client.get_id_token(refresh_token=None)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.fetch_financial_statements(...)
  - kabusys.data.jquants_client.fetch_market_calendar(...)
  - 保存: save_daily_quotes / save_financial_statements / save_market_calendar

- ETL / 品質:
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.quality.run_all_checks(...)

---

ご不明点（例: 実行時に出る具体的なエラーへの対処、追加のデータ取得・戦略実装方法など）があれば、目的に合わせた README の追記あるいは使用例（cron / Airflow / 実運用での発注フロー例）を作成します。どの分野を掘り下げたいか教えてください。