KabuSys
=======

日本株向け自動売買システムの主要モジュール群とユーティリティをまとめたリポジトリの README です。  
この README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語で説明します。

概要
----
KabuSys は日本株の自動売買（発注エンジン）とそれを支える監視・研究・ポートフォリオ構築・AI（ニュース NLP / レジーム判定）機能を提供するモジュール群です。  
設計方針の例：
- 本番・ペーパートレードを環境変数 KABUSYS_ENV で切替可能（development / paper_trading / live）。
- DB は DuckDB（分析用）と SQLite（監視・履歴用）を併用。
- .env ベースの設定、対話式ウィザードと検証 CLI を備える。
- LLM を使ったニュースセンチメントやレジーム判定を実装（OpenAI クライアントを利用）。
- 監視コンポーネントは kill flag による安全停止、アラート発行、ログ永続化を行う。

主な機能
---------
- ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを切替え、ブローカークライアントを生成して発注を行う。
  - paper_trading 環境では MockBrokerClient と data/paper_trading.db を使用して本番 DB と分離。
  - 起動時にプロセス優先度を "high" に設定。
- Monitoring（監視）起動スクリプト（run_monitoring.py）
  - system / trade / risk の各モニタを定期ポーリングして監視ログを SQLite に記録。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- MonitoringDB（monitoring/monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard のテーブルを管理。冪等に初期化／マイグレーションを行う。
- RiskMonitor / TradeMonitor / SystemMonitor / KillSwitch / MonitoringEngine
  - ドローダウン・ポジション上限などのリスク監視、kill.flag による Engine 停止判定、アラート連携。
- Portfolio モジュール（portfolio/）
  - 候補選定、ウェイト計算、ポジションサイズ計算、セクター制限、レジーム乗数など純粋関数実装。
- Research モジュール（research/）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算など（DuckDB を利用）。
- AI モジュール（ai/）
  - news_nlp: raw_news を集約して OpenAI でセンチメントを算出し ai_scores に記録。
  - regime_detector: ETF の MA 乖離とマクロニュースの LLM スコアを合成して market_regime に書き込み。
- ユーティリティ
  - setup_logging（ログ設定: stdout + 日次ローテートファイル）
  - process_priority（プロセス優先度、CPU affinity 設定）
  - config_setup（.env 対話ウィザード）および validate_config（設定検証 CLI）
- ツール
  - paper_verification_report（ペーパートレード検証レポート出力ツール）

依存関係（例）
--------------
必要最小限の Python パッケージ（実行環境によって追加が必要）：
- duckdb
- psutil
- openai (OpenAI の Python SDK)
- PyYAML（config 検証で YAML 検査をしたい場合）

インストール例：
- 仮想環境を作成してから必要パッケージをインストールしてください。
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. リポジトリをクローンし、Python 仮想環境を用意する。
2. 必要パッケージをインストール（上記参照）。
3. 対話式で .env を作成（推奨）:
   - python -m kabusys.config_setup
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を利用する場合）
     - PAPER_FILL_MODE（paper_trading 時の fill 挙動: instant/partial/never/reject）
4. 設定の検証:
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いになります。

環境変数（主要なもの）
---------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: 監視のポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

使い方（実行例）
----------------

1. .env を用意して検証
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. 監視プロセスを起動（常駐）
   - python -m kabusys.run_monitoring
   - 動作: process priority を high にし、監視ループを開始します。ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で設定（デフォルト 60 秒）。
   - 注意: Monitoring は環境設定にかかわらず本番 sqlite_path を使用して監視ログを保存します（監視ログは本番 DB に保管されます）。

3. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - 起動時、KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します（本番 DB と分離）。
   - 停止方法: data/stop_requested.flag を作成すると run_execution は検知して安全停止を行います。KillSwitch は data/kill.flag を作成して Engine の停止を指示します（監視コンポーネントが条件を満たすと書き込みます）。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（--db で上書き可）

