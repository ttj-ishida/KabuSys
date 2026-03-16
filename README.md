# KabuSys

日本株向け自動売買 / データ基盤ライブラリ（README 日本語版）

概要
----
KabuSys は日本株の自動売買システムおよびデータプラットフォーム向けのライブラリ群です。本プロジェクトは主に以下を提供します。

- J-Quants API クライアント（株価・財務・市場カレンダー取得）
- DuckDB ベースのスキーマ定義と初期化ロジック（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→オーダー→約定のトレーサビリティ）

現状、strategy / execution / monitoring のパッケージは雛形になっており、主に data 層と config が実装済みです。

主な機能
--------
- J-Quants クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）に準拠する固定間隔レートリミッタ
  - 再試行（指数バックオフ、最大 3 回）、408/429/5xx を対象
  - 401 応答時は自動でリフレッシュトークンを使って ID トークン再取得して 1 回リトライ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を回避
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution 層のテーブル DDL を提供
  - インデックス定義、外部キーを考慮した作成順序
  - 監査用テーブル（signal_events, order_requests, executions）と専用初期化関数あり

- ETL パイプライン
  - run_daily_etl による一括処理（カレンダー取得 → 株価 → 財務 → 品質チェック）
  - 差分更新（DB 最終取得日を基に未取得範囲だけ取得）
  - backfill による数日前からの再取得で API 後出し修正を吸収
  - 品質チェックは全件収集（Fail-Fast ではない）

- 品質チェック
  - 欠損データ（OHLC 欠損）
  - スパイク（前日比 ±X% 超）
  - 主キー重複
  - 日付不整合（未来日付・非営業日データ）

セットアップ
----------
前提
- Python 3.10 以上（型ヒントに | を使用しているため）
- DuckDB パッケージなど必要なライブラリ（下記参照）

インストール（例）
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

2. 必要パッケージのインストール（例）
   - pip install duckdb

   ※ パッケージ配布（pyproject.toml / setup）がある場合は pip install -e . などを使用してください。

環境変数
- 自動でプロジェクトルートの .env / .env.local をロードします（CWD に依存せず __file__ を基準に探索）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須環境変数（本システムの一部機能で必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID

その他（任意・デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxx"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C12345678"
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

使い方（簡単なコード例）
--------------------

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" でインメモリ可
```

2) 監査ログスキーマ追加（既存接続へ）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
# または監査専用 DB を作る場合
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

3) J-Quants の ID トークン取得
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

4) 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

5) 個別 ETL ジョブ（例：株価だけ）
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

API の特徴（重要ポイント）
- jquants_client._request は内部でレート制御・再試行・401 自動リフレッシュを扱います。
- fetch_* 関数はページネーション対応で全件を返します。
- save_* 関数は INSERT ... ON CONFLICT DO UPDATE を利用して冪等に保存します。
- ETL は品質チェック（quality.run_all_checks）を実行し、QualityIssue のリストを返します。
- quality モジュールは問題を収集して返す設計で、呼び出し側が処理方針（停止・警告）を決められます。

開発メモ / 注意点
-----------------
- DuckDB の初期化は schema.init_schema を最初に呼ぶこと（get_connection はスキーマを作成しません）。
- run_daily_etl は内部で最大限エラーハンドリングを行い、個別ステップの失敗が全体を停止させないように設計されています（ただし errors に記録します）。
- audit モジュールでは全 TIMESTAMP を UTC で保存するため、init_audit_schema は SET TimeZone='UTC' を実行します。
- strategy / execution / monitoring の各パッケージは将来的に拡張される想定で、現状は空の __init__.py です。

ディレクトリ構成
----------------
（リポジトリ内の主要ファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理、自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存機能）
    - schema.py              # DuckDB スキーマ定義・初期化
    - pipeline.py            # ETL パイプライン（差分更新・品質チェック）
    - audit.py               # 監査ログ（トレーサビリティ）
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            # 発注実行モジュール（拡張ポイント）
  - monitoring/
    - __init__.py            # 監視・アラート（拡張ポイント）

ライセンス / 貢献
-----------------
- 本リポジトリのライセンス情報（LICENSE ファイル）がある場合はそちらに従ってください。
- バグ報告・改善案は Issue/PR で受け付けてください。

最後に
-----
この README はコードベースに基づく概要と運用上の要点をまとめたものです。実行時には J-Quants や kabu ステーションのアクセス権、API トークン、ローカルの DB 書き込み権限などを適切に設定してください。

必要であれば README に追加したいサンプルコマンドや CI/CD 用の実行例、より詳細な運用手順（cron / Airflow などでのジョブ化）を追記します。どの情報を優先して補足しましょうか？