# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETLパイプライン、DuckDBスキーマ定義、品質チェック、監査ログの初期化を提供します。

---

## プロジェクト概要

KabuSys は日本株の市場データ取得〜保存〜品質チェックまでをカバーする基盤モジュール群です。主な用途は以下です。

- J-Quants API から株価・財務・カレンダー情報を取得
- 取得データを DuckDB に冪等的に保存（ON CONFLICT DO UPDATE）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注 → 約定のトレース用テーブル群）初期化

設計上の特徴:
- API レート制限（デフォルト 120 req/min）に合わせた RateLimiter
- 冪等性を意識した保存ロジック
- 401 時の自動トークンリフレッシュ／リトライ（指数バックオフ）
- 取得タイミング（fetched_at / UTC）を保存して Look-ahead bias を防止

---

## 機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB 保存）
  - Rate limiting、リトライ、401 自動リフレッシュ、fetched_at 記録
- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) / get_connection(db_path)
- data.pipeline
  - 差分更新・バックフィルを行う ETL（run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl）
  - ETLResult により実行結果・品質問題・エラーを収集
- data.quality
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
  - run_all_checks（まとめ実行）
- data.audit
  - 監査ログ用テーブルの初期化（init_audit_schema, init_audit_db）
- config
  - .env / .env.local からの自動環境変数読み込み（プロジェクトルート検出）
  - Settings クラス（settings）で各種設定値にアクセス（J-Quants トークンや DB パス等）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
- その他
  - パッケージは src/kabusys 配下で構成

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | を使用）
- 仮想環境推奨

1. リポジトリをクローンしてワークツリーを作成
   - （例）git clone ...; cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 少なくとも duckdb が必要:
     - pip install duckdb
   - その他プロジェクトで必要なパッケージがあれば requirements.txt からインストールしてください:
     - pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成すると、自動的に読み込まれます。
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）

例 `.env`（最小）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
```

---

## 使い方（例）

以下は基本的な利用例です。Python スクリプトや REPL で実行できます。

1) DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照
conn = init_schema(settings.duckdb_path)
```

2) J-Quants の ID トークンを取得（明示的に）
```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

3) 生データの ETL（日次パイプライン）の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # デフォルトで今日を対象に ETL 実行
print(result.to_dict())
```

run_daily_etl の主なパラメータ:
- target_date: ETL 対象日（省略時は今日）
- id_token: テスト時などに外部から注入可能
- run_quality_checks: 品質チェックを実行するか
- spike_threshold: スパイク検出閾値（デフォルト 0.5）
- backfill_days: 差分更新時のバックフィル日数（デフォルト 3）

4) 個別 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

# 例: 株価 ETL のみ実行
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

5) 品質チェックを個別に実行する
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None, reference_date=None)
for i in issues:
    print(i)
```

6) 監査ログ（audit）テーブルの初期化
```python
from kabusys.data.audit import init_audit_schema, init_audit_db
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)  # 既存接続に監査テーブルを追加する

# もしくは専用 DB として初期化
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 設計上の注意点

- Rate limiting:
  - jquants_client は 120 req/min（デフォルト）に合わせた固定間隔スロットリングを実装しています。過度な並列リクエストに注意してください。
- リトライと認証:
  - ネットワークエラー（408/429/5xx）には指数バックオフで最大 3 回リトライします。
  - 401 を受け取った場合はリフレッシュトークンから ID トークンを自動再取得して再試行（1 回のみ）。
- 冪等性:
  - DuckDB への保存は ON CONFLICT DO UPDATE により冪等化されています。
- 時刻:
  - 取得時刻など監査用の timestamp は UTC で記録されます（audit.init は TimeZone を UTC に設定します）。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を起点に `.env` と `.env.local` を自動ロードします。
  - OS 環境変数 > .env.local > .env の優先順位です。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル／ディレクトリ（src/kabusys 配下）:

- src/kabusys/
  - __init__.py  -- パッケージ定義（__version__）
  - config.py    -- 環境変数/設定管理（Settings, 自動 .env 読み込み）
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
    - schema.py            -- DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py          -- ETL パイプライン（差分更新・バックフィル・品質チェック）
    - audit.py             -- 監査ログテーブル定義・初期化
    - quality.py           -- データ品質チェック（欠損/スパイク/重複/日付不整合）
    - pipeline.py          -- ETL orchestration（run_daily_etl 等）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記は現状のコードベースに含まれる主要モジュールの一覧です）

---

## 追加情報 / 今後の拡張案

- 実運用（live）での注文送信／ブローカー API 連携は execution モジュールで拡張が必要です。
- Slack 通知やモニタリング（monitoring）機能は未実装の部分を埋めて利用することが想定されています。
- テスト用フレームワーク・CI の追加（自動化テスト、モックを使った API テスト等）を推奨します。

---

もし README に加えたいチュートリアル（例: 初回ロード手順、cron での日次実行スクリプト、kabu-station 連携のサンプルなど）があれば、具体的な利用シナリオに合わせて追記します。