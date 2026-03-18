KabuSys
=======

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants / RSS 等からのデータ取得、DuckDB スキーマ管理、ETL パイプライン、品質チェック、監査ログ用スキーマなどを備え、戦略層や実行層と連携できるよう設計されています。

概要
----
- 言語: Python
- 目的: 日本株のデータ収集・整備（OHLCV、財務、マーケットカレンダー、ニュース）および ETL/品質チェック/監査ログ基盤
- 永続化: DuckDB（デフォルトパス: data/kabusys.duckdb）
- セキュリティ/堅牢性設計:
  - API レート制御（J-Quants: 120 req/min）
  - 冪等保存（ON CONFLICT を用いた更新）
  - HTTP リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - RSS の SSRF や XML 攻撃対策（スキーム検査、プライベートIP拒否、defusedxml、受信サイズ制限）

主な機能
--------
- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート判定、OS 環境変数優先、.env.local は上書き）
  - 必須項目は取得時に検査して明示的なエラーを通知
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミッター、リトライ、トークン自動リフレッシュ、フェッチ日時（fetched_at）記録
  - DuckDB への冪等保存用関数（save_daily_quotes / save_financial_statements / save_market_calendar）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化（トラッキングパラメータ削除）、記事 ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF/圧縮爆弾対策、defusedxml による安全な XML パース
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO NOTHING / RETURNING）と銘柄抽出・紐付け
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義と初期化関数（init_schema）
  - インデックス作成、:memory: 接続対応
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分・バックフィル）、市場カレンダー先読み、品質チェック連携
  - run_daily_etl による一括実行（ETL 結果を ETLResult で返す）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日取得、夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - strategy → signal → order_request → executions までトレース可能な監査テーブル群、監査スキーマ初期化
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日付／非営業日）などを検出するチェック群

セットアップ手順
----------------
前提:
- Python 3.9+（型ヒントで|演算子等を利用しているため、少なくとも 3.10 を推奨）
- duckdb, defusedxml 等の依存ライブラリ

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発用途で logger 等追加のライブラリがあれば適宜インストール）

3. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を配置すると自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション等の API パスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : 通知先 Slack チャネル ID

任意（デフォルトあり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / ...（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env)
- JQUANTS_REFRESH_TOKEN="xxxxx"
- KABU_API_PASSWORD="secret"
- SLACK_BOT_TOKEN="xoxb-..."
- SLACK_CHANNEL_ID="C0123456"
- DUCKDB_PATH="data/kabusys.duckdb"

使い方（抜粋）
-------------
以下はライブラリの主要な使い方例です（Python スクリプトまたは REPL）。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB に初期化
conn = schema.init_schema("data/kabusys.duckdb")

# インメモリ DB
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL 実行（J-Quants から差分取得〜品質チェック）
```python
from kabusys.data import pipeline
from kabusys.data import schema
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄コードの紐付けも行う
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

4) マーケットカレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

5) 監査ログスキーマ初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
```

6) J-Quants API を直接呼ぶ（トークン取得 / ページネーション対応の fetch）
```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()  # settings.jquants_refresh_token から取得
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

設定（Settings / 環境変数の挙動）
--------------------------
- 自動 .env 読み込み
  - プロジェクトルートは __file__ を起点に .git か pyproject.toml を探索して決定します。
  - 優先順位: OS 環境変数 > .env.local > .env
  - テスト時など自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット

- Settings API
  - kabusys.config.settings を通じて設定値を参照できます（例: settings.jquants_refresh_token）

ディレクトリ構成（主なファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py                        : 環境変数・設定管理
- data/
  - __init__.py
  - jquants_client.py               : J-Quants API クライアント（取得・保存）
  - news_collector.py               : RSS 収集・記事整備・保存
  - pipeline.py                     : ETL パイプライン（run_daily_etl 等）
  - schema.py                       : DuckDB スキーマ定義・初期化
  - calendar_management.py          : カレンダー管理・営業日判定
  - audit.py                        : 監査ログスキーマ
  - quality.py                      : データ品質チェック
- strategy/
  - __init__.py
- execution/
  - __init__.py
- monitoring/
  - __init__.py

注意事項 / よくある運用上のポイント
----------------------------------
- DuckDB に対する DDL/INSERT は基本的に冪等化されていますが、ETL 設計に合わせてバックアップやトランザクション運用を検討してください。
- J-Quants API のレートやレスポンス仕様は変更される可能性があるため、実運用ではログ監視とエラーハンドリング（監視アラート）を整備してください。
- news_collector では外部 URL の検証（スキーム・プライベートIPの拒否）、受信サイズ制限、gzip 解凍後のサイズ検査などを実装しています。カスタム RSS ソースを追加するときは URL の妥当性を確認してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境読み込み挙動を制御できます。また、jquants_client._urlopen や news_collector._urlopen 等をモックしてネットワーク依存を排除することを推奨します。

ライセンス / 貢献
-----------------
本 README はコードベースの説明です。ライセンスやコントリビュートガイドがある場合はプロジェクトルートにそれらのファイル（LICENSE, CONTRIBUTING.md 等）を追加してください。

お問い合わせ / 実装補足
--------------------
この README はコードから読み取れる設計意図・主要 API をまとめたものです。各関数の詳細な挙動（引数、例外、返り値）については該当モジュールの docstring を参照してください。必要であればサンプルスクリプトや CI 用ジョブ定義（ETL スケジュール、監視ジョブ）を追加で作成できます。