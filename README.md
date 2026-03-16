# KabuSys

日本株自動売買システムのライブラリ（ライブラリ部分の README）。  
このリポジトリはデータパイプライン、データスキーマ、J-Quants API クライアント、監査ログ等を提供し、戦略層や発注層と組み合わせて自動売買プラットフォームを構築するための基盤を担います。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向け自動売買プラットフォームの基盤モジュール群です。主に以下の機能を提供します。

- J-Quants API クライアント（株価日足、財務データ、JPX マーケットカレンダー取得）
- DuckDB ベースのデータスキーマ定義・初期化
- ETL（差分更新・バックフィル）パイプラインと品質チェック
- 監査ログ（シグナル → 発注 → 約定 トレーサビリティ）
- 環境変数/設定管理（.env 自動ロード、必須変数の検査）
- 戦略・実行・監視のための名前空間（strategy, execution, monitoring — 実装は別途）

設計上のポイント:
- API レート制限（120 req/min）とリトライ（指数バックオフ、401 時の自動トークン更新）を厳守
- データの取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を抑止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で処理

---

## 主な機能一覧

- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB への冪等保存）
  - API レート制御、再試行、トークンキャッシュ

- data.schema
  - init_schema(db_path) : DuckDB スキーマ初期化（Raw / Processed / Feature / Execution 層）
  - get_connection(db_path) : 既存 DB への接続取得

- data.pipeline
  - run_daily_etl(conn, target_date=None, ...) : 日次差分 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl : 個別 ETL ジョブ

- data.audit
  - init_audit_schema(conn) / init_audit_db(db_path) : 監査用テーブル初期化（signal_events, order_requests, executions）

- data.quality
  - 欠損、スパイク、重複、日付不整合などの品質チェック群
  - run_all_checks(conn, ...) でまとめて実行し QualityIssue のリストを返す

- config
  - .env 自動ロード（プロジェクトルート検出: .git / pyproject.toml）
  - settings オブジェクト経由で必須設定を取得
  - 環境: development / paper_trading / live

---

## 要件

- Python 3.10+
- duckdb
- （標準ライブラリの urllib 等を使用。HTTP クライアント実装は標準 urllib。）

必要な Python パッケージはプロジェクトの pyproject.toml / requirements.txt を参照してください（本 README のコードベースはライブラリ部のみ）。

---

## セットアップ手順

1. リポジトリをクローンし、開発環境を用意します。

   python 仮想環境を作成・有効化後、依存をインストールしてください（例）:

   pip install duckdb

   （パッケージ配布や開発インストールがある場合は `pip install -e .` 等を利用）

2. 環境変数設定（.env）

   プロジェクトルート（.git か pyproject.toml と同じ階層）に `.env` または `.env.local` を作成します。自動ロードはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須環境変数（少なくとも以下を設定してください）:

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

   任意 / デフォルトあり:
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" をセットすると .env の自動ロードを無効化

   .env の読み込みルール（優先順位）:
   OS 環境変数 > .env.local > .env
   （config モジュールがプロジェクトルートを探索して自動読み込みします）

3. データベース初期化

   DuckDB スキーマを初期化して DB 接続を得ます（例: data/kabusys.duckdb を使用する場合）。

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査テーブルを別 DB または同一接続に追加する場合:

   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)

---

## 使い方（クイックスタート）

以下は主要な利用例です。実際のアプリでは例外処理やログ設定、周辺の戦略・実行コードを組み合わせてください。

1) DuckDB 初期化と日次 ETL 実行（最小例）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

# DB 初期化（ファイルがなければ作成）
conn = init_schema("data/kabusys.duckdb")

# 日次 ETL 実行（target_date を省略すると今日）
result = run_daily_etl(conn)

# ETL 結果確認
print(result.to_dict())
```

2) J-Quants から直接データ取得して保存する（個別利用）

```python
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema(":memory:")  # テスト用インメモリ DB

# id_token を自前で取得して渡すことも可能
id_token = jq.get_id_token()

records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2023,1,1), date_to=date(2023,12,31))
saved = jq.save_daily_quotes(conn, records)
print("saved rows:", saved)
```

3) 監査ログ初期化（専用 DB を用いる場合）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# または既存 conn に対して init_audit_schema(conn)
```

4) 品質チェックの実行（ETL 後に呼ぶ）

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

---

## 注意点 / 実装の挙動

- API レート制御: jquants_client 内部で 120 req/min（最小間隔 0.5 秒相当）を守るためのスロットリングを実装しています。
- 再試行ロジック: 408/429/5xx 系のエラーは最大 3 回の指数バックオフでリトライします。401 はトークンを自動リフレッシュして 1 回リトライします。
- トークンキャッシュ: ページネーションなどで同一プロセス内で id_token を共有するためのキャッシュがモジュールレベルにあります。
- データ保存は冪等: save_* 関数は ON CONFLICT DO UPDATE を使って重複を排除します。外部からの直接挿入などで重複が起きる可能性は quality.check_duplicates で検出できます。
- 時刻とタイムゾーン: fetched_at や監査テーブルの TIMESTAMP は UTC を基本（監査初期化で SET TimeZone='UTC' を実行）。
- .env の自動読み込みはプロジェクトルートが特定できない場合にはスキップされます。テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成

（コードベースに含まれる主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/         # 発注・ブローカー連携関連（名前空間）
    - __init__.py
  - strategy/          # 戦略関連（名前空間）
    - __init__.py
  - monitoring/        # 監視関連（名前空間）
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py    # J-Quants API クライアント（取得・保存ロジック）
    - schema.py           # DuckDB スキーマ定義と初期化
    - pipeline.py         # ETL パイプライン（差分更新、品質チェック）
    - audit.py            # 監査ログ（signal/order/execution）
    - quality.py          # データ品質チェック（欠損・スパイク・重複・日付不整合）
- pyproject.toml / setup.cfg 等（プロジェクトルートに存在する想定）

---

## 開発メモ / 拡張ポイント

- strategy / execution / monitoring パッケージは名前空間のみ用意されています。実際の戦略ロジック・発注ブリッジはここに実装してください。
- 発注周りは冪等鍵（order_request_id）と監査ログによるトレーサビリティを前提に設計されています。実運用でのブローカー接続や再送ロジックは execution 層で実装してください。
- 品質チェックは Fail-Fast ではなく全件の問題を収集する設計です。ETL の呼び出し側で結果の重大度に応じたアクション（停止、警告、Slack 通知等）を実装してください。
- DuckDB のスキーマは拡張しやすいように層構造で設計されています。追加のインデックスやテーブルは schema.py に追加してください。

---

この README はライブラリの利用開始ガイドです。詳しい設計資料（DataPlatform.md, DataSchema.md 等）がプロジェクト内にある想定ですので、運用時はそちらも参照してください。質問や追加のドキュメントが必要であればお知らせください。