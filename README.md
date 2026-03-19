kabusys
=======

日本株向けの自動売買／データプラットフォーム用ライブラリ（モジュール群）。
データ取得（J-Quants）、ETL、DuckDB スキーマ、特徴量生成、シグナル生成、
ニュース収集、研究用ユーティリティなどを包含する内部ライブラリです。

本 README はコードベース（src/kabusys）を元にした概要・セットアップ・使い方・構成説明です。

プロジェクト概要
----------------
KabuSys は日本株の自動売買システム向けの共通基盤ライブラリです。主な責務は次の通りです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得して DuckDB に保存する。
  - レートリミット・リトライ・トークン自動リフレッシュを備える。
- DuckDB ベースのデータスキーマを提供し、Raw / Processed / Feature / Execution 層を管理する。
- ETL パイプライン（差分取得、バックフィル、品質チェック）を実装する。
- 研究（research）用にファクター計算・特徴量探索ユーティリティを提供する。
- 戦略（strategy）層：特徴量正規化・合成（feature_engineering）とシグナル生成（signal_generator）を提供する。
- ニュース収集（RSS）と記事→銘柄リンク付けのユーティリティを提供する。
- 発注／監視／実行（execution / auditing）用のスキーマ雛形を含む。

機能一覧
--------
主な機能（モジュール別）

- kabusys.config
  - .env/.env.local 自動読み込み（プロジェクトルート検出）、環境変数取得ラッパ。
  - 必須設定の取得（JQUANTS_REFRESH_TOKEN 等）と env / log レベルチェック。

- kabusys.data.jquants_client
  - J-Quants API への安全な HTTP ラッパ（ページネーション、レート制御、リトライ）。
  - fetch/save の組（fetch_daily_quotes / save_daily_quotes, fetch_financial_statements / save_financial_statements, fetch_market_calendar / save_market_calendar）。
  - DuckDB に対する冪等保存（ON CONFLICT）。

- kabusys.data.schema
  - DuckDB のスキーマ定義（raw_prices, raw_financials, prices_daily, features, ai_scores, signals, orders, executions, positions 等）。
  - init_schema(db_path) で DB の初期化を行う。

- kabusys.data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック（差分取得・バックフィル対応）。
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）。

- kabusys.data.news_collector
  - RSS フィード収集、XML 安全パース（defusedxml）、SSRF 対策、トラッキングパラメータ除去、記事 ID 生成、raw_news 保存、銘柄抽出。

- kabusys.data.calendar_management
  - 営業日判定 / 次営業日 / 前営業日 / 期間の営業日取得、カレンダー更新ジョブ。

- kabusys.data.stats
  - zscore_normalize：クロスセクション Z スコア正規化ユーティリティ。

- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）、将来リターン／IC 計算、summary 等。

- kabusys.strategy
  - build_features(conn, target_date)：研究ファクターを正規化して features テーブルへ保存。
  - generate_signals(conn, target_date, threshold, weights)：features と ai_scores を統合して売買シグナルを作成し signals テーブルへ保存。
  - 売買ルール、Bear レジーム抑制、エグジット判定（ストップロス等）を含む。

セットアップ手順
----------------
前提
- Python 3.8+（typing の一部で | 型を使用しているため 3.10+ を推奨）
- ネットワーク接続（J-Quants API 等）および DuckDB を使用可能な環境

必須ライブラリ（例）
- duckdb
- defusedxml

pip を用いる例:
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

（パッケージ化されていれば pip install -e . など）

環境変数
- .env/.env.local または環境変数で設定します。自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。
- 自動ロードを無効にする場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な必須環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）

オプション
- KABUSYS_ENV — environment: development, paper_trading, live（default: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（default: data/monitoring.db）

初期 DB 作成
- Python REPL またはスクリプトで DuckDB DB とスキーマを初期化します:

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

使い方（代表的な操作例）
----------------------

