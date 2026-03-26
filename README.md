KabuSys
=======

日本株向けの自動売買・リサーチ基盤ライブラリです。  
バックテスト、ファクター計算、シグナル生成、データ取得（J‑Quants）、ニュース収集などの主要機能をモジュール化して提供します。

要約
----
- 名前: KabuSys
- 目的: 日本株の戦略研究および自動売買の基盤提供（データ取得 → 特徴量生成 → シグナル生成 → 発注/実行 / バックテスト）
- 言語: Python (3.10+ を推奨)
- 主な外部依存: duckdb, defusedxml（その他は標準ライブラリ中心）

主な機能
--------
- 環境設定読み込み（.env / 環境変数）と型安全な Settings ラッパー
- ファクター計算（Momentum / Volatility / Value 等）と Z スコア正規化
- 特徴量（features）テーブル作成（build_features）
- シグナル生成（generate_signals）：複数コンポーネントの重み付け合成、Bear 判定、BUY/SELL 判定、signals テーブルへの冪等書き込み
- ポートフォリオ構築:
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - リスク調整（セクター上限、レジーム乗数）
  - サイジング（position sizing、単元丸め、aggregate cap）
- バックテストフレームワーク:
  - 取引シミュレータ（擬似約定、手数料・スリッページモデル）
  - バックテストループ（run_backtest）とメトリクス算出（CAGR, Sharpe, MaxDD, WinRate 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- データ取得・ETL:
  - J‑Quants API クライアント（認証リフレッシュ、ページネーション、リトライ、レート制限）
  - DuckDB への冪等保存ユーティリティ（raw_prices / raw_financials / market_calendar 等）
- ニュース収集:
  - RSS フィード取得、XML の安全パース、本文正規化、記事ID生成、DB 保存（raw_news / news_symbols）
  - SSRF / Gzip / 大容量対策 等のセーフガード
- 研究用ユーティリティ:
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー

セットアップ手順
---------------
前提: Python 3.10 以上を想定（型ヒントに | 演算子を使用）

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb defusedxml
   - （プロジェクトをeditableで使う場合）プロジェクトルートで:
     - pip install -e .

   追加で使用するライブラリがある場合は requirements.txt を参照してください（無ければ上の 2 パッケージが主な外部依存です）。

3. 環境変数設定
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（.git または pyproject.toml があるディレクトリをプロジェクトルートとして探索）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時等に便利）。

 必須環境変数（Settings 参照）
   - JQUANTS_REFRESH_TOKEN  （J‑Quants 認証用リフレッシュトークン）
   - KABU_API_PASSWORD      （kabuステーション API パスワード）
   - SLACK_BOT_TOKEN        （Slack 通知用 Bot トークン）
   - SLACK_CHANNEL_ID       （Slack チャンネル ID）
 オプション（デフォルトあり）
   - KABU_API_BASE_URL  (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH        (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH        (デフォルト: data/monitoring.db)
   - KABUSYS_ENV        (development | paper_trading | live; デフォルト: development)
   - LOG_LEVEL          (DEBUG|INFO|...; デフォルト: INFO)

使い方（主要例）
----------------

1) バックテスト実行（CLI）
   - DB は事前に DuckDB スキーマを初期化・データ投入しておく必要があります（kabusys.data.schema.init_schema を利用）。
   - 実行例:
     python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db path/to/kabusys.duckdb

   - 主要引数:
     --start / --end : 実行期間
     --cash : 初期資金
     --slippage / --commission : スリッページ・手数料
     --allocation-method : equal | score | risk_based
     --max-positions, --lot-size など

2) Python API から（サンプル）
   - DuckDB 接続初期化:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 特徴量生成:
     from kabusys.strategy import build_features
     from datetime import date
     count = build_features(conn, date(2024, 1, 31))

   - シグナル生成:
     from kabusys.strategy import generate_signals
     generate_signals(conn, date(2024, 1, 31), threshold=0.6)

   - バックテスト（プログラム的呼び出し）:
     from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)

   - J‑Quants からのデータ取得と保存:
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
     records = fetch_daily_quotes()  # 引数で日付/コードを指定可能
     save_daily_quotes(conn, records)

   - RSS ニュース収集:
     from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
     res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_code_set)

3) Settings（環境変数ラッパー）
   - from kabusys.config import settings
     token = settings.jquants_refresh_token
     is_live = settings.is_live

注意点 / 運用メモ
-----------------
- .env 読み込みはプロジェクトルート（.git または pyproject.toml を含むディレクトリ）から行われます。配布後に CWD 依存で動かないよう配慮済みです。
- .env.local は .env を上書きするため開発環境の機密値上書きに便利です。ただし OS 環境変数は保護されます。
- J‑Quants クライアントはレート制限（120 req/min）と自動トークンリフレッシュ、リトライを組み込んでいます。
- ニュース収集は SSRF / XML 脆弱性 / Gzip bomb / サイズ制限 等に配慮した安全実装です。
- バックテストでは prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等のテーブルが事前に整備されている必要があります。kabusys.data.schema.init_schema を利用して DB を作成してください。

ディレクトリ構成（主なファイル）
------------------------------
以下はソースツリー（src/kabusys）内の主なモジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                         # 環境設定（Settings）
  - execution/                         # 発注・実行関連（実装/拡張ポイント）
  - portfolio/
    - __init__.py
    - portfolio_builder.py            # 候補選定・重み算出
    - position_sizing.py              # 株数計算・aggregate cap
    - risk_adjustment.py              # セクターキャップ・レジーム乗数
  - strategy/
    - __init__.py
    - feature_engineering.py          # features 作成（Z スコア正規化等）
    - signal_generator.py             # final_score 算出・BUY/SELL 生成
  - research/
    - __init__.py
    - factor_research.py              # momentum/volatility/value 計算
    - feature_exploration.py          # IC / forward returns / summary
  - backtest/
    - __init__.py
    - engine.py                       # run_backtest（ループ全体）
    - simulator.py                    # PortfolioSimulator（約定ロジック）
    - metrics.py                      # バックテスト指標計算
    - run.py                          # CLI エントリポイント
    - clock.py
  - data/
    - jquants_client.py               # J‑Quants API クライアント
    - news_collector.py               # RSS 収集・DB 登録
    - (schema.py が存在し、DB 初期化用関数を持つ想定)
  - monitoring/                        # 監視・通知関連（拡張ポイント）

ライセンス / 貢献
-----------------
- 本ドキュメントではライセンスファイルは示していません。リポジトリの LICENSE を確認してください。
- バグ報告や改善提案は Issue / Pull Request で受け付けます。PR ではユニットテスト・ドキュメント更新を含めてください。

最後に
------
この README はコードベースの主要機能と使い方をまとめたものです。より詳細なアルゴリズムや設計意図はソースコード内の docstring（各モジュールの先頭コメント）および StrategyModel.md / PortfolioConstruction.md などの設計ドキュメントを参照してください（リポジトリに同梱されている想定）。