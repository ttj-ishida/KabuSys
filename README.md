# KabuSys

日本株自動売買プラットフォームのライブラリ群（KabuSys）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、DuckDB スキーマ／監査ログなど、自動売買システムの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを安全かつ冪等に取得・保存
- RSS フィードからニュース記事を収集して DuckDB に保存し、銘柄コードを抽出
- ETL（差分更新 + バックフィル）とデータ品質チェック（欠損／スパイク／重複／日付不整合）
- DuckDB ベースのスキーマ定義（Raw / Processed / Feature / Execution / Audit）
- 監査ログ（signal → order → execution のトレース）を保持する機能

設計上の要点：
- API レート制限（J-Quants: 120 req/min）を尊重する RateLimiter 実装
- HTTP リトライ（指数バックオフ、401 ならトークン自動リフレッシュ）
- Look-ahead bias を防ぐため fetched_at を UTC で記録
- DuckDB への挿入は ON CONFLICT を使って冪等性を確保
- RSS 取得時の SSRF 対策、XML パースの安全化（defusedxml）、レスポンスサイズ制限などセキュリティ対策を実装

---

## 主な機能一覧

- データ取得（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - 保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- ETL（kabusys.data.pipeline）
  - run_daily_etl による市場カレンダー・株価・財務の差分取得／保存と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行
- スキーマ定義と初期化（kabusys.data.schema）
  - init_schema/db 接続取得、各レイヤーのテーブル定義とインデックス
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、記事ID生成（正規化URL の SHA-256 先頭 32 文字）
  - raw_news への冪等保存、news_symbols（記事-銘柄紐付け）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日、期間内営業日リスト、夜間カレンダー更新ジョブ
- 品質チェック（kabusys.data.quality）
  - 欠損／スパイク／重複／日付不整合の検出
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions によるトレーサビリティ

---

## セットアップ手順

前提：Python 3.10+（型ヒントで | を用いるため）を想定します。

1. リポジトリをチェックアウト
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 代表的な依存：duckdb, defusedxml
   - 例:
     pip install duckdb defusedxml

   （パッケージ配布用に requirements.txt / pyproject.toml があればそれを使ってください）

4. 開発環境（editable）インストール（任意）
   - プロジェクトルートに pyproject.toml がある場合:
     pip install -e .

5. 環境変数の設定
   - プロジェクトルートの .env / .env.local を自動で読み込みます（初期設定）。
   - 自動読み込みをスキップするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の環境変数（README 用サンプル）:
- JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
- KABU_API_PASSWORD=<kabu_api_password>
- SLACK_BOT_TOKEN=<slack_bot_token>
- SLACK_CHANNEL_ID=<slack_channel_id>

設定（任意/デフォルトあり）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）

例 .env（簡易）:
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（プログラム例）

以下は主要な利用例です。これらは Python スクリプトやバッチジョブから呼び出して使います。

- DuckDB スキーマ初期化（初回のみ）
```python
from kabusys.data.schema import init_schema

# ファイルパスまたは ":memory:" を指定
conn = init_schema("data/kabusys.duckdb")
# conn は duckdb.DuckDBPyConnection
```

- 監査ログ用 DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_duckdb.duckdb")
```

- 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 個別 ETL ジョブを実行（株価のみ）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- RSS ニュース収集ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出に使用する有効な銘柄コードセット（例: {'7203','6758',...}）
result = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
print(result)  # {source_name: inserted_count}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- J-Quants からのデータ取得を直接呼ぶ（トークン手動注入）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

token = get_id_token()  # settings から refresh token を使って id token を取得
quotes = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,2,1))
```

注意点：
- 自動で id_token キャッシュ / リフレッシュが行われます。テスト時は id_token を明示的に渡して副作用を抑えられます。
- J-Quants のレート制限（120 req/min）を内部で遵守していますが、外部ループで連続実行する場合は注意してください。

---

## ディレクトリ構成

主要ファイル・モジュール（リポジトリ内 src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み（.env / .env.local）、settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・認証・リトライ・レート制御）
    - news_collector.py
      - RSS 取得、前処理、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と初期化（Raw/Processed/Feature/Execution 等）
    - pipeline.py
      - ETL パイプライン（差分更新 / 品質チェック / run_daily_etl）
    - calendar_management.py
      - 営業日判定、calendar_update_job
    - audit.py
      - 監査ログ（signal_events / order_requests / executions）初期化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py（戦略実装は各ユーザーが追加）
  - execution/
    - __init__.py（発注・ブローカー連携は拡張領域）
  - monitoring/
    - __init__.py（監視・アラート用モジュール領域）

---

## 環境・運用に関する補足

- 環境変数の自動読み込み
  - プロジェクトルート（このファイルの親階層から .git または pyproject.toml を探索）にある .env / .env.local を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- ロギング / 実行モード
  - KABUSYS_ENV: development / paper_trading / live（is_dev / is_paper / is_live で分岐可能）
  - LOG_LEVEL: ログレベルを制御します

- セキュリティと耐障害性
  - RSS の SSRF 対策、XML の安全パーサ（defusedxml）、受信サイズ制限
  - J-Quants API はリトライとトークン自動リフレッシュを備えています
  - DuckDB への挿入はオンコンフリクト対処を行い、ETL は冪等性を維持

---

## トラブルシューティング

- 環境変数エラー
  - Required な変数が未設定だと settings プロパティが ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。
- DB 初期化の権限エラー
  - DUCKDB_PATH の親ディレクトリが存在しない場合は自動作成されますが、ファイルシステムの権限を確認してください。
- J-Quants API の認証失敗
  - get_id_token が 401/認証エラーを返す場合、refresh token の値を見直してください。
- RSS 取得が失敗する / サイズオーバー
  - ログに原因が出力されます（Content-Length 超過 / gzip 解凍失敗 / XML パース失敗 等）

---

この README はコードベース内の docstring および設計コメントに基づき作成しています。戦略ロジック（strategy/）やブローカ連携（execution/）は各運用環境に合わせて実装・拡張してください。質問や追加で README に入れたい内容があれば教えてください。