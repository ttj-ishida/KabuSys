# KabuSys

日本株自動売買プラットフォームのライブラリ群。データ取得・ETL、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定トレース）、品質チェックなどの基盤機能を提供します。

## 概要
KabuSys は以下を主な目的として設計されたモジュール群です。
- J-Quants API からの市場データ（株価、財務、マーケットカレンダー）取得と DuckDB への永続化（冪等保存）
- RSS ベースのニュース収集と銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、次／前営業日取得等）
- 監査ログ（戦略 → シグナル → 発注リクエスト → 約定）用スキーマと初期化処理
- ETL パイプライン（差分更新、バックフィル、品質チェック）

設計上の特徴：
- J-Quants API のレート制限（120 req/min）を考慮したレートリミッタとリトライ（指数バックオフ）
- 取得タイミング（fetched_at）を UTC で保存し、Look-ahead Bias の抑止
- DuckDB に対して冪等的に INSERT（ON CONFLICT）する実装
- RSS の取得では SSRF・XML Bomb 対策（スキーム検証、プライベートIP判定、defusedxml、受信サイズ制限 等）

---

## 主な機能一覧
- data/jquants_client.py
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - get_id_token（リフレッシュトークンから id_token 取得、401 で自動リフレッシュ）
  - save_* 関数で DuckDB に冪等保存
- data/pipeline.py
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェックの一括 ETL 実行
  - 差分取得（最終取得日ベース）と backfill（後出し修正吸収）
- data/news_collector.py
  - RSS 取得、記事正規化（URL除去、空白正規化）、記事ID生成（正規化URL の SHA-256 先頭32文字）
  - SSRF 対策・gzip 上限チェック・XML パースの堅牢化
  - raw_news へのバルク保存（INSERT ... RETURNING）と news_symbols の紐付け
- data/schema.py
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution）
  - init_schema / get_connection
- data/calendar_management.py
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチで J-Quants からの差分取得）
- data/quality.py
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks でまとめて実行
- data/audit.py
  - 監査ログ用スキーマ定義と初期化（signal_events / order_requests / executions）
- config.py
  - 環境変数からの設定取得（.env 自動読み込み、.env.local が上書き）
  - 必須変数チェック、KABUSYS_ENV / LOG_LEVEL の検証

---

## セットアップ手順

前提
- Python 3.9+（型注釈や一部の文法を前提としています。プロジェクトで適切なバージョンを使用してください）
- duckdb を使用するためネイティブバイナリが必要です（pip でインストール可能）

1. リポジトリをクローン/取得
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトで追加の依存があれば requirements.txt を用意して pip install -r requirements.txt）
4. 環境変数の設定
   - プロジェクトルート（pyproject.toml または .git がある階層）に `.env` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

推奨インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

環境変数（最低限必要なものの例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用トークン（必須なケースあり）
- SLACK_CHANNEL_ID: 通知先チャンネルID（必須なケースあり）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb（省略可）
- SQLITE_PATH: デフォルト data/monitoring.db（省略可）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主要な API と実行例）

以下は Python からの基本的な使い方例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

2) 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema を実行済みとする
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

特徴:
- run_daily_etl はカレンダー取得 → 株価差分取得（backfill 対応）→ 財務差分取得 → 品質チェック の順で実行します。
- id_token を外部で取得して注入することも可能（テスト容易性向上）。

3) RSS ニュース収集と保存
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes は抽出対象の有効な銘柄コード集合（例: '7203','6758' ...）
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # 各ソースごとの新規保存件数
```

4) カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
d = date(2026, 3, 17)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

5) 監査ログ（audit schema）初期化（別DBでも可）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

6) J-Quants の id_token を明示的に取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意点:
- jquants_client._request は内部でレート制限・リトライ・401 自動リフレッシュのロジックを備えています。
- news_collector.fetch_rss は SSRF / Gzip Bomb / XML パースエラー等の保護を行いますが、外部ネットワーク例外は呼び出し元でハンドルしてください。

---

## 環境変数の自動読み込み挙動
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` を自動的に読み込みます。
- 読み込み優先順は OS 環境変数 > .env.local > .env です（.env.local は .env を上書き）。
- 自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

---

## ディレクトリ構成（主要ファイル）
プロジェクトの主要なモジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py          # J-Quants API クライアント（取得・保存）
    - news_collector.py         # RSS ニュース収集・保存・銘柄抽出
    - schema.py                 # DuckDB スキーマ定義と init_schema/get_connection
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    # マーケットカレンダー管理（営業日判定等）
    - audit.py                  # 監査ログ（発注→約定トレース）スキーマ初期化
    - quality.py                # データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記はリポジトリ内の主要なソースファイルを抜粋したものです）

---

## 開発・運用時の注意事項
- DuckDB のファイルパスは settings.duckdb_path（デフォルト data/kabusys.duckdb）で管理されます。運用環境ではバックアップや永続ストレージの確保を検討してください。
- KABUSYS_ENV により開発/ペーパートレード/ライブの振る舞いを分けられます（ログ出力や実際の発注処理の切り替えは上位ロジックで実装してください）。
- ETL の backfill_days を十分に確保して API 側の後出し訂正を吸収してください（デフォルト 3 日）。
- ニュース収集時の銘柄抽出は単純な 4 桁数字マッチに基づくため、誤検出や見落としがあります。必要に応じて known_codes を与え、抽出ロジックを拡張してください。
- 監査ログ関連のテーブルは TTL や削除を基本的に行わない前提で設計されています。データサイズや運用要件に応じた保守方針を検討してください。

---

## 付録：よく使う関数（まとめ）
- schema.init_schema(db_path)
- schema.get_connection(db_path)
- jquants_client.get_id_token(refresh_token=None)
- jquants_client.fetch_daily_quotes(...)
- jquants_client.save_daily_quotes(conn, records)
- pipeline.run_daily_etl(conn, target_date=None, ...)
- news_collector.run_news_collection(conn, sources=None, known_codes=None)
- calendar_management.calendar_update_job(conn)
- audit.init_audit_db(db_path)
- quality.run_all_checks(conn, ...)

---

問題や追加で README に載せたい内容（例：より詳細な依存関係、CI 設定、実運用での監視/アラート設計など）があれば教えてください。必要に応じてサンプル .env.example や requirements.txt の草案も作成します。