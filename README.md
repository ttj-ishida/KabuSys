README — KabuSys
=================

概略
----
KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリ兼実行スクリプト群です。本リポジトリは以下の領域を含みます。

- Execution：発注エンジン（ExecutionEngine）と注文管理
- Monitoring：システム監視・アラート・Kill Switch
- Research：DuckDB を使ったファクター計算・特徴量解析
- Portfolio：銘柄選定・配分・ポジションサイジング
- AI：ニュース NLP によるセンチメント評価、レジーム検出
- Tools：レポート生成・設定ウィザード等のユーティリティ

特徴
----
- 実行環境分離（development / paper_trading / live）
  - paper_trading 時は MockBrokerClient を用い、paper_trading DB に記録（本番 DB と分離）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）を束ねる MonitoringEngine
- Kill Switch による安全停止（条件を満たすと data/kill.flag を書き込む）
- DuckDB を利用した解析（ファクター計算・将来リターン・IC 等）
- OpenAI を用いたニュースセンチメント評価（gpt-4o-mini を想定）
- ロギングとプロセス優先度設定ユーティリティ（ログは日次ローテーション）

動作要件（例）
--------------
- Python 3.10+
- ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の検証に使用）
- 注意: requirements.txt は含まれていないため、プロジェクトに合わせてインストールしてください。

セットアップ手順
----------------
1. リポジトリをクローン／展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 必要なパッケージをインストール
   - pip install duckdb psutil openai
   - （検証に PyYAML が必要な場合）pip install pyyaml
4. 初期設定ファイル (.env) を作成
   - 対話ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して手動で作成
5. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗とする場合: python -m kabusys.validate_config --strict
6. データディレクトリ等が必要なら作成（多くのコードが起動時に自動作成しますが念のため）
   - mkdir -p data logs

主要な環境変数（主なもの）
--------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 運用／挙動
  - KABUSYS_ENV — 実行環境（development / paper_trading / live）
  - PAPER_FILL_MODE — paper_trading 時の fill 動作（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアする (0/1)
- パス関連（デフォルト）
  - DUCKDB_PATH (data/kabusys.duckdb)
  - SQLITE_PATH (data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
  - PID_FILE_PATH (data/execution.pid)
  - KILL_FLAG_PATH (data/kill.flag)
- ログ
  - LOG_LEVEL (デフォルト: INFO)
  - LOG_DIR (デフォルト: logs/)
- OpenAI
  - OPENAI_API_KEY — AI モジュール利用時に必要
- モニタリング間隔
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

使い方（実行例）
----------------

1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）

3. ExecutionEngine 起動（発注エンジン）
   - python -m kabusys.run_execution
   - 動作環境により KABUSYS_ENV を設定（例: paper_trading）
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 停止方法: data/stop_requested.flag を作成するとループが検知して停止します
   - 実行中は pid ファイル（data/execution.pid）を作成します

4. Monitoring 起動（監視ループ）
   - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
     - MONITOR_POLL_INTERVAL が未設定ならデフォルト 60 秒
   - 監視は本番 sqlite_path を利用（環境に依存せず monitoring 用 DB を使用）
   - stop フラグ: data/stop_requested.flag の作成でモニタリングループを停止

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

6. AI / 研究用 API（プログラムから呼び出す）
   - kabusys.ai.score_news(conn, target_date, api_key=...)
     - DuckDB の接続を渡してニュースセンチメントを ai_scores に書き込みます（OPENAI_API_KEY 必須）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
   - 研究系: kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等

停止・Kill Switch
-----------------
- 監視が Kill 条件を満たすと KillSwitch が data/kill.flag を作成します。ExecutionEngine は kill.flag の存在を検出して安全停止します。
- 手動で強制停止したい場合:
  - data/stop_requested.flag を作成すると run_execution・run_monitoring のループが検知して終了します。
  - kill.flag を削除したい場合は削除（ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動でクリアされる挙動に注意）。

ロギング
--------
- ロガーは kabusys.utils.logging_setup.setup_logging により設定されます。
- デフォルトログディレクトリ: logs/
- 各アプリ（execution / monitoring 等）は logs/<app_name>.log に日次ローテーションで出力されます。

その他の注意点 / 補足
---------------------
- paper_trading モードでは本番 DB と分離して data/paper_trading.db に記録されます（環境変数で上書き可能）。
- OpenAI を使うモジュールは API の失敗時フェイルセーフ（スコア 0.0 等）を組み込んでいますが、API キーは必須です。
- config/*.yaml の内容検証は PyYAML がインストールされている場合に実行されます。
- 一部モジュールは DuckDB のテーブル構造（prices_daily, raw_financials, raw_news 等）を前提としています。データパイプラインは kabusys.data.pipeline などに実装されている想定です。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                # 環境変数・設定管理
    config_setup.py          # .env 対話ウィザード
    validate_config.py       # 設定検証 CLI
    run_execution.py         # ExecutionEngine 起動スクリプト
    run_monitoring.py        # Monitoring 起動スクリプト
    tools/
      paper_verification_report.py
    utils/
      logging_setup.py
      process_priority.py
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py         # （ファイル参照：存在）
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py         # （ファイル参照：存在）
    execution/
      execution_engine.py
      order_manager.py
      order_repository.py
      broker_factory.py
      reconciler.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    ai/
      news_nlp.py
      regime_detector.py
    data/                      # 実行時に生成されることがある（DB / フラグ等）
    logs/                      # ログ出力先

（注）上のツリーは主要ファイルを抜粋したものです。実際のファイル一覧はリポジトリの内容を参照してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在する場合）。

問い合わせ・開発メモ
--------------------
- 開発中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを抑制できます（テスト時に便利）。
- テスト／デバッグ時は run_monitoring / run_execution を直接実行する以外に、個別クラス（SystemMonitor / RiskMonitor / MonitoringEngine）の run_once を unittest から呼ぶことで副作用を抑えた検証が可能です。

以上。必要であれば、README に入れるサンプル .env のテンプレートやコマンド例を追記しますか？