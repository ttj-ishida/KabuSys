# KabuSys

日本株自動売買システムのコアライブラリ群および起動用スクリプト群です。本リポジトリは以下の機能モジュールを含みます: 注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を用いたニュース/レジーム判定、各種ユーティリティと CLI。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援する内部ライブラリと運用スクリプトの集合です。設計方針の一部：

- 実運用（live）とペーパートレード（paper_trading）を明確に分離
- DuckDB / SQLite を用いたデータ分析・監視ログ永続化
- OpenAI を用いたニュースセンチメント / レジーム判定（任意）
- モジュールは副作用を極力抑え、テストしやすい純粋関数や明確な I/O を備える
- 運用の安全策（Kill Switch、監視、ログ、PID/フラグファイル）を提供

---

## 主な機能一覧

- 起動スクリプト
  - python -m kabusys.run_execution: ExecutionEngine（注文実行）起動
  - python -m kabusys.run_monitoring: SystemMonitor ポーリング起動
- 環境設定／検証 CLI
  - python -m kabusys.config_setup: .env 作成ウィザード
  - python -m kabusys.validate_config: 設定検証 CLI
- 監視（monitoring）
  - SystemMonitor: システムリソース・データ鮮度・Execution プロセス監視
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常、ドローダウンやポジション上限監視
  - KillSwitch: 条件発生時に data/kill.flag を出力し ExecutionEngine に停止命令
  - MonitoringDB: SQLite に監視ログ・トレードログ・リスクログを永続化
- Execution（execution）
  - BrokerClientFactory: 環境に応じて実ブローカー or MockBroker を提供（paper_trading の分離）
  - ExecutionEngine, OrderManager, Reconciler, RiskManager 等の実行コンポーネント
- ポートフォリオ構築（portfolio）
  - 銘柄選定、重み付け、ポジションサイズ計算、セクター制約、レジーム乗数
- リサーチ（research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ
- AI（ai）
  - news_nlp: OpenAI を使ったニュースセンチメント評価 → ai_scores への書き込み
  - regime_detector: MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB から検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリへ移動：

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成・有効化（任意）：

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール（requirements.txt がある場合）：

   pip install -r requirements.txt

   主要な依存例:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   ※ requirements.txt が無い場合は上記を個別にインストールしてください。

4. 初期 .env の作成（推奨）：

   python -m kabusys.config_setup

   ウィザードに従って .env を作成します（.env は絶対に Git にコミットしないでください）。

5. 設定の検証：

   python -m kabusys.validate_config
   # 警告も FAIL 扱いにする場合：
   python -m kabusys.validate_config --strict

6. データディレクトリの準備（必要に応じて）：

   デフォルトのファイルパス（Settings を参照）:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db

   ログ出力先はデフォルト logs/ ディレクトリ（LOG_DIR 環境変数で変更可）。

---

## 使い方（起動方法・主要コマンド）

- ExecutionEngine（注文実行）を起動:

  python -m kabusys.run_execution

  挙動：
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使います。本番 DB と完全分離。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に stop_requested.flag が出現するとエンジンを stop() して終了します。
  - 実行中に data/execution.pid に PID を出力します（設定により変更可能）。

- Monitoring（ポーリングループ）を起動:

  python -m kabusys.run_monitoring

  挙動：
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは常に本番 DB へ）。
  - data/stop_requested.flag を検出すると監視ループを終了します。

- .env 作成ウィザード:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポートの生成:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定例
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI / リサーチ等はライブラリ関数として呼び出します（例）:

  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  必要に応じて DuckDB 接続や API キー（OPENAI_API_KEY）を渡して使用します。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — default: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...） — default: INFO
- LOG_DIR: ログ格納ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）
- KILL_FLAG_CLEAR_ON_START: 本番環境で起動時に kill.flag を自動クリアするか（0/1）

Settings クラスは .env と OS 環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して行います。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 運用上の注意 / 安全装置

- Kill Switch:
  - RiskMonitor が条件（ドローダウン超過、ポジション上限超過等）を満たすと KillSwitch が data/kill.flag に理由を書き込みます。
  - ExecutionEngine は kill.flag の存在を検知して停止（安全機構）。
  - kill.flag は明示的に消去（KillSwitch.clear()）しない限り残ります。KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に自動でクリアされますが、本番では 0 を推奨します。

- stop_requested.flag:
  - run_execution/run_monitoring は data/stop_requested.flag を監視し、存在を検知するとループ終了やエンジン停止を行います。運用で安全に停止させたい場合に利用します。

- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出してプロセス優先度を引き上げます（プラットフォーム依存で失敗した場合は警告）。

- ロギング:
  - 共通の setup_logging を使い、コンソール（stdout）と日次ローテートファイルに統一的に出力します。logs/ ディレクトリに app_name.log が生成されます。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要な配置は以下の通りです（src/kabusys をルートとする）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定と .env 自動ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (実装あり)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装あり)
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
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py
  - data/                    — 実行時に使用するファイル置き場（DB / flag / pid 等）
  - logs/                    — ログ出力先（デフォルト）

（上記は主要ファイルの抜粋です。詳細はソースツリーをご確認ください。）

---

## 開発・デバッグのヒント

- .env を編集したら python -m kabusys.validate_config で検証する習慣をつけてください。
- Paper Trading を実行する場合は KABUSYS_ENV=paper_trading を設定すると実ブローカーを使わずに安全に動作確認できます（DB は data/paper_trading.db を使用）。
- OpenAI を使う機能を試すときは必ず OPENAI_API_KEY を設定してください。API 失敗時には多くの箇所でフォールバックが用意されていますが、結果が NOP になることがあります。
- DuckDB / SQLite にアクセスする関数群は外部副作用を抑えた設計になっているため、単体テストが容易です。テスト時にはパスを差し替えてください。

---

## ライセンス / 注意

この README はコードベースに基づく簡易ドキュメントです。実運用時は config/*.yaml、StrategyModel.md、PortfolioConstruction.md などの設計ドキュメントや運用手順書を必ず参照し、安全対策を確認してください。

もし README に追加したいコマンドや導入手順、あるいは CI / デプロイ手順があればご指示ください。README を拡張して反映します。