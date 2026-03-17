# KabuSys

日本株向け自動売買基盤のコアライブラリ（KabuSys）。  
データ取り込み（J-Quants / RSS）、ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレース）を主に提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムで必要となるデータ基盤・ETL・品質チェック・監査ログのためのモジュール群を提供します。主な目的は以下です。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS フィードからニュース収集（SSRF/zipbomb 対策・トラッキングパラメータ除去・冪等保存）
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution / Audit 層）
- 日次 ETL（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注〜約定フローをトレースする監査用スキーマ

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を守る仕組み
- ネットワーク／HTTP エラーに対する指数バックオフリトライ
- データ保存は冪等に設計（ON CONFLICT DO UPDATE / DO NOTHING）
- 監査ログは削除せず記録を残す方針（トレーサビリティ重視）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出: .git or pyproject.toml）
  - 必須環境変数の検証（Settings クラス）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - ID トークン取得、ページネーション対応のデータ取得
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への保存 (save_daily_quotes / save_financial_statements / save_market_calendar)
  - レートリミッタ、再試行、401 自動リフレッシュ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・XML パース（defusedxml）
  - URL 正規化・トラッキングパラメータ除去・記事ID は URL ハッシュで冪等化
  - SSRF 対策（スキーム検証・ホストプライベートチェック・リダイレクト検査）
  - レスポンスサイズ上限（Gzip を含む）による DoS 対策
  - DuckDB への冪等保存（raw_news, news_symbols）
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema(db_path) による初期化（冪等）
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL: カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得、バックフィル、品質チェックの統合
- 品質チェック（kabusys.data.quality）
  - 欠損データ / スパイク検出 / 重複 / 日付不整合など
  - run_all_checks(conn, ...) で一括実行し QualityIssue のリストを返す
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions など、発注から約定までの監査用テーブル
  - init_audit_schema / init_audit_db を提供

---

## セットアップ手順

前提:
- Python 3.10+（型注釈に | を使用しているため）
- git 等の一般的な開発ツール

1. リポジトリをクローン（またはソースを配置）
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - 最小: duckdb, defusedxml
   - pip install duckdb defusedxml
   - その他、運用に応じて Slack クライアントや kabu ステーション用クライアント等を追加してください
4. 環境変数（.env）を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例: .env（必須キーのみ抜粋）
```
JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
KABU_API_PASSWORD=<your_kabu_api_password>
SLACK_BOT_TOKEN=<your_slack_bot_token>
SLACK_CHANNEL_ID=<your_slack_channel_id>
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- .env.local が存在する場合は .env の値を上書きします（OS 環境変数は保護され上書きされません）。
- settings から各値を取得すると、未設定の必須キーは ValueError を送出します。

---

## 使い方

以下は代表的な利用例（スクリプトからの利用イメージ）。

1) DuckDB スキーマを初期化する
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ: conn = schema.init_schema(":memory:")
```

2) 日次 ETL を実行する（J-Quants トークンは settings による自動取得/リフレッシュ）
```python
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存DBに接続
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブを実行する
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes を渡すと記事と銘柄の紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
summary = news_collector.run_news_collection(conn, known_codes=known_codes)
print(summary)
```

4) J-Quants の生データ取得・保存（個別利用）
```python
from kabusys.data import jquants_client as jq
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"Saved {saved} daily quotes")
```

5) 設定値の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 未設定だと ValueError
print(settings.duckdb_path)            # Path オブジェクト
```

注意点（重要）:
- J-Quants クライアントは API のレート制限を守るために内部でスロットリングを行います。過度の同時呼び出しは避けてください。
- fetch_* 関数はページネーション対応で全件取得します。大量取得時は時間がかかる場合があります。
- news_collector は外部からのフィードを取得するため、ネットワークエラーは発生し得ます。run_news_collection は各ソースごとにエラー処理して継続します。

---

## ディレクトリ構成

リポジトリ（src/kabusys）内のおおまかな構成:

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__）と公開モジュール一覧
- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス
- src/kabusys/data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存・認証）
  - news_collector.py
    - RSS 収集、前処理、DuckDB 保存、銘柄抽出
  - schema.py
    - DuckDB スキーマ定義、init_schema、get_connection
  - pipeline.py
    - ETL パイプライン（run_daily_etl、run_prices_etl 等）
  - audit.py
    - 監査ログ用スキーマと初期化（init_audit_schema / init_audit_db）
  - quality.py
    - データ品質チェック（欠損、スパイク、重複、日付整合性）
- src/kabusys/strategy/
  - __init__.py (将来的に戦略アルゴリズムを配置)
- src/kabusys/execution/
  - __init__.py (将来的にブローカー接続・発注ロジックを配置)
- src/kabusys/monitoring/
  - __init__.py (監視・アラート関連を配置)

---

## 実運用での注意点

- 機密情報（API トークン、パスワード）は必ず安全に管理してください（.env はバージョン管理に含めない）。
- ETL のスケジューリング（cron / Airflow / Prefect 等）は運用側で行ってください。run_daily_etl は単回実行関数として設計されています。
- 監査ログおよび重要な品質問題は外部監視（Slack 通知など）と組み合わせて運用することを推奨します。
- DuckDB ファイルは同時書き込みに注意が必要です。複数プロセスが書き込みを行う場合は排他制御を検討してください。

---

## 付録: よく使う API の一覧（関数）

- config
  - settings (Settings)
- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)
- data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
- data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path)

---

必要であれば、README にサンプル .env.example、より詳細な実行例（cron/airflow 用タスク記述）、テスト方法、依存パッケージの固定リスト（requirements.txt）などを追加します。どの情報を優先して追記しますか？