1) DuckDB スキーマ初期化
- DB ファイルを初期化して接続を得る:

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（株価 / 財務 / カレンダー）
- run_daily_etl を使って一括実行。J-Quants の id_token は settings から自動取得します。

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

3) 特徴量構築（strategy.feature_engineering）
- DuckDB 上の prices_daily / raw_financials を使って features を構築します。

  from datetime import date
  from kabusys.strategy import build_features
  n = build_features(conn, date(2024, 1, 31))
  print(f"features upserted: {n}")

4) シグナル生成（strategy.signal_generator）
- features / ai_scores / positions を参照して signals を生成します。

  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date(2024, 1, 31), threshold=0.6)
  print(f"signals written: {total}")

5) RSS ニュース収集と保存
- RSS からニュースを収集して raw_news / news_symbols に保存します。

  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)

6) 研究用ユーティリティ
- 将来リターン・IC・サマリの計算:

  from kabusys.research import calc_forward_returns, calc_ic, factor_summary
  fwd = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5,21])
  ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")

設定管理（config）
-----------------
- settings = kabusys.config.settings から各種設定へアクセスできます（例: settings.jquants_refresh_token）。
- .env 読み込みルール: OS 環境変数 > .env.local > .env。不要な自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- Settings 型では KABUSYS_ENV の許容値チェックや LOG_LEVEL の検証が行われます。

ディレクトリ構成
----------------
主要ファイル/ディレクトリ（src/kabusys をルートとしたツリーの抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント + 保存ユーティリティ
    - news_collector.py            -- RSS ニュース収集 / DB 保存
    - schema.py                    -- DuckDB スキーマ定義 / init_schema
    - stats.py                     -- zscore_normalize 等統計ユーティリティ
    - pipeline.py                  -- ETL パイプライン実装
    - calendar_management.py       -- カレンダー管理（営業日判定 等）
    - audit.py                     -- 監査ログ用スキーマ（トレース用）
    - features.py                  -- zscore_normalize を再エクスポート
  - research/
    - __init__.py
    - factor_research.py           -- momentum/value/volatility 算出
    - feature_exploration.py       -- forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py       -- features テーブル構築
    - signal_generator.py          -- signals テーブル生成（BUY/SELL 判定）
  - execution/                      -- 発注 / 実行関連（雛形）
  - monitoring/                     -- 監視用（SQLite 等、別モジュールに依存する想定）

注意事項 / 実運用上のポイント
----------------------------
- J-Quants API 利用にはトークンが必要です。rate limit（120 req/min）を尊重するよう組まれていますが、運用での負荷は注意してください。
- DuckDB のトランザクション扱いや ON CONFLICT の挙動はバージョン依存の可能性があります。init_schema の実行は一度行えば OK です。
- ニュース収集では外部 URL の検証（SSRF 対策）や XML の安全パース（defusedxml）を導入していますが、運用環境のネットワークポリシーに注意してください。
- generate_signals / build_features は発注 API に依存しない層です。実際の発注は execution 層を実装して接続する必要があります。
- tests や CI はこの README に含まれていません。ローカルでの検証には :memory: DuckDB を利用すると便利です。

貢献 / 開発
------------
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して環境依存の自動ロードを無効化できます。
- DuckDB の初期化・ETL・戦略ロジックは独立しているため、ユニットテストは各関数をモックした上で実行可能です。
- 研究用モジュールは外部ライブラリに依存しないように実装されています。大量データ解析や可視化は別途 pandas / numpy を導入して行うのが実用的です。

ライセンス / 著作権
------------------
- （この README はコードから自動生成されたドキュメントです。実際のライセンス情報はプロジェクトルートの LICENSE / pyproject.toml 等を参照してください。）

以上。必要であればセクションの追加（API リファレンス、環境変数一覧のテンプレート、よくあるトラブルシュートなど）も作成します。どの部分を優先して詳述しますか？