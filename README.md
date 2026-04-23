README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。
このリポジトリには、実行エンジン起動スクリプト、監視（Monitoring）コンポーネント、
ポートフォリオ構築／サイズ算出ユーティリティ、リサーチ（ファクター計算・特徴量解析）、
AI ベースのニュースセンチメント／レジーム判定などのモジュールが含まれます。

主な設計方針
- 起動スクリプト群はモジュール化され、logging・DB 初期化・プロセス優先度調整等を統一的に行う。
- Paper trading（ペーパートレード）は本番 DB と分離して専用 SQLite を使用する。
- DuckDB を分析用データベースとして利用。DuckDB 接続を受け取る純粋関数群で分析処理を実装。
- OpenAI を使った NLP 部分（ニューススコアリング / レジーム判定）は API キーを環境変数で設定。
- .env の対話式生成・検証ツールを提供し、起動前チェックを支援する。

機能一覧
--------
- 実行エンジン起動: run_execution.py
  - live / paper_trading / development 環境での起動をサポート
  - Paper trading 時は MockBrokerClient を使い DB を分離
  - ExecutionEngine（スレッド）で発注・整合処理・リスク管理を実行
- 監視（Monitoring）: run_monitoring.py / monitoring_engine.py
  - システム状態（CPU/メモリ/ディスク）、データ鮮度、注文ログ等を定期記録
  - Kill Switch、アラート生成等の連携
- 監視 DB 層: monitoring_db.py（SQLite）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルの作成・操作
- リスク監視: risk_monitor.py（ドローダウン・ポジション数監視）
- ポートフォリオ構築: portfolio/（候補選定、重み算出、ポジションサイズ計算、セクター上限等）
- リサーチ: research/（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール: ai/news_nlp.py（ニュース NLP スコアリング）、ai/regime_detector.py（市場レジーム判定）
- ユーティリティ:
  - 環境設定ウィザード: config_setup.py（.env 対話生成）
  - 設定検証 CLI: validate_config.py（起動前チェック）
  - ログ設定ユーティリティ: utils/logging_setup.py
  - プロセス優先度設定: utils/process_priority.py
  - Paper Trading 検証レポート: tools/paper_verification_report.py

前提・依存
-----------
必須（実行環境により一部はオプション）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- (任意) PyYAML — validate_config の YAML 検証で使用

インストール例（仮）:
pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンしてワークディレクトリへ移動
2. 必要なパッケージをインストール
   - 例: pip install duckdb psutil openai PyYAML
3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードで各環境変数を入力するとプロジェクトルートに .env が生成されます
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります
5. データディレクトリとログディレクトリの確認
   - デフォルト DB / ファイル:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログ: logs/
   - 必要なら .env で DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR を上書き
6. OpenAI を使う場合:
   - 環境変数 OPENAI_API_KEY を設定（.env に保存可）

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 設定:
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時)
- OPENAI_API_KEY: AI 機能利用時に必須
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL

使い方（起動 / コマンド）
------------------------
- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading モード（MockBrokerClient、別 DB）
  - 起動時に data/stop_requested.flag が存在すると起動しません
  - 実行中は data/execution.pid（デフォルト）を作成します
  - 強制停止: data/stop_requested.flag を作成して待つ（スレッド停止処理が入ります）
  - Kill Switch によって data/kill.flag が作成されると ExecutionEngine 側で停止されます

- 監視（Monitoring）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）
  - 監視は本番 sqlite_path を常に参照（環境にかかわらず）
  - 停止: data/stop_requested.flag を作成することで監視ループが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可能

- AI 機能（ニュース NLP / レジーム判定）
  - ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください

停止・フラグ管理
----------------
- stop_requested.flag: run_execution.py / run_monitoring.py の停止監視に使用するファイル（data/stop_requested.flag）
  - このファイルが存在すると両スクリプトは安全に終了します
- kill.flag: KillSwitch が書き込み、ExecutionEngine に停止シグナルを送ります（デフォルト path は Settings.kill_flag_path）
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数・設定読み込みロジック（.env 自動読み込み）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py         — SQLite テーブル初期化・読み書き層
- system_monitor.py        — システム状態・データ鮮度監視
- trade_monitor.py         — （注文ログ監視）※（ファイルには一部のみ含まれている想定）
- risk_monitor.py          — ドローダウン・ポジション上限監視
- kill_switch.py           — kill.flag 書込ロジック
- monitoring_engine.py     — モニタ群の統合ループ
- alert_manager.py         — （アラート送信管理）※別ファイル想定

src/kabusys/execution/
- execution_engine.py      — 実行エンジン本体（EngineConfig / run_session）
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py
- broker_factory.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py              — ニュースを OpenAI でスコア化
- regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント合成）
- __init__.py

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- logging_setup.py         — ログ設定ユーティリティ
- process_priority.py      — プロセス優先度 / CPU affinity

ログ
----
- デフォルトは logs/<app_name>.log（日次ローテーション、30日分保持）
- setup_logging でログディレクトリ/レベルを制御（環境変数 LOG_DIR / LOG_LEVEL も参照）
- コンソール出力は stdout に出力されます

開発者への注意点 / 補足
-----------------------
- .env は決して Git にコミットしないでください（config_setup のヘッダにも明記）。
- validate_config は起動前チェックとして必ず実行すること（特に本番起動時）。
- Paper trading は本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- AI 関連は外部 API（OpenAI）に依存し、料金が発生します。API キーの管理に注意してください。
- DuckDB の SQL 実行や各分析関数は外部 DB スキーマ（prices_daily / raw_financials 等）を前提としています。データ挿入手順は別途用意してください。

ライセンス・著作権
-----------------
この README ではライセンス情報を示していません。実際のプロジェクト配布時は LICENSE ファイルを追加してください。

お問い合わせ
------------
このコードベースについての疑問や改善提案はリポジトリ管理者へご連絡ください。