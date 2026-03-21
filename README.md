# KabuSys

日本株向け自動売買インフラ（ライブラリ）  
このリポジトリは、J-Quants からの市場データ取得、DuckDB によるデータ基盤、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含む日本株自動売買システムのコアコンポーネント群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の層を持つ設計方針に沿って実装されています。

- Data Layer (DuckDB)
  - 生データ（raw） -> 整形済み（processed） -> 戦略用特徴量（feature）
- Research / Strategy
  - ファクター計算、Zスコア正規化、特徴量合成、シグナル生成
- Data Fetching
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
- News Collection
  - RSS からニュースを収集し銘柄紐付け
- Execution / Audit
  - シグナル／発注／約定／ポジションの監査用スキーマ群

設計上の特徴:
- 冪等性を意識した DB 書き込み（ON CONFLICT を利用）
- ルックアヘッドバイアス回避（target_date 時点データのみ利用）
- 外部依存を最小化（DuckDB や defusedxml など必須ライブラリのみ想定）
- テストしやすいようにトークン注入や自動環境変数ロードの制御をサポート

---

## 主な機能一覧

- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - トークン取得（get_id_token）、自動リフレッシュ、レートリミット管理、再試行
- DuckDB スキーマ管理
  - init_schema / get_connection（DB 初期化と接続）
- ETL パイプライン
  - run_daily_etl（市場カレンダー、株価、財務データの差分取得・保存・品質チェック）
  - run_prices_etl / run_financials_etl / run_calendar_etl などの個別ジョブ
- ニュース収集
  - fetch_rss / save_raw_news / save_news_symbols / run_news_collection
  - URL 正規化、SSRF 対策、トラッキングパラメータ除去
- ファクター・リサーチ
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- 特徴量 & シグナル
  - build_features（Z スコア正規化・ユニバースフィルタ・features テーブル書込）
  - generate_signals（ai_scores 統合、最終スコア算出、BUY/SELL シグナル生成）
- カレンダー管理・営業日ユーティリティ
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- 監査ログ（Audit）スキーマ群
  - signal_events, order_requests, executions など

---

## セットアップ手順

前提:
- Python 3.10+
- DuckDB
- defusedxml
- （任意）その他依存ライブラリ（標準ライブラリ以外は最小限）

1. リポジトリをクローンして、パッケージをインストール（開発モード等）
   - 例:
     ```bash
     git clone <repo-url>
     cd <repo-root>
     pip install -e .
     ```
   - 必要パッケージを手動で入れる場合:
     ```bash
     pip install duckdb defusedxml
     ```

2. 環境変数の準備
   - ルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。
   - 必須の環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN （J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD （kabuステーション API パスワード）
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルトあり:
     - KABUSYS_ENV = development | paper_trading | live （デフォルト: development）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - サンプル `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     KABU_API_PASSWORD=yyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     LOG_LEVEL=INFO
     ```

3. DuckDB スキーマ初期化
   - Python REPL かスクリプトで:
     ```python
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - :memory: を指定してインメモリ DB で動かすことも可能:
     ```python
     conn = init_schema(":memory:")
     ```

---

## 使い方（代表的な例）

以下は主要なワークフローの簡単なコード例です。すべて Python から呼び出します。

- 日次 ETL を実行する
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- 特徴量をビルドする（build_features）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  count = build_features(conn, target_date=date(2026, 1, 15))
  print(f"features upserted: {count}")
  ```

- シグナルを生成する（generate_signals）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2026, 1, 15), threshold=0.6)
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を与えると記事中の銘柄コード抽出/紐付けを行う
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- カレンダー更新バッチ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants のトークン取得／データ取得（テストやデバッグ用）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()
  rows = fetch_daily_quotes(id_token=token, date_from=date(2026,1,1), date_to=date(2026,1,15))
  ```

注意:
- 関数は DuckDB の接続（duckdb.DuckDBPyConnection）を受け取る設計です。複数モジュールで同一接続を使うことが想定されています。
- 日付は datetime.date オブジェクトで与えてください。

---

## 環境変数（主な項目）

- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABU_API_BASE_URL — 省略可（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — 必須（通知連携用）
- SLACK_CHANNEL_ID — 必須
- DUCKDB_PATH — 省略可（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 省略可（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

設定は .env（または .env.local）に記述可能。パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）から自動で読み込みます。

---

## ディレクトリ構成

主要ファイル／モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py      — RSS ニュース収集・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理
    - audit.py               — 監査ログスキーマ（signal_events 等）
    - features.py            — features 用の公開インターフェイス
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py — forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — build_features（正規化・ユニバースフィルタ）
    - signal_generator.py    — generate_signals（final_score, BUY/SELL生成）
  - execution/
    - __init__.py            — （発注・execution 層の実装箇所）
  - monitoring/              — （監視・メトリクス用 DB 等を置く想定）

各モジュールはドキュメントを内部に持っており、関数シグネチャや設計方針・注意点が記載されています。まずは schema.init_schema で DB を作成し、pipeline.run_daily_etl → strategy.build_features → strategy.generate_signals の順でワークフローを試してください。

---

## 開発上の注意点 / ヒント

- DuckDB の初期化は一度だけ実行すればよく、init_schema は冪等です。
- ETL は差分取得ロジックを持つため、初回はデータ量に応じて時間がかかることがあります。
- J-Quants API のレート制限により大量リクエスト時は _MIN_INTERVAL_SEC にそった待ちが発生します。
- ニュース収集では外部 URL を扱うため SSRF 対策やレスポンスサイズ制限が施されていますが、運用環境では既知の RSS ソースのみを使うことを推奨します。
- KABUSYS_ENV を `live` にすると実運用向けの挙動（特定制約・通知など）を有効にする可能性があります。paper_trading で十分に検証してから移行してください。
- 自動 .env 読み込みは便利ですが CI / テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して明示的に環境を注入してください。

---

## 追加情報 / 貢献

- 各モジュール内の docstring に処理フローと設計方針が書かれているため、拡張や修正時は該当箇所のコメントに従ってください。
- テストや CI を整備する場合、get_id_token 等のネットワーク依存関数はモックしやすい設計になっています（id_token を注入可能）。
- 不具合報告・機能追加は issue / PR をお願いします。

---

必要であれば、README に実行例のスクリプト（cron / systemd ユニット）、ログ設定例、運用チェックリスト（監視・アラート閾値）を追加します。どの情報を優先して追加しますか？