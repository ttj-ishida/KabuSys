KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
主な目的は以下を実現することです。

- シグナル生成・ポートフォリオ構築（research / portfolio）
- 発注実行（execution エンジン。paper_trading / live を切替可能）
- システム監視・アラート・Kill Switch（monitoring）
- ニュースを用いた AI スコアリング / レジーム判定（ai）
- ペーパートレード検証用レポート生成などツール群（tools）
- ロギング・プロセス優先度設定などユーティリティ（utils）

主な特徴
--------
- 環境別挙動: KABUSYS_ENV による development / paper_trading / live 切替
  - paper_trading では MockBrokerClient を用い、データベースは分離（data/paper_trading.db）
- 監視モジュール: SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
- Kill Switch: 指定条件で data/kill.flag を書き込み、ExecutionEngine を停止可能
- DuckDB（分析用）＋SQLite（監視/発注ログ）を併用するデータ層
- OpenAI を利用したニュース NLP（score_news）やレジーム判定（score_regime）
- 設定ウィザード（config_setup）・設定検証（validate_config）を提供
- 日次ローテートのログ出力（logs/<app>.log）をデフォルトで設定

機能一覧
--------
- execution
  - ExecutionEngine：発注実行ループ、リスク管理、OrderManager 等
  - BrokerClientFactory：環境に応じて本番/モックブローカーを生成
- monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセス、データ鮮度監視
  - TradeMonitor：発注ログの監視（滞留注文、約定異常など）
  - RiskMonitor：ドローダウン・ポジション上限の監視、risk_logs への記録
  - MonitoringEngine：複数モニタを束ねてポーリング・通知
  - KillSwitch：停止フラグ生成ロジック
  - monitoring_db：SQLite におけるテーブル定義と永続化 API
- portfolio
  - 候補選定、重み計算、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、ファクター統計
- ai
  - news_nlp: raw_news から OpenAI を用いて銘柄ごとのセンチメントスコアを生成
  - regime_detector: ETF の MA とマクロニュースを組合せて市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を解析して検証レポートを生成
- utils
  - logging_setup: 統一的なログ設定（stdout + 日次ローテートファイル）
  - process_priority: プラットフォーム非依存のプロセス優先度 / CPU affinity 設定
- 設定ヘルパー
  - config_setup: 対話式 .env ウィザード
  - validate_config: .env や config/*.yaml の事前検証

セットアップ手順
----------------
前提: Python 3.9+（プロジェクトの実際の要求は pyproject.toml 等を参照してください）

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 手動インストール例（主に利用するパッケージ）:
     - pip install duckdb psutil openai
     - PyYAML は validate_config の YAML 検証に使われる（任意）:
       - pip install PyYAML

4. 環境変数の設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env を直接作成（例）:
     - JQUANTS_REFRESH_TOKEN=your_token
     - KABU_API_PASSWORD=your_password
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...
   - 重要: .env は絶対にリポジトリにコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

基本的な使い方
--------------
起動スクリプトはモジュールとして実行します。

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録
    - PID ファイル: data/execution.pid（デフォルト）
    - 停止: data/stop_requested.flag を作成すると安全に停止（run_execution は監視して停止処理を行う）

- Monitoring を起動（監視）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視ログは SQLite（settings.sqlite_path）に記録されます（monitoring は本番 sqlite_path を常に使用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で上書き可能。環境変数 PAPER_TRADING_SQLITE_PATH も利用可能。

OpenAI 関連
- news_nlp / regime_detector を使う場合は OPENAI_API_KEY を環境変数に設定してください。
- API 呼び出しはリトライ／バックオフや JSON 検証を組み込んでいますが、APIキーやレート制限には注意してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能利用時に必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
- MONITOR_POLL_INTERVAL (監視ポーリング間隔 秒) — default: 60
- PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject) — default: instant
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか 0/1) — default: 0

運用・停止・トラブルシューティング
---------------------------------
- 停止フラグ:
  - run_execution/run_monitoring はプロジェクト内 data/stop_requested.flag を確認して安全に終了します。
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine を停止させます（監視ロジックからの介入）。
- PID ファイル:
  - 実行エンジンは data/execution.pid を使用／更新します。プロセス管理で利用可能です。
- ログ:
  - デフォルトは logs/<app_name>.log に日次ローテーションで出力。ログディレクトリ作成に失敗した場合はコンソールのみの出力になります。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、必要なカラムがない場合は ALTER TABLE で追加します。
- 設定エラー:
  - python -m kabusys.validate_config を実行して事前にチェックしてください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要なモジュール構成です（抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (監視用通知管理 ※実装に依存)
  - execution/               — ExecutionEngine に関するモジュール群
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/ (ランタイム)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 用)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/ (ランタイム)
    - execution.log, monitoring.log, ...

開発者向けメモ
---------------
- 全体方針:
  - 研究/分析（DuckDB）と運用（SQLite/発注）は分離してあるため、分析処理は本番 DB へ書き込まない設計を推奨。
  - AI 呼び出し部分はフェイルセーフ（API 失敗時のフォールバック）を組み込んでいますが、実運用時は API レートやコストに留意してください。
- テスト:
  - AI 呼び出し関数はテストでモックできるように分離実装されています（_call_openai_api を patch）。
  - validate_config は --strict で警告もエラーにできます。CI に組み込むことを推奨します。

ライセンスとバージョン
---------------------
- パッケージバージョンは kabusys.__version__ に定義されています（現状 0.1.0）。
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

問い合わせ / コントリビュート
----------------------------
- バグ報告、機能要望、改善提案はリポジトリの Issue またはプロジェクトの運用ルールに従ってください。
- 大きな設計変更を行う場合は事前に RFC レベルで議論してください。

以上で README の概要です。必要であれば以下を追加できます:
- 具体的な .env サンプルファイル
- docker / systemd サービスユニット例
- API（内部クラス・メソッド）ドキュメントの詳細化
どれを追加しますか？