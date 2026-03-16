# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
データ収集（J-Quants）、ETL、データ品質チェック、DuckDBスキーマ、監査ログ基盤などを含みます。  
（発注・戦略・モニタリング周りはモジュール構成を提供しており、実装は拡張可能です）

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向け基盤ライブラリです。主に以下を提供します。

- J-Quants API からのデータ取得（株価日足、四半期財務、JPXカレンダー）
- DuckDB を用いたスキーマ定義と初期化
- ETL パイプライン（差分更新、バックフィル、先読みカレンダー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- 環境変数/.env 読み込みと設定ラッパー

設計上のポイント：
- API レート制御（120 req/min）とリトライ（指数バックオフ、401時のトークン自動リフレッシュ）
- データ保存は冪等（ON CONFLICT DO UPDATE）
- 監査ログは削除しない前提でトレーサビリティを厳格化
- DuckDB を想定した高速な SQL ベース処理

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - get_id_token（リフレッシュトークン→IDトークン）
  - save_* 系で DuckDB に冪等保存
  - レートリミッタ／リトライ／トークン自動再取得
- data.schema
  - DuckDB のテーブルDDL定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) により DB ファイルを初期化
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl: 日次の差分ETL + 品質チェックを一括実行
- data.quality
  - 欠損検出、スパイク検出、重複検出、日付整合性チェック
  - run_all_checks でまとめて実行
- data.audit
  - 監査テーブル（signal_events, order_requests, executions）と初期化関数
- config
  - .env / .env.local を自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で必須設定を参照
- strategy / execution / monitoring
  - パッケージ構成（拡張用プレースホルダ）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒント等で | 型を使用）
- Git（プロジェクトルート検出に使われます）

1. リポジトリをクローン、作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb

   （パッケージ化されている場合は `pip install -e .` でローカルインストール可能）

4. 環境変数の準備
   - プロジェクトルートに `.env` および必要に応じて `.env.local` を置きます。
   - 自動読み込みはデフォルトで有効。テスト時等に無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数例（.env に記載）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_station_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C...

任意:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL  （デフォルト: INFO）
- DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
- SQLITE_PATH=data/monitoring.db

例 `.env`（簡易）
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456

5. データベース初期化
   - Python REPL またはスクリプトから schema.init_schema() を呼び出して DuckDB を初期化します（親ディレクトリは自動作成されます）。

---

## 使い方（基本例）

以下は最小限の Python サンプルです。

- DuckDB スキーマの初期化（ファイル版）
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")

- インメモリDB を使う場合
  conn = schema.init_schema(":memory:")

- 監査テーブルを追加で初期化
  from kabusys.data import audit
  audit.init_audit_schema(conn)

- J-Quants から日次ETL を実行（自動で settings.jquants_refresh_token を使用）
  from kabusys.data import pipeline
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- IDトークンを明示的に渡す場合（テストや並列制御時）
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()
  result = pipeline.run_daily_etl(conn, id_token=id_token)

- 品質チェックのみ実行
  from kabusys.data import quality
  issues = quality.run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)

注意点
- run_daily_etl は内部で calendar → prices → financials → quality の順で実行します。各ステップは個別に捕捉され、1ステップの失敗で他が停止しない設計です（結果の ETLResult に errors が格納されます）。
- J-Quants API のレート制御を内部で行います。大量並列リクエストは避けてください。

---

## 環境変数一覧（重要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション:
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読込を無効化)

settings オブジェクトから簡単に参照できます:
from kabusys.config import settings
print(settings.duckdb_path, settings.is_live)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py                - パッケージエントリ（version）
    config.py                  - 環境変数/.env 管理と Settings
    data/
      __init__.py
      jquants_client.py        - J-Quants API クライアント（取得＋保存）
      schema.py                - DuckDB スキーマ定義・初期化
      pipeline.py              - ETL パイプライン（差分更新・バックフィル）
      quality.py               - データ品質チェック
      audit.py                 - 監査ログ（signal/order/execution）定義
      pipeline.py              - ETL 実行エントリ
    strategy/
      __init__.py              - 戦略層（拡張用）
    execution/
      __init__.py              - 発注実装（拡張用）
    monitoring/
      __init__.py              - モニタリング（拡張用）

その他:
  pyproject.toml / setup.cfg / README.md（本ファイル）

---

## 開発メモ / 実装上の注意

- API の再試行・リフレッシュロジックは jquants_client._request に実装されています。401は1回だけトークン再取得を試みます（再帰防止のフラグあり）。
- データ保存はすべて ON CONFLICT DO UPDATE を用いるためリトライや部分失敗時の冪等性が担保されています。
- quality.run_all_checks は Fail-Fast ではなく問題を全て収集して返します。重大度（error/warning）に応じて呼び出し側で対応してください。
- DuckDB のテーブル作成時に親ディレクトリが存在しない場合は自動作成されます。
- 監査ログは UTC タイムゾーンで保存するように設計されています（init_audit_schema は SET TimeZone='UTC' を実行します）。

---

## ライセンス / 貢献

（このリポジトリのライセンス、コントリビューション方針をここに記載してください）

---

必要であれば、README にサンプル .env.example、より詳しい使用例（cron/ci での ETL 実行方法、Slack 通知統合例、kabu-station の発注フローサンプル）を追加します。どの項目を拡充したいか教えてください。