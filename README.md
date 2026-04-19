# KabuSys

バージョン: 0.1.0

日本株向けの自動売買システム（プロトタイプ）。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究用ファクター計算、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含みます。本リポジトリはライブラリ／起動スクリプト群を提供します。

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境設定（.env）の作成
- 設定検証
- 使い方（起動スクリプト）
- 主要環境変数
- 停止・Kill スイッチ
- ディレクトリ構成（主要ファイル）
- 注意事項

---

プロジェクト概要
- 戦略のシグナル生成 → ポートフォリオ構築 → 発注（実売買/ペーパートレード）までの一連処理を想定したモジュール群を備えています。
- 監視（System / Trade / Risk）と自動停止（Kill Switch）機能により安全運用を支援します。
- DuckDB を用いた研究用データ解析、SQLite による監視ログ永続化、OpenAI を用いたニュース NLP（センチメント）・レジーム判定のサポートを提供します。

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番/ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアント抽象化
  - リスク管理（RiskManager）、注文管理（OrderManager）、照合（Reconciler）
  - 実行時に PID ファイル管理・stop フラグ監視
- Monitoring（run_monitoring.py）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - TradeMonitor / RiskMonitor と統合する MonitoringEngine
  - MONITOR_POLL_INTERVAL によるポーリング間隔の上書き（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）: .env を対話式に生成・更新
- 設定検証ツール（validate_config.py）: .env や config/*.yaml のチェック
- Paper Trading 検証レポート（tools/paper_verification_report.py）
- 研究用モジュール（research/）: ファクター計算（momentum/value/volatility）や IC 計算等
- AI モジュール（ai/）: ニュースセンチメント（news_nlp）、レジーム判定（regime_detector）
- ポートフォリオ構築（portfolio/）: 候補選定、重み計算、リスク調整、ポジションサイズ算出
- ユーティリティ（utils/）: ロギング設定、プロセス優先度設定 等
- 監視ログ永続化（monitoring/monitoring_db.py）: SQLite スキーマの初期化・読み書き

前提条件
- Python 3.9+（型注釈や一部書式を踏まえた推奨）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイルの YAML 検証で任意）
- （実運用時）kabuステーションや J-Quants 等の各 API アカウント / 認証情報

セットアップ手順（例）
1. リポジトリをクローン / プロジェクトルートに移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（必要に応じて requirements.txt を用意してください）
   - pip install duckdb psutil openai pyyaml
4. デフォルトで使用するディレクトリ作成（任意）
   - mkdir -p data logs

環境設定（.env）の作成
- 対話式ウィザードで .env を生成:
  - python -m kabusys.config_setup
  - ウィザードは既存 .env を読み込み、入力済み値は Enter で再利用できます。
- 必須の環境変数（最低限設定する項目）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- AI 機能を使う場合
  - OPENAI_API_KEY を設定してください。

設定検証
- validate_config により起動前に設定の誤りを検出できます:
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）になります:
    - python -m kabusys.validate_config --strict

使い方（主要スクリプト）
- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いペーパートレード用 DB（data/paper_trading.db）に記録されます（本番 DB と分離）。
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=120）
  - 注意: Monitoring は環境にかかわらず本番 sqlite_path を使用します（監視ログは共通で保管）。
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- AI モジュール（プログラム的呼び出し）
  - kabusys.ai.score_news や kabusys.ai.regime_detector.score_regime を呼び出し。OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を設定。
- ログ設定
  - 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出します。デフォルトログディレクトリは logs/、日次ローテーション・30日分保持。

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 環境制御
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0|1
- DB パス
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db） — paper_trading 用 DB
- AI
  - OPENAI_API_KEY
- モニタリング
  - MONITOR_POLL_INTERVAL（秒） — run_monitoring のポーリング間隔上書き
- その他
  - LOG_DIR（ログ出力先ディレクトリ）
  - PID_FILE_PATH（実行エンジンの PID ファイルパス）
  - KILL_FLAG_PATH（Kill Switch 用フラグファイル）

停止・Kill スイッチ
- 実行停止フラグ
  - run_execution / run_monitoring は project_root/data/stop_requested.flag の存在を監視し、検出時に安全に停止します。管理者が停止させたい場合はこのフラグファイルを作成してください。
- Kill Switch（自動停止）
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - KillSwitch は冪等で書き込み、clear() で削除できます。
  - 設定 KILL_FLAG_CLEAR_ON_START=1 を有効にすると起動時に kill.flag を自動クリアします（本番環境では 0 を推奨）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 自動読み込み、Settings クラス
  - config_setup.py             — .env 対話式ウィザード
  - validate_config.py          — 設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py          — ロギング初期化ユーティリティ
    - process_priority.py       — プロセス優先度 / CPU affinity 設定
  - execution/
    - execution_engine.py       — 実行エンジン（EngineConfig, run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py          — SQLite スキーマ・永続化層
    - system_monitor.py         — システム状態・データ鮮度監視
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
    - news_nlp.py                — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py        — 市場レジーム判定（OpenAI 連携）
  - tools/
    - paper_verification_report.py
  - data/                       — 実行時に使用する SQLite / PID / flag 等（デフォルト）
  - logs/                       — ログファイル出力先（デフォルト）

簡単なファイルツリー例（省略形）
- data/
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - stop_requested.flag
  - kill.flag
- logs/
  - execution.log
  - monitoring.log
  - ...

注意事項 / 運用メモ
- Monitoring は監視用 DB（SQLITE_PATH）を環境にかかわらず使用します（監視ログは共通）。Execution は KABUSYS_ENV=paper_trading の場合、paper_trading_db を使用して本番 DB から分離します。
- process_priority の設定は psutil を使用し、OS により管理者権限が必要になる場合があります。失敗時は警告ログを出してスキップします。
- AI（OpenAI）連携機能は API の利用料金とレートリミットに注意して利用してください。429/ネットワーク障害等に対するリトライ実装がありますが、過度の呼び出しは避けてください。
- ログディレクトリ作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。
- .env は機密情報を含むため Git にコミットしないでください。

お問い合わせ / 開発メモ
- 各モジュールはドメイン別に分割されており、単体テストしやすい純粋関数スタイルの箇所（portfolio/*.py、research/*.py 等）と、DB/API を扱う副作用のある箇所（execution/*、monitoring/*、ai/*）があります。ユニットテストやモックの差し替えを想定して設計されています。

---

この README はコードベース（src/kabusys）に基づく概要です。運用や導入の際は各設定ファイル（config/*.yaml）や追加ドキュメント、運用手順書を併せて参照してください。