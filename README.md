KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略層を備えた自動売買基盤のライブラリです。  
主に以下を提供します。

- J-Quants からの株価・財務・マーケットカレンダーの取得（差分取得・レート制限・リトライ対応）
- DuckDB によるデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義および初期化
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量生成（Zスコア正規化）
- シグナル生成（特徴量 + AIスコア統合 → BUY / SELL シグナル）
- RSS ニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去）
- ETL（差分取得、品質チェック）とカレンダーバッチジョブ
- 発注・監査（スキーマ・データ構造の用意）

特徴
----
主な機能一覧（実装済み／提供 API）

- 環境設定
  - .env / 環境変数自動読み込み（プロジェクトルートを探索）
  - 必須設定は Settings 経由で取得（例: settings.jquants_refresh_token）

- データ取得・保存（kabusys.data.jquants_client）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - レート制限・リトライ・トークン自動リフレッシュ・ページネーション対応

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path) で必要なテーブル / インデックスを一括作成
  - get_connection(db_path) で接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl(conn, target_date, ...)
  - 差分取得ロジック、バックフィル、品質チェック呼び出し

- ニュース収集（kabusys.data.news_collector）
  - fetch_rss(url, source) → 記事整形、SSRF対応
  - save_raw_news, save_news_symbols, run_news_collection

- ファクター計算 / 研究（kabusys.research）
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank

- 特徴量生成（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) → features テーブルへ UPSERT（Zスコア正規化・ユニバースフィルタ）

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights) → signals テーブルへ書き込み
  - BUY / SELL ルール（Stop-loss, score threshold, Bear regime 抑制 等）

- ユーティリティ
  - 統計関数（kabusys.data.stats.zscore_normalize）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day 等）
  - 監査用スキーマ（audit モジュール）

セットアップ手順
----------------

前提
- Python 3.10+（コードは型アノテーションに Python 3.10 以降を想定）
- ネットワーク接続（J-Quants API、RSS フィード など）
- J-Quants のリフレッシュトークン等の外部資格情報

必要なパッケージ（最低限）
- duckdb
- defusedxml

例: 仮想環境を作って必要パッケージをインストールする
- Unix/macOS:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install --upgrade pip
  - pip install duckdb defusedxml

※ プロジェクトが pyproject.toml / setup を持つ場合は pip install -e . で開発インストールできます。

環境変数（重要）
- JQUANTS_REFRESH_TOKEN：J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD：kabuステーション API パスワード（必須）
- KABU_API_BASE_URL：kabuステーション API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN：Slack ボットトークン（必須）
- SLACK_CHANNEL_ID：通知先 Slack チャンネル（必須）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV：実行環境（development, paper_trading, live）
- LOG_LEVEL：ログレベル（DEBUG/INFO/...）

自動 .env 読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）で .env/.env.local を自動読み込みします。
- テスト等で自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

簡単な .env の例
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567
- DUCKDB_PATH=data/kabusys.duckdb
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

使い方（基本の流れ）
-------------------

1) DuckDB スキーマ初期化
- Python から実行例:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

  これで必要なテーブルが作成されます（:memory: も指定可能）。

2) 日次 ETL を実行してデータを取得・保存する
- 例:
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

  - ETL はカレンダー、価格、財務を差分取得し、品質チェックを実行します。

3) 特徴量の構築
- 例:
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import build_features

  conn = get_connection("data/kabusys.duckdb")
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

4) シグナル生成
- 例:
  from datetime import date
  from kabusys.data.schema import get_connection
  from kabusys.strategy import generate_signals

  conn = get_connection("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")

5) ニュース収集（RSS）
- 例:
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes=set(["7203","6758"]))
  print(results)

6) カレンダーバッチ（夜間ジョブ）
- calendar_update_job(conn, lookahead_days=90) を定期実行してください。

注意事項・設計方針（抜粋）
-----------------------
- すべての日次処理・ファクター計算は「ルックアヘッドバイアス」を避ける設計（target_date 時点のデータのみ参照）です。
- J-Quants クライアントはレート制限（120 req/min）を守るためスロットリングし、408/429/5xx を指数バックオフでリトライします。401 ならトークン自動リフレッシュを試みます。
- ニュース収集は SSRF／XML Bomb 等の攻撃を考慮して実装されています（_SSRFBlockRedirectHandler、defusedxml、最大読み取りバイト数制限等）。
- DB への保存は可能な限り冪等（ON CONFLICT）で実装されています。
- 各モジュールは発注 API 実装（execution 層）に直接依存しないよう設計されています。発注層は別実装を前提に監査用スキーマ等を提供します。

ディレクトリ構成（要約）
----------------------

（主要モジュールのみ抜粋、src/kabusys 以下）

- kabusys/
  - __init__.py                パッケージ定義（version 等）
  - config.py                  環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py        J-Quants API クライアント（fetch/save）
    - news_collector.py        RSS 収集・保存・銘柄抽出
    - schema.py                DuckDB スキーマ定義と init_schema/get_connection
    - stats.py                 zscore_normalize 等統計ユーティリティ
    - pipeline.py              ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   市場カレンダー管理（is_trading_day など）
    - features.py              data.stats の公開インターフェース
    - audit.py                 監査ログ用スキーマ（signal_events 等）
    - execution/               発注関連（空パッケージのことが多い）
  - research/
    - __init__.py
    - factor_research.py       モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py   将来リターン / IC / 統計要約
  - strategy/
    - __init__.py
    - feature_engineering.py   特徴量構築（build_features）
    - signal_generator.py      シグナル生成（generate_signals）
  - monitoring/                監視モジュール（ディレクトリ存在想定）
  - execution/                 発注実装領域（外部ブローカー連携など）

補足 / 開発のヒント
-------------------
- 自動 .env ロードを無効化したいテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を :memory: で使用すると単体テストが高速になります（init_schema(":memory:")）。
- ログレベルは環境変数 LOG_LEVEL で制御できます（DEBUG/INFO/…）。
- settings.jquants_refresh_token 等はプロパティで必須チェックされ、未設定時は ValueError を投げます。

ライセンス・貢献
----------------
- 本 README はコードベースからの抜粋説明です。実プロジェクトへの導入時は責任者の方針に従ってください。  
- 貢献やバグ報告はリポジトリの Issue / PR フローを利用してください。

以上。必要であれば README の英語版、CI / デプロイ手順、運用チェックリスト（Slack 通知、バックアップ、監査ログの保持方針等）を追加できます。どの情報を詳しく補足しますか？