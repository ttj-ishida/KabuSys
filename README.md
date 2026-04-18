KabuSys — 日本株自動売買システム（README）
==================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能を備えています。

- 注文実行エンジン（ExecutionEngine）とペーパートレード分離
- システム監視・アラート・Kill Switch
- ポートフォリオ構築（候補選定・重み計算・株数決定）
- 研究用ファクター計算・特徴量探索（DuckDB を利用）
- ニュース NLP を用いた銘柄センチメント（OpenAI）と市場レジーム判定
- 運用補助ツール（.env ウィザード、設定検証、Paper Trading 検証レポート 等）

この README は開発者・運用者向けのセットアップ手順、主要な使い方とディレクトリ構成をまとめたものです。

主な機能一覧
-------------
- run_execution: ExecutionEngine を起動（KABUSYS_ENV によって本番 / paper_trading を切替）
- run_monitoring: SystemMonitor のポーリングループを起動（監視ログを SQLite に記録）
- config_setup: 対話式 .env 生成ウィザード（python -m kabusys.config_setup）
- validate_config: .env と config/*.yaml の事前チェック（--strict オプションあり）
- tools.paper_verification_report: Paper Trading の検証レポート生成
- monitoring コンポーネント:
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager
- portfolio コンポーネント:
  - 候補選定（select_candidates）、重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes）
  - セクター上限適用（apply_sector_cap）・レジーム乗数（calc_regime_multiplier）
- research コンポーネント:
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary 等）
- ai コンポーネント:
  - news_nlp.score_news（OpenAI を用いたニュース ⇒ 銘柄別スコア）
  - regime_detector.score_regime（ETF MA とマクロニュースを統合してレジーム判定）
- utils: ロギング設定、プロセス優先度設定など運用ユーティリティ

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境を作成して有効化してください（venv / pyenv など）。

2. 依存ライブラリをインストール
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - pyyaml（validate_config の YAML 検証に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合はそちらを使用してください。）

3. .env の準備
   - 対話式で生成する: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して .env を作成してください。
   - 自動ロード:
     - プロジェクトルート（.git または pyproject.toml を検出）存在時、自動で .env を読み込みます。
     - テスト等で自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定の検証
   - python -m kabusys.validate_config
   - 厳密モード（警告を FAIL にする）: python -m kabusys.validate_config --strict

5. DB ファイルとログディレクトリ
   - デフォルトの DB/ログパスは .env の設定で上書き可能です。
     - DUCKDB_PATH: data/kabusys.duckdb（分析用）
     - SQLITE_PATH: data/monitoring.db（監視ログ）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード分離用）
     - LOG_DIR: logs/
   - ログディレクトリは自動作成を試みますが、作成失敗時はコンソール出力のみになります。

主要な環境変数（要点）
--------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai.* 機能）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL / LOG_DIR / DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH

使い方（コマンド例）
-------------------
- 環境生成（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 本番（KABUSYS_ENV=live の場合は実際に発注されます。注意して使用）
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレード（DB は data/paper_trading.db に記録）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 停止 / キル
  - 監視・実行プロセスは data/stop_requested.flag の存在を監視します（run_monitoring, run_execution）。
  - KillSwitch は data/kill.flag を作成して ExecutionEngine を停止させる仕組みです（監視が条件を満たすと書き込み）。
  - 実行起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / レジーム判定（プログラムから呼び出す）
  - ニューススコア: from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定: from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)
  - 両関数は OpenAI API キー（引数 or 環境変数 OPENAI_API_KEY）を必要とします。

主なライブラリ API（抜粋）
-----------------------
- kabusys.portfolio
  - select_candidates(buy_signals, max_positions)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, ...)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(factor_records, forward_records, factor_col, return_col)

- kabusys.ai
  - score_news(conn, target_date, api_key=None)

- monitoring
  - MonitoringDB, RiskMonitor, SystemMonitor, MonitoringEngine, KillSwitch

ログとデバッグ
--------------
- ロギングは kabusys.utils.logging_setup.setup_logging で統一して設定されます。
- デフォルトでは stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- LOG_LEVEL 環境変数でログレベルを制御できます。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理（自動 .env 読み込み含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py   (一部実装ファイルは省略)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py   (一部実装はプロジェクト内)
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルート（想定）
- .env, .env.local
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/
  - monitoring.db
  - paper_trading.db
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log
- src/...

運用上の注意
------------
- KABUSYS_ENV=live で起動すると実際の発注が行われます。十分にテスト・設定確認を行ってから使用してください。
- validate_config の出力を必ず確認し、特に本番（live）時は LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値を確認してください。
- OpenAI を利用する機能は API 呼び出しが発生します。利用時は API 利用料やレート制限に注意してください。
- データベースファイルはディスクに書き込まれるため、バックアップやディスク使用量の監視を推奨します。

貢献 / 拡張
-----------
- 新しい戦略・リサーチコードは research や portfolio の純粋関数群として追加してください（副作用なしが望ましい）。
- 実行エンジン・監視のテストを充実させるため、DB や OpenAI 呼出し箇所はモックしやすい設計を維持しています。

ライセンス
----------
（ここにライセンス情報を記載してください）

以上。設置・運用で不明点があれば使用する環境（OS、Python バージョン、.env の中身の差分など）を添えて質問してください。