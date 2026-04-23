README — KabuSys (日本株自動売買システム)
概要
- KabuSys は日本株向けの自動売買・リサーチ・監視ユーティリティ群を集めた Python パッケージです。
- 主な目的:
  - 発注エンジン（ExecutionEngine）と監視（Monitoring）
  - ポートフォリオ構築・リスク制御ロジック（純粋関数）
  - 研究用ファクター計算・特徴量解析
  - AI（LLM）を使ったニュースセンチメント評価・レジーム判定
  - ペーパートレード用検証レポート生成

機能一覧
- 実行エンジン起動スクリプト (run_execution.py)
  - KABUSYS_ENV に応じて実口座 / ペーパートレードを切替
  - paper_trading 環境では MockBroker を用い、data/paper_trading.db に記録
  - プロセス優先度設定、PID / stop flag による制御
- 監視ループ起動スクリプト (run_monitoring.py)
  - SystemMonitor をポーリングして system_status 等を記録
  - MONITOR_POLL_INTERVAL 環境変数で間隔上書き（デフォルト 60 秒）
  - 監視は本番 sqlite_path を参照（環境に依存しない）
- 設定ウィザード (config_setup.py)
  - 対話式で .env を生成 / 更新
- 設定検証 CLI (validate_config.py)
  - .env / config/*.yaml / DB パス等の事前チェック。--strict オプションで警告も fail 扱い
- ペーパートレード検証レポート (tools/paper_verification_report.py)
  - Paper Trading DB を読み、稼働率・注文成功率・レイテンシ等を集計して判定
- ポートフォリオ関連（pure functions）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
  - セクターキャップ適用、レジーム乗数（apply_sector_cap, calc_regime_multiplier）
  - 発注株数計算（calc_position_sizes）
- 研究モジュール
  - ファクター計算（momentum/volatility/value）
  - 将来リターン・IC 計算・特徴量サマリ
- AI（LLM）関連
  - ニュースセンチメント評価（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI API（gpt-4o-mini）を利用（API キー必要）
- 監視 DB ラッパー（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard の CRUD を提供
- ユーティリティ
  - 統一的なロギング設定 (utils/logging_setup.py)
  - プロセス優先度 / CPU affinity 設定 (utils/process_priority.py)

セットアップ手順（ローカル開発向け）
1. ソースを取得
   - リポジトリをクローンまたは展開してプロジェクトルートを用意します。

2. 仮想環境（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要な依存: duckdb, psutil, openai, pyyaml（validate をフルに実行する場合）
   - 例:
     pip install duckdb psutil openai pyyaml

4. .env の作成
   - 対話式ウィザードを使う（推奨）:
     python -m kabusys.config_setup
   - もしくは手動で .env をプロジェクトルートに作成。
   - 自動ロード:
     - デフォルトで .env と .env.local がプロジェクトルートから自動ロードされます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - OPENAI_API_KEY（AI 機能を使用する場合）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - LOG_LEVEL（例: INFO）
   - MONITOR_POLL_INTERVAL（run_monitoring 用、秒、デフォルト 60）

   注意: validate_config.py を先に実行して不足を検出できます:
     python -m kabusys.validate_config
     python -m kabusys.validate_config --strict

使い方（主要コマンド）
- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution エンジン起動
  - 通常起動（プロセスとして実行）
    python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
    - 実行中は data/execution.pid を利用、停止は data/stop_requested.flag を作成して行う
    - Kill Switch（監視側）が有効なら data/kill.flag で停止を要求可能

- Monitoring 起動
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH 優先）

- AI 機能（プログラムから利用）
  from kabusys.ai import score_news
  # DuckDB 接続を渡してスコア生成
  score_news(conn, target_date, api_key="...")

  市場レジーム:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="...")

ログ・DB の取り扱い
- ログ:
  - utils.logging_setup.setup_logging を各起動スクリプトから呼び出し、logs/<app_name>.log に日次ローテーションで出力します。
  - ログディレクトリは環境変数 LOG_DIR で変更可能（デフォルト logs/）。

- DB:
  - 分析用 DuckDB: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - 監視用 SQLite: SQLITE_PATH（デフォルト data/monitoring.db）
  - ペーパートレード用 SQLite: PAPER_TRADING_SQLITE_PATH（paper_trading 時のみ使用、デフォルト data/paper_trading.db）
  - monitoring_db.init_monitoring_db は冪等にテーブルおよびマイグレーションを行います。

停止・強制停止フラグ
- 停止フラグ:
  - data/stop_requested.flag を作ると run_monitoring / run_execution のループは検知して終了します（run_execution は起動時に既にフラグがあれば起動しません）。
- Kill Switch:
  - 監視コンポーネントがリスク条件（ドローダウン超過・ポジション上限超過等）を検出すると data/kill.flag を書き込み、Execution 側で停止処理を行います。
  - KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合は起動時に自動でクリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理（.env 自動ロードを含む）
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照あり)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照あり)
  - execution/                 — 発注関連（Engine, BrokerFactory, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                      — (実行時に使用されるデフォルトディレクトリ)
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパートレードデフォルト)
    - kabusys.duckdb (デフォルト)

補足 / ベストプラクティス
- 本番（KABUSYS_ENV=live）では .env を厳重に管理し、JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD を安全に扱ってください。
- validate_config を先に実行して設定漏れを検出してください。
- AI 機能を使う場合は OPENAI_API_KEY の管理に注意し、料金・レート制限を考慮してください。
- ローカル開発では KABUSYS_ENV=development にして実データや発注を伴わない動作を確認してください。
- Paper trading を使う場合は PAPER_TRADING_SQLITE_PATH を確認して本番 DB と分離されていることを確認してください。

最小 .env サンプル（説明用）
JQUATS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=your_openai_key_here

お問い合わせ / 開発メモ
- プロジェクトルートの .env.example（存在する場合）を参考にしてください。
- 追加の設定ファイルは config/*.yaml（system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml）です。validate_config で存在チェックを行います。

以上。必要があれば実行例や .env のテンプレートをさらに詳しく作成します。