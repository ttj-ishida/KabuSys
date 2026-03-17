# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株の自動売買基盤を構築するためのライブラリ群です。  
J-Quants からの市場データ取得、RSS ベースのニュース収集、DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）、データ品質チェック、監査ログ（トレーサビリティ）など、データ取得から監査までの主要なコンポーネントを提供します。

主な特徴
--------
- J-Quants API クライアント（株価日足・財務データ・マーケットカレンダー）
  - レート制限（120 req/min）対応のスロットリング
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias を防止
- DuckDB ベースのスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース収集（RSS）モジュール
  - URL 正規化・トラッキングパラメータ除去
  - SSRF 対策、XML 攻撃対策（defusedxml）、レスポンスサイズ制限
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で冪等性を確保
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 環境変数ベースの設定管理（.env / .env.local の自動読み込み）

動作要件
--------
- Python 3.10 以上
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）
- （任意）kabuステーション API 接続情報（発注実装時）

インストール
------------
pip を使った簡易例:

```bash
python -m pip install "duckdb" "defusedxml"
# 本プロジェクトをパッケージ化している場合:
# python -m pip install .
```

設定（環境変数 / .env）
-------------------
プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（テスト等では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動読み込みを無効化できます）。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能利用時）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（通知機能利用時）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

その他（任意・デフォルトあり）:
- KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング等）パス（デフォルト: data/monitoring.db）

.env の簡易例:

```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

セットアップ手順
----------------
1. 依存ライブラリをインストールする（上記参照）。
2. 環境変数を設定（.env を作成）。
3. DuckDB スキーマを初期化する。

Python REPL / スクリプト例:

```python
from kabusys.data import schema

# DuckDB ファイルを初期化して接続を取得
conn = schema.init_schema("data/kabusys.duckdb")
```

監査スキーマを同じ DB に追加する場合:

```python
from kabusys.data import audit
# 既存の conn を渡す
audit.init_audit_schema(conn)
```

基本的な使い方
------------

- 日次 ETL の実行例（データ取得 → 保存 → 品質チェック）:

```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続（初回は init_schema を呼ぶ）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- News（RSS）収集ジョブの実行例:

```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources は {source_name: rss_url} の辞書。省略時は DEFAULT_RSS_SOURCES を使用
results = news_collector.run_news_collection(conn)
print(results)
```

- カレンダー更新バッチ（夜間ジョブ）の実行:

```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

- J-Quants API を直接呼んでデータを取得する（テスト・デバッグ用）:

```python
from kabusys.data import jquants_client as jq
# トークン省略時は settings.jquants_refresh_token を使用して自動で取得されます
daily = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
```

注意点 / 実装上のポイント
------------------------
- J-Quants API クライアントは内部でレートリミット（120 req/min）を守るようスロットリングしています。
- ネットワーク障害や 5xx/429/408 のレスポンスに対してリトライ（最大 3 回、指数バックオフ）します。401 はトークン自動リフレッシュ後に 1 回リトライします。
- NewsCollector は SSRF 対策（リダイレクト検査・プライベートホストチェック）、XML の脆弱性対策（defusedxml）、レスポンスサイズ制限を備えています。
- DuckDB への保存は冪等操作（ON CONFLICT DO UPDATE / DO NOTHING）を採用しており、再実行時の重複を避けます。
- 環境変数は Settings クラスで検証され、KABUSYS_ENV / LOG_LEVEL 等は許容値がチェックされます。

ディレクトリ構成
----------------
パッケージ内の主な構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - pipeline.py            — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - audit.py               — 監査ログ（トレーサビリティ）初期化
    - quality.py             — 品質チェック（欠損・スパイク等）
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

上記はコードベースの主要モジュールを表しています。strategy / execution / monitoring は各自のロジック実装に応じて拡張します。

テストとデバッグ
----------------
- 自動 .env 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストで明示的に環境を制御したい場合に便利です）。
- unit テストでは jquants_client のネットワーク呼び出しや news_collector._urlopen 等をモックして外部依存を切り離すことを推奨します。
- DuckDB では `":memory:"` を指定してインメモリ DB を使用できます（テスト目的）。

貢献 / 連絡
-----------
バグ報告や機能提案は Issue を作成してください。実運用に用いる場合は API キーや資格情報の管理に十分ご注意ください（.env を適切に保護し、CI/CD に秘匿情報を直接埋め込まない等）。

---

以上がプロジェクトの概要と利用方法の概要です。必要であれば README に含めるサンプルやデプロイ手順（systemd / cron / Airflow 等）を追記できます。どの例を詳しく追加しますか？