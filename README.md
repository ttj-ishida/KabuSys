README
======

概要
----
KabuSys は日本株向けの自動売買システムの骨格を提供する Python コードベースです。本リポジトリは次を目的としています:

- シグナル生成・ポートフォリオ構築・ポジションサイズ計算（純粋関数）
- 注文発行・注文管理・リスク制御を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働監視・トレード監視・リスク監視と Kill Switch（自動停止）機構
- DuckDB / SQLite を利用した分析・永続化
- LLM（OpenAI）を使ったニュースセンチメントや市場レジーム判定のためのユーティリティ
- ペーパートレード結果の検証レポート出力ツール

主な特徴
--------
- ExecutionEngine: 実際の注文 API（kabuステーション）またはペーパートレード用の MockBrokerClient を切り替え可能
- 監視機能: SystemMonitor / TradeMonitor / RiskMonitor と KillSwitch による自動停止・アラート
- 設定管理: .env 自動読み込み、対話式ウィザード（config_setup）と起動前検証（validate_config）
- 研究用ツール: DuckDB 接続でファクター計算・特徴量解析（research モジュール）
- AI 支援: ニュースの NLP スコアリング、マクロセンチメントによるレジーム判定（OpenAI 利用）
- ロギング: 統一的なログ設定（コンソール + 日次ローテーティングファイル）

必須 / 推奨依存パッケージ
------------------------
主に利用するパッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の検証を行う場合に必要）
- （標準ライブラリ: sqlite3, logging, threading, datetime など）

インストール例（仮）
- 仮想環境を作成して依存をインストールします（requirements.txt を用意している前提）。
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt

セットアップ手順
--------------
1. プロジェクトルートに移動（この README のある場所）
2. .env の初期作成（対話式ウィザード）
   python -m kabusys.config_setup
   ウィザードに従い必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力します。
3. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。
4. 必要に応じてデータディレクトリを作成（デフォルトでは data/ や logs/）
   mkdir -p data logs

主要な環境変数（抜粋）
---------------------
（.env で設定 / config_setup で生成）

必須（少なくとも値を設定すること）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

主要な任意・挙動制御変数
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - paper_trading のときは MockBrokerClient を使い、ペーパートレード専用 DB に記録します。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp, regime_detector）で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0|1）

自動 .env ロード
- プロジェクトルートに .env / .env.local がある場合、自動で環境変数へ読み込みます。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

運用に関するファイル（フラグ / PID）
- data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine はこの存在を検知して停止）
- data/stop_requested.flag: 開発用の外部停止フラグ（run_monitoring/run_execution が監視している）
- data/execution.pid（デフォルト）: ExecutionEngine の PID ファイル

よく使うコマンド / 使い方
-----------------------

1) 設定ウィザード（対話式）:
   python -m kabusys.config_setup

2) 設定検証:
   python -m kabusys.validate_config
   厳密モード:
   python -m kabusys.validate_config --strict

3) ExecutionEngine 起動（本番 or paper_trading によって挙動切替）
   - 通常:
     python -m kabusys.run_execution
   - 環境を切り替えて起動（例: ペーパートレード）
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   実行時は設定された SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を参照します。起動時に data/stop_requested.flag が存在すると起動せず終了します。

4) 監視ループ起動（SystemMonitor のポーリング）
   python -m kabusys.run_monitoring
   - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
   - 監視は本番用 sqlite_path を常に参照します（KABUSYS_ENV に依存しない）。
   - 停止は data/stop_requested.flag を作成することで実施できます。

5) ペーパートレード検証レポート生成:
   python -m kabusys.tools.paper_verification_report
   期間指定例:
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   データベース指定:
   python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
   もしくは環境変数 PAPER_TRADING_SQLITE_PATH を設定します。

6) AI 系機能（プログラムから呼び出し）
   - ニューススコアリング:
     from kabusys.ai.news_nlp import score_news
     score_news(duckdb_conn, target_date, api_key="…")
   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key="…")

監視・停止の仕組み（運用メモ）
-----------------------------
- Monitoring 系は MonitoringDB（SQLite）に system_status / trade_logs / risk_logs / positions / dashboard を保持します。
- RiskMonitor が DRAWDOWN / POSITION_LIMIT を検知すると risk_logs に記録し、KillSwitch が条件を満たすと data/kill.flag を書き込みます。
- ExecutionEngine は起動中に kill.flag の存在を監視し、存在時に安全に停止します。
- 開発時は data/stop_requested.flag を作成することで run_monitoring/run_execution を外部から停止できます（監視スクリプトも同フラグを見ます）。

データベース（monitoring）スキーマ（要約）
----------------------------------------
monitoring_db モジュールで作成されるテーブル（冪等で作成）:
- system_status: recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs: logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions: code (PK), qty, avg_price, current_price, updated_at
- risk_logs: logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard: id=1 の集計行 (portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 起動前設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ（主要ファイル）
- ai/
  - news_nlp.py            — ニュース NLP スコアリング
  - regime_detector.py     — 市場レジーム判定
- monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py       — （ファイルはこの README の抜粋に含まれていませんが存在を想定）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py       — 通知管理（抽象・実装）
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
- tools/
  - paper_verification_report.py

（上記は本リポジトリの主要モジュールを抜粋した構成です）

開発上の注意 / ポイント
-----------------------
- KABUSYS_ENV に応じて挙動が変わります。特に live（本番）では kill flag の自動クリアなど危険な設定を避けてください。
- .env は決してリポジトリにコミットしないでください（config_setup.py のヘッダにも明示）。
- OpenAI API を利用する機能は API キーとコストに注意して運用してください。API エラー時はフォールバックやレトライ処理が入っていますが、キー未設定では ValueError を送出します。
- run_execution / run_monitoring ではプロセス優先度を最初に "high" に上げようとします（psutil による設定、権限がない場合は警告にとどまります）。
- DuckDB / SQLite のパスはデフォルトで data/ 以下を使います。権限やディスク容量に注意してください。
- test 用に各種内部関数はモック可能（_call_openai_api などを patch してテストできます）。

ライセンス / 貢献
-----------------
本 README はコードベースの説明用です。実際のライセンスや貢献ルールはリポジトリルートの LICENSE / CONTRIBUTING を参照してください。

補足
----
- この README はリポジトリ内のソースから抜粋して要点をまとめたものです。詳しい挙動や追加の CLI オプションは各モジュールの docstring や実装を参照してください。