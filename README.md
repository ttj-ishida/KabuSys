README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / モニタリング用の小規模フレームワークです。本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- ExecutionEngine：発注・注文管理・リスク管理（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文状態・リスク監視、Kill Switch（自動停止）
- Portfolio：候補選定、重み付け、ポジションサイズ算出、セクター制約・レジーム乗数
- Research：ファクター計算・将来リターン・IC/統計解析
- AI：ニュースを LLM（OpenAI）でスコアリングしてマーケットシグナル生成
- ユーティリティ：設定ウィザード、設定検証、ログ設定など

機能一覧
--------
主要な機能（抜粋）:

- 起動スクリプト
  - run_execution.py — ExecutionEngine の起動（KABUSYS_ENV により paper_trading モードは MockBroker を使用）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 設定管理
  - config_setup.py — 対話式 .env 作成 / 更新ウィザード
  - validate_config.py — .env と config/*.yaml の事前検証 CLI
  - Settings クラス — 環境変数からの設定取得とデフォルト管理
- モニタリング
  - system_monitor/trade_monitor/risk_monitor を束ねる monitoring_engine
  - KillSwitch による kill.flag 書き込みで ExecutionEngine を停止
  - SQLite ベースの永続化層（monitoring_db）
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベースの株数算出、セクター上限やレジーム乗数
- リサーチ
  - momentum/volatility/value 等のファクター計算（DuckDB SQL）
  - 将来リターン計算、IC（Spearman ランク相関）計算、統計サマリ
- AI（OpenAI）
  - news_nlp.score_news — ニュース記事をバッチで LLM に送って銘柄別センチメントを書込む
  - regime_detector.score_regime — ETF とマクロニュースを組合せて日次レジーム判定を書込む
- ツール
  - tools/paper_verification_report.py — ペーパートレード DB から検証レポート生成

セットアップ手順
----------------

1. Python 環境の準備（推奨: Python 3.10+）

2. 依存パッケージのインストール（例）
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証を行う場合）
   例:
     pip install duckdb psutil openai pyyaml

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを使う:
       python -m kabusys.config_setup
   - 手動で作る場合、必須環境変数:
       JQUANTS_REFRESH_TOKEN（必須）
       KABU_API_PASSWORD（必須）
     推奨/任意変数（例）:
       KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
       DUCKDB_PATH — デフォルト: data/kabusys.duckdb
       SQLITE_PATH — デフォルト: data/monitoring.db
       PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時）
       OPENAI_API_KEY — OpenAI を使う機能で必要
       LOG_LEVEL, LOG_DIR など

   - 自動 .env ロード:
     モジュール読み込み時にプロジェクトルートの .env/.env.local を自動読み込みします。
     (無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定)

4. DB 初期化
   - 実行スクリプトが起動時に必要テーブルを作成します（monitoring は init_monitoring_db を実行）。

使い方
------

基本的なコマンド（プロジェクトルートで実行）:

- 設定ウィザード
    python -m kabusys.config_setup

- 設定検証（起動前チェック）
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict  # 警告を FAIL 扱い

- ExecutionEngine を起動
    python -m kabusys.run_execution
  挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - プロセス優先度は実行開始時に High に設定を試みます。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 停止命令は kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を書き込むか、外部で stop_requested.flag を作成することで行えます。

- Monitoring を起動
    python -m kabusys.run_monitoring
  挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
    - monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを保存します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行います（run_monitoring はこのフラグを検知して終了します）。

- Paper Trading 検証レポート生成
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH で SQLite DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先されます）。

- AI スコアリング / レジーム判定
  これらはプログラム的に呼び出します（例）:
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
  必要な環境変数:
    OPENAI_API_KEY（関数の api_key 引数でも渡せます）
  注意:
    - OpenAI 呼び出しは失敗時にフォールバック（スコア 0.0 等）する設計ですが、API キーが未設定だと例外になり得ます。

設定 / 環境変数（主要）
--------------------
主な環境変数とデフォルト:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を使う際に必要
- LOG_LEVEL: INFO（ログ詳細度）
- LOG_DIR: logs/（ログファイル保存先）
- MONITOR_POLL_INTERVAL: run_monitoring 用の秒数（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

停止/Kill フラグ
----------------
- data/kill.flag:
  - KillSwitch が検出した重大リスク（ドローダウンやポジション上限超過）時に書き込まれ、
    ExecutionEngine を停止させるためのトリガーになります。
- data/stop_requested.flag:
  - 外部からの「プロセスを止めてほしい」要求。run_execution/run_monitoring はこのファイルを検知すると
    実行中ループを終了します。

ログ
----
- ログは標準出力（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリは LOG_DIR 環境変数、またはデフォルト logs/。
- ログレベルは LOG_LEVEL で設定（例: DEBUG, INFO, WARNING, ERROR）。

ディレクトリ構成
----------------
主要ファイル / モジュール構成（src/kabusys 以下、抜粋）:

- kabusys/
  - __init__.py
  - config.py                — Settings クラス（環境変数読み込み、自動 .env ロード等）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - execution/               — 実際の発注エンジン関連（broker_factory, execution_engine, order_manager 等）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースを LLM でスコア化して ai_scores に書き込む
    - regime_detector.py     — ETF とマクロ記事から日次レジーム判定
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

注意事項 / 実運用上のポイント
---------------------------
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と分離され、PAPER_TRADING_SQLITE_PATH に記録されます。
- monitoring 側は KABUSYS_ENV に依存せず常に本番 sqlite_path を参照（監視は本番 DB を観測する想定）。
- .env を誤ってリポジトリにコミットしないでください（config_setup でも README に警告あり）。
- OpenAI を使う機能は API コストとレート制限に注意してください（retry/backoff 実装あり）。
- process priority や CPU affinity の設定は OS に依存し失敗する場合があります（ログに警告が出ます）。
- DuckDB を使って大量の時系列計算を行います。データ準備（prices_daily / raw_financials / raw_news 等）が前提です。

開発者向けメモ
---------------
- 自動 .env 読込はプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。テスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- LLM 呼び出し部分（news_nlp, regime_detector）はテストしやすいように API 呼び出し箇所をラップしており、テスト時にモック差し替えできます（関数名参照）。
- monitoring_db.init_monitoring_db はスキーママイグレーション（カラム追加）を安全に行います。

サポート / 参照
----------------
- 実装に関する詳細は各モジュールの docstring / コメントを参照してください。
- 設定ファイル生成後は validate_config で起動前チェックを必ず実行してください。

以上。必要あれば README に追記したい項目（例: 更に詳細な実行例、Docker 化手順、CI 設定など）を教えてください。