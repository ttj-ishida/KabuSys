KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した Python パッケージです。  
ファクター計算・ポートフォリオ構築、発注エンジン（ExecutionEngine）および監視（Monitoring）、
さらにニュースの LLM ベースセンチメント評価などを含むモジュール群で構成されています。

主な特徴
--------
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター上限・レジーム乗数）
- 発注エンジン（本番 / ペーパートレード切替、リスク管理、注文管理）
- 監視（システム稼働率、データ鮮度、滞留注文、ドローダウン監視、Kill Switch）
- DuckDB / SQLite を用いたデータ管理と永続化レイヤ
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメントスコア生成）
- 各種 CLI: 環境設定ウィザード、設定検証、Paper Trading レポート生成 等
- ロギングの統一設定（stdout と日次ローテーションファイル）

セットアップ
-----------
1. Python 環境の準備（推奨: Python 3.10+）
2. 依存パッケージをインストール
   - 必要な主なライブラリ: duckdb, psutil, openai, (PyYAML は設定検証用)
   - 例:
     pip install -r requirements.txt
     （requirements.txt が無い場合は上記ライブラリを個別にインストール）

3. プロジェクトルートに .env を作成
   - 対話式ウィザードを利用すると簡単です:
     python -m kabusys.config_setup
   - 自動ロード: kabusys.config.Settings はデフォルトでプロジェクトルートの .env ／ .env.local を読み込みます。
   - 自動ロードを無効化するには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定の検証（必須環境変数やファイルパスのチェック）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗扱いになります。

5. データ / ログディレクトリ
   - デフォルトの DB / ログ:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視用): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/（日次ローテーションで <app_name>.log）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / LOG_DIR を上書きしてください。
   - ログディレクトリは setup_logging() が起動時に自動作成します。失敗した場合はコンソールログのみになります。

主な環境変数（代表）
-------------------
- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API 用トークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH — DB ファイルパス
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 本番での自動 Kill Flag クリア（0/1、デフォルト 0）

使い方（主要コマンド）
--------------------

- 環境設定ウィザード（.env の作成・更新）
  python -m kabusys.config_setup

- 設定検証（.env と config/*.yaml のチェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper_trading 用 DB に記録します。
  - 停止制御:
    - 起動中に data/stop_requested.flag を作成すると起動しない / 実行中に検知して停止します。
    - 実行時の PID は data/execution.pid に保存されます（設定で変更可）。

- Monitoring を起動（ポーリングループ）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でループ間隔を上書きできます（秒。デフォルト: 60）。
  - 監視は常に本番 sqlite_path を参照して状態を書き込みます（環境に依存せず監視 DB を使う設計）。
  - 停止は data/stop_requested.flag を作成して検知できます。

- Paper Trading 検証レポート生成（ツール）
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション --db で SQLite パスを指定できます（デフォルト: PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。

- AI 関連（プログラム API）
  - ニュース NLP（銘柄別センチメント）:
    from kabusys.ai import score_news
    score_news(conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai import regime_detector
    regime_detector.score_regime(conn, target_date, api_key=...)

停止 / Kill Switch
------------------
- ExecutionEngine に対する「緊急停止（Kill Switch）」は data/kill.flag で行います。KillSwitch クラスは
  リスクアラート（ドローダウン超過やポジション上限超過）を検出したときにこのファイルを書き込みます。
- stop_requested.flag（data/stop_requested.flag）を作成すると run_execution / run_monitoring のループが安全に終了します。

ログ
----
- 共通ログ設定は kabusys.utils.logging_setup.setup_logging で行われます。
- stdout （StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）に出力されます。
- ログレベルは LOG_LEVEL 環境変数、または setup_logging の引数で制御します。

ディレクトリ構成（概要）
----------------------
（プロジェクトルートの src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・.env の自動読み込みと Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                — 発注エンジン関連（BrokerFactory, Engine, OrderManager, RiskManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/                     — データ処理 / pipeline（DuckDB を想定）
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

補足・運用上の注意
-----------------
- KABUSYS_ENV の値によって挙動が切り替わります（development, paper_trading, live）。
  live を使う際は LINE 通知設定や各種シークレットを確実に設定し、validate_config でチェックしてください。
- OpenAI 関連機能を使うには OPENAI_API_KEY が必要です。API 呼び出しは再試行ロジックを持ちますが、失敗時はフェイルセーフで継続する実装が多く採用されています。
- DB スキーマのマイグレーションは init_monitoring_db 等で簡単な互換処理を実施しますが、本格的な移行は別途注意が必要です。
- process_priority.set_process_priority() により起動時にプロセス優先度を高く設定しようとしますが、権限により失敗することがあります（ログに警告）。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（開発版）

以上。運用やセットアップで不明点があれば、実際の環境（OS、Python バージョン、使用する Broker）を教えてください。用途に応じた運用手順の補足や systemd / supervisor 用のサービスファイル例も作成できます。