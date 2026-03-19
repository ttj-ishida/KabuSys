# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
主に以下を提供します。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB ベースのデータスキーマと ETL パイプライン（差分取得・品質チェック）
- RSS ベースのニュース収集・前処理・銘柄紐付け
- リサーチ向けのファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ
- 発注・監査（スキーマ設計のみ。ブローカ接続等は別実装）などの基盤機能

バージョン: 0.1.0

---

## 特徴（機能一覧）

- data/
  - jquants_client: J-Quants API クライアント（レートリミット、リトライ、トークン自動リフレッシュ、ページネーション対応）
  - schema: DuckDB 用スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - pipeline / etl: 日次差分 ETL（価格・財務・カレンダー）、品質チェック実行
  - news_collector: RSS 取得・前処理・DB 保存・銘柄抽出（SSRF対策、gzip制限、XMLサニタイズ）
  - quality: 欠損・重複・スパイク・日付不整合チェック
  - calendar_management: JPX カレンダー管理・営業日ユーティリティ（next/prev/is_trading_day 等）
  - audit: 発注〜約定までの監査ログ用スキーマ初期化ユーティリティ
  - stats: Zスコア正規化などの統計ユーティリティ
- research/
  - factor_research: モメンタム／ボラティリティ／バリュー等のファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC 計算、factor_summary 等
- config: 環境変数の読み込みと設定ラッパー（.env/.env.local の自動読み込み、必須チェック）
- 自動化を想定した堅牢な設計（冪等性、トランザクション管理、ログ、エラー区分）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型注釈で | を利用しているため）
- DuckDB を使用（ローカルファイルまたは :memory:）

1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - 主要依存:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - （補足）ネットワーク/HTTP に標準ライブラリ urllib を使用するため `requests` は必須ではありません。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を置くと自動で読み込まれます（自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（Settings で require されるもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知を使う場合（必須になっている箇所があれば）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - KABU_API_PASSWORD — kabuステーション API を使う場合
   - 任意（デフォルトあり）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=abcdef...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. スキーマ初期化（DuckDB）
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)
     # または明示的にパス指定
     # conn = init_schema("data/kabusys.duckdb")
     ```

---

## 使い方（主要ワークフロー例）

以下は代表的な操作例です。実行は Python スクリプト / バッチで行ってください。

1. 日次 ETL を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")  # 既に初期化済みなら get_connection でも可
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. J-Quants のデータを直接取得・保存する（細かい制御）
   ```python
   import duckdb
   from kabusys.data import jquants_client as jq

   conn = duckdb.connect("data/kabusys.duckdb")
   token = jq.get_id_token()  # settings.jquants_refresh_token を使用してトークン取得
   records = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved = jq.save_daily_quotes(conn, records)
   print(f"saved {saved} records")
   ```

3. RSS ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   import duckdb

   conn = duckdb.connect("data/kabusys.duckdb")
   # known_codes は銘柄抽出のための有効銘柄セット（例: exchange のコードリスト）
   known_codes = {"7203", "6758", "9984"}  # 実環境では全銘柄セットを用意
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # 各ソースごとの新規保存件数
   ```

4. ファクター計算（リサーチ）
   ```python
   from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   target = date(2024, 1, 31)
   mom = calc_momentum(conn, target)
   vol = calc_volatility(conn, target)
   val = calc_value(conn, target)

   # 将来リターン（翌日など）
   fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
   # 例: mom の mom_1m と fwd の fwd_1d の IC 計算
   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   print("IC:", ic)
   ```

5. カレンダー関連ユーティリティ
   ```python
   from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
   import duckdb
   from datetime import date

   conn = duckdb.connect("data/kabusys.duckdb")
   d = date(2024, 1, 1)
   print(is_trading_day(conn, d))
   print(next_trading_day(conn, d))
   print(get_trading_days(conn, date(2024,1,1), date(2024,1,10)))
   ```

---

## 自動環境変数読み込みの挙動

- パッケージ起点（このファイルの親ディレクトリが .git または pyproject.toml を含むルート）を探索して `.env` と `.env.local` を自動読み込みします。
- 読み込みの優先順位: OS 環境変数 > .env.local > .env
- テスト等で自動読み込みを無効化したい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースはシェル形式（export 付き・クォート・コメント）に対応しています。

---

## ディレクトリ構成

主要ファイル/モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - etl.py
      - quality.py
      - calendar_management.py
      - audit.py
      - stats.py
      - features.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

（上記はリポジトリに含まれる主要モジュール。data 配下に ETL / スキーマ / 収集ロジックがまとまっています。）

---

## 開発・デプロイに関する注意点

- DuckDB の DDL では一部の RDBMS の制約（ON DELETE CASCADE など）を意図的に使わない設計になっています。アプリ側での削除順序に注意してください。
- J-Quants API のレート制限（120 req/min）をモジュール側で制御していますが、運用時は別途レート・失敗時の監視を導入してください。
- news_collector は外部 RSS を収集するため、SSRF 対策やコンテンツサイズ制限、XML の安全パースをしています。独自にフィードを追加する際はホワイトリストやタイムアウトを適切に設定してください。
- 環境（KABUSYS_ENV）に応じて本番口座/発注ロジックの挙動を切り替える想定です。環境を `live` にする際は十分な安全確認を行ってください。

---

## 参考（よく使う関数一覧）

- 初期化
  - kabusys.data.schema.init_schema(db_path)
  - kabusys.data.schema.get_connection(db_path)
- ETL / パイプライン
  - kabusys.data.pipeline.run_daily_etl(conn, target_date=...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.pipeline.run_financials_etl(...)
  - kabusys.data.pipeline.run_calendar_etl(...)
- J-Quants クライアント
  - kabusys.data.jquants_client.get_id_token(refresh_token=None)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
- ニュース
  - kabusys.data.news_collector.fetch_rss(url, source)
  - kabusys.data.news_collector.run_news_collection(conn, sources, known_codes)
- リサーチ / ファクター
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(conn, target_date, horizons)
  - kabusys.research.calc_ic(factor_records, forward_records, factor_col, return_col)
  - kabusys.data.stats.zscore_normalize(records, columns)

---

必要なら README にサンプル .env.example、動作確認用の最小スクリプト、または CI / デプロイ手順（systemd / cron での ETL スケジューリング等）を追加できます。どの情報を優先して追記したいか教えてください。