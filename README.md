README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは取引エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、リサーチ／ポートフォリオ構築、AI を使ったニュース解析などのユーティリティ群を提供します。設計方針として本番／ペーパートレードの分離、ログ・DB の永続化、LLM 呼び出しでの堅牢なリトライ処理やフェイルセーフを重視しています。

主な機能
--------
- ExecutionEngine（発注エンジン）
  - 実口座（live）／ペーパートレード（paper_trading）切替サポート
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler 等による発注と整合性管理
- Monitoring（監視）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度監視）
  - TradeMonitor（発注・約定ログチェック）※実装参照
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（危険検知時に data/kill.flag を書き込み Execution を停止）
  - MonitoringEngine によるポーリングループ・アラート発行
- Portfolio（ポートフォリオ構築）
  - 候補抽出、等重・スコア重み付け、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research（リサーチ）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ
- AI / LLM ユーティリティ
  - ニュースのセンチメント（news_nlp）を OpenAI（gpt-4o-mini 等）でスコア化して ai_scores に格納
  - 市場レジーム判定（regime_detector）で MA とマクロセンチメントの合成判定
- ツール
  - config_setup: 対話式 .env 作成ウィザード
  - validate_config: 起動前チェック（環境変数・YAML ファイル・DB パス等）
  - paper_verification_report: ペーパートレードの検証レポート生成

前提 / 必要要件
---------------
- Python 3.9+
- 必要な主要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に使用）
- SQLite（標準ライブラリで対応）
- ネットワーク接続（OpenAI を利用する場合）

インストール（例）
-----------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要ライブラリをインストール（プロジェクトに requirements.txt がない場合は手動で）
   - pip install duckdb psutil openai PyYAML

設定（.env）
-----------
プロジェクトルートの .env / .env.local から自動ロードされます（OS 環境変数より後で読み込まれます）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

代表的な環境変数（例・デフォルト）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db) — Monitoring は常に本番 sqlite_path を参照
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 時の専用 DB
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID （任意、アラート用）
- KILL_FLAG_CLEAR_ON_START (0|1) — 本番で 1 は危険（Kill Switch の自動クリア）

設定ウィザード（対話式）
--------------------
初回セットアップには対話式ウィザードを推奨します:
- python -m kabusys.config_setup
実行後に .env ファイルが生成されます（Git にコミットしないでください）。

設定検証
--------
起動前に設定の簡易チェックを行えます:
- python -m kabusys.validate_config
厳格モード（警告も失敗扱い）:
- python -m kabusys.validate_config --strict

使い方（起動例）
----------------
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 補足: ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとループを抜けます。

- Execution エンジンを起動
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録され本番と分離されます。
  - 停止: data/stop_requested.flag または kill.flag の影響で停止します。実行中は PID を data/execution.pid に書きます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

ログ
---
- 共通のログ初期化ユーティリティにより stdout と日次ローテートファイル（logs/<app_name>.log）へ出力します。
- LOG_DIR 環境変数でログディレクトリを変更可能。デフォルトは logs/。

停止・Kill Switch
-----------------
- 手動停止フラグ: プロジェクトルートの data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了または停止処理を行います。
- 自動停止（Kill Switch）: RiskMonitor 等が危険判定をした場合に data/kill.flag を書き込み、ExecutionEngine に停止要求を送ります。KillSwitch は冪等に書き込みを行います。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要なモジュール・パッケージです（ファイル名は一部抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理（.env 自動ロード）
  - config_setup.py          — .env 対話式ウィザード
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
    - trade_monitor.py  (参照実装)
    - kill_switch.py
    - alert_manager.py  (参照実装)
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
  - utils/
    - logging_setup.py
    - process_priority.py

補足・運用メモ
--------------
- DB ファイル:
  - 監視用 SQLite: settings.sqlite_path（デフォルト data/monitoring.db）
  - DuckDB(分析): settings.duckdb_path（デフォルト data/kabusys.duckdb）
  - ペーパートレード: settings.paper_sqlite_path（data/paper_trading.db）
- 監視プロセスは settings.kill_flag_path（デフォルト data/kill.flag）を使って Execution 停止を指示します。
- Settings クラスは必須環境変数の未設定時に ValueError を送出するため、実行前に validate_config を実行しておくことを推奨します。
- OpenAI など外部 API を使う機能は API キーが必須です（OPENAI_API_KEY）。

ライセンス / 注意事項
--------------------
- .env は機密情報を含むため、絶対に Git 等にコミットしないでください。
- 本ソフトウェアは投資助言を提供するものではありません。実運用を行う場合は十分な検証と安全対策を行ってください。

以上。必要に応じて README に加えたい項目（例: systemd unit ファイル例、具体的な設定例、requirements.txt）を指示してください。