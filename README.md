KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・検証・モニタリングを目的とした小規模なトレーディングフレームワークです。  
主な設計方針は次の通りです。

- 戦略・ポートフォリオ構築は純粋関数で実装（メモリ内計算）。
- 実行（発注）ロジックはブローカークライアント抽象化を通じて本番 / ペーパーを切替可能。
- 監視（Monitoring）コンポーネントでシステム稼働状況やリスク（ドローダウン等）を自動監視し、必要なら Kill Switch を発動。
- DuckDB を分析用に、SQLite を監視・発注ログ用に使用。
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP / レジーム判定機能を搭載（APIキー必須）。

主な機能
--------
- ExecutionEngine（実行エンジン）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - RiskManager / OrderManager / Reconciler 等による発注管理
  - PID ファイル管理・停止フラグ対応
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 発注ログの滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、dashboard 更新
  - KillSwitch: 条件発生時に data/kill.flag を書き込んで ExecutionEngine を停止
  - MonitoringEngine: 監視ループとアラート通知連携
- Portfolio モジュール
  - 候補選別、等金額・スコア加重、セクター上限適用、ポジションサイズ算出（単元丸め含む）
- Research（研究用）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン / IC 計算 / 統計サマリー等
- AI 機能
  - news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores に保存
  - regime_detector: MA200 とマクロニュースを合成して市場レジーム判定
- ユーティリティ
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前の設定検証ツール
  - tools.paper_verification_report: ペーパートレード検証レポート生成

セットアップ
------------
1. Python と依存パッケージのインストール（例）
   - 推奨: Python 3.10+
   - 必要な主なパッケージ: duckdb, psutil, openai, pyyaml（YAML 検証が必要な場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

2. プロジェクトルートに移動（.git / pyproject.toml を基準に自動検出します）。

3. .env の初期作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
     - LOG_LEVEL（例: INFO）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

5. ディレクトリ / ファイルの準備
   - data ディレクトリ（SQLite / PID / flag ファイル用）と logs ディレクトリ（ログ）を作成するか、起動時に自動作成されますが権限に注意してください。

使い方
------
- 実行エンジン（Execution）
  - 普通に起動:
    - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録します。
    - process priority を high に設定し、data/execution.pid に PID を書く設計になっています。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 停止は外部から data/stop_requested.flag を作成する、または監視側の Kill Switch（data/kill.flag）で実施します。

- 監視ループ（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は production 用の sqlite_path を環境にかかわらず使用します（監視 DB は本番 DB を参照）。
  - 監視ループの停止:
    - data/stop_requested.flag が存在するとループは終了します。

- .env の生成 / 更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルトの DB: data/paper_trading.db、--db で上書き可。

- AI 機能
  - news_nlp.score_news / regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY）を要求します。キーは環境変数か関数引数で渡します。
  - OpenAI を利用する処理は外部 API 呼び出しのため、API エラー時はフェイルセーフ（スコアを 0 にする等）で処理継続する実装です。

監視 / 停止フラグ (重要)
------------------------
- stop_requested.flag
  - run_monitoring / run_execution が参照する外部停止フラグ。存在すると起動中ループを終了します。
  - パス: <project_root>/data/stop_requested.flag（コードで探索しています）

- kill.flag
  - KillSwitch が書き込むファイル。ExecutionEngine を即時停止させるために使用されます。
  - デフォルト: data/kill.flag
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 に設定すると自動クリアされます（本番では 0 推奨）。

ロギング
--------
- setup_logging ユーティリティにより、標準出力（stdout）と日次ローテートされたファイルログを設定します。
- 環境変数:
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- ログファイル例: logs/execution.log, logs/monitoring.log

データベース
-----------
- DuckDB（分析用）
  - デフォルト: data/kabusys.duckdb
- SQLite（監視・トレードログ）
  - 監視 DB（monitoring.db）: data/monitoring.db（monitoring 用）
  - ペーパートレード DB: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）
- monitoring_db.init_monitoring_db は起動時に必要なテーブルとインデックスを冪等に作成します。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必須）
- MONITOR_POLL_INTERVAL（監視間隔 秒、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading の fill 振る舞い、instant|partial|never|reject）
- LOG_LEVEL, LOG_DIR
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 以下の主なファイル/モジュールです（簡易ツリー）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - execution/               — 実行関連（broker, engine, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
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

- データ・ログディレクトリ（実行時に生成されることが多い）
  - data/
    - monitoring.db (デフォルト)
    - paper_trading.db (ペーパー)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - logs/
    - execution.log
    - monitoring.log
    - ...

注意事項 / 運用上のヒント
------------------------
- 本番環境では KABUSYS_ENV=live に設定する前に validate_config で設定を必ず確認してください。
- kill.flag や stop_requested.flag の扱いには注意してください。KILL_FLAG_CLEAR_ON_START を本番で 1 にするのは危険です（kill.flag が誤って消える可能性があるため）。
- OpenAI を利用する部分は API コストとレイテンシに注意してください。rate limit 対応やリトライが実装されていますが、プロダクション用途では料金・レートの監視が必要です。
- DuckDB / SQLite のバックアップや格納先パスは運用ポリシーに従って管理してください。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0（コード内定義）

最後に
------
この README はコードベースの主要な構成と運用手順の概要を記したものです。詳細は各モジュールの docstring やソースコード（特に config.py / run_*.py / monitoring/ / execution/）を参照してください。質問や追加で説明が必要な箇所があれば教えてください。