KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買およびそれを支える運用・監視用ユーティリティ群をまとめた Python パッケージです。  
主な目的は以下です。

- シグナル → 発注の実行（ExecutionEngine）
- リスク監視・システム監視（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio）
- 研究用ファクター計算・特徴量解析（Research）
- ニュースを使った NLP スコアリング / レジーム判定（AI）
- 各種ツール（設定ウィザード、検証レポート生成など）
- ロギング・プロセス優先度などのユーティリティ

機能一覧
--------
- 起動スクリプト
  - run_execution.py : ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合はペーパートレード用モード）
  - run_monitoring.py : SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔を上書き可能）
- 設定管理 / 検証
  - config_setup.py : 対話式で .env を作成／更新するウィザード
  - validate_config.py : .env / config/*.yaml の事前検証 CLI（--strict オプションあり）
- モニタリング
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch, alert_manager 等
  - SQLite（monitoring.db）に監視ログを永続化
- 発注関連
  - ExecutionEngine、OrderManager、RiskManager、Reconciler、BrokerClientFactory（paper/live 切替）
  - paper_trading モードでは MockBrokerClient を使い data/paper_trading.db に分離
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、セクター制限、レジーム乗数、株数決定（単元丸め含む）
- 研究（Research）
  - ファクター計算（momentum / volatility / value）、将来リターン、IC 計算、統計サマリー
  - DuckDB を用いた SQL/Python ベースの集計
- AI 関連
  - news_nlp.score_news: OpenAI を用いてニュースセンチメントを銘柄単位にスコア化し ai_scores に書き込み
  - regime_detector.score_regime: MA 乖離 + マクロニュースセンチメントで市場レジーム判定・書き込み
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・約定率・レイテンシ等）
- ユーティリティ
  - logging_setup: stdout + 日次ローテートファイルの統一ログ設定
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config: .env 自動ロード・Settings オブジェクト提供

セットアップ手順
----------------
以下はローカル開発 / テスト用の一般的な手順です。

1. リポジトリを取得
   - git clone ... （プロジェクトルートは .git または pyproject.toml を基準に自動検出します）

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt
   - 主要な依存例:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定ファイル検証で任意）

4. .env 作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - --env-file で別パス指定可能
   - 作成後、python -m kabusys.validate_config で検証
     - --strict を付けると警告もエラー扱いになる

5. データディレクトリ準備
   - デフォルトでは data/ 以下に DB（data/monitoring.db, data/kabusys.duckdb, data/paper_trading.db など）を置きます。必要に応じて .env でパスを変更してください。

重要な環境変数（主なもの）
-------------------------
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
  - paper_trading: 発注はモック、DB は data/paper_trading.db を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で参照される API キー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_PATH: Kill Switch 用 flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=クリアしない・デフォルト0）

使い方（主要コマンド）
--------------------
- 設定・検証
  - 対話式 .env 作成:
    - python -m kabusys.config_setup
  - 設定検証:
    - python -m kabusys.validate_config [--strict]

- 実行 / 発注エンジン
  - ExecutionEngine 起動:
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading を指定するとペーパートレード用 DB / MockBroker を使用します

- 監視
  - SystemMonitor ポーリング開始:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
    - 監視は Settings.sqlite_path を使用（環境に依らず本番の監視 DB を参照）

- AI / 研究
  - news_nlp の利用例（プログラム内 API）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

- ツール
  - Paper Trading 検証レポート:
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill Switch 関連
---------------------
- run_execution / run_monitoring は data/stop_requested.flag（プロジェクトルート data/stop_requested.flag）を検知するとループを終了します（起動中のスレッドを停止）。
- Kill Switch（自動停止）は Monitoring の判定により data/kill.flag を書き込みます。ExecutionEngine は起動時にこの flag を検出すると起動を中止します（paper/live 共通）。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアしますが、本番では 0 を推奨します。
- PID ファイル: data/execution.pid（デフォルト）は ExecutionEngine 実行中に書き込まれます。

ログ
----
- ログは標準出力と日次ローテートファイル（logs/<app_name>.log）に出力されます。ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数読み込み・Settings
- config_setup.py           — .env 作成ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor 起動スクリプト

- execution/                — 発注関連（Engine, OrderManager, RiskManager, BrokerFactory など）
- monitoring/
  - monitoring_db.py        — SQLite 永続層
  - monitoring_engine.py
  - system_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - trade_monitor.py        — （滞留注文・約定異常などの監視）
  - alert_manager.py
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py

補足 / 運用上の注意
------------------
- DB 分離: paper_trading モードでは発注データを専用の PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録し、本番データと完全に分離します。
- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（ファイル出力は無効化）。
- OpenAI API を使用する機能は API キーの設定が必須です。API 呼び出しはリトライ・フォールバックのロジックを備えていますが、キー未設定では例外が発生します。
- 監視ループ（run_monitoring）は Settings.sqlite_path を参照し、環境にかかわらず本番の監視 DB を使用する点に注意してください。
- .env は機密情報を含みうるため Git にコミットしないでください（config_setup にもその旨の注意あり）。

ライセンス / バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0

さらに詳しいドキュメント
----------------------
各モジュール（monitoring, execution, portfolio, research, ai）には docstring と詳細コメントがあり、実装に沿った仕様が記載されています。開発時は該当モジュールの docstring を参照してください。

―――
必要であれば README に「requirements.txt の推奨内容」や「systemd / supervisor 用の起動例」も追記できます。どの情報を追加しますか？