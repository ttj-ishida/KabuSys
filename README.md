KabuSys — 日本株自動売買フレームワーク
================================

概要
----
KabuSys は日本株向けの自動売買・研究・バックテスト用ライブラリです。  
主な目的は次のとおりです：

- J-Quants 等から市場データを収集して DuckDB に保存する ETL
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- 特徴量エンジニアリング → シグナル生成（BUY/SELL）
- ポートフォリオ構築（候補選定、配分、リスク調整、サイジング）
- バックテストエンジン（擬似約定、マーク・トゥ・マーケット、メトリクス計算）
- ニュース収集と銘柄紐付け（RSS）

機能一覧
--------
主な機能（モジュール別）：

- data/
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、レート制限、DuckDB への保存ユーティリティ）
  - news_collector: RSS 収集、前処理、raw_news 保存、銘柄抽出（SSRF 対策・gzip 制限等）
- research/
  - factor_research: prices_daily / raw_financials を使ったファクター計算（mom/vol/value）
  - feature_exploration: 将来リターン、IC、統計サマリー等の解析ユーティリティ
- strategy/
  - feature_engineering: ファクターの正規化・フィルタ・features テーブルへの書き込み
  - signal_generator: features + ai_scores を統合して BUY / SELL シグナル生成
- portfolio/
  - portfolio_builder: 候補選定・重み計算（等配分・スコア配分）
  - position_sizing: 発注株数計算（risk_based / equal / score、単元丸め、aggregate cap）
  - risk_adjustment: セクターキャップ適用、レジーム乗数
- backtest/
  - engine: バックテスト全体ループ（データコピー、シグナル生成 → 約定 → 時価評価）
  - simulator: 擬似約定モデル（スリッページ・手数料・部分約定・履歴記録）
  - metrics: バックテストの評価指標（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - run: CLI エントリポイント（期間・初期資金・スリッページ等を指定して実行）
- 設定管理
  - config: 環境変数 / .env 自動読み込み、必須キーチェック、環境切替（development / paper_trading / live）

セットアップ手順
--------------
前提
- Python 3.10+（typing | union 表記等を考慮）
- 必要パッケージ（一例）: duckdb, defusedxml（実行環境に合わせて requirements を用意してください）

手順例

1. リポジトリをクローンしてインストール（開発モード）
   - git clone ... && cd repo
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -e .     # setup.py / pyproject.toml がある前提

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

3. 環境変数 (.env) を準備
   プロジェクトルート（.git または pyproject.toml を基準）に .env または .env.local を置けます。
   自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の優先順で読み込まれます。
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   代表的な変数（README 用抜粋）:
     - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD      (必須) — kabu API 用パスワード
     - KABU_API_BASE_URL      (任意) — デフォルト http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN        (必須) — Slack 通知用
     - SLACK_CHANNEL_ID       (必須) — Slack チャネル ID
     - DUCKDB_PATH            (任意) — default: data/kabusys.duckdb
     - SQLITE_PATH            (任意) — default: data/monitoring.db
     - KABUSYS_ENV            (任意) — development / paper_trading / live
     - LOG_LEVEL              (任意) — DEBUG/INFO/... 

4. DuckDB スキーマ初期化
   - 本コードは data.schema.init_schema() を通じて DuckDB のスキーマを初期化する想定です（実装ファイルに従って下さい）。
   - 例: from kabusys.data.schema import init_schema; conn = init_schema("data/kabusys.duckdb")

使い方（代表的な例）
------------------

- バックテスト（CLI）
  - 事前に DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar 等が揃っている必要があります。
  - 実行例:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - 主要引数: --cash, --slippage, --commission, --allocation-method, --max-positions, --lot-size 等

- Python API の利用例
  - DuckDB 接続を作成:
    - from kabusys.data.schema import init_schema
    - conn = init_schema("data/kabusys.duckdb")
  - 特徴量計算 → シグナル生成:
    - from datetime import date
      from kabusys.strategy import build_features, generate_signals
    - build_features(conn, target_date=date(2024, 1, 10))
    - generate_signals(conn, target_date=date(2024, 1, 10))
  - バックテストをプログラム的に実行:
    - from kabusys.backtest.engine import run_backtest
    - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  - J-Quants からデータ取得（例）:
    - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    - recs = fetch_daily_quotes(date_from=..., date_to=...)
    - save_daily_quotes(conn, recs)

注意・運用上のポイント
---------------------
- 設計上、研究モジュール（research）とストラテジー/バックテストは「ルックアヘッドバイアス」を避けるために target_date 時点までのデータのみを使用するように実装されています。
- jquants_client はレート制限（120 req/min）とリトライ・トークン自動リフレッシュを備えています。API 利用時は設定されたトークンを .env 等に置いてください。
- news_collector は RSS の SSRF/巨大レスポンス対策・XML 安全パース等を実装しており、大量データ処理時は MAX_RESPONSE_BYTES の制約に注意してください。
- config.Settings は自動で .env/.env.local を読み込みます。テスト時に自動読み込みを抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

ディレクトリ構成
----------------
主要なファイル／フォルダ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境設定管理（.env 自動ロード、Settings クラス）
  - data/
    - jquants_client.py              — J-Quants API クライアント + DuckDB 保存ユーティリティ
    - news_collector.py              — RSS 収集・前処理・保存
    - (schema.py, calendar_management.py などがプロジェクトに含まれる想定)
  - research/
    - factor_research.py             — mom/vol/value の計算
    - feature_exploration.py         — IC/forward returns/summary
  - strategy/
    - feature_engineering.py         — features テーブル作成
    - signal_generator.py            — final_score を計算して signals を作成
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 発注株数計算、aggregate cap
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py                      — バックテストの主ループ
    - simulator.py                   — 擬似約定モデル・履歴管理
    - metrics.py                     — バックテスト評価指標計算
    - run.py                         — CLI 用エントリポイント
    - clock.py                       — 将来拡張用の模擬時計
  - execution/                        — 発注実装（パッケージとしてエクスポートされるが実装は別途）
  - monitoring/                       — 監視・アラート用コード（別途実装想定）
  - portfolio/__init__.py, strategy/__init__.py, research/__init__.py, backtest/__init__.py など

開発・貢献
----------
- コードはドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に準拠する設計でモジュール化されています。新機能やバグ修正はモジュール単位で PR を作成してください。
- 単体テスト・統合テストを用意し、重要な計算（サイジング・シグナルロジック・バックテスト結果）が再現可能であることを確認してください。

ライセンス / 免責
-----------------
- 本リポジトリはサンプル実装（研究・教育目的）を想定しています。実運用に用いる場合は十分な検証・法的確認・リスク管理を行ってください。

補足
----
- README に記載の例はリポジトリ内のスキーマ実装や環境に依存します。init_schema 等の補助関数はプロジェクト内の data.schema モジュールを参照して実行してください。
- 追加で知りたい使い方（例: news_collector の個別実行方法、J-Quants のトークン発行手順、具体的な DuckDB スキーマ定義など）があれば教えてください。必要に応じて README を拡張します。