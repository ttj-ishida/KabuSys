KabuSys — 日本株自動売買システム — README
概要
本リポジトリは日本株を対象とした自動売買フレームワーク（研究・データ取得・シグナル生成・バックテスト・シミュレーション）を提供します。主に以下のレイヤーで構成されています。
- data: J-Quants からのデータ取得、ニュース収集、DuckDB への保存
- research: ファクター計算・特徴量探索
- strategy: 特徴量正規化（feature engineering）とシグナル生成
- portfolio: 銘柄選定・配分・ポジションサイジング・リスク調整
- backtest: バックテストエンジン、シミュレータ、メトリクス計算
- execution / monitoring: 実行・監視層（インターフェース／拡張ポイント）
設定管理は kabusys.config に集約され、.env ファイル／環境変数から読み込みます。

主な機能
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info 等
  - DuckDB へ冪等に保存する save_* 関数
- RSS ベースのニュース収集（SSRF対策・トラッキング除去・記事ID生成・DB保存）
  - fetch_rss, save_raw_news, run_news_collection など
- 研究用ファクター計算
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
  - ファクター探索ユーティリティ（IC, forward returns, summary）
- 特徴量エンジニアリング
  - build_features(conn, target_date): ファクターの正規化・features テーブルへの UPSERT
- シグナル生成
  - generate_signals(conn, target_date, ...): features / ai_scores / positions を元に BUY/SELL シグナルを作成し signals テーブルへ冪等書き込み
  - Bear レジーム抑制、ストップロス判定などを実装
- ポートフォリオ構築
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes: risk-based / equal / score の単元丸め・aggregate cap 対応
  - apply_sector_cap, calc_regime_multiplier によるリスク制御
- バックテスト
  - run_backtest(...)：本番 DB をインメモリにコピーして日次ループでシミュレーションを実行
  - PortfolioSimulator による約定処理（部分約定、スリッページ、手数料のモデル化）
  - バックテスト用 CLI: python -m kabusys.backtest.run
- バックテスト評価指標
  - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades

セットアップ手順（開発環境想定）
1. リポジトリのクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境作成（例）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - 本リポジトリには requirements.txt を明示していないため、最低限以下をインストールしてください：
     pip install duckdb defusedxml
   - 実行環境に応じて他のライブラリ（例: requests, pandas 等）を追加してください。
   - 開発中は `pip install -e .` でローカルパッケージとしてインストールできます（setup 配下がある場合）。

4. 環境変数 / .env の準備
   - ルートに .env または .env.local を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（Settings.require が要求するもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード（実運用で使用）
     - SLACK_BOT_TOKEN — Slack 通知で使用
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db

5. DB スキーマ初期化
   - kabusys.data.schema.init_schema(db_path) を呼び出して DuckDB のスキーマを初期化してください。
   - バックテスト／シグナル生成には以下テーブルが必要：
     - prices_daily, features, ai_scores, market_regime, market_calendar, stocks, positions, signals, raw_prices, raw_financials, raw_news, news_symbols など（schema.init_schema 参照）

使い方（代表例）
- バックテスト（CLI）
  - 事前に DuckDB に必要データ（prices_daily 等）を投入しておく必要があります。
  - 実行例:
    python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db path/to/kabusys.duckdb
  - オプション: --cash, --slippage, --commission, --allocation-method, --max-positions, --lot-size 等。

- Python API でバックテストを呼ぶ
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest
  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  conn.close()
  result.history / result.trades / result.metrics が取得可能

- 特徴量構築（feature engineering）
  from kabusys.strategy import build_features
  conn = init_schema("path/to/kabusys.duckdb")
  count = build_features(conn, target_date)  # target_date は datetime.date
  conn.close()

- シグナル生成
  from kabusys.strategy import generate_signals
  conn = init_schema("path/to/kabusys.duckdb")
  n = generate_signals(conn, target_date)
  conn.close()

- J-Quants データ取得（例）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  data = fetch_daily_quotes(date_from=..., date_to=...)
  conn = init_schema("path/to/kabusys.duckdb")
  saved = save_daily_quotes(conn, data)
  conn.close()

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection
  conn = init_schema("path/to/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes=known_code_set)
  conn.close()

設定上の注意点 / 運用メモ
- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を基準に行われます。テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- settings.env は "development" / "paper_trading" / "live" のいずれかを期待します。live では実運用に注意してください（実際の発注層実装が含まれる場合）。
- J-Quants API クライアントは 120 req/min のレート制御を実装しており、HTTP 429 等でリトライを行います。ID トークンは自動でリフレッシュされます。
- バックテストでは本番 DB をインメモリの DuckDB にコピーして実行するため、本番の signals / positions テーブルは汚染されません。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py (パッケージ公開)
  - config.py (環境変数 / Settings)
  - data/
    - jquants_client.py (J-Quants API クライアント, 保存ユーティリティ)
    - news_collector.py (RSS 取得・前処理・DB保存)
    - ...（schema, calendar_management 等 想定）
  - research/
    - factor_research.py (mom/vol/value の計算)
    - feature_exploration.py (forward returns, IC, summary)
  - strategy/
    - feature_engineering.py (build_features)
    - signal_generator.py (generate_signals)
  - portfolio/
    - portfolio_builder.py (候補選定、重み計算)
    - position_sizing.py (株数計算、aggregate cap)
    - risk_adjustment.py (sector cap, regime multiplier)
  - backtest/
    - engine.py (run_backtest、バックテストループ)
    - simulator.py (PortfolioSimulator, 約定/MTM)
    - metrics.py (バックテスト評価指標)
    - run.py (CLI エントリポイント)
    - clock.py (模擬時計)
  - execution/ (発注層プレースホルダ)
  - monitoring/ (監視用プレースホルダ)

開発・拡張のヒント
- DB スキーマの初期化・マイグレーションは kabusys.data.schema に集約する想定です。バックテスト用に init_schema(":memory:") が用意されています。
- strategy/feature_engineering と research/factor_research は DuckDB 接続を受け取る純粋関数で設計されており、ユニットテストが容易です。
- ニュース収集は SSRF・XML Bomb 等の安全対策を実装しています。fetch_rss 内の _urlopen をモックすることで外部ネットワークアクセスを切り離したテストが可能です。
- 実際の発注（kabuステーション等）を行う場合は execution 層を実装し、Settings や実行モード（is_live / is_paper）を活用して安全に切り替えてください。

問い合わせ / 貢献
- バグ報告・機能提案は issue を立ててください。
- コードの拡張は PR をお願いします。設計上の意図（BacktestFramework.md / StrategyModel.md / DataPlatform.md 等）がコメントに記載されていますので参照してください。

以上。必要であれば README にサンプル .env.example、実行例のより詳細なコマンド、あるいは DB スキーマの抜粋を追加します。どの情報を追記しますか?