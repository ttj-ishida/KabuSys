# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。  
データ取得・ETL、データ品質チェック、DuckDBスキーマ、監査ログ（発注→約定のトレーサビリティ）など、戦略実行に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を主眼に設計されたライブラリです。

- J-Quants API から株価・財務データ・市場カレンダーを取得し、DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- DuckDB 上のスキーマ定義（Raw / Processed / Feature / Execution / Audit 層）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- kabu ステーション API や Slack への通知などと連携するための設定管理

設計ポイントの例:
- API レート制限（120 req/min）とリトライロジックを内蔵
- データ取得時に fetched_at を UTC で記録し、look-ahead bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

---

## 主な機能一覧

- データ取得（J-Quants）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー
  - ページネーション対応、トークン自動リフレッシュ、リトライ／バックオフ実装
- ETL パイプライン
  - 差分更新（最終取得日を基準に差分のみ取得）
  - backfill による後出し修正吸収
  - 市場カレンダーの先読み
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit のテーブル定義とインデックス
  - スキーマ初期化関数（init_schema / init_audit_schema）
- データ品質チェック
  - 欠損データ、スパイク（前日比閾値）、重複、日付不整合の検出
  - QualityIssue オブジェクトで集約して返却
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルによる完全なトレーサビリティ

---

## 必要条件・依存関係

主に以下が必要です（実行環境に応じて追加の依存がある可能性があります）:

- Python 3.9+（型注釈で | を使用しているため）
- duckdb
- 標準ライブラリ（urllib, json, logging など）

（パッケージ化時は requirements に記載してください。ここでは duckdb が必須です。）

---

## 環境変数（.env に設定する主要キー）

KabuSys は .env / .env.local / OS 環境変数から設定を読み込みます（プロジェクトルートに `.git` または `pyproject.toml` がある場合、自動ロードされます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の主な環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development | paper_trading | live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb
   - （プロジェクトがパッケージ化されている場合）pip install -e .
4. プロジェクトルートに `.env` を作成して必要な環境変数を設定
5. DuckDB スキーマの初期化（次節の「使い方」を参照）

ヒント:
- 自動で .env を読み込ませたくない（テスト等）の場合は、実行前に `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡単な例）

以下は Python スクリプトからスキーマを初期化し、日次 ETL を実行する最小例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
# デフォルトパスを使う場合は settings.duckdb_path を参照しても良い
conn = init_schema("data/kabusys.duckdb")
```

2) 監査ログ（audit）テーブルを追加する（任意）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # 既存 conn に audit テーブルを追加
```

3) 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

4) J-Quants の id_token を直接取得（必要なとき）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

ETL 実行時の主要パラメータ:
- target_date: ETL の基準日
- run_quality_checks: 品質チェックを行うか（デフォルト True）
- spike_threshold / backfill_days / calendar_lookahead_days: 調整可能

ETL の戻り値は ETLResult オブジェクトで、取得数・保存数・品質チェックの結果・エラー概要を含みます。

---

## API / モジュールの概要（主なエントリ）

- kabusys.config
  - settings: 環境変数ラッパ（settings.jquants_refresh_token など）
  - 自動で .env/.env.local をプロジェクトルートから読み込む
- kabusys.data.jquants_client
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - save_daily_quotes(), save_financial_statements(), save_market_calendar()
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.quality
  - run_all_checks(conn, ...)
  - check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## 実行時の注意点

- J-Quants API のレート制限は 120 req/min に設定されています。jquants_client モジュールでスロットリング制御していますが、他の外部 API 呼び出しと併せて運用する際は留意してください。
- get_id_token はリフレッシュトークンを用いて idToken を取得します。401 受信時は自動的にリフレッシュしてリトライする仕組みがあります。
- DuckDB のスキーマ初期化は冪等（既にテーブルがあれば作成をスキップ）です。
- 監査ログは削除を想定していません（ON DELETE RESTRICT）。運用時はストレージ管理に注意してください。
- すべての TIMESTAMP は UTC で扱う方針です（監査ログ等で SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成

リポジトリの主要ファイル / ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要モジュールの役割:
- config.py: 設定・環境変数管理
- data/: データ取得・ETL・スキーマ・品質チェック・監査ログ
- strategy/: 戦略実装を置く想定の領域（現在はパッケージのみ）
- execution/: 発注・約定関連（パッケージのみ）
- monitoring/: 監視・メトリクス（パッケージのみ）

---

## 開発 / テスト向けヒント

- テストや CI では自動で .env を読み込みたくない場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB をメモリで使う場合は db_path に ":memory:" を指定できます（init_schema(":memory:")）。
- ETL や品質チェックのユニットテストは、duckdb の in-memory 接続を使うと高速です。

---

## ライセンス / 貢献

（ここにライセンスやコントリビュート方法を追記してください）

---

README は以上です。必要であれば、セットアップの詳細な手順（requirements.txt や CI 設定、例外ハンドリング方針、運用マニュアルなど）を追記します。どの項目を詳しく追加しますか？