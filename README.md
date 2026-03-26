KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買・リサーチ・バックテスト用ライブラリです。  
DuckDB を用いたデータ基盤、J-Quants API クライアント、ニュース収集、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテストエンジン、シミュレータ等を含むモジュール群で構成されています。  
パッケージは src/kabusys 以下に実装されています。

主な機能
--------
- データ取得・ETL
  - J-Quants API クライアント（株価、財務データ、上場情報、マーケットカレンダー）
  - RSS ニュース収集（SSRF対策・トラッキングパラメータ除去・記事ID生成）
  - DuckDB への冪等保存ユーティリティ
- 研究用モジュール（research）
  - モメンタム／ボラティリティ／バリュー 等のファクター計算
  - 将来リターン計算、IC（スピアマン）の算出、ファクターサマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 研究で生成した生ファクターを正規化・合成して features テーブルへ保存
- シグナル生成（strategy.signal_generator）
  - features と AI スコアを統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ格納
  - Bear レジーム抑制、エグジット判定（ストップロス等）
- ポートフォリオ構築（portfolio）
  - 候補選定、配分（等金額/スコア加重）、リスク調整（セクター上限、レジーム乗数）、株数決定（リスクベース等）
- バックテスト（backtest）
  - run_backtest による全体ループ、擬似約定シミュレータ、評価指標（CAGR, Sharpe, MaxDD 等）
  - CLI ランナー（python -m kabusys.backtest.run）
- 実行層 / 監視（骨組み）：execution, monitoring（現状はパッケージエクスポートのためのプレースホルダ等）

動作要件
--------
- Python 3.10 以上（型ヒントや union 型（|）を利用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード）を行うためインターネット接続が必要

セットアップ
-----------
1. リポジトリをクローンして仮想環境を作成
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. インストール
   - pip install -e .  または  pip install duckdb defusedxml
   - (プロジェクトルートが setuptools/pyproject を含む想定。適宜 requirements.txt を用意している場合はそちらを使用)

3. 環境変数 (.env)
   - プロジェクトルートの .env（および .env.local）から自動で読み込まれます（CWD には依存しません）。
   - 自動読み込みを無効にする場合:
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注機能等で使用）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack 通知先チャネル ID
   - 任意 / デフォルトあり
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — monitoring 用 SQLite（デフォルト: data/monitoring.db）
   - .env のパースは kabusys.config に記述された仕様に従います（export 付き行、クォート、コメント処理など対応）。

初期データベースの用意
--------------------
本ライブラリは DuckDB スキーマ初期化関数（kabusys.data.schema.init_schema）を利用して DB を開きます。init_schema を実行してスキーマを作成・初期化してください（schema スクリプトは必須）。  
（本リポジトリに schema 実装がある場合は init_schema(args.db) を呼ぶことで DuckDB ファイルが準備されます）

基本的な使い方（例）
------------------

1) バックテスト（CLI）
   - 例:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db path/to/kabusys.duckdb
   - オプション: --slippage, --commission, --max-position-pct, --allocation-method, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size 等

2) Python API（REPL / スクリプト）
   - DuckDB 接続の初期化（例: from kabusys.data.schema import init_schema）
   - 特徴量構築
     from kabusys.strategy import build_features
     conn = init_schema("data/kabusys.duckdb")
     build_features(conn, target_date=date(2024, 1, 31))
   - シグナル生成
     from kabusys.strategy import generate_signals
     generate_signals(conn, target_date=date(2024, 1, 31))
   - バックテスト（プログラムから）
     from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     # result.history / result.trades / result.metrics を参照

3) データ取得・保存（J-Quants）
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   - recs = fetch_daily_quotes(date_from=..., date_to=...)
   - save_daily_quotes(conn, recs)
   - 同様に fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar / fetch_listed_info が利用可能

4) ニュース収集
   - from kabusys.data.news_collector import run_news_collection
   - run_news_collection(conn, sources=None, known_codes=set_of_codes)
   - 個別ユーティリティ: fetch_rss, save_raw_news, extract_stock_codes など

設定と挙動に関する注意事項
------------------------
- .env 自動ロード:
  - 優先順位: OS 環境変数 > .env.local > .env
  - テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれか。is_live/is_paper/is_dev プロパティで参照可能。
- ログレベルの検証あり（LOG_LEVEL）。
- J-Quants API クライアントは内部でレートリミッタ、リトライロジック、401 時のトークンリフレッシュ等の安全機構を備えています。
- ニュース収集は SSRF 対策、レスポンスサイズ制限、gzip 解凍後のサイズ検査など堅牢性に配慮しています。

主要モジュールと責務（ディレクトリ構成）
--------------------------------------
src/kabusys/
- __init__.py: パッケージメタ情報
- config.py: 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- data/
  - jquants_client.py: J-Quants API クライアント（取得 & DuckDB への保存関数含む）
  - news_collector.py: RSS ニュース取得・保存・銘柄抽出
  - (schema.py 等: DB スキーマ初期化・管理 / calendar_management 等が存在する想定)
- research/
  - factor_research.py: モメンタム/バリュー/ボラティリティ などのファクター計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー等
- strategy/
  - feature_engineering.py: features テーブル作成（正規化・フィルタ）
  - signal_generator.py: final_score 計算・BUY/SELL シグナル生成
- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算（リスク制御・単元丸め・aggregate cap）
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- backtest/
  - engine.py: run_backtest（メインループ・補助）
  - simulator.py: PortfolioSimulator（擬似約定・履歴管理）
  - metrics.py: バックテストメトリクス（CAGR, Sharpe 等）
  - run.py: CLI エントリポイント
  - clock.py: SimulatedClock（将来拡張用）
- execution/: 発注層（プレースホルダ）
- monitoring/: 監視 / メトリクス（プレースホルダ）
- research/__init__.py, portfolio/__init__.py, backtest/__init__.py, strategy/__init__.py: パブリック API をエクスポート

例: 主要関数のエクスポート
- kabusys.strategy.build_features(conn, target_date)
- kabusys.strategy.generate_signals(conn, target_date)
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.news_collector.run_news_collection(...)

開発・貢献
----------
- コードはモジュール毎に単体テストを書くことを推奨します（特にデータ処理・数値処理部分）。
- .env.example（プロジェクトルートに置くことを想定）を参照し、必要な環境変数を設定してください。
- 自動ロードはプロジェクトルートの検出に .git または pyproject.toml を利用します。パッケージ配布後も正しく動作するよう実装されています。

ライセンス
---------
（ライセンス情報はリポジトリに含めてください。ここでは明記していません。）

補足
----
この README はコードベース（src/kabusys/*）の主要機能と使用方法をまとめたものです。実運用の前に schema の初期化、データ投入手順（J-Quants からのデータ取得）、およびバックテスト用のデータ品質チェック（欠損値・日付レンジ等）を十分に行ってください。質問や追加の利用例が必要であれば教えてください。