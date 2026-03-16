KabuSys
=======

日本株向けの自動売買 / データプラットフォーム用ライブラリ（プロジェクト骨格）。  
主に J-Quants API から市場データを取得して DuckDB に格納し、ETL・品質チェック・監査ログを提供します。

概要
----
KabuSys は以下を目的としたモジュール群です。

- J-Quants API からの株価（OHLCV）、財務データ、JPX マーケットカレンダー取得
- DuckDB に対するスキーマ定義・初期化
- 差分 ETL パイプライン（backfill 対応・レート制限・リトライ・トークンリフレッシュ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ用スキーマ（シグナル→発注→約定のトレーサビリティ）
- 設定管理（.env 自動読み込み、環境変数経由）

主な機能一覧
--------------
- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - settings オブジェクト経由で必須/任意設定を取得
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限（120 req/min）、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) でスキーマを作成
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(conn, ...)：市場カレンダー→株価→財務→品質チェックの一括実行（差分更新・backfill）
  - 個別ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl
  - ETL 実行結果を ETLResult オブジェクトで返す（品質問題・エラーを集約）
- 品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks でまとめて実行し QualityIssue のリストを返す
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルを初期化する init_audit_schema(conn)
  - 監査用インデックスを作成、UTC タイムゾーン使用を前提

セットアップ手順
----------------

1. リポジトリをクローン（またはソースを取得）
   - 例: git clone <repo-url>

2. Python 環境
   - 推奨: Python 3.10 以上（型注記に | を使用）
   - 仮想環境を作成して有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 最低限: duckdb
   - 例:
     - pip install duckdb
   - 将来的に pyproject.toml / requirements.txt があれば pip install -r requirements.txt または pip install -e . を使用

4. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を配置すると自動読み込みされます。
   - 自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須環境変数（.env の例）
--------------------------
以下は主要な環境変数の一覧と用途例です（名前は実際のコードで参照されるもの）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack 通知先チャンネル ID
- KABUSYS_ENV (任意, default=development)
  - 'development', 'paper_trading', 'live' のいずれか
- LOG_LEVEL (任意, default=INFO)
  - 'DEBUG','INFO','WARNING','ERROR','CRITICAL'
- KABU_API_BASE_URL (任意)
  - kabu ステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH / SQLITE_PATH (任意)
  - データベースファイルパス（デフォルトは data/kabusys.duckdb など）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

基本的な使い方
---------------

以下は最小限の操作例です。

- スキーマ初期化（DuckDB）
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数 DUCKDB_PATH を参照します
conn = schema.init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

- 監査ログスキーマを追加
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

- 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # デフォルトで今日を対象に実行
print(result.to_dict())
```

- 個別ジョブ（任意の日付・トークン注入も可能）
```python
from datetime import date
from kabusys.data.pipeline import run_prices_etl
# run_prices_etl(conn, target_date, id_token=None, ...)
fetched, saved = run_prices_etl(conn, date(2025, 1, 1))
```

- J-Quants の id_token を直接取得（テスト・デバッグ用）
```python
from kabusys.data import jquants_client as jq
id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用
```

主要 API の説明（抜粋）
---------------------
- schema.init_schema(db_path) → DuckDB 接続（全テーブル・インデックス作成）
- audit.init_audit_schema(conn) → 監査用テーブルを追加
- jquants_client.fetch_daily_quotes(...) → J-Quants から株価をページネーション取得
- jquants_client.save_daily_quotes(conn, records) → raw_prices に冪等保存
- pipeline.run_daily_etl(conn, ...) → 市場カレンダー→株価→財務→品質検査の一括 ETL
- quality.run_all_checks(conn, ...) → 全品質チェックを実行し QualityIssue のリストを返す

実装上のポイント / 設計の要点
----------------------------
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml による判定）を基準に行うため、CWD に依存しません。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- J-Quants クライアントは 120 req/min のレート制限を守るため固定間隔スロットリングを使用。またリトライ（指数バックオフ）を実装、401 発生時はリフレッシュして 1 回リトライします。
- DuckDB への保存は ON CONFLICT DO UPDATE（冪等）で差分を吸収します。
- ETL は差分更新をデフォルトとし、backfill_days による後出し修正吸収を行います。
- 品質チェックは Fail-Fast を避け、すべてのチェックを実行して QualityIssue を返し、呼び出し側で判断できるようにしています。
- 監査ログは削除しない前提（FOREIGN KEY は ON DELETE RESTRICT）、すべて UTC タイムスタンプを保存します。

ディレクトリ構成（主要ファイル）
-------------------------------
(src ディレクトリ配下のファイル一覧を抜粋)

- src/kabusys/
  - __init__.py                パッケージ定義（version 等）
  - config.py                  環境変数・設定管理（settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py        J-Quants API クライアント（取得・保存ロジック）
    - schema.py                DuckDB スキーマ定義・初期化
    - pipeline.py              ETL パイプライン（差分更新・品質チェック）
    - audit.py                 監査ログ（signal/order/execution）スキーマと初期化
    - quality.py               データ品質チェック
  - strategy/
    - __init__.py              戦略関連プレースホルダ
  - execution/
    - __init__.py              発注・ブローカ連携プレースホルダ
  - monitoring/
    - __init__.py              監視・モニタリングプレースホルダ

トラブルシューティング
---------------------
- .env が読み込まれない：
  - プロジェクトルートが .git または pyproject.toml を含む場所であるか確認
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
- J-Quants API の認証エラー（401）が発生する：
  - JQUANTS_REFRESH_TOKEN が有効か確認。get_id_token() で取得テストをしてください。
- DuckDB に接続できない / ファイルが作成されない：
  - DUCKDB_PATH のパーミッション、親ディレクトリが存在するか確認。init_schema は親ディレクトリを自動作成しますが、パーミッションがない場合は失敗します。

ライセンス / 貢献
-----------------
（このテンプレートには明示的なライセンスファイルが含まれていないため、利用時はプロジェクトに適切な LICENSE を追加してください。）

---

この README は現状のコードベース（src/kabusys 内のモジュール）に基づいています。拡張（戦略実装、ブローカー接続、監視 UI、CI/CD など）を行う場合は、各レイヤの拡張ポイント（strategy/, execution/, monitoring/）に実装を追加してください。