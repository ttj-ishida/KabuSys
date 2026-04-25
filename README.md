# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
主な目的は、戦略の実行（ExecutionEngine）、システム監視（Monitoring）、リサーチ／ファクター計算、ペーパートレード検証、およびAIを用いたニュースセンチメント評価を提供することです。

バージョン: 0.1.0

---

## 概要

このリポジトリは自動売買システムのコア機能をモジュール化した Python パッケージです。主要コンポーネントは次のとおりです。

- Execution: 注文作成・送信・リスク管理を担う ExecutionEngine（本番・ペーパートレード対応）
- Monitoring: システム状態・注文状態・リスク指標をポーリングしてログ・アラート・Kill Switch を管理
- Portfolio: 銘柄選定、配分、ポジションサイズ計算などのポートフォリオ構築ロジック（純粋関数）
- Research: DuckDB を使ったファクター計算・特徴量探索（モジュール単体で動作）
- AI: OpenAI を使ったニュースセンチメント評価・市場レジーム判定（外部 API 必須）
- Tools: ペーパートレードの検証レポート生成などのユーティリティスクリプト
- Config: .env 読み込み・設定ウィザード・検証ツール

設計方針として「本番データへの不必要なアクセスを避ける」「ルックアヘッドバイアスを防ぐ（date.today() を直接参照しない等）」「フェイルセーフ（API失敗時のフォールバック）」を重視しています。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により実際のブローカー or Mock を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 環境変数・config/*.yaml の起動前検証 CLI
- 監視
  - MonitoringDB: SQLite に監視ログ永続化（system_status, trade_logs, risk_logs, positions, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
- Execution 側
  - BrokerClientFactory（本番 or mock 切り替え）
  - OrderManager / OrderRepository / RiskManager / ExecutionEngine / Reconciler
- ポートフォリオ構成
  - 銘柄選定、等重／スコア重み、リスク調整（セクターキャップ、レジーム乗数）、株数決定（単元丸め、aggregate cap）
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI 関連
  - news_nlp: OpenAI でニュースをセンチメント評価し ai_scores に書き込み
  - regime_detector: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime 判定
- ツール
  - paper_verification_report.py: ペーパートレードの稼働率・注文成功率・レイテンシ等のレポート生成

---

## 前提・依存関係

主な外部依存（抜粋）:
- Python 3.9+（型注釈の一部に合わせて推奨）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を有効にする場合）

インストール例:
- 仮想環境作成
  - python -m venv .venv
  - source .venv/bin/activate
- パッケージインストール（pip）
  - pip install duckdb psutil openai PyYAML

（プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール（上記参照）
4. .env を作成
   - 対話式ウィザード実行:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成。最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - (AI 機能を使う場合) OPENAI_API_KEY=...
   - 既定ではプロジェクトルートの .env が自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合: python -m kabusys.validate_config --strict
6. データディレクトリを作成
   - デフォルトの DB / ログパス: data/, logs/
   - 必要なら環境変数で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更

注意:
- ペーパートレード（KABUSYS_ENV=paper_trading）は専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）にログを書き、本番 DB と分離されます。
- 監視は monitoring.db（デフォルト data/monitoring.db）を使用します。monitoring は常に本番 sqlite_path を参照します（コード内の設計）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading → MockBrokerClient を使用、データは data/paper_trading.db に記録
    - 起動時に data/stop_requested.flag が既に存在する場合は起動を中止
    - プロセス優先度を high に設定（できる環境で）
    - 停止は data/stop_requested.flag を作成することで通知

- Monitoring を起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）にログを書きます
  - 停止はプロジェクトルートの data/stop_requested.flag を作成して行います

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で変更可能
  - レポートでは稼働率・注文成功率・送信率・レイテンシ等を算出し PASS/FAIL を出力

- AI / リサーチ関数の利用（ライブラリとして）
  - 例（Python REPL / スクリプト内）:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime
    - これらは DuckDB 接続や target_date、OpenAI APIキーを引数に取ります。API キーは引数または環境変数 OPENAI_API_KEY を使用。

- ロギング
  - setup_logging() でコンソール出力（stdout）と日次ローテートファイル（logs/<app_name>.log）を設定します。
  - 環境変数 LOG_DIR / LOG_LEVEL により挙動を制御可能。

停止／Kill Switch:
- KillSwitch は監視ロジック（リスク・ドローダウン等）により data/kill.flag を書き込み、ExecutionEngine 側で検出すると発注を停止・シャットダウンする仕組みです。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合は kill.flag を自動クリア（開発用。注意: 本番では 0 推奨）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 DB（monitoring）デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API を使う場合に必須
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）

例 (.env の最小例):
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

（.env は絶対に Git 管理にコミットしないでください）

---

## 開発・デバッグのヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を基準）を検索して行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- run_execution/run_monitoring はプロセス優先度や PID ファイルを用いて運用環境向けに設計されています。ローカルでのデバッグ時はこれらの副作用を把握してください（data/ ディレクトリにファイルが作成されます）。
- DuckDB を使ったリサーチ関数は外部の価格テーブル（prices_daily / raw_financials など）を参照します。必ず適切な DuckDB ファイルを指定してテストしてください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン
  - config.py — .env 自動読み込み・Settings クラス
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/ — ExecutionEngine 周辺（BrokerFactory, OrderManager, RiskManager, Reconciler など）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義と永続化ロジック
    - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py（監視サブシステム）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（選定・配分・サイズ計算）
  - research/
    - factor_research.py, feature_exploration.py（DuckDB ベースのファクター計算・解析）
  - ai/
    - news_nlp.py — ニュースを OpenAI でセンチメント付与
    - regime_detector.py — 市場レジーム判定ロジック
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - data/ — 実行時生成データ（DB・flag・pid など。通常は gitignore）

---

## 注意事項 / 運用上の注意

- 本システムは売買（実際の発注）を含むため、本番環境で運用する場合は設定（KABUSYS_ENV=live）、API キー、LINE 等の通知設定、Kill Switch の挙動を十分に確認してください。
- KILL_FLAG_CLEAR_ON_START=1 は利便性のために開発で使えますが、本番では 0 を推奨します（誤って Kill Switch をクリアしてしまう危険があるため）。
- OpenAI 等外部 API 呼び出しで料金やレート制限が発生します。API キー／利用量の管理に注意してください。
- データベースファイルやログファイルのパスは環境変数で上書きできます。運用環境では永続化先とバックアップ方針を決めてください。

---

README は開発・運用開始時のガイドラインです。さらに詳細な仕様（StrategyModel.md、PortfolioConstruction.md、各モジュールのドキュメント）がある場合はそちらも参照してください。必要であれば各モジュールの具体的な使用例やユニットテストの実行手順も追記できます。