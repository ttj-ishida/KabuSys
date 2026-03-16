# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）
バージョン: 0.1.0

このリポジトリはデータ取得・ETL、データ品質チェック、監査ログ（トレーサビリティ）といった
自動売買システムの基盤機能を提供します。戦略実装・発注実装は strategy / execution モジュールで行います。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成された軽量な日本株データプラットフォームです。

- J-Quants API からの市場データ（株価日足、四半期財務、マーケットカレンダー）取得
- DuckDB によるスキーマ定義・永続化（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得 + バックフィル + 品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレースを UUID 連鎖で保存）
- 環境設定の集中管理（.env の自動読み込み、Settings API）

設計上の特徴:
- API レート制限（J-Quants: 120 req/min）を考慮したスロットリング
- リトライ（指数バックオフ）とトークン自動リフレッシュ
- ETL の冪等性（DuckDB に ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast にせず全件収集して呼び出し元が判断可能

---

## 主な機能一覧

- data.jquants_client
  - J-Quants から daily quotes、financial statements、market calendar を取得
  - 取得・保存（DuckDB）用のユーティリティ（fetched_at の付加、ページネーション）
- data.schema
  - DuckDB のスキーマ定義（raw_prices, raw_financials, market_calendar, features, signals, orders, trades, positions, ...）
  - init_schema / get_connection を提供
- data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェック の一連処理
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新・バックフィル対応）
- data.quality
  - 欠損、スパイク、重複、日付不整合を検出するチェック群
  - QualityIssue データ構造で問題を返す
- data.audit
  - signal_events / order_requests / executions 等、監査用テーブルの初期化・管理
- config
  - .env / 環境変数の読み込み（自動ロード）、Settings クラスによる型付きアクセス

---

## 動作要件

- Python 3.10+
- パッケージ依存（代表例）
  - duckdb
  - （標準ライブラリのみで動作するコードも多いですが、環境に応じて追加が必要になる可能性があります）

requirements.txt がある場合はそれを利用してください。なければ最低限次をインストールしてください:

pip install duckdb

---

## セットアップ手順

1. レポジトリをチェックアウト / クローン

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - あるいは最低限: pip install duckdb

4. 環境変数（.env）を作成
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと、自動的に読み込まれます（デフォルト）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID（必須）
   - 任意:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

6. DuckDB スキーマの初期化
   - Python REPL / スクリプトで次を実行して DB とテーブルを作成します（親ディレクトリがなければ自動生成されます）。

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

7. 監査ログテーブルの初期化（必要なら）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する最小例:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（既に存在する場合はスキップ）
conn = init_schema(settings.duckdb_path)

# ETL 実行（引数を指定せずデフォルトで今日の処理）
result = run_daily_etl(conn)
print(result.to_dict())
```

- 特定日を対象に ETL を実行する例:

```python
from datetime import date
result = run_daily_etl(conn, target_date=date(2024, 1, 10))
```

- トークンを明示的に渡す（テスト用）:

```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token(refresh_token="dummy_refresh_token")
# 取得した id_token を pipeline に渡す
result = run_daily_etl(conn, id_token=id_token)
```

- 監査ログを初期化して監査用 DB を独立して作る:

```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

- 品質チェックのみ実行する例:

```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

注意点:
- run_daily_etl は内部で market calendar → prices → financials の順に実行します。品質チェックで重大な error が見つかった場合でも、ETL 自体は各ステップごとに例外処理され継続します。戻り値の ETLResult で errors / quality_issues を確認してください。
- 自動で .env をロードしますが、テスト中などで無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## API / 主要関数一覧（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.slack_bot_token, settings.duckdb_path など

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- kabusys.data.quality
  - check_missing_data(conn, target_date=None)
  - check_spike(conn, target_date=None, threshold=...)
  - check_duplicates(conn, target_date=None)
  - check_date_consistency(conn, reference_date=None)
  - run_all_checks(conn, ...)

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリ内の主なファイル・ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            # J-Quants API クライアント（取得・保存）
      - schema.py                    # DuckDB スキーマ定義・初期化
      - pipeline.py                  # ETL パイプライン
      - audit.py                     # 監査ログ（signal/order/execution）
      - quality.py                   # データ品質チェック
      - (その他: pipeline 用ユーティリティ等)
    - strategy/
      - __init__.py                  # 戦略ロジック（実装はここに追加）
    - execution/
      - __init__.py                  # 発注実装（証券会社連携）用
    - monitoring/
      - __init__.py                  # 監視・メトリクス用（将来的な拡張）
- pyproject.toml or setup.py (プロジェクトルートに存在する想定)
- .env, .env.local (自動ロード対象 / ユーザ作成)

---

## 運用上の注意

- J-Quants API のレート制限（120 req/min）を超えないようにしてください。ライブラリは簡易的なレートリミッタを実装していますが、複数プロセスから同時にアクセスする場合は注意が必要です。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に保存されます。バックアップやロックに注意してください。
- 全てのタイムスタンプは UTC ベースで保存する設計になっています（監査ログなどでは明示的に UTC をセット）。
- KABUSYS_ENV は development / paper_trading / live のいずれかを指定してください。live モードでは特に発注ロジックなどの慎重な挙動が求められます。

---

もし README に追加したい利用シナリオ（例: cron での定期実行スクリプト、Slack 通知のサンプル、kabuステーション連携の詳細など）があれば、その情報に合わせて手順・サンプルコードを追記します。