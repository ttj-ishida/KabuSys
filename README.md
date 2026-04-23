# KabuSys — README (日本語)

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたパッケージです。  
本リポジトリには以下の主要機能を持つコンポーネントが含まれます。

- 発注エンジン（ExecutionEngine）: ブローカークライアントを介した発注・注文管理・リスク監視
- 監視（Monitoring）: システム状態・注文状況・リスク監視と Kill Switch
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイジング、セクター制約など
- リサーチ/ファクター計算: モメンタム / ボラティリティ / バリュー等の計算（DuckDB を想定）
- AI モジュール: ニュース NLP（OpenAI）によるセンチメントスコア化、レジーム判定
- ツール: ペーパートレード検証レポート生成等
- 設定ユーティリティ: .env 生成ウィザード、設定検証 CLI
- ログ、プロセス優先度などのユーティリティ

主な特長
--------
- 環境（development / paper_trading / live）に応じた挙動切替
  - paper_trading: Mock ブローカーを使い、発注データは data/paper_trading.db に記録（本番 DB と分離）
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB に利用
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント・レジーム判定機能（API キー必須）
- Kill Switch（data/kill.flag）による安全停止、監視コンポーネントからの自動フラグ書き込み
- ログはコンソールと日次ローテーションファイル（logs/<app>.log）に出力

必要条件（主な依存パッケージ）
----------------------------
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config 検証で YAML パースを行う場合）
- （インストール方法はプロジェクトの requirements.txt があればそちらを参照）

セットアップ手順
----------------

1. リポジトリをクローンしてワークディレクトリへ移動

   git clone <repo>
   cd <repo>

2. 仮想環境作成・有効化（推奨）

   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を推奨）

4. .env ファイルの初期作成（対話式ウィザード）

   python -m kabusys.config_setup

   ウィザードは .env（デフォルト）に必要な環境変数を出力します。重要な必須項目:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   （OpenAI を使う場合は OPENAI_API_KEY を環境に設定してください）

5. 設定検証

   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict

環境変数（主要）
----------------
- KABUSYS_ENV: 実行環境（development | paper_trading | live）  
  - paper_trading の場合は MockBroker を利用し data/paper_trading.db に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60） — run_monitoring で参照
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 他: 実行・監視関連設定

使い方（主なスクリプト / コマンド）
---------------------------------

- 監視ループ起動（SystemMonitor を定期実行）
  python -m kabusys.run_monitoring

  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（例: export MONITOR_POLL_INTERVAL=30）。  
  監視は常に本番の sqlite_path を使用します（環境に依らず監視 DB を共通利用）。

- 発注エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution

  KABUSYS_ENV=paper_trading のときは MockBroker を使い発注は data/paper_trading.db に記録されます。  
  起動時に data/stop_requested.flag が存在すると起動をスキップします。停止は同ファイル作成で行います。

- 設定ウィザード（.env の作成/更新）
  python -m kabusys.config_setup

- 設定検証（.env / config/*.yaml の検証）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで SQLite ファイルを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。

AI 関連（ニュース NLP / レジーム判定）
--------------------------------------
- AI 機能は OpenAI API を利用します。API キーは OPENAI_API_KEY 環境変数で指定してください。
- ニュースセンチメント: kabusys.ai.news_nlp.score_news (DuckDB 接続と target_date を与えて実行)
- レジーム判定: kabusys.ai.regime_detector.score_regime

ログ / ローテーション
--------------------
- logging_setup.setup_logging を起動スクリプトで呼び出し、コンソール（stdout）と日次ファイル出力（logs/<app>.log）を初期化します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/。存在しない場合は作成を試みます。

停止 / Kill Switch
-----------------
- 実行中の Engine を外部から停止する方法:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のメインループが検知して終了します（run_execution はスレッド停止処理を行います）。
  - KillSwitch（自動）: 監視コンポーネントが条件（ドローダウン超過等）を満たすと data/kill.flag を作成し ExecutionEngine を停止させます。
- Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

ディレクトリ構成（概要）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数/設定読み込み・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py       — ロギング初期化ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py       — SQLite 読み書きレイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py      — システム状態・データ鮮度のチェック
  - trade_monitor.py       —（注文監視ロジック）※コード断片では省略
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — フラグファイルでの停止制御
  - monitoring_engine.py   — 複数モニタの統合ポーリング
  - alert_manager.py       —（アラート送信ロジック）※コード断片では省略
- execution/
  - execution_engine.py    — 発注エンジン本体（EngineConfig, run_session 等）
  - order_manager.py
  - order_repository.py
  - broker_factory.py      — ブローカークライアント生成（Mock を含む）
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py   — 候補選定、重み付け
  - position_sizing.py     — 株数決定、投下金額スケーリング
  - risk_adjustment.py     — セクターキャップ、レジーム乗数
- research/
  - factor_research.py     — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ等
- ai/
  - news_nlp.py            — ニュースセンチメント（OpenAI）処理
  - regime_detector.py     — 市場レジーム判定
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- monitoring/...           — 監視周りコンポーネント群
- その他: data/（DB・flag・pid ファイル）、logs/（出力ログ）

注意事項 / 運用上のガイド
-----------------------
- .env は機密情報を含むため、絶対にリポジトリへコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリアや設定値に注意してください（validate_config で警告あり）。
- OpenAI API 呼び出しはコストが発生します。rate-limit/エラー処理は実装されていますが、運用時はキーと呼び出し頻度に注意してください。
- DuckDB / SQLite のファイルはバックアップ・排他制御（複数プロセスの同時書き込み）に注意して運用してください。

バージョン
----------
パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。

サポート・拡張
--------------
- 新しい戦略やブローカーを追加する場合は execution/broker_factory.py や execution モジュールを拡張してください。
- DuckDB 上のデータスキーマ（prices_daily / raw_financials / raw_news 等）に沿ってリサーチ関数は動作します。データ投入のためのパイプラインは別途実装してください。

以上。必要であれば README にサンプル .env テンプレートや起動例（systemd / cron 用）を追記できます。どの情報を追加したいか教えてください。