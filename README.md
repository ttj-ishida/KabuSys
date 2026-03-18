# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
J-Quants や kabuステーション からデータを取得して DuckDB に格納し、特徴量計算・品質チェック・監査ログを提供します。研究（Research）用途のファクター計算ユーティリティも含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- データ取得（J-Quants API）と保存（DuckDB）  
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集（RSS）と銘柄紐付け
- マーケットカレンダー管理（JPX）
- ファクター計算（Momentum / Value / Volatility など）とリサーチ支援（IC 計算等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（自動 .env ロード）

設計観点としては「冪等性」「Look-ahead バイアス回避（fetched_at）」「外部API呼び出しのリトライ／レート制御」「DuckDB中心のローカルデータレイヤ」が採用されています。

---

## 主な機能一覧

- data/jquants_client: J-Quants からのデータ取得（株価、財務、カレンダー）、保存（raw_prices, raw_financials, market_calendar）  
  - レート制限（120 req/min）制御、リトライ、401 時の自動トークンリフレッシュ
- data/schema: DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution/Audit 層）
- data/pipeline: 日次 ETL（差分取得・保存・品質チェック）
- data/news_collector: RSS から記事収集・前処理・DB 保存・銘柄コード抽出
- data/calendar_management: 営業日判定、next/prev trading day、夜間カレンダー更新ジョブ
- data/quality: 欠損・スパイク・重複・将来日付等の品質チェック
- research/*: 特徴量計算（momentum, volatility, value）、将来リターン計算、IC（スピアマン）計算、Zスコア正規化
- audit: 監査用テーブル定義（signal_events, order_requests, executions 等）
- config: .env / 環境変数読み込み、必須設定の抽象化

---

## セットアップ

前提
- Python 3.10 以上（typing の新構文や union 型 `|` を使用）
- 必要ライブラリ（例）:
  - duckdb
  - defusedxml
  - （標準ライブラリの urllib 等を使用）

例: 仮想環境を作成してインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発インストール（パッケージ化されている場合）
# pip install -e .
```

環境変数（最低限必要なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
- KABUSYS_ENV           : development | paper_trading | live（省略時: development）
- LOG_LEVEL             : DEBUG | INFO | ...（省略時: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH           : 監視DB 等（省略時: data/monitoring.db）

.env の自動読み込み
- プロジェクトルート（.git または pyproject.toml を探索）に `.env` / `.env.local` があれば自動で読み込まれます。
- テスト等で自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

例: .env（参考）
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=yyyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易ガイド）

以下は Python インタプリタやスクリプトからの実行例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# ファイルパスは settings.duckdb_path と一致させても良い
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes を渡すと本文から銘柄（4桁）抽出して news_symbols に紐付けする
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)
```

4) 研究用ファクター計算例
```python
from kabusys.data.schema import get_connection
from kabusys.research import calc_momentum, calc_volatility

conn = get_connection("data/kabusys.duckdb")
from datetime import date
d = date(2024, 1, 31)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
```

5) J-Quants からの直接データ取得（テスト）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from datetime import date
quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
fins = fetch_financial_statements(date_from=date(2023,1,1), date_to=date(2024,1,1))
```

注意点
- J-Quants API 呼び出しはレート制限があり、またトークンが必要です。settings.jquants_refresh_token を設定してください。
- DuckDB のテーブル作成は冪等に実装されています。既存 DB に対して init_schema を呼んでも安全です。

---

## 主要 API（モジュール別概観）

- kabusys.config
  - settings: 環境変数ラッパ（必須値は _require でチェック）
- kabusys.data.schema
  - init_schema(db_path) / get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token (トークンリフレッシュ)
- kabusys.data.pipeline
  - run_daily_etl (日次 ETL のエントリポイント)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss / save_raw_news / run_news_collection / extract_stock_codes
- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なファイル・ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/         (発注関連モジュール用ディレクトリ)
    - strategy/          (戦略モデル用ディレクトリ)
    - monitoring/        (監視・アラート用)
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - stats.py
      - pipeline.py
      - features.py
      - calendar_management.py
      - audit.py
      - etl.py
      - quality.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py

この README に含まれる説明は上記ソースの実装に基づいています。詳細な設定や拡張（例えば broker 連携、発注ロジック、Slack 通知、監視ダッシュボードなど）はそれぞれのディレクトリに実装を追加してください。

---

## 開発・運用上の注意

- 安全性:
  - news_collector は SSRF 対策、XML パースの脆弱性対策（defusedxml）を実装していますが、運用環境の追加セキュリティ（プロキシ/ネットワーク制限等）を検討してください。
- 品質管理:
  - run_daily_etl 内の品質チェックは Fail-Fast ではなく問題を収集して返す設計です。CI もしくは運用スクリプト側で重大度に応じた対応を行ってください。
- 本番運用:
  - KABUSYS_ENV を `live` に設定すると本番モードの判定が可能です。paper_trading 環境で十分に検証してから本番に移行してください。
- テスト:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うことでテスト時に .env の自動ロードを無効化できます。
  - DuckDB の `:memory:` を使えばインメモリ DB で単体テストが簡単に行えます。

---

必要であれば README に書くサンプル .env.example や、具体的な CLI / systemd / cron の設定例、CI 用のワークフロー、より具体的な実行例（Slack 通知や発注フロー）を追記します。どの部分を優先で追加しましょうか？