# KabuSys

日本株向けの自動売買システム用ライブラリ（モジュール群）。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、DuckDB スキーマ／監査ログ等を含む。研究（research）と運用（execution）で共通に使えるユーティリティを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のレイヤーを提供します。

- Data layer
  - J-Quants API クライアント（取得・保存・ページネーション・リトライ・レート制御）
  - DuckDB スキーマの定義と初期化
  - ETL パイプライン（日次差分取得・バックフィル・品質チェック）
  - ニュース（RSS）収集と銘柄紐付け
  - 市場カレンダー管理
- Research / Strategy layer
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量正規化（Z スコア）・features テーブル作成
  - シグナル生成（final_score 計算、BUY/SELL 判定、SELL の優先処理）
- Execution / Monitoring（スケルトン）
  - 発注・約定・ポジション・監査ログ用スキーマを用意

設計上、ルックアヘッドバイアス防止・冪等性（ON CONFLICT / トランザクション）・API レート制御・堅牢な入力検査に留意しています。

---

## 主な機能一覧

- J-Quants API クライアント
  - 株価（日足）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - 自動トークンリフレッシュ、再試行（指数バックオフ）、レートリミッタ
  - DuckDB への冪等保存ユーティリティ（save_*）

- DuckDB スキーマ管理
  - init_schema(db_path) による全テーブル／インデックスの作成
  - get_connection(db_path) で既存 DB に接続

- ETL パイプライン
  - run_daily_etl(...)：市場カレンダー取得 → 株価差分 ETL → 財務差分 ETL → 品質チェック

- ファクター計算 / 特徴量生成
  - calc_momentum / calc_volatility / calc_value（research/factor_research）
  - zscore_normalize（クロスセクション Z スコア）
  - build_features(conn, target_date)：features テーブルへの日付単位置換挿入（冪等）

- シグナル生成
  - generate_signals(conn, target_date, threshold, weights)：final_score に基づく BUY/SELL 判定・signals テーブルへ挿入（冪等）
  - Bear レジーム判定、エグジット条件（ストップロス等）

- ニュース収集
  - RSS 取得（SSRF対策・gzip/サイズ上限・XML 脆弱性対策）
  - raw_news 保存・news_symbols で銘柄紐付け
  - run_news_collection(conn, sources, known_codes)

- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job: 先読み（lookahead）で J-Quants から差分更新

---

## セットアップ手順

前提: Python 3.10+（型ヒントで `|` 合成を利用しているため）

1. リポジトリをクローン／配置
2. 必要なパッケージをインストール（最低限）
   - duckdb
   - defusedxml
   - （標準ライブラリのみで動作するモジュールが多いですが、上記は必須）

例:
```bash
python -m pip install duckdb defusedxml
```

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと、自動で読み込まれます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
   - 任意 / デフォルトあり
     - KABUS_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

4. データベース初期化（DuckDB）
   - Python REPL やスクリプトで schema.init_schema を呼ぶと必要なテーブルが作成されます。

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

---

## 使い方（簡易ガイド）

以下は主要ワークフローの例。

1) DuckDB 初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants トークンは settings から取得）
```python
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量の作成（features テーブルへ）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, date.today())
print(f"features 作成件数: {count}")
```

4) シグナル生成（signals テーブルへ）
```python
from kabusys.strategy import generate_signals
from datetime import date

n = generate_signals(conn, date.today(), threshold=0.6)
print(f"生成したシグナル数: {n}")
```

5) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes: 有効な銘柄コードのセット（例: prices_daily から抽出）
known_codes = {"7203", "6758", ...}
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

6) カレンダー先読み更新
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

---

## 主要 API / 呼び出し一覧（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token / kabu_api_password / slack_bot_token / slack_channel_id / duckdb_path / env / log_level 等

- Data / J-Quants
  - kabusys.data.jquants_client.get_id_token(refresh_token=None)
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar

- スキーマ
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.schema.get_connection(db_path)

- ETL
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...)

- Research / Strategy
  - kabusys.research.calc_momentum / calc_volatility / calc_value
  - kabusys.strategy.build_features(conn, target_date)
  - kabusys.strategy.generate_signals(conn, target_date, threshold, weights)

- News
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.save_raw_news(conn, articles)
  - run_news_collection(conn, sources, known_codes)

- Calendar
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job(conn, lookahead_days)

---

## ディレクトリ構成（主要ファイル）

```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      stats.py
      pipeline.py
      features.py
      calendar_management.py
      audit.py
      (…raw/processed/etl/audit関連の実装)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    execution/
      __init__.py
    monitoring/
      (監視・Slack通知等の実装場所)
```

各モジュールの役割は上部の「主な機能一覧」を参照してください。

---

## 実運用上の注意 / 補足

- 環境変数は自動で .env / .env.local から読み込まれます（プロジェクトルートベース）。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。
- J-Quants API はレート制限（120 req/min）に対する制御やリトライロジックを実装済みです。大量取得時はAPIの制約を守ってください。
- DuckDB スキーマは冪等に作成されますが、スキーマ更新が必要な場合はマイグレーション戦略を検討してください。
- シグナル生成と発注（execution 層）は分離設計です。generate_signals は signals テーブルへ出力するのみで、直接発注APIを呼びません（発注層で signal_queue を監視して処理する想定）。
- ニュース収集は RSS の仕様・ソースの安定性に依存します。SSRF、XML 脆弱性、gzip bomb、レスポンスサイズ等に対する防御処理を備えていますが、運用時はソースの変更に注意してください。

---

## 開発・拡張ポイント

- StrategyModel.md / DataPlatform.md 等のドキュメントに設計意図が記載されています（リポジトリに含まれる前提）。
- weights の微調整、閾値（threshold）やストップロス等は generate_signals の引数で調整可能です。
- execution 層（証券会社 API への送信、order lifecycle）の実装は本コードベースのスキーマに沿って追加してください。
- 品質チェック（quality モジュール）は pipeline の一部として呼ばれます。品質ルールの追加・チューニングが可能です。

---

不明点や README に追記したい利用例（CI/CD、cron による日次実行、監視通知の設定等）があれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。