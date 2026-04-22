KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株の自動売買・バックオフィス・監視・リサーチ機能を備えた小規模なトレーディングフレームワークです。本リポジトリは以下の主要機能群を含みます。

- 発注実行エンジン（ExecutionEngine）とブローカークライアント抽象化（実運用 / ペーパートレードの分離）
- 監視サブシステム（System / Trade / Risk のモニタリング、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助機能（ニュース NLP によるセンチメント、レジーム判定）
- 簡易ツール（ペーパー検証レポート生成など）
- 環境設定ウィザード・設定検証 CLI

主な機能一覧
-------------
- run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に記録して本番 DB と分離。
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照。
- monitoring/*: MonitoringDB（SQLite）を中心とした永続化、System/Trade/Risk モニタ、KillSwitch、AlertManager 統合（MonitoringEngine）。
- portfolio/*: 候補選定、等重／スコア重み、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ算出（単元丸め、aggregate cap）。
- research/*: DuckDB 接続を使ったファクター計算（モメンタム、ボラティリティ、バリュー）、将来リターン、IC 計算、統計サマリー。
- ai/*: OpenAI（gpt-4o-mini）を用いたニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。API エラー時はフェイルセーフで継続。
- tools/paper_verification_report.py: ペーパートレード DB から稼働率・約定率・レイテンシなどを集計し PASS/FAIL 判定を出力するツール。
- config_setup.py: 対話式 .env 作成ウィザード。
- validate_config.py: .env と config/*.yaml の事前検証 CLI。
- utils: ロギング設定（ログファイル日次ローテーション）とプロセス優先度設定ユーティリティ。

セットアップ手順
----------------
前提
- Python 3.9+（duckdb/openai 等の互換性に応じて調整）
- Git, SQLite（標準ライブラリ）、任意で systemd/cron 等

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - 追加（任意）: PyYAML（validate_config の YAML 検証用）
     - pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数ファイルを作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（下の「重要な環境変数」を参照）

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合: python -m kabusys.validate_config --strict

6. データディレクトリ準備
   - デフォルトでは data/ 以下を使用します。必要に応じて .env のパスを調整してください。
   - 監視・PID・フラグファイル: data/execution.pid, data/kill.flag, data/stop_requested.flag など

重要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。paper_trading は DB を分離。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 向け）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp, ai/regime_detector で使用）
- LOG_LEVEL: ログ出力レベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 監視・Kill Switch 関連

使い方（主要スクリプト）
------------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup
    - 対話形式で .env を生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
    - .env の必須変数や config/*.yaml の存在・YAML パース（PyYAML がインストールされている場合）を確認します。

- 実行エンジン起動（本番／ペーパー共通）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は paper DB を使います。
    - 起動時に data/stop_requested.flag が既に存在すると起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます。停止には data/stop_requested.flag の作成や Kill Switch を利用します。

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定できます（秒）。
    - 監視は常に Settings.sqlite_path（本番監視 DB）を使います。

- AI / レジーム / ニュース
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - これらは DuckDB コネクションを受け取り DB のテーブルを参照／更新します。
    - OPENAI_API_KEY を環境変数にセットするか、api_key を渡してください。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

運用上の注意
-------------
- KABUSYS_ENV=live の場合は特に .env の値に注意してください（validate_config は注意喚起します）。
- Kill Switch:
  - KillSwitch はリスク条件（ドローダウン、ポジション上限）で data/kill.flag を書き、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を全スクリプトが使用します。log_dir（LOG_DIR 環境変数）に日次ローテートでログを保存します。
- ペーパートレード:
  - paper_trading モードでは MockBrokerClient が使用され、データは paper_sqlite_path に記録されます（本番 DB と完全分離）。
- OpenAI 呼び出し:
  - API の失敗（429 / タイムアウト / 5xx）にはエクスポネンシャルバックオフでリトライします。失敗時はフェイルセーフ（スコア 0 や処理スキップ）で続行します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数 / Settings 管理（自動 .env ロードを含む）
- config_setup.py           — .env 対話式ウィザード
- validate_config.py        — 設定検証 CLI
- run_execution.py          — ExecutionEngine 起動スクリプト
- run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py        — 共通のログ設定
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py        — （ファイルは repo に含まれる想定）
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py        — （実装ありならアラート送信のハンドラ）
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
- execution/                 — ExecutionEngine, BrokerFactory, OrderManager 等（別ディレクトリに各実装）
- data/                      — 実行時に利用される DB / フラグ / PID（data/ 以下を想定）

（備考）リポジトリの一部モジュールは参照のみで完全実装が別ファイルに分かれている場合があります。実運用には ExecutionEngine・Broker クライアント等の実実装が必要です。

ライセンス・貢献
----------------
この README はコードベースからの要点をまとめたものです。実リポジトリには LICENSE ファイルや CONTRIBUTING.md がある場合がありますので、それらを参照してください。

サンプル .env (最小)
-------------------
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

最後に
------
実際に運用する前に必ず python -m kabusys.validate_config で設定を検証し、ペーパートレード環境で十分なテストを行ってください。質問や補足があれば実行例や具体的なユースケースに合わせて README を拡張します。