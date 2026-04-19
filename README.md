KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のプロジェクトです。
主な要素として、発注を担う ExecutionEngine、稼働状況やリスクを監視する Monitoring、一連のポートフォリオ構築・リスク制御ロジック、リサーチ（ファクター計算・特徴量解析）、および AI を用いたニュースセンチメント／レジーム判定機能を含みます。ローカル開発用（development）、ペーパートレード（paper_trading）、本番（live）を想定した設定管理と運用ツールが揃っています。

主な機能
--------
- Execution
  - ExecutionEngine による注文管理、OrderRepository / OrderManager / Reconciler / RiskManager 等の実装
  - paper_trading モードでは MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、Execution プロセスの監視
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウン・ポジション上限の監視
  - KillSwitch：閾値超過時に data/kill.flag を書き込み、Execution を停止する仕組み
  - MonitoringEngine：各モニタを束ねた定期実行ループ（ポーリング）
- ポートフォリオ構築
  - 候補選定、等金額／スコア加重配分、リスクベースのポジションサイズ計算
  - セクター制限やレジームに基づく調整
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - DuckDB を使った高速な分析クエリ
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（ai_scores テーブルへの永続化）
  - マクロニュース＋ETF MA を使った市場レジーム判定（market_regime への書き込み）
  - API 呼び出しは堅牢にリトライ/フォールバック処理実装
- 運用・ユーティリティ
  - 対話式 .env 作成ウィザード（config_setup）
  - 起動前設定検証ツール（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）
  - 共通ログ設定（logs/<app>.log、日次ローテート）、プロセス優先度設定ユーティリティ

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートに移動
   - この README はパッケージの src/kabusys を前提としています。

2. Python 環境の用意
   - Python 3.10+ を推奨
   - 仮想環境を作成・有効化（venv / pipenv / poetry 等）

3. 依存ライブラリのインストール（例）
   - 必要パッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - pyyaml（設定検証で YAML を検査する場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （本リポジトリに requirements.txt がある場合はそれを使用してください。）

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 重要: .env は絶対にバージョン管理にコミットしないこと

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

注意: OpenAI を使う機能を利用する場合は OPENAI_API_KEY を .env に設定してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能使用時に必要）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
- MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1、デフォルト 0）

使い方
------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: --strict

- 実運用（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading DB に記録
    - data/execution.pid に PID を書く
    - data/stop_requested.flag / data/kill.flag により外部停止が可能

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 動作:
    - Settings に基づく sqlite_path（monitoring は環境にかかわらず本番 sqlite_path を使用）
    - MONITOR_POLL_INTERVAL でループ間隔を調整可能
    - stop_requested.flag を検知すると監視ループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数が未設定の場合）

- AI / リサーチ関係（プログラム的利用）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

- ログ
  - デフォルトログディレクトリ: logs/
  - 各アプリ名ごとに日次ローテートされたログが生成されます（例: logs/execution.log, logs/monitoring.log）
  - LOG_DIR / LOG_LEVEL で制御可能

運用で使うファイル・フラグ
------------------------
- data/execution.pid — ExecutionEngine の PID（起動時に書き込まれる）
- data/stop_requested.flag — 起動ループを優雅に停止させるためのフラグ
- data/kill.flag — KillSwitch による停止シグナル（Production ではデフォルトでクリアしないこと推奨）
- DB:
  - DuckDB: data/kabusys.duckdb（分析用）
  - SQLite: data/monitoring.db（監視ログ）
  - Paper trading 用 SQLite: data/paper_trading.db（paper_trading 時に使用）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義・バージョン
- config.py — 環境変数/設定管理（自動 .env ロード機能を持つ）
- config_setup.py — 対話式 .env 作成ウィザード
- validate_config.py — 起動前の設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- execution/ — 発注エンジン関連（EngineConfig, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, broker_factory 等）
- monitoring/
  - monitoring_db.py — SQLite を用いた監視ログ層
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 各モニタ実装
  - monitoring_engine.py, kill_switch.py, alert_manager.py
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI呼び出し）
  - regime_detector.py — マクロ + ETF MA によるレジーム判定
- utils/
  - logging_setup.py — 共通ロギング設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成ツール

注意点 / 運用上のヒント
---------------------
- .env は絶対にコミットしない（機密情報を含む）。config_setup で生成してください。
- 本番 env(KABUSYS_ENV=live) では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0。
- OpenAI API を使う機能はコストとレイテンシを伴います。API キーの管理とレート制御に注意してください。
- monitoring は MONITOR_POLL_INTERVAL 環境変数で秒数を変更できます（デフォルト 60 秒）。不正な値（0 以下や非整数）は 60 秒にフォールバックします。
- paper_trading モードは本番 DB と分離されていますが、設定ミスで本番 API にアクセスしないように env を必ず確認してください。

ライセンス・貢献
----------------
（この README はコードベースに基づき自動生成されています。実際のライセンス、貢献ルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。）

以上。必要であれば、README に含める具体的なコマンド例や systemd / supervisor 用のサービス記述テンプレート、依存パッケージの正確な requirements.txt を追記します。どの情報を追加しますか？