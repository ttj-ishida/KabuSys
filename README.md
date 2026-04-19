# KabuSys

日本株自動売買システムの一部をまとめた Python パッケージ。戦略の研究／ファクター計算、ポートフォリオ構築、注文実行（本番 / ペーパートレード）、監視・アラート、LLM ベースのニュースセンチメント評価などのユーティリティ群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要な以下の機能をモジュール化したライブラリ／実行スクリプト群です。

- 市場データ（DuckDB）を使ったファクター計算・研究（momentum / volatility / value 等）
- ポートフォリオ構築（候補選定・重み付け・株数決定・単元丸め）
- ExecutionEngine（発注ロジック）と BrokerClientFactory による注文送信（本番 / ペーパー分離）
- 監視（System / Trade / Risk モニタ）と Kill Switch（条件を満たしたら Execution を停止）
- ai モジュール：OpenAI を用いたニュースセンチメント評価（銘柄別）と市場レジーム判定
- 開発支援ツール：.env 対話ウィザード、設定検証ツール、Paper Trading 検証レポート生成

設計ポリシーの例:
- ルックアヘッドバイアスを避ける（date.today() の直接参照を避ける等）
- ペーパートレードは本番 DB と物理的に分離
- フェイルセーフ（API 失敗時はスキップして継続する設計）
- テスト容易性（関数を純粋関数にして副作用を抑える）

---

## 主な機能一覧

- config
  - 環境変数読み込み（.env / .env.local の自動読み込み、無効化オプションあり）
  - Settings クラス（アプリ全体で利用する設定）
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- execution
  - ExecutionEngine（run_execution 起動スクリプト）
  - BrokerClientFactory（環境に応じて Mock / 実ブローカーを生成）
  - OrderRepository / OrderManager / RiskManager / Reconciler
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - MonitoringDB（SQLite ベースの永続化層）
  - KillSwitch（kill.flag による Execution 停止）
  - run_monitoring 起動スクリプト（ポーリング）
- portfolio
  - candidate 選定、等配分・スコア配分、ポジションサイズ計算、セクター上限・レジーム乗数
- research
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / summary）
- ai
  - news_nlp: OpenAI を用いたニュースセンチメントの集約・スコアリング（ai_scores へ書き込み）
  - regime_detector: ma200 とマクロニュースを組み合わせた市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB を集計し検証レポート生成
- utils
  - logging_setup: 統一的なロギング設定（stdout + 日次ローテーションファイル）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

## 前提 / 必要パッケージ（例）

最低限必要なパッケージ（実プロジェクトでは requirements.txt を参照してください）:
- Python 3.9+（型注釈の使用を考慮）
- duckdb
- psutil
- openai
- sqlite3（標準ライブラリ）
- PyYAML（config 検証で任意。存在しない場合は YAML 検証をスキップ）

例:
- 仮想環境の作成・有効化
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- パッケージのインストール（例）
  - pip install duckdb psutil openai PyYAML

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を用意する
   - git clone <repo>
   - cd <repo>
   - python -m venv .venv && source .venv/bin/activate

2. 依存パッケージをインストールする
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上の必須パッケージを個別にインストール）

3. .env を作成する（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
   - .env 自動読み込みはデフォルトで有効（プロジェクトルートを基準）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証を行う
   - python -m kabusys.validate_config
   - 厳格モード（警告も FAIL）: python -m kabusys.validate_config --strict

5. 必要なディレクトリを作成
   - data/ （DB や PID / flag を格納）
   - logs/ （ログファイル。logging_setup が自動作成）

注意:
- 監視は Monitoring が常に本番 sqlite_path（SQLITE_PATH）を参照します（KABUSYS_ENV に依存しない）。
- ExecutionEngine は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用し、本番と完全分離します。

---

## 使い方

起動スクリプト一覧（パッケージとして実行）

- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
    - 実行中に data/stop_requested.flag が作成されると安全に停止します
    - PID ファイル: data/execution.pid（設定により変更可能）

- Monitoring 起動（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 停止は data/stop_requested.flag を生成するか KeyboardInterrupt

- Paper Trading 検証レポート（コマンドライン）
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB パスを指定可能

- ai モジュール（プログラムから呼び出し）
  - 例: ニューススコアリング
    - from kabusys.ai import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - cnt = score_news(conn, target_date=datetime.date(2026,4,10), api_key="...")

  - market regime 判定
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

- ログ
  - デフォルト: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - stdout にも出力されます。LOG_DIR 環境変数でログディレクトリを変更可能。

停止・安全操作:
- ExecutionEngine を強制停止させたい（Kill Switch 発動）は monitoring の KillSwitch によって data/kill.flag が書き込まれます。ExecutionEngine は指定された kill flag によって停止判定を行います。
- stop_requested.flag（data/stop_requested.flag）を作成すると run_execution / run_monitoring のループを安全に抜けます。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能に必要）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ出力先ディレクトリ。デフォルト: logs/）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- KILL_FLAG_PATH（KillSwitch のパス、デフォルト: data/kill.flag）
- PID_FILE_PATH（ExecutionEngine の PID ファイルパス、デフォルト: data/execution.pid）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

config_setup による .env 生成時の各キーは対話式ヘルプが表示されます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py (Settings, .env 自動読み込み)
- config_setup.py (.env 対話ウィザード)
- validate_config.py (設定検証 CLI)
- run_execution.py (ExecutionEngine 起動スクリプト)
- run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

サブパッケージ:
- ai/
  - __init__.py
  - news_nlp.py (ニュースセンチメント -> ai_scores)
  - regime_detector.py (市場レジーム判定)
- monitoring/
  - __init__.py
  - monitoring_db.py (SQLite スキーマ + MonitoringDB)
  - system_monitor.py
  - trade_monitor.py (※実装あり)
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (※実装あり)
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- tools/
  - __init__.py
  - paper_verification_report.py
- utils/
  - __init__.py
  - logging_setup.py
  - process_priority.py

その他:
- data/ （DB、PID、flag 等）
- logs/ （ログファイル）

---

## 開発上の注意点 / 補足

- 監視（Monitoring）は設計上、環境に関わらず本番 sqlite（SQLITE_PATH）を使用して監視ログを蓄積します。一方で ExecutionEngine は KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB を使って発注履歴を分離します。
- OpenAI を使う機能は API キーが必須です。API 呼び出しは再試行やバックオフ、レスポンス検証（JSON 抽出・バリデーション）を実装しており、失敗時は安全側のフォールバックを行います。
- logs ディレクトリ作成に失敗した場合はコンソール出力のみで動作を継続します（logging_setup の挙動）。
- 設定検証ツールは PyYAML がインストールされていると config/*.yaml のパース検証を行います。インストールされていない場合はスキップして警告を出します。
- データ鮮度やプロセス PID の stale 検出など、監視の一部は DB の dashboard / positions 等の集計に依存します。初期状態では dashboard レコードが存在しないことが想定されるため、監視は NOP 的に動作します。

---

必要であれば README に起動例の具体的なコマンド（systemd unit / docker-compose 例）や requirements.txt の推奨内容、CI 用のテスト実行手順、より詳細なディレクトリツリーを追加できます。どの情報を優先して追記しますか？