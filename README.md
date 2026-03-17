# KabuSys

日本株向けの自動売買／データ基盤ライブラリ（KabuSys）。J-Quants API や RSS を使ったデータ取得・ETL、DuckDB スキーマ、品質チェック、ニュース収集、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータプラットフォームのための共通ライブラリ群です。主に以下を目的とします。

- J-Quants API からの市場データ（株価日足・財務・市場カレンダー）取得
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いたデータスキーマ定義・初期化
- ETL（差分取得・保存）パイプラインとデータ品質チェック
- 監査ログ（シグナル→発注→約定のトレーサビリティ構築）
- カレンダー管理（営業日判定、翌営業日/前営業日取得）

設計面での注力点：
- API レート制限とリトライ（J-Quants クライアント）
- 冪等性（DuckDB 側は ON CONFLICT を利用）
- SSRF 対策、XML 安全性（news_collector）
- ETL の差分更新・バックフィル戦略
- 品質チェックは全件収集（Fail-Fast ではない）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants からのデータ取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - レートリミッタ、リトライ、トークン自動リフレッシュ
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）

- data/news_collector.py
  - RSS フィード取得・XML パース（defusedxml 使用）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256）
  - SSRF 対策（スキーム検証・プライベートアドレス検出）
  - raw_news / news_symbols へのバルク保存（トランザクション、INSERT RETURNING）

- data/schema.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - インデックス定義、init_schema() による初期化

- data/pipeline.py
  - 差分 ETL と日次パイプライン（run_daily_etl）
  - backfill（後出し修正吸収）、品質チェック呼び出しの統合

- data/calendar_management.py
  - market_calendar の更新ジョブ（calendar_update_job）
  - 営業日判定・next/prev_trading_day・get_trading_days 等

- data/quality.py
  - 欠損チェック、スパイク検知、重複チェック、日付整合性検査
  - QualityIssue 型で問題を集約

- data/audit.py
  - signal_events / order_requests / executions 等の監査用スキーマと初期化関数（init_audit_schema / init_audit_db）

- config.py
  - .env / 環境変数の読み込み（自動ロード機能）
  - settings オブジェクト経由で設定取得（トークン・DB パス・Slack 等）
  - 自動ロードの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

前提: Python 3.10 以上を推奨（型ヒントで | を使用しています）。

1. リポジトリをクローン／作業ディレクトリへ移動

2. 仮想環境作成（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須（代表例）:
     - duckdb
     - defusedxml
   - 実際のプロジェクトでは requirements.txt / pyproject.toml を利用してください。
   例:
   - pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env ファイルを置くと自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   推奨の環境変数（.env 例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO

5. DB スキーマの初期化
   - DuckDB ファイルを作成してスキーマを初期化します（data/schema.init_schema を使用）。

---

## 使い方（簡単な例）

以下はライブラリを使って DuckDB を初期化し、日次 ETL を実行する最小例です。

1) スキーマを初期化して接続を取得する:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は .env / 環境変数から取得されます
conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブを実行:
```python
from kabusys.data.news_collector import run_news_collection
# known_codes: 銘柄抽出に使う有効コードセット（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=None, known_codes=None)
print(res)  # {source_name: saved_count}
```

4) J-Quants から株価を個別に取得して保存:
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

token = None  # None の場合、モジュール内キャッシュにより自動取得/リフレッシュされます
records = jq.fetch_daily_quotes(id_token=token, code="7203", date_from=None, date_to=None)
saved = jq.save_daily_quotes(conn, records)
```

5) 監査ログ用スキーマの初期化（監査DBを別ファイルに作る場合）:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

ログやエラーは標準的な logging を利用します。LOG_LEVEL 環境変数で制御してください。

---

## よく使う API / 関数一覧（抜粋）

- settings（kabusys.config）
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env, settings.is_live など

- DuckDB スキーマ
  - init_schema(db_path) -> DuckDB 接続
  - get_connection(db_path)

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl(conn, target_date, ...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
  - run_daily_etl(conn, target_date=None, run_quality_checks=True, ...)

- ニュース収集（kabusys.data.news_collector）
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- 品質チェック（kabusys.data.quality）
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=0.5)
  - check_missing_data / check_spike / check_duplicates / check_date_consistency

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py          # J-Quants API クライアント・保存ロジック
      - news_collector.py         # RSS ニュース収集
      - schema.py                 # DuckDB スキーマ定義・初期化
      - pipeline.py               # ETL パイプライン（差分更新 / run_daily_etl）
      - calendar_management.py    # マーケットカレンダー管理
      - audit.py                  # 監査ログ（トレーサビリティ）
      - quality.py                # データ品質チェック
    - strategy/                    # 戦略関連（プレースホルダ）
      - __init__.py
    - execution/                   # 発注実行関連（プレースホルダ）
      - __init__.py
    - monitoring/                  # 監視関連（プレースホルダ）
      - __init__.py

---

## 注意事項・開発メモ

- 自動 .env ロード
  - config.py はプロジェクトルート（.git または pyproject.toml）を探索して .env / .env.local を自動で読み込みます。
  - テスト時など自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants トークン
  - get_id_token() はリフレッシュトークンから ID トークンを取得します。jquants_client はモジュールレベルで id_token をキャッシュし、401 を検知すると 1 回リフレッシュして再試行します。

- レート制限・リトライ
  - J-Quants は 120 req/min を守るための固定間隔レートリミッタを実装しています。HTTP エラーやネットワークエラーに対する指数バックオフリトライも備えています。

- セキュリティ
  - news_collector は defusedxml、SSRF 対策、応答サイズ制限（MAX_RESPONSE_BYTES）などを実装しており、安全なフィード収集を目指しています。

- DuckDB
  - init_schema() は冪等にテーブル・インデックスを作成します。複数プロセスからの同時更新やバックアップ運用は使用状況に応じて検討してください。

---

## 開発・テスト向けヒント

- news_collector._urlopen はテストでモック可能（外部通信を差し替えられる設計）。
- run_news_collection や ETL 関数は DuckDB の ":memory:" 接続を使って単体テスト可能です。
- audit.init_audit_schema の transactional フラグでトランザクション実行を切り替えられます（DuckDB のトランザクション性に注意）。

---

もし README に追加したい具体的なコマンド例（systemd タイマー / cron ジョブ / Dockerfile など）や、CI/テストの記載があれば教えてください。プロジェクトに合わせて追記します。