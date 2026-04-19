README
=====

概要
----
KabuSys は日本株の自動売買および研究支援を目的としたモジュール群です。  
主な機能は以下の通りです: シグナルからポートフォリオ構築・ポジションサイズ計算、発注実行エンジン、監視（監視ログ・アラート・Kill Switch）、ファクター計算・リサーチ、ニュースの NLP によるセンチメント評価、ペーパートレード検証ツールなど。

本リポジトリはパッケージ化された Python モジュール群（src/kabusys 以下）で構成されており、設定は .env で行います。DuckDB/SQLite を利用したデータ保存、OpenAI API 連携（ニュース評価 / レジーム判定）などの外部依存があります。

主な機能一覧
--------------
- 環境設定ウィザード:
  - python -m kabusys.config_setup による .env の対話式作成/更新
- 設定検証:
  - python -m kabusys.validate_config による .env と config/*.yaml の事前検証
- 実行エンジン起動:
  - python -m kabusys.run_execution で ExecutionEngine を起動（本番 / ペーパー切替対応）
- 監視ループ起動:
  - python -m kabusys.run_monitoring で SystemMonitor を定期実行（監視ログ保存、Kill Switch 評価等）
- 監視永続化:
  - monitoring_db モジュールにより SQLite に system_status / trade_logs / positions / risk_logs / dashboard を保存
- リスク監視:
  - RiskMonitor によるドローダウン・ポジション上限チェック、risk_logs へ記録
- Kill Switch:
  - 条件を満たすと data/kill.flag を書き込み、実行エンジン停止を促す仕組み
- ポートフォリオ構築:
  - 候補選定（スコアソート）、等ウェイト／スコア加重、リスクベースポジションサイズ計算、セクター制限、レジーム乗数
- 研究用モジュール:
  - ファクター（Momentum/Value/Volatility）計算、将来リターン計算、IC 計算、統計サマリー
- ニュース NLP / レジーム判定:
  - OpenAI（gpt-4o-mini）によるニュースセンチメント評価（ai.news_nlp）、マクロ + ETF MA による市場レジーム判定（ai.regime_detector）
- ツール:
  - paper_trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 記法などを使用）
- SQLite（組み込み）、DuckDB（パッケージで導入）
- OpenAI API を利用する場合は API キー（OPENAI_API_KEY）が必要

1. リポジトリを取得
   - git clone ...（プロジェクトルートを作成）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 以下は最低限の例です。プロジェクトに requirements.txt がある場合はそちらを利用してください。
     - pip install duckdb psutil openai
     - PyYAML は config/*.yaml のパース検証（validate_config）で必要: pip install pyyaml

4. 環境変数 / .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 主要な環境変数（ウィザードで設定される / 説明）
     - JQUANTS_REFRESH_TOKEN （必須）
     - KABU_API_PASSWORD （必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパー専用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能使用時）
     - LOG_LEVEL（例: INFO）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知に使用）
   - .env の自動読み込み:
     - kabusys.config はプロジェクトルート (.git または pyproject.toml を基準) を検出し、自動で .env / .env.local を読み込みます。
     - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 問題があれば修正して再度検証。--strict を付けると警告も失敗扱いになります。

使い方（主要コマンド）
--------------------
- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が既に存在すると起動しません（安全措置）。
  - 実行中は data/execution.pid（デフォルト）に PID を出す実装が渡されます。

- 監視ループを起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して記録します。
  - 停止フラグ data/stop_requested.flag を検知すると監視ループを終了します。

- .env を作る（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定できます（デフォルト: data/paper_trading.db）。

重要なファイル・フラグ（運用メモ）
---------------------------------
- data/kill.flag
  - KillSwitch が条件を満たすと書き込むファイル（実行停止の指示）。Settings.kill_flag_path（デフォルト: data/kill.flag）で制御。
- data/stop_requested.flag
  - run_execution / run_monitoring のループを終了させるためにチェックされる停止フラグ（run_*.py 内で参照）。
- logs/
  - ログは logs/<app_name>.log に日次ローテーションで保存されます（kabusys.utils.logging_setup）。
- DB
  - DuckDB: デフォルト data/kabusys.duckdb（分析・prices_daily 等）
  - SQLite (monitoring): data/monitoring.db（system_status, trade_logs, positions, risk_logs, dashboard）
  - Paper trading用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

ディレクトリ構成（抜粋）
---------------------
リポジトリルート（例）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み / Settings クラス
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — ロギング設定ユーティリティ
      - process_priority.py    — プロセス優先度・CPU affinity 設定
    - execution/                — 実行エンジン関連（broker, engine, order_manager 等）
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py       — SQLite スキーマと永続化 API
      - system_monitor.py      — システム監視（CPU / メモリ / データ鮮度）
      - trade_monitor.py       — 注文監視（滞留・約定異常 など）
      - risk_monitor.py        — ドローダウン／ポジション数監視
      - kill_switch.py         — kill.flag 書き込みロジック
      - monitoring_engine.py   — 複数モニタの総括ループ
      - alert_manager.py       — （アラート送信ロジック）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py            — ニュースセンチメント（OpenAI）連携
      - regime_detector.py     — レジーム判定（ETF MA + マクロ NLP）
    - tools/
      - paper_verification_report.py
- data/                        — データ・フラグ用ディレクトリ (デフォルト)
- logs/                        — ログ出力ディレクトリ（自動作成）
- config/                      — config/*.yaml（各種設定テンプレート）

備考 / 運用上の注意
-------------------
- .env はセキュアな情報（API トークン、パスワード）を含むため絶対に Git にコミットしないでください。
- monitoring は run_monitoring.py 内で「監視は本番 sqlite_path を使用する」と明示されています。環境切替に注意してください。
- KABUSYS_ENV=paper_trading により発注はモック化され、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へログを残します。本番 DB と完全に分離してください。
- OpenAI 連携機能を利用する際は API コストとレートリミットに留意してください。news_nlp、regime_detector はリトライ・バックオフ処理を実装していますが、API 使用量は監視してください。
- サードパーティ依存（duckdb, psutil, openai, PyYAML 等）については、適宜バージョン固定を行うことを推奨します。

問い合わせ / 開発のヒント
-----------------------
- 設定に関する問題はまず python -m kabusys.validate_config を実行して検出してください。
- ログの設定は kabusys.utils.logging_setup.setup_logging で統一されているため、カスタム起動スクリプトからも利用してください。
- 単体機能の呼び出しはモジュールを直接インポートしてテストできます（例: kabusys.portfolio.calc_position_sizes 等）。DuckDB など DB 接続を引数で受け取る設計なのでモックテストしやすくなっています。

以上。必要であれば README に含める例やコマンドを更に追記します。どの部分を詳細化しますか？