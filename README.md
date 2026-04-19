README
======

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。本リポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュース NLP を使ったセンチメント評価、ペーパートレード検証レポート等のユーティリティを含みます。設計方針としては以下を重視しています。

- 本番／ペーパートレードを環境変数で分離（データベースやブローカークライアントを切替）
- DuckDB を分析用に、SQLite を運用ログ／監視用に使用
- LLM 呼び出しは失敗に強く、リトライやフォールバックを用意
- CLI ツールで .env のウィザード／設定検証／レポート生成を提供

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用の DB に分離。
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応。
- Monitoring（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を呼び、状態を SQLite に記録。
  - Kill Switch により重大アラート時に Execution を停止可能。
  - MONITOR_POLL_INTERVAL によるポーリング間隔制御（デフォルト 60 秒）。
- ai モジュール
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores に保存。
  - regime_detector: ETF（1321）の MA とマクロニュースセンチメントを合成して市場レジーム判定し永続化。
- portfolio モジュール
  - 候補選定・重み計算（等配分・スコア重み）、セクターキャップ適用、ポジションサイズ計算（単元丸め・リスク制限反映）。
- research モジュール
  - ファクター（モメンタム / ボラティリティ / バリュー）計算や将来リターン、IC 計算など研究用関数群（DuckDB 接続で動作）。
- ユーティリティ
  - config_setup.py: .env を対話式に作成 / 更新するウィザード。
  - validate_config.py: .env と config/*.yaml を起動前に検証する CLI。
  - tools.paper_verification_report: ペーパートレードの検証レポート生成。

前提 / 依存
-----------
最低限の想定環境例:
- Python 3.10+
- 必須ライブラリ（実行に必要）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
- 開発 / 補助:
  - PyYAML（validate_config の YAML 検証に使用。無くても実行可能だが警告が出ます）
- SQLite（標準ライブラリに含まれるため通常不要）

セットアップ手順
----------------
1. リポジトリをクローンして、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 依存ライブラリをインストールします（requirements.txt がある場合）。
   - pip install -r requirements.txt
   - もしくは最低限:
     - pip install duckdb psutil openai

3. .env を作成します（ウィザード推奨）。
   - python -m kabusys.config_setup
     - 対話式で J-Quants トークン、kabu API パスワード、環境（KABUSYS_ENV）等を設定できます。
   - 作成後、設定を検証:
     - python -m kabusys.validate_config
     - エラーがあれば修正してください。--strict を付けると警告も失敗扱いになります。

主要な環境変数（抜粋）
---------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API のパスワード
- 環境切替:
  - KABUSYS_ENV: execution 環境 ("development" | "paper_trading" | "live"), デフォルト "development"
    - paper_trading の場合、BrokerClient はモックを使用し DB は data/paper_trading.db に分離されます
- DB / ファイル:
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用ファイル（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効。デフォルト "0"）
- ログ:
  - LOG_LEVEL: ログレベル（"DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"、デフォルト "INFO"）
  - LOG_DIR: ログ保存先（デフォルト logs/）
- Monitoring:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- Paper Trading 挙動:
  - PAPER_FILL_MODE: "instant" | "partial" | "never" | "reject"（デフォルト "instant"）
- OpenAI:
  - OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で利用）

使い方（起動 / CLI）
-------------------
- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整可（例: export MONITOR_POLL_INTERVAL=30）

- 実行エンジン起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録します。

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

停止 / Kill Switch / 停止フラグ
------------------------------
- graceful stop:
  - 監視・実行プロセスはプロジェクトルート/data/stop_requested.flag を検出するとループを抜けて終了します（各 run_*.py が参照）。
- Kill Switch:
  - RiskMonitor 等の判定で KillSwitch がトリガーした場合、data/kill.flag が書き込まれ、ExecutionEngine 側が起動中であれば停止を受けます。
  - KILL_FLAG_CLEAR_ON_START を "1" にすると起動時に kill.flag を自動でクリアします（本番では推奨しません）。

ログ
----
- logging_setup が共通のログ設定を提供します（コンソール stdout + 日次ローテートファイル logs/<app_name>.log）。
- app_name は起動スクリプトで指定（例: setup_logging(app_name="execution")）。

ライブラリ / API 概要（開発者向け）
--------------------------------
- kabusys.config: .env 自動読み込み、環境変数のラッパー Settings。
- kabusys.monitoring:
  - monitoring_db: SQLite テーブル定義・CRUD ラッパー（MonitoringDB）。
  - system_monitor: システム状態・データ鮮度チェック（psutil、DuckDB からの最新日チェック）。
  - risk_monitor, trade_monitor, monitoring_engine, kill_switch, alert_manager（アラート送信ロジックは別に実装）。
- kabusys.execution: ExecutionEngine、OrderManager、RiskManager 等（発注ロジックは execution 配下）。
- kabusys.portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数。
- kabusys.research: DuckDB を使ったファクター計算（モメンタム / ボラティリティ / バリュー）や IC、統計サマリ。
- kabusys.ai: news_nlp（OpenAI を使った銘柄センチメント）、regime_detector（市場レジーム判定）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルの抜粋です（完全な一覧はリポジトリを参照してください）。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・.env ロード / Settings
  - config_setup.py           — .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - execution/                — 発注・リスク管理関連
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - trade_monitor.py (参照)
    - alert_manager.py (参照)
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

補足・運用メモ
--------------
- データベースのパス（DuckDB / SQLite）は .env で変更可能。デフォルトは data/ 以下に保存します。
- run_execution/run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限不足で失敗しても警告に留めます。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須です。キー未設定時は ValueError を送出する箇所があります。
- YAML パースや OpenAI SDK の互換性等により、実行環境のライブラリバージョンに依存する部分があります。CI / 運用環境では requirements を固定しておくことを推奨します。

貢献 / 開発
-----------
- 新機能追加やバグ修正は Pull Request を通してください。
- 重要: .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- テストや CI の整備は歓迎します。AI 呼び出し部分はモックやパッチで置き換え可能な設計になっています。

以上。README に記載の手順でセットアップ・起動を行い、まずは config_setup → validate_config → python -m kabusys.run_monitoring / run_execution を順に試すことを推奨します。