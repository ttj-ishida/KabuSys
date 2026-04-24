KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買およびそれを支える分析・監視ツール群をまとめたプロジェクトです。  
主な目的は、戦略の信号生成 → ポートフォリオ構築 → 発注（実発注 / ペーパートレード） → 監視・リスク管理 を一貫して実行できることです。

本 README はリポジトリ内の主要スクリプト／モジュールの使い方、セットアップ手順、ディレクトリ構成を日本語でまとめたものです。

主な機能
--------
- 発注エンジン（ExecutionEngine）
  - 本番（kabuステーション）とペーパートレード（MockBroker）を切替可能
  - リスク制御（最大ポジション比率、利用率、回路遮断など）
  - 発注ログを SQLite に永続化、DuckDB にも接続
- 監視（Monitoring）
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの有無などの監視
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション上限監視
  - Kill Switch: リスク条件（例: ドローダウン閾値）で停止フラグを書き込み、ExecutionEngine を停止
  - アラート（LINE 等）発行（設定がある場合）
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定、等配分/スコア重み、リスク調整（セクター上限、レジーム乗数）
  - 株数決定（リスクベース、等配分など）、単元株丸め、aggregate cap のスケーリング
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを DuckDB 上の prices_daily / raw_financials から計算
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- AI 支援
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコアを生成し ai_scores に保存
  - 市場レジーム判定（ETF MA + マクロニュースの LLM スコア合成）
- 運用ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

セットアップ手順（ローカル開発向け）
-----------------------------------
前提: Python 3.9+ を想定（duckdb / psutil / openai 等が必要）。必要に応じて pyproject.toml / requirements.txt を参照してください。

1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （任意）PyYAML を入れると validate_config が YAML ファイルの中身検証を行えます:
     - pip install pyyaml

   （プロダクション用にさらに依存関係がある場合は、プロジェクトの依存ファイルを参照して下さい）

4. 初期設定（.env）
   - 対話式ウィザードを使って .env を作成・更新できます:
     - python -m kabusys.config_setup
   - ウィザードで設定する代表的な環境変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意）
     - LOG_LEVEL (DEBUG | INFO | ...)
     - KILL_FLAG_CLEAR_ON_START (0/1)

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります:
     - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
------------------------

- ExecutionEngine を起動（発注処理）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存:
    - paper_trading: MockBrokerClient を使い、データは data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可能）に記録します（本番 DB と完全分離）。
    - live: 実発注（kabuステーション）を行います（十分に注意してください）。
  - 起動時に data/execution.pid に PID を書き、停止は data/stop_requested.flag や data/kill.flag により制御できます。
  - ExecutionEngine は設定されたリスク制御（RiskManager）や OrderManager と連携します。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 初期化は本番 sqlite_path（Settings.sqlite_path）を使います（環境に関わらず監視 DB は本番 DB を参照）。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます（またはキーボード割り込み）。

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ関数の呼び出し（ライブラリ利用例）
  - Python からモジュール関数をインポートして利用可能:
    - from kabusys.ai.news_nlp import score_news
      - score_news(conn, target_date, api_key=None)  # conn は duckdb connection
    - from kabusys.ai.regime_detector import score_regime
      - score_regime(conn, target_date, api_key=None)
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

運用上の注意
------------
- 環境変数や .env は機密情報を含み得ます。.env を絶対にリポジトリにコミットしないでください（config_setup も注意喚起を出します）。
- KABUSYS_ENV=live の場合は本番口座に実際の発注が行われます。設定（特に API パスワード・LINE 通知・KILL SWITCH）を慎重に確認してください。
- Kill Switch（デフォルト: data/kill.flag）はドローダウン・ポジション上限等で起動する仕組みです。KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアされますが、本番では 0 を推奨します。
- 監視は本番 DB（Settings.sqlite_path）を参照します。Monitoring の DB 初期化は冪等で行われますが運用ポリシーに従って下さい。
- ロギング: logs/ に日次ローテートでログが出力されます（kabusys.utils.logging_setup）。

主要な設定項目（Settings に定義）
--------------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（ペーパートレードでの執行モデル: instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU/MEMORY/DISK 閾値（監視用）
- KABUSYS_ENV（development | paper_trading | live）
- LOG_LEVEL

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数の自動ロード機能と Settings クラス定義
- config_setup.py
  - .env 作成・更新の対話式ウィザード
- validate_config.py
  - 起動前設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV により動作切替）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py
    - ペーパートレードの検証レポート生成
- ai/
  - news_nlp.py
    - ニュースを OpenAI でスコアリングして ai_scores に書き込むロジック
  - regime_detector.py
    - ETF MA とマクロニュースで市場レジーム判定
- research/
  - factor_research.py
    - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py
    - 将来リターン、IC、統計サマリ等
- portfolio/
  - portfolio_builder.py
    - 候補選定・重み計算
  - risk_adjustment.py
    - セクターキャップ・レジーム乗数
  - position_sizing.py
    - 株数決定・スケーリング・単元丸め
- monitoring/
  - monitoring_db.py
    - 監視用 SQLite スキーマと MonitoringDB ラッパー（log_system_status, log_trade_event, upsert_dashboard 等）
  - system_monitor.py
    - システム状態・データ鮮度確認
  - risk_monitor.py
    - ドローダウン・ポジション数の監視
  - kill_switch.py
    - kill.flag の生成・判定ロジック
  - monitoring_engine.py
    - 複数モニタを束ねるエンジン（run / run_once）
  - trade_monitor.py (プロジェクト内に存在)
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など
    - 発注ロジック・リスク管理・ブローカ抽象化
- utils/
  - logging_setup.py
    - ログの統一設定（stdout + 日次ローテーション）
  - process_priority.py
    - プロセス優先度・CPU affinity 設定ユーティリティ
- data/ (実行時に生成される想定)
  - monitoring.db（デフォルト）
  - paper_trading.db（ペーパートレード用）
  - kill.flag / stop_requested.flag / execution.pid
- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
    - validate_config で存在／パースを確認（PyYAML があると内容検証も行う）

監視・停止フロー（概略）
-----------------------
- Monitoring の RiskMonitor が検査結果に基づき KillSwitch.evaluate を呼ぶ
- KillSwitch が条件（ドローダウンやポジション上限）に該当すると data/kill.flag に理由を書き込む（冪等）
- ExecutionEngine は起動時に kill_flag_clear_on_start の設定に従い kill.flag をクリアするオプションがある。実行中は kill.flag の存在を監視して停止する仕組みを持たせられます（run_execution のループで stop flag を確認）。

トラブルシューティング（よくある点）
------------------------------------
- ログディレクトリ作成失敗
  - 権限やパスの問題で logs/ が作れない場合はコンソール出力のみとなります。logging_setup が警告を出します。
- DuckDB / SQLite のパス
  - デフォルトは data/*. だがプロダクションでは明示的に環境変数で指定することを推奨します。
- OpenAI API
  - OPENAI_API_KEY が未設定だと AI モジュールは例外を投げます。テストではモック化して使用する設計です。

最後に
-----
この README はコードベースから抽出した主要な使い方と概観をまとめたものです。詳細な実装や追加の運用手順（デプロイ、監視アラートの LINE セットアップなど）は別途ドキュメントや運用手順書にまとめてください。必要であれば README を拡張して、起動例、systemd / Supervisor の unit サンプル、CI / テスト手順等も追記できます。必要な内容を指定してください。