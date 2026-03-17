# KabuSys

日本株自動売買システムのコアモジュール群です。  
データ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）、および DuckDB スキーマ定義を含みます。

主にバックエンドのライブラリ群として設計され、外部の実行コンポーネント（スケジューラ、ブローカー接続、Slack 通知など）から呼び出して利用します。

概要
- 高信頼なデータ取得（J-Quants API）と差分更新を行う ETL パイプライン
- RSS からのニュース収集と記事→銘柄紐付け
- DuckDB による三層（Raw / Processed / Feature）データスキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理（営業日判定、next/prev 営業日取得）
- 監査ログ（signal → order_request → execution のトレース）
- 設定は環境変数 / .env から読み込み（自動読み込み機能あり）

主な機能一覧
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価（日足）、財務（四半期 BS/PL）、市場カレンダー取得
  - レート制限（120 req/min）順守、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得、backfill、品質チェック統合、日次 ETL 実行 run_daily_etl
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化、SSRF 対策、gzip サイズチェック、DuckDB 保存
  - 記事IDは正規化 URL の SHA-256（先頭32文字）
- スキーマ管理（kabusys.data.schema）
  - DuckDB テーブル定義と初期化（init_schema / get_connection）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job：夜間バッチで J-Quants から差分更新
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルとインデックス初期化
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合を検出・報告する API

セットアップ手順（ローカル）
前提
- Python 3.10 以上推奨（| 型アノテーションを使用）
- Git 等でリポジトリをクローン済み

1) 仮想環境の作成（任意）
```
python -m venv .venv
source .venv/bin/activate   # Unix/macOS
.venv\Scripts\activate      # Windows
```

2) 必要パッケージをインストール
本リポジトリに requirements.txt がない場合、少なくとも以下を入れてください：
```
pip install duckdb defusedxml
```
パッケージとしてインストールして開発する場合:
```
pip install -e .
```
（プロジェクトに setup/pyproject がある場合はそちらを利用）

3) 環境変数の準備
ルートに `.env` または `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。  
主要な環境変数:
- 必須:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
  - SLACK_BOT_TOKEN       : Slack ボットトークン（通知機能を使う場合）
  - SLACK_CHANNEL_ID      : Slack チャンネル ID（通知機能を使う場合）
- 任意（デフォルトあり）:
  - KABUSYS_ENV (development | paper_trading | live) - デフォルト "development"
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) - デフォルト "INFO"
  - KABU_API_BASE_URL - kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH - DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH - SQLite 監視 DB（デフォルト data/monitoring.db）

.env の読み込みルール
- 読み込み順: OS 環境 > .env.local > .env
- export KEY=val 形式にも対応
- 引用符、エスケープ、インラインコメントなど一般的な .env パターンを処理

使い方（簡単な例）
以下はインタラクティブに利用する例です。パッケージをインストールしていることを前提とします。

1) DuckDB スキーマの初期化
```python
from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成してテーブルを作る
```

2) 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を省略すると今日が対象
print(result.to_dict())
```
- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック を順に実行します。
- id_token を明示的に渡してテストすることも可能（パラメータ id_token）。

3) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

4) RSS ニュース収集（raw_news に保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

# conn は schema.init_schema で作成した DuckDB 接続を流用するのが一般的
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)  # {source_name: 新規保存数}
```
- known_codes に銘柄コード集合を渡すと、記事本文から銘柄コード抽出して news_symbols に紐付けます。

5) 監査ログスキーマの初期化（別 DB または既存 DuckDB に追加）
```python
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存 conn に追加
init_audit_schema(conn)

# 監査専用 DB を作る
audit_conn = init_audit_db("data/audit.duckdb")
```

主な API の説明（抜粋）
- kabusys.config.settings
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.slack_bot_token / settings.duckdb_path など
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - save_daily_quotes(conn, records)
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30) -> list[NewsArticle]
  - save_raw_news(conn, articles) -> list[new_ids]
  - run_news_collection(conn, sources=None, known_codes=None) -> dict[source->count]
- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path) -> DuckDB connection
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)

注意点 / 実装上の特徴
- J-Quants クライアントは内部で固定間隔レートリミッタ（120 req/min）とリトライ（指数バックオフ）を実装しています。401 はトークン自動リフレッシュを試みます。
- fetch_* 関数はページネーション対応。モジュールレベルで id_token をキャッシュしてページ間で再利用します。
- NewsCollector は SSRF 対策、gzip サイズチェック、defusedxml による XML パース保護、トラッキングパラメータの除去など安全面に配慮しています。
- DuckDB スキーマは冪等に作成されるように設計され、ON CONFLICT / DO UPDATE / DO NOTHING を多用して再実行時の安全性を担保します。
- 品質チェックは Fail-Fast にせず、検出された問題をリスト化して呼び出し元に返します。呼び出し元で重大度に応じた対処を行ってください。

ディレクトリ構成（主要ファイル）
（src 配下を想定）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント & DuckDB 保存
    - news_collector.py      -- RSS 収集・正規化・保存
    - pipeline.py            -- ETL パイプライン（差分更新・run_daily_etl 等）
    - schema.py              -- DuckDB スキーマ定義 & init_schema
    - calendar_management.py -- カレンダー管理（営業日判定など）
    - audit.py               -- 監査ログ（signal/order_request/execution）
    - quality.py             -- データ品質チェック
  - strategy/                 -- 戦略関連（空のパッケージ / 戦略を入れる場所）
  - execution/                -- 発注・ブローカ連携（空のパッケージ / 拡張ポイント）
  - monitoring/               -- 監視関連（空のパッケージ / 拡張ポイント）

開発 / テスト向けメモ
- 自動 .env ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に便利）。
- ネットワーク IO を伴う関数（fetch_rss / _urlopen / jquants_client._request）はモックしやすいように設計されています（テスト時には外部呼び出しを差し替えてください）。
- DuckDB のインメモリモード ":memory:" を使えばテストでファイル作成不要です。

今後の拡張ポイント（参考）
- execution パッケージに証券会社（kabuステーション等）向けの注文送信・状態管理ロジックを実装
- strategy パッケージに具体的な売買戦略とリスク管理ルールを追加
- Slack 通知・監視用ダッシュボードや外部ジョブスケジューラとの統合

問い合わせ / コントリビュート
- 本 README はコードベースから抽出した設計意図と使用例をまとめたものです。実行環境やセキュリティ要件に応じて .env や DB パス等を調整してください。バグ報告や改善提案はリポジトリの issue をご利用ください。