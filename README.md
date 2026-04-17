README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。本リポジトリは以下の主要機能を持ちます。

- 実行エンジン（ExecutionEngine）：発注・注文管理・リスク管理を行うプロセス
- 監視（Monitoring）：システム稼働状況・注文滞留・リスク（ドローダウン等）をポーリングしてログ保存・アラート・Kill Switch 制御を行う
- ポートフォリオ構築：候補選定、重み計算、ポジションサイズ決定などの純粋関数群
- リサーチ：ファクター計算、特徴量探索、IC 計算など（DuckDB による時系列処理）
- AI モジュール：ニュースのセンチメント付与（OpenAI）・市場レジーム判定
- 開発支援ツール：.env ウィザード、設定検証、Paper Trading 検証レポート生成 等

設計上の要点：
- 実稼働向け設計（プロセス優先度の設定、PID/flag ベースの停止制御、SQLite/DuckDB による永続化）
- Paper Trading（シミュレーション）と Live（本番）を DB レベルで明確に分離
- LLM 呼び出しはフォールバック/リトライ・レスポンス検証を備えフェイルセーフ化

機能一覧
--------
主な機能と位置（モジュール）:

- 実行・発注
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV により paper_trading 用 DB を使用）
  - execution/*: BrokerFactory、OrderManager、RiskManager、Reconciler 等（発注ワークフロー）
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定）
  - monitoring/*: SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、KillSwitch、MonitoringDB、AlertManager 等
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み付け、セクター制約、ポジションサイズ計算
- リサーチ
  - research/*: ファクター計算（momentum/value/volatility）、forward returns、IC、統計サマリ
- AI
  - ai/news_nlp.py: ニュース記事を OpenAI でセンチメント化して ai_scores に保存
  - ai/regime_detector.py: ma200 とマクロニュースセンチメントを合成して日次レジーム判定
- ツール
  - config_setup.py: 対話式 .env ウィザード（初期設定）
  - validate_config.py: .env および config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成

セットアップ手順
--------------
前提
- Python 3.9+（ソースは型注釈等を使用）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai（AI 機能利用時）
  - PyYAML（設定 YAML 検証を行う場合）
  - その他プロジェクト固有の依存は pyproject.toml 等を参照

例（pip）
- 仮想環境作成、アクティベート
  - python -m venv .venv
  - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
- インストール
  - pip install -r requirements.txt  （requirements.txt がある場合）
  - あるいは必要パッケージを個別に pip install duckdb psutil openai pyyaml

初期設定 (.env)
1. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - 画面の指示に従い必須値（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を入力
2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）扱いになる

主な環境変数（代表）
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
  - KABU_API_PASSWORD: kabuステーション API パスワード
- 運用・挙動制御
  - KABUSYS_ENV: execution モード（development | paper_trading | live）
    - paper_trading の場合、発注は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒, run_monitoring.py、デフォルト 60）
  - PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、"" または "0" で無効）
- ログ等
  - LOG_LEVEL（DEBUG/INFO/...）
  - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
- ファイルパス
  - PID_FILE_PATH（デフォルト data/execution.pid）
  - KILL_FLAG_PATH（デフォルト data/kill.flag）

使い方
------
起動・停止
- 実行エンジン起動（例）
  - python -m kabusys.run_execution
  - 起動時にプロセス優先度を high に設定します
  - KABUSYS_ENV=paper_trading の場合、paper_trading DB に記録されます
- 監視起動（例）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒, デフォルト 60）
  - 監視は settings.sqlite_path（監視 DB）を使用します（KABUSYS_ENV に依らず production パスを使用）
- 停止制御
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループが検知して停止します
  - KillSwitch（監視側）が条件を満たすと data/kill.flag を生成し ExecutionEngine に停止シグナルを送ります
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では注意）

ツール
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 機能
- ニューススコアリング:
  - kabusys.ai.score_news（内部で OpenAI を呼ぶ）
  - OPENAI_API_KEY を設定してください
  - score_news は DuckDB 接続と target_date を受け取り ai_scores テーブルへ書き込みます
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime を呼び出す（同様に OPENAI_API_KEY が必要）

運用上の注意
- run_monitoring は監視 DB（settings.sqlite_path）を利用します。環境にかかわらず本番の monitoring DB を参照します。
- run_execution は環境に応じて paper_trading 用 DB を使用して本番 DB との混在を防ぎます。
- PID ファイルと kill.flag / stop_requested.flag による外部制御を行います。運用時はこれらの取り扱いに注意してください。
- OpenAI を使用する機能は API 使用料が発生します。API キーの管理を行ってください。

ディレクトリ構成
----------------
リポジトリ内の主なファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - config_setup.py          — .env ウィザード CLI
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py            — ニュースの OpenAI スコアリング
      - regime_detector.py     — 市場レジーム判定（ma200 + LLM）
    - monitoring/
      - monitoring_db.py       — SQLite 永続化レイヤ
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
    - utils/
      - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - execution/                — 発注・Order 管理等（参照されるモジュール群）
    - data/                     — 実行時に利用する data/*.db、flag、pid 等（プロジェクトルートに data/ 配置）

注: この README はコードベースから抽出した情報をまとめたものです。各モジュールの詳しい使用法はソース内の docstring / コメントを参照してください。

ライセンス / バージョン
---------------------
- パッケージバージョンは kabusys.__version__ で管理（例: "0.1.0"）
- ライセンス情報はプロジェクトルートの LICENSE 等を参照してください。