5. AI スコアリング／レジーム判定（コードから呼び出す）
   - ニュース NLP（ai.news_nlp.score_news）:
     - 引数に DuckDB 接続と target_date、api_key（または OPENAI_API_KEY 環境変数）を渡して実行。
   - レジーム判定（ai.regime_detector.score_regime）:
     - DuckDB 接続と target_date、api_key を渡して呼び出す。
   - 例（対話的またはスクリプトから）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(conn, date(2026,4,1), api_key="sk-...")

停止・フラグ
------------
- run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag を監視し、存在を検知するとループを終了します（手動停止用）。
- KillSwitch（監視側）は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります（監視のルールに基づき自動で書き込む）。
- run_execution は data/execution.pid に PID を書く（実装による）。起動前に停止フラグが既にあれば起動しません。

ログ
---
- ロガーは stdout とファイル（logs/<app_name>.log）に出力します。ファイルは日次ローテーション、30 日分保持。
- ログディレクトリは環境変数 LOG_DIR かデフォルト logs/ を使用します。
- setup_logging() を各起動スクリプトが呼び出します（app_name: execution / monitoring）。

簡単なトラブルシューティング
----------------------------
- .env を正しく作成したか python -m kabusys.validate_config で確認してください。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合、warning が出ます。自動作成されるケースもありますが、作成権限を確認してください。
- OpenAI を使う機能は API キーが必要です。キーが無いと ValueError を投げます。
- psutil による優先度設定は権限が必要になることがあります（AccessDenied が発生する場合は警告が出てスキップされます）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"

- 起動スクリプト / 設定
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - config.py              — Settings（.env / 環境変数読み込み・検証）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI

- execution/ (発注関連)  ※実装ファイルは省略（リポジトリに存在）
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py

- monitoring/
  - monitoring_db.py       — SQLite テーブル初期化 / 永続化 API
  - system_monitor.py      — CPU/MEM/DISK/データ鮮度/プロセス監視
  - risk_monitor.py        — ドローダウン・ポジション数監視
  - trade_monitor.py       — 発注ログ監視（滞留注文・価格異常など）
  - monitoring_engine.py   — 各 Monitor を束ねるポーリングエンジン
  - kill_switch.py         — kill.flag 制御
  - alert_manager.py       — （アラート送信の管理）

- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数計算・単元丸め・制約処理
  - risk_adjustment.py     — セクター制限・レジーム乗数

- research/
  - factor_research.py     — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン、IC、summary 等

- ai/
  - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書込み
  - regime_detector.py     — マクロ＋MA を用いた市場レジーム判定

- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - その他ユーティリティ群

- tools/
  - paper_verification_report.py — ペーパートレードの検証レポート

データ / ロック / フラグ（パス）
--------------------------------
- data/monitoring.db              — デフォルト監視 SQLite（Settings.sqlite_path）
- data/paper_trading.db           — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/kabusys.duckdb             — デフォルト DuckDB（Settings.duckdb_path）
- data/kill.flag                  — KillSwitch が書込む停止フラグ
- data/stop_requested.flag        — 起動スクリプトがループ終了に使う停止フラグ
- data/execution.pid              — run_execution が PID を書き込むファイル（実装に依存）

拡張と注意点
--------------
- DuckDB への SQL クエリでテーブル名（prices_daily / raw_financials / raw_news 等）を期待しています。実データを読み込むスクリプトや ETL が別途必要です。
- LLM（OpenAI）を利用する機能は API コストとレスポンスの不確実性を伴います。呼び出しはリトライやフォールバックが組まれていますが、実運用時はキー管理とコスト監視が重要です。
- production（KABUSYS_ENV=live）では kill/alert 設定を慎重に（KILL_FLAG_CLEAR_ON_START=0 推奨）。

ライセンス / 貢献
-----------------
（本 README には記載がありません。必要に応じて LICENSE ファイルや貢献ガイドを追加してください。）

最後に
------
この README はコードベース（主要モジュール）に基づく概要ガイドです。各モジュールの詳細な使い方（API、引数、戻り値、エラー条件）はソースコード内の docstring を参照してください。質問や補足が必要であれば、具体的な用途（例: 実際の起動コマンド、.env の例、AI のテスト方法）を教えてください。必要に応じてサンプル .env の雛形や運用手順を追加で作成します。