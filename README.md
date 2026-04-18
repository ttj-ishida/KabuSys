README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部実装です。本リポジトリには以下の機能群が含まれており、取引エンジン（ExecutionEngine）、監視系（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLU（OpenAI を利用したセンチメント評価）などをモジュール化しています。

主な特徴
- 実行モードの切り替え（development / paper_trading / live）
- ExecutionEngine と Monitoring の起動スクリプト
- Paper Trading（実際の発注は行わず MockBroker を利用、専用 SQLite に記録）
- モニタリング DB（SQLite）による稼働ログ / 注文ログ / リスクログ管理
- Kill Switch（閾値超過時に data/kill.flag を書き込み ExecutionEngine を停止）
- Portfolio 構築・ポジションサイズ計算（等配分・スコア重み・リスクベース）
- Research（DuckDB を用いたファクター計算・特徴量解析）
- News NLP（OpenAI を用いた銘柄別センチメント評価）およびレジーム判定
- ロギングユーティリティ（コンソール + 日次ローテートファイル）

機能一覧
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading 時は専用 DB と MockBroker を使用）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
- 設定管理
  - config_setup.py: .env を対話式で作成 / 更新するウィザード
  - validate_config.py: .env と config/*.yaml の簡易検証 CLI
  - config.py: Settings クラス（環境変数から各種設定を解決）
- モニタリング
  - monitoring_db.py: SQLite スキーマ初期化・読み書き
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種チェックロジック
  - monitoring_engine.py: 各 Monitor を束ねる実行ループ
  - kill_switch.py: フラグファイルによる停止制御
- Execution（発注関連）
  - execution パッケージ（BrokerFactory、ExecutionEngine、OrderManager、RiskManager 等）※主要実装は別ファイルに格納
- Portfolio（銘柄選定・配分・サイズ計算）
  - portfolio モジュール（select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier）
- Research（DuckDB ベースのファクター計算・IC など）
  - research パッケージ（calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等）
- AI 関連
  - ai.news_nlp: OpenAI を用いた銘柄別ニュースセンチメント付与（ai_scores への書き込み）
  - ai.regime_detector: ETF・マクロニュースを使った日次レジーム判定
- ツール
  - tools.paper_verification_report: Paper Trading DB を使った検証レポート生成

セットアップ手順
----------------
前提
- Python 3.10 以上（タイプヒントで | を使用しているため）
- 必要な Python パッケージ:
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（validate_config が YAML の内容検証を行う場合）

インストール例（venv を想定）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb psutil openai
   - （検証用）pip install PyYAML

3. リポジトリルートで初期ディレクトリを作成
   - mkdir -p data logs

環境変数（.env）
- config_setup.py のウィザードで .env を作成するのが簡単です:
  - python -m kabusys.config_setup
- 主要な環境変数（抜粋）
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABUSYS_ENV: execution 環境（development | paper_trading | live）。デフォルト: development
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用。デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等

自動 .env ロード
- 起動時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env と .env.local を自動的に読み込みます。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定検証
- .env の作成後、設定検証を実行:
  - python -m kabusys.validate_config
  - 警告も厳格に扱う場合: python -m kabusys.validate_config --strict

使い方
------
主要な実行コマンド（パッケージモードで実行可能）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 説明: KABUSYS_ENV により paper_trading の場合は MockBroker を使い data/paper_trading.db に記録。起動時に data/stop_requested.flag があれば起動せず終了します。
  - 停止: 実行中に data/stop_requested.flag を作成すると実行ループが検知して Engine.stop() を呼びます。Kill Switch による停止は data/kill.flag が書き込まれる仕組みです。

- Monitoring（SystemMonitor）を起動
  - python -m kabusys.run_monitoring
  - 説明: Settings.sqlite_path（monitoring DB）へ接続し SystemMonitor を定期ポーリングします。デフォルト 60 秒ごと。
  - ポーリング間隔の上書き:
    - export MONITOR_POLL_INTERVAL=30  # 30秒間隔
  - stop フラグ: data/stop_requested.flag を作成するとループを終了します。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / Research API（ライブラリ関数）
  - ai.score_news(conn, target_date, api_key=None) — DuckDB 接続と日付を渡してニューススコアを ai_scores に書き込む
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定を market_regime テーブルへ書き込む
  - research.calc_momentum(...) / calc_volatility(...) / calc_value(...) などは DuckDB 接続を与えて利用

停止 / Kill
- ExecutionEngine を外部から停止したい場合:
  - Kill Switch が働く条件（ドローダウン超過等）が成立すると monitoring が data/kill.flag を書き込みます（Settings.kill_flag_path でパス指定可）。
  - 手動で強制停止させたい場合は data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します。

ログ
- デフォルトで logs/ ディレクトリに日次ローテートログが作成されます（logs/execution.log, logs/monitoring.log 等）。
- LOG_DIR 環境変数または setup_logging の引数で変更可能。

簡易 .env 例
- .env（参考。機密情報は必ず管理下に置く）
  JQUANTS_REFRESH_TOKEN=your_jquants_token_here
  KABU_API_PASSWORD=your_kabu_password_here
  KABUSYS_ENV=development
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  LOG_LEVEL=INFO
  OPENAI_API_KEY=sk-xxxxx
  KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成（主要ファイル）
--------------------------------
src/
  kabusys/
    __init__.py
    config.py                     # Settings / .env ロードロジック
    config_setup.py               # .env 対話ウィザード
    validate_config.py            # 起動前検証 CLI
    run_execution.py              # ExecutionEngine 起動スクリプト
    run_monitoring.py             # SystemMonitor 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py
    utils/
      __init__.py
      logging_setup.py            # ログ設定ユーティリティ
      process_priority.py         # プロセス優先度 / CPU affinity
    monitoring/
      monitoring_db.py            # SQLite schema + DB 操作ラッパ
      system_monitor.py
      trade_monitor.py            # （存在する前提の監視モジュール）
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py            # （通知管理: LINE 等。詳細実装は別）
    execution/
      ...                         # BrokerFactory / ExecutionEngine / OrderManager 等
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    data/                          # （実行時に生成されることが多い）
      monitoring.db (default)
      paper_trading.db (paper mode)
      kill.flag
      stop_requested.flag
    logs/                          # ログ出力先（デフォルト）

注意事項 / 運用上のヒント
- production (KABUSYS_ENV=live) 設定時は .env に機密情報を含めない、また .env を Git に絶対にコミットしないでください。
- validate_config.py の --strict モードは本番移行前に有用です（警告を FAIL 扱いにできます）。
- デフォルトでは Monitoring は Settings.env に依らず「本番 sqlite_path」を使用する仕様に注意してください（監視ログは本番 DB に蓄積される想定）。
- Paper Trading は発注系を本番 DB と分離して記録するため、テスト・検証が安全に行えます。
- OpenAI 関連処理は外部 API を利用するため、API キーと利用料に注意してください。API の一時エラーはバックオフしてリトライする実装になっていますが、失敗時はフォールバック動作で継続します。

ライセンス / 貢献
-----------------
本 README はコードベースの説明を目的としたドキュメントです。実際のライセンスや貢献ルールはリポジトリのトップレベルファイル（LICENSE, CONTRIBUTING.md 等）を参照してください。

問題・質問
---------
具体的な使い方や拡張方法（例: ExecutionEngine の設定変更、Broker の実装、通知チャネル追加など）については、知りたい対象と目的を教えてください。追加のドキュメントやサンプルコマンドを作成します。