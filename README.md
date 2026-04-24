README
=====

概要
----
KabuSys は日本株向けの自動売買・研究・監視ツール群です。  
主な目的は以下をサポートすることです:

- 自動売買エンジン（ExecutionEngine） — 実口座 / ペーパートレード両対応
- システム・注文・リスク監視（Monitoring） — ログ永続化・アラート・Kill Switch
- ポートフォリオ構築ユーティリティ（選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB 経由）
- AI を使ったニュースセンチメント解析・レジーム判定（OpenAI）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート等）

このリポジトリは「ライブラリ＋起動スクリプト＋運用ツール」を含むモノリシックなコードベースです。

主な機能
--------
- Execution
  - 実際のブローカー / モックブローカーの切替（KABUSYS_ENV=paper_trading でペーパートレード）
  - リスク管理ルール（max_position_pct, max_utilization 等）
  - 注文管理・再収束（reconciler）等の実行コンポーネント統合

- Monitoring
  - CPU/メモリ/ディスク/プロセス状態の定期チェックと記録（SQLite）
  - 取引ログ / ポジション / リスクログの永続化
  - Kill Switch（条件を満たすと data/kill.flag を書き込み、Execution を停止させる）
  - MonitoringEngine による定期ポーリング（間隔は環境変数で調整可）

- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value 等） — DuckDB を使用
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - 候補選定・重み計算・ポジションサイズ計算・セクター調整等の純粋関数群

- AI
  - ニュース記事を OpenAI へ送り銘柄別センチメントを算出して ai_scores テーブルへ書き込み
  - マクロニュース + ETF MA200乖離を合成して市場レジーム（bull/neutral/bear）を判定

- 運用ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report）

前提条件
--------
- Python 3.10 以上
- 必要なパッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合に必要）
- SQLite（組み込み）/ DuckDB（Python ライブラリ）

インストール
------------
1. 仮想環境を作成して有効化することを推奨します:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があればそれを使ってください:
    pip install -r requirements.txt）

セットアップ手順
--------------
1. プロジェクトルートに移動（.git または pyproject.toml を含むディレクトリが自動検出されます）。

2. .env の作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
   - ウィザードに従って値を入力するとプロジェクトルートに .env が生成されます。

   重要（必須環境変数）
   - JQUANTS_REFRESH_TOKEN （必須）
   - KABU_API_PASSWORD    （必須）

   任意 / デフォルト
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH — デフォルト: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
   - LOG_LEVEL — デフォルト: INFO
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 通知用（任意）
   - OPENAI_API_KEY — AI 機能を使う場合に必要

3. 設定検証:
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合:
     python -m kabusys.validate_config --strict

4. データディレクトリ等の初期化:
   - 必要に応じて data/ ディレクトリを作成（多くは自動生成されますが権限問題がないか確認してください）。

基本的な使い方
--------------
- ExecutionEngine を起動（本番/ペーパートレード挙動含む）
  - python -m kabusys.run_execution
  - 動作:
    - 起動時にプロセス優先度を high に試みます
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離します
    - 停止: data/stop_requested.flag が存在するとエンジンは停止します
    - Kill Switch により data/kill.flag が書き込まれるとエンジンを停止させる仕組みがあります

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings.sqlite_path（デフォルト data/monitoring.db）へ監視ログを記録します（監視は環境にかかわらず本番 sqlite を使用）
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - 停止: data/stop_requested.flag を検知するとループを終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間フィルタ:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能（デフォルト: data/paper_trading.db）

- AI/リサーチ API（ライブラリ関数として利用）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  - ポートフォリオ構築:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

運用上の注意点
-------------
- kill.flag / stop_requested.flag / execution.pid / data ファイル
  - Kill Switch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
  - 外部から確実に停止したい場合は stop_requested.flag を作成すると run_* スクリプトが検知して終了します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では推奨しません）。

- Monitoring は常に Settings.sqlite_path を参照して監視ログを記録します。KABUSYS_ENV に関わらず本番用 DB パスが使われますので注意してください。

- Paper Trading（KABUSYS_ENV=paper_trading）は mock ブローカー＋専用 SQLite（PAPER_TRADING_SQLITE_PATH）で本番データと完全分離されるよう設計されています。

- OpenAI API の利用に関しては API のレート制限・コストに注意してください。score_news / score_regime はリトライやフォールバック挙動を備えていますが、API キー未設定時は例外になります。

環境変数一覧（抜粋）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 運用 / オプション（デフォルト値）
  - KABUSYS_ENV: development | paper_trading | live  （default: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: INFO
  - LOG_DIR: logs/
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0 | 1
  - MONITOR_POLL_INTERVAL: ポーリング秒数（run_monitoring 用、default=60）
  - PAPER_FILL_MODE: instant | partial | never | reject  （デフォルト: instant）
  - OPENAI_API_KEY: OpenAI API 利用時に必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）

ディレクトリ構成（抜粋）
--------------------
src/kabusys/
- __init__.py
- config.py                — 環境設定読み込み / Settings クラス
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュースセンチメント解析（OpenAI）
  - regime_detector.py     — マーケットレジーム判定（AI + MA200）
- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py       — （ファイルに含まれていないが存在を期待）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — （ファイルに含まれていないが存在を期待）
- execution/
  - execution_engine.py    — ExecutionEngine の実装（主要ロジック）
  - broker_factory.py      — ブローカークライアント生成
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

ログ / データファイル
--------------------
- デフォルトログ: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション）
- SQLite（監視）: data/monitoring.db
- SQLite（ペーパー）: data/paper_trading.db
- DuckDB（分析）: data/kabusys.duckdb
- 制御フラグ:
  - data/kill.flag          — Kill Switch トリガー
  - data/stop_requested.flag — 外部からプロセス停止要求
  - data/execution.pid      — ExecutionEngine PID（run_execution が使用）

開発・拡張のヒント
-------------------
- DuckDB 接続を渡して処理する設計のため、ローカルで prices_daily / raw_financials / raw_news 等のテーブルを用意すれば研究関数を簡単に実行できます。
- AI 周りの API 呼び出しはユニットテストでモック化しやすいように分離されています（内部の _call_openai_api を patch する等）。
- config/*.yaml を外部設定として使用する想定があるため、PyYAML をインストールすると validate_config が YAML の中身まで検証します。

ライセンス / 貢献
-----------------
（この README には記載がありません。プロジェクトに LICENSE があればそちらを参照してください。）

問い合わせ / サポート
-------------------
実運用時の注意点や拡張についてはプロジェクト内ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）を参照してください。