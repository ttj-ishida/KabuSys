# KabuSys

日本株自動売買システムのパッケージ（README）。このドキュメントはリポジトリ内の主要スクリプト・モジュール構造と利用手順を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買システムの基礎ライブラリ群です。  
主な機能は以下のとおりです。

- 取引エンジン起動スクリプト（ExecutionEngine）と監視ループ（Monitoring）
- Paper Trading（ペーパートレード）向け分離DBサポート
- ポートフォリオ構築、ポジションサイズ計算、セクター制限などの投資ロジック
- DuckDB を用いたリサーチ・ファクター計算モジュール
- OpenAI を使ったニュース NLP（センチメント）と市場レジーム判定
- 監視ログの永続化（SQLite）とアラート / Kill Switch 機能
- 環境設定ウィザード・設定検証ツール・検証レポート生成ツール

バージョン: 0.1.0

---

## 主な機能一覧

- 実行系
  - run_execution.py: ExecutionEngine を起動（本番 / paper_trading をサポート）
  - ブローカークライアントを環境に応じて生成（Mock を含む）
  - リスク制御（RiskManager）、注文管理（OrderManager）、照合（Reconciler）などの組立て

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整可能）
  - MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor を束ねる
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard テーブルを提供
  - KillSwitch: 条件に応じて data/kill.flag を書き込み ExecutionEngine 停止を促す

- リサーチ / ファクター
  - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC（Information Coefficient）等の分析ユーティリティ

- AI / NLP
  - news_nlp.py: raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書き込み
  - regime_detector.py: ETF の MA とマクロニュースの LLM 評価を合成して市場レジームを判定

- ポートフォリオ構築
  - portfolio_builder: 候補選定・等配分・スコア加重
  - position_sizing: 株数決定（リスクベース / 等配分 / スコア配分）
  - risk_adjustment: セクター上限適用、レジーム乗数

- ユーティリティ
  - logging_setup: 統一的ログ設定（stdout + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config.py: .env 自動読み込み / Settings クラス（環境変数ラッパ）
  - config_setup.py: .env 対話ウィザード
  - validate_config.py: 起動前に設定と config/*.yaml を検証
  - tools/paper_verification_report.py: paper_trading の検証レポート生成

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローンして作業ディレクトリへ移動

2. Python 仮想環境の作成（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 必要なパッケージをインストール  
   （依存一覧はリポジトリの requirements.txt があればそれを使用。なければ主要パッケージを手動で）

   pip install duckdb psutil openai

   注:
   - PyYAML は config/*.yaml の内容検証に必要（任意）
   - duckdb / psutil / openai は主な依存

4. ディレクトリ作成（ログ / DB / data）

   mkdir -p data logs

   実行スクリプトはデフォルトで以下のパスを使用します（必要に応じて環境変数で上書き可）:
   - data/kabusys.duckdb (DUCKDB_PATH のデフォルト: data/kabusys.duckdb)
   - data/monitoring.db (SQLITE_PATH のデフォルト: data/monitoring.db)
   - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト: data/paper_trading.db)
   - logs/<app_name>.log

5. .env を作成（対話式ウィザード推奨）

   python -m kabusys.config_setup

6. 設定検証

   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）※ monitoring は常に本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- PID_FILE_PATH / KILL_FLAG_PATH: PID ファイル / Kill Flag のパス（必要に応じて指定）

注意:
- config.py はプロジェクトルートにある .env / .env.local を自動的に読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- .env は決して Git にコミットしないでください。

---

## 使い方（主なコマンド例）

- 環境設定ウィザード（.env を生成 / 更新）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  python -m kabusys.run_execution

  動作概要:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録して本番 DB と分離します
  - 起動時に data/stop_requested.flag が存在すると起動を行いません
  - 停止は data/stop_requested.flag を作成することでエンジンに通知されます（または KillSwitch が data/kill.flag を書き込み停止を促す）

- Monitoring を起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring

  オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は常に Settings.sqlite_path（本番監視 DB）を使用します

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチモジュールの利用（プログラム内から呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - kabusys.research.calc_momentum(conn, date), calc_value(), calc_volatility(), calc_forward_returns() 等
  - ポートフォリオ関数: kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes

---

## 停止 / Kill フロー

- run_monitoring.py / run_execution.py は共に `data/stop_requested.flag` を監視しています。システム停止をリクエストする場合、このファイルを作成するとループが終了します。
- KillSwitch（監視側）は条件により `data/kill.flag` を書き込み、ExecutionEngine 側でこれを検出して発注処理を停止する仕組みです。
- KILL_FLAG_CLEAR_ON_START が `1` の場合、ExecutionEngine の起動時に kill.flag を自動削除します（本番では `0` 推奨）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py — 環境変数の読み込み / Settings
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI

- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

- execution/  （発注関連、Engine 実装や OrderManager 等: 省略）
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- monitoring/
  - monitoring_db.py
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
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- data/  （実行時に作成されるファイル例）
  - monitoring.db (デフォルト)
  - paper_trading.db (paper モード)
  - stop_requested.flag
  - kill.flag
  - execution.pid
- logs/  （ログファイルを保存）

---

## 追加情報 / 実運用上の注意

- 監視（Monitoring）は常に本番用 sqlite_path を参照します。Paper Trading を行う際は ExecutionEngine 側で paper_db に分離されるため混同しないように注意してください。
- OpenAI を利用するモジュール（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライ・フェイルセーフ処理が組み込まれていますが、API 使用料には注意してください。
- logging_setup は起動ごとに既存ハンドラをクリアして再設定します。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- process_priority は psutil を使って OS に応じた優先度を設定します。権限不足で設定が失敗することがありますが、その場合は警告ログが出力され処理は継続されます。
- DB の初期化（monitoring_db.init_monitoring_db）は冪等に設計されておりスクリプト起動時に自動で実行されます。

---

この README はプロジェクト内のソースコードに基づいて作成しています。各モジュールの詳細な使い方は該当ファイルの docstring やコメントを参照してください。必要であれば、特定機能（例: ExecutionEngine の API、OrderRepository の仕様、AI スコアリングの詳細など）について別途詳しいドキュメントを作成します。