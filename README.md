README
======

概要
----
KabuSys は日本株向けの自動売買および研究用ライブラリ／実行基盤です。  
主に以下を目的とします。

- 発注エンジン（ExecutionEngine）の起動と注文管理（本番 / ペーパートレード切替）
- システム稼働監視（SystemMonitor / MonitoringEngine）と Kill Switch による自動停止
- ポートフォリオ構築（銘柄選定・重み付け・株数計算）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- ニュースを用いた LLM ベースのセンチメント（AI スコア）付与
- ペーパートレード検証レポート生成ツール

主な設計方針:
- 本番とペーパートレードの DB を分離（KABUSYS_ENV により切替）
- .env を用いた環境変数管理（config_setup.py によるウィザード）
- DuckDB を分析用データベースとして利用、SQLite を監視／履歴に利用
- OpenAI (gpt-4o-mini 等) を使った NLP 処理を含むが、API キーは明示的に提供する

主な機能一覧
-------------
- 実行系
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
  - BrokerClientFactory によりブローカークライアントを生成
  - リスク管理（RiskManager）、オーダーマネージャー、照合処理（Reconciler）

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: System/Trade/Risk 各モニタを束ねて周期的に実行
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard テーブル管理

- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・等配分／スコア加重配分
  - portfolio.position_sizing: 株数決定、資金制約・単元丸め、スケールダウンロジック
  - portfolio.risk_adjustment: セクターキャップ適用・レジーム乗数

- 研究・解析
  - research.factor_research: Momentum / Volatility / Value 等ファクター計算（DuckDB ベース）
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）等

- AI（LLM）関連
  - ai.news_nlp: raw_news をまとめて OpenAI に送信し銘柄別センチメントを ai_scores に書込む
  - ai.regime_detector: ETF 1321 の MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定

- ツール
  - tools.paper_verification_report: ペーパートレード DB を元に運用品質（稼働率、成功率、レイテンシ等）を集計しレポート出力

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリへ
   - 例: git clone ... ; cd <repo>

2. Python 環境（推奨: venv）を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要依存（本リポジトリから推測）:
     - pip install duckdb psutil openai PyYAML
   - 注意: PyYAML は config YAML の検証で任意。OpenAI は AI 機能利用時に必要。

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - LOG_LEVEL: INFO
     - OPENAI_API_KEY: （AI 機能を使う場合に設定）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになる

6. データディレクトリ・ログディレクトリ作成（必要に応じて）
   - data/ と logs/ はプログラム起動時に自動作成されることが多いが、アクセス権に注意

使い方（主要コマンド）
--------------------

- 環境変数の例（Linux/macOS）
  - export KABUSYS_ENV=development
  - export OPENAI_API_KEY="sk-..."

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - ペーパートレードで起動する場合:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - この場合は MockBroker が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され本番 DB と分離される

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
    - export MONITOR_POLL_INTERVAL=30

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — raw_news を AI で採点して ai_scores に書込
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)  — 市場レジームを判定し DB に保存

停止・Kill Switch
-----------------
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution がこのファイルを検出すると順次停止処理を行う
  - data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine の停止を促す（存在すれば Execution 側で検出）
  - PID ファイル: data/execution.pid（ExecutionEngine 起動時に作成）
- 注意:
  - Settings.kill_flag_clear_on_start が "1" に設定されていると起動時に kill.flag を自動でクリアする（本番では推奨されない）

ログ
----
- ログ出力は kabusys.utils.logging_setup.setup_logging により統一管理
- デフォルトログディレクトリ: logs/
- 各アプリケーションは app_name（例: "execution", "monitoring"）ごとにファイル logs/<app_name>.log へ日次ローテーションで出力（30日保持）
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で設定

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: AI 機能を使う場合は必須
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring 用）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか ("0" or "1")

監視 DB（SQLite）スキーマ概要
---------------------------
monitoring.db（init_monitoring_db によって作成）
- system_status: CPU/メモリ/ディスク/プロセス稼働等のポーリング履歴
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled など）、latency_ms 列あり
- positions: ポジション保存（code 主キー）
- risk_logs: リスク関連アラートログ
- dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュールとファイルの抜粋です（実際のリポジトリは src/ 直下に配置）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (アラート送信ロジック)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - (データパイプライン / DuckDB 参照用モジュール等)
  - utils/
    - logging_setup.py
    - process_priority.py
    - (その他ユーティリティ)

補足・運用上の注意
-----------------
- .env は機密情報（API キー等）を含むため決して Git にコミットしないでください。
- 本番運用 (KABUSYS_ENV=live) 時は KILL_FLAG_CLEAR_ON_START を 0（自動クリアしない）にすることを推奨します。
- OpenAI 呼び出しは API レートや費用に注意し、API キーの管理を徹底してください。
- psutil を用いてプロセス優先度や CPU affinity を調整しますが、権限の都合で失敗する場合があります（警告ログで通知）。
- DuckDB / SQLite のファイルパスは Settings によりカスタマイズ可能です。運用環境ではデータ配置先とバックアップを検討してください。

ライセンス・その他
-----------------
- この README はコードベース内の docstring と実装から生成された概要です。実運用前に各種設定（API キー、DB パス、ログ設定）を十分に確認してください。

問題や不足している情報があれば、どの点について詳しく知りたいか教えてください。README のテンプレートやコマンド例を追加で整備します。