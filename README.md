# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ。J-Quants など外部データソースからのデータ取得、DuckDB によるデータ管理（スキーマ定義・初期化）、ETL パイプライン、ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ等の基盤機能を提供します。

主にライブラリ/モジュールとして利用し、戦略（strategy）や発注ロジック（execution）を組み合わせて運用することを想定しています。

---

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の厳守、再試行（指数バックオフ）、401 時の自動トークン更新
  - 取得日時（fetched_at）を記録し Look-ahead Bias を防止
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - インデックス、制約を含む冪等的な初期化（init_schema）
- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル、品質チェックの一括処理（run_daily_etl）
  - 個別ジョブ（run_prices_etl、run_financials_etl、run_calendar_etl）
- ニュース収集（RSS）
  - RSS フィード取得、本文前処理、記事 ID の冪等生成（正規化した URL の SHA-256 ハッシュ）
  - SSRF 対策、受信サイズ制限、XML パース保護（defusedxml）
  - DuckDB への冪等保存（raw_news, news_symbols）
- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ（calendar_update_job）
  - 営業日判定・前後営業日探索・期間内営業日取得（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - データ未取得時の曜日ベースフォールバック
- データ品質チェック
  - 欠損・重複・前日比スパイク・日付不整合の検出（QualityIssue を返す）
  - run_all_checks で全チェックを一括実行
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティ用スキーマ、初期化関数（init_audit_schema / init_audit_db）
- 設定管理
  - .env / .env.local / OS 環境変数の自動ロード（プロジェクトルート検出）
  - 必須環境変数の検証用 Settings オブジェクト

---

## 要件

- Python 3.10+
- 必要ライブラリ（最低）:
  - duckdb
  - defusedxml

（プロジェクトの pyproject.toml / requirements ファイルに依存関係を追加してください）

---

## セットアップ

1. リポジトリをクローン／配置
2. 仮想環境を作成して有効化 (推奨)
   - python -m venv .venv
   - source .venv/bin/activate など
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されていれば pip install -e .）
4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと、自動的に読み込まれます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（API 認証）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意/デフォルト値
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)、デフォルト development
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

参考: .env.example をプロジェクトに用意しておくと設定しやすくなります。

---

## 使い方（基本例）

以下は Python スクリプト内での基本的な使い方例です。

- DuckDB スキーマの初期化（初回のみ）

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # DuckDB ファイルを作成・テーブル作成
```

- 監査ログ用 DB 初期化（監査専用 DB を分ける場合）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL の実行

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
print(result.to_dict())
```

- ニュース収集ジョブの実行

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema(settings.duckdb_path)

# known_codes: 銘柄抽出用の有効な銘柄コード集合を渡すと、news_symbols に紐付ける
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- カレンダー更新ジョブ（夜間バッチ向け）

```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"保存件数: {saved}")
```

- J-Quants のトークン取得・API 利用（直接利用したい場合）

```python
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を参照して取得
quotes = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
```

---

## 注意・設計上のポイント

- API レート制限・リトライ
  - jquants_client は 120 req/min を守るために固定間隔スロットリングを行います。HTTP 408/429/5xx 等は再試行（指数バックオフ）。401 は自動でトークンを再取得して 1 回リトライします。
- データ保全・冪等性
  - DuckDB への保存は ON CONFLICT を利用して冪等性を確保しています（重複挿入・更新を排除）。
- ニュース収集の安全性
  - defusedxml を使った XML パース、受信サイズ制限、SSRF 対策（リダイレクト先の検証・プライベート IP 拒否）など、外部入力に対する防御を組み込んでいます。
- 品質チェックは Fail-Fast ではなく全件収集
  - run_all_checks は問題をすべて収集して返します。呼び出し側が重大度に応じた対応（停止・通知など）を決定します。

---

## 主要 API（モジュール一覧・簡単説明）

- kabusys.config
  - settings: 環境変数から各種設定を取得する Settings オブジェクト
  - 自動 .env 読み込み機能（プロジェクトルート検出）
- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- kabusys.data.calendar_management
  - calendar_update_job, is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_duplicates, check_spike, check_date_consistency
- kabusys.data.audit
  - init_audit_schema, init_audit_db

（strategy/execution/monitoring パッケージはエントリプレースホルダ / 実装対象です）

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル構成（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - pipeline.py
      - calendar_management.py
      - schema.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

DuckDB スキーマの主要テーブル（data/schema.py に定義）
- raw_prices, raw_financials, raw_news, raw_executions
- prices_daily, market_calendar, fundamentals, news_articles, news_symbols
- features, ai_scores
- signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
- 監査用: signal_events, order_requests, executions

---

## 開発・デバッグのヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト時に環境変数を明示的に制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB はファイルベースですが、init_schema に ":memory:" を渡すとインメモリ DB になります（テストに便利）。
- テーブルの初期化は冪等なので、複数回 init_schema を呼んでも安全です。
- ログ出力は settings.log_level で制御できます。ログは障害解析や ETL の実行状況確認に有用です。

---

## 付記

この README はコードベースから把握できる設計・主要機能をまとめたものです。運用にあたっては .env.example や DataPlatform.md / API ドキュメント等の補助ドキュメントを参照し、各種キーや API 利用制限、商用運用に伴う安全対策（認証情報の保護、レート設計、リスク管理ルールなど）を整備してください。