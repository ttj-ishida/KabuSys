# KabuSys

日本株向け自動売買システムのミニマル実装コレクションです。  
本リポジトリは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、研究用ファクター計算、ニュースNLP / レジーム判定（OpenAI 利用）などを含むモジュール群を提供します。

Version: 0.1.0

---

## 概要

- 実際の発注を伴う本番（live）モード、発注を模擬するペーパートレード（paper_trading）モード、開発（development）モードを想定した設計。
- SQLite（監視・注文履歴等）および DuckDB（時系列データ分析）をデータ永続化に使用。
- 監視コンポーネントで稼働率・データ鮮度・滞留注文・ドローダウン等をチェックし、必要に応じて Kill Switch を発動して ExecutionEngine を停止可能。
- ニュースセンチメントやマクロセンチメントの評価に OpenAI（gpt-4o-mini 等）を利用する機能を含む（APIキー必須）。
- 研究用のファクター計算・特徴量探索ユーティリティを用意（DuckDB 接続を受け取って計算）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - paper_trading モードでは MockBrokerClient を使用し、paper DB に完全分離して記録
  - リスク管理（RiskManager）・注文管理（OrderManager）・再整合（Reconciler）等

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（monitoring_db: system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch（条件により data/kill.flag を書き込み、Execution を停止）

- Portfolio（銘柄選定・配分・株数計算）
  - 候補選定、等加重/スコア加重、リスクベースのポジションサイジング
  - セクター上限適用、レジーム乗数（bull/neutral/bear）など

- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー等

- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: ETF の MA 乖離 + マクロニュースを合成して日次レジームを判定

- Tools
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）
  - 設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

---

## セットアップ手順（概要）

前提
- Python 3.10+ を推奨（型アノテーションの union 表記などを使用）
- OS: Linux / macOS / Windows（process priority 設定は OS に依存）

1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate

3. 依存パッケージをインストール
   - 必要な主なライブラリ:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（config 検証で YAML ファイルの検査を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt があれば pip install -r requirements.txt を使用してください）

4. ディレクトリ作成（自動で作られることもありますが手動準備しておくと安心）
   - mkdir -p data logs

5. .env の作成
   - 対話ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参考に）。自動ロードの仕組み:
     - OS 環境変数 > .env.local > .env の順で適用（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）

6. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いして exit(1)

---

## 必須／主要な環境変数

重要な環境変数（デフォルト値は .env 作成ウィザードに記載）:

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI を使うモジュールで必要
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログファイル保存先（デフォルト: logs/）
- PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch が書き込むフラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=クリア, 0=クリアしない）
- PAPER_FILL_MODE — paper_trading 時のモック約定挙動（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）。環境変数で上書き可能。

注意:
- paper_trading を使用する場合、発注ロジックは MockBroker を使い paper DB（PAPER_TRADING_SQLITE_PATH）に記録し、本番 DB とは分離されます。
- OpenAI 関連機能を使うには OPENAI_API_KEY が必須。

---

## 使い方（主要コマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話形式で作成／更新します。

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告も FAIL 扱いにできます。

- ExecutionEngine（取引実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し data/paper_trading.db に記録されます。
  - 停止方法:
    - ExecutionEngine は起動中に data/stop_requested.flag の存在を監視します。ファイルが存在するとエンジンは停止します。
    - KillSwitch が trigger すると data/kill.flag を書き込み、ExecutionEngine はそれを検出して停止します（KILL_FLAG_CLEAR_ON_START に注意）。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更できます（デフォルト 60）。
  - 監視はどの環境変数設定でも sqlite_path（本番）を使って監視データを書き込みます。
  - 停止方法:
    - data/stop_requested.flag の作成で監視ループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

---

## ログ・データ

- ログ
  - デフォルト: logs/<app_name>.log に日次でローテートされ保存されます（30日保持）。
  - コンソール出力は stdout に出ます（cron 等で stdout/stderr をまとめてリダイレクトしやすいよう配慮）。

- データ
  - data/ 下に SQLite、DuckDB、pid/flag ファイルを配置する想定。
  - 監視 DB の初期化・マイグレーションは init_monitoring_db() で行われます（冪等）。

---

## Kill / Stop の仕組み（簡単に）

- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring/run_execution が起動時に参照する「外部からの即時停止要求」用ファイル。
  - ファイルが存在すると監視ループ／ExecutionEngine は起動を中断したり実行中止を行います（run_execution は起動直後にこのフラグがあれば起動を中止）。

- kill.flag（data/kill.flag）
  - KillSwitch（監視コンポーネント）がリスク条件等に応じて書き込むファイル。
  - ExecutionEngine 起動時に kill.flag があれば（設定により）自動クリアされるか、Engine が停止トリガーを受けます。KILL_FLAG_CLEAR_ON_START を確認してください。

---

## 開発・テストのヒント

- 自動で .env を読み込む処理は、プロジェクトルート（.git または pyproject.toml がある場所）を起点に行われます。テスト時に自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を呼ぶ関数（news_nlp / regime_detector）は外部からモック可能になるよう設計されています（ユニットテストでの patch が可能）。
- DuckDB をデータソースとして渡すことで研究用関数を DB に対して安全に実行できます（本番口座に影響を与えません）。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (存在する想定)
    - kill_switch.py
    - alert_manager.py (存在する想定)
  - execution/
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
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のファイルは src/kabusys 以下を参照してください。上は主要ファイルの抜粋です）

---

## 注意事項 / 補足

- 本リポジトリは自動売買システムの構成要素を例示する実装群です。実際の資金を扱う際は十分な検証・バックテスト・安全対策（制御系の冗長化、監査ログ、手動停止手順、権限管理等）を行ってください。
- OpenAI 等外部 API の利用はコストおよびレイテンシに注意が必要です。API キーは漏洩しないよう .env を Git 管理から除外してください。
- ローカルでの動作確認・単体テストを推奨します。monitoring / execution の連携はファイルフラグ（data/kill.flag, data/stop_requested.flag）に依存するため、手動での停止・再開手順をドキュメント化して運用してください。

---

必要があれば、README に含めるコマンドの具体的な例（.env テンプレート、systemd / service ファイル例、Dockerfile 例 など）や、各モジュール（ExecutionEngine, MonitoringEngine, AI モジュールなど）の詳細設計ドキュメントを追加で作成します。どの項目を優先して深掘りしますか？