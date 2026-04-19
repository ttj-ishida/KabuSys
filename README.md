KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリです。
トレード実行、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース評価などの主要機能を含みます。
以下は本コードベースの簡易 README（日本語）です。

プロジェクト概要
---------------
KabuSys は自動売買エンジン（ExecutionEngine）と監視系（Monitoring）を中心に、次のような機能を提供します。

- 発注・注文管理・リスク管理を含む Execution エンジン
- System / Trade / Risk を監視する Monitoring 系
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- DuckDB を用いたファクター計算・リサーチ（モメンタム / ボラティリティ / バリュー）
- OpenAI を用いたニュースセンチメント（AI スコアリング）および市場レジーム判定
- Paper Trading モード（本番 DB とは分離された SQLite へ記録）
- CLI 支援ツール（.env ウィザード、設定検証、Paper Trading の検証レポート生成）

主な特徴
--------
- 明確に分離された設定管理（Settings クラス、.env 自動読み込み）
- Monitoring と Execution の安全機構（kill flag / stop flag / PID ファイル）
- DuckDB を分析用 DB、SQLite を監視・注文ログ用 DB として併用
- OpenAI（gpt-4o-mini 等）でニュース・マクロを解析するプラグイン
- プロセス優先度・ログ設定ユーティリティ（platform 非依存の実装）

動作前提・依存
----------------
最低限必要な環境（目安）:
- Python 3.10+
- 必要なライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証時に利用、必須ではない）

インストール例:
- 仮想環境を作成してから:
  - pip install duckdb psutil openai pyyaml

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリへ移動

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml

3. .env の初期作成（ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を対話的に生成します。生成先はプロジェクトルートの .env（オプションで --env-file で変更可）。

4. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数などをチェックします。--strict を付けると警告もエラー扱いになります。

5. データディレクトリの作成（必要なら）
   - デフォルトの SQLite / DuckDB / ログディレクトリは data/ または logs/ 配下です。起動時に自動作成される場合もありますが、権限等の問題がある場合は事前に作成してください。

主要環境変数（代表）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: execution 動作モード (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" でクリア）

注意:
- Settings モジュールはプロジェクトルートの .env / .env.local を自動ロードします（OS 環境変数より低優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要スクリプト）
------------------------

- ExecutionEngine の起動（本番 / ペーパートレードの起動）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 実行中に stop_requested.flag を作成すると Engine を停止します。
  - PID ファイル: data/execution.pid（デフォルト）にプロセス ID を書きます。

- Monitoring の起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（単位: 秒、デフォルト: 60）
  - Monitoring は設定にかかわらず本番 sqlite_path を使用して監視ログを記録します。
  - stop 用のフラグファイル: data/stop_requested.flag を検知するとループを抜けて終了します。

- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（プログラムから呼び出す関数）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースをスコアリングし ai_scores テーブルへ書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ書き込みます。
  - これらは CLI ではなく Python API です。簡易例:
    - python -c "from datetime import date; import duckdb; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, date(2026,4,12), api_key='...'))"

動作上の注意点（安全機構）
-----------------------
- Kill Switch:
  - RiskMonitor / TradeMonitor / SystemMonitor の判定により KillSwitch が data/kill.flag を作成します。Execution はこの flag を検知して安全に停止します。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に kill.flag を自動クリアできますが、本番では 0 を推奨。

- Stop フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します（手動シャットダウン用）。

- ログ:
  - ログは logs/ ディレクトリの <app_name>.log に日次ローテーションで出力されます（TimedRotatingFileHandler）。
  - setup_logging() で標準出力（stdout）にも出力します。ログレベルは LOG_LEVEL 環境変数または引数で制御。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュールと説明です（完全な一覧ではありませんが主要部分を抜粋）:

- kabusys/
  - __init__.py (バージョン等)
  - config.py
    - Settings クラス: 環境変数読み取り・.env 自動ロードロジック
  - config_setup.py
    - .env 対話ウィザード
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading モード対応）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py (統一ログ設定)
    - process_priority.py (プロセス優先度 / CPU affinity 設定)
  - monitoring/
    - monitoring_db.py (SQLite を使った監視ログ永続層)
    - system_monitor.py (CPU/メモリ/ディスク/データ鮮度の監視)
    - trade_monitor.py (注文滞留・約定異常検出 等) — （コードベースに含まれている前提）
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (kill.flag 管理)
    - monitoring_engine.py (複数モニタを束ねる)
    - alert_manager.py (通知管理) — （コードベースに含まれている前提）
  - execution/
    - execution_engine.py (ExecutionEngine 本体) — （コードベースに含まれている前提）
    - broker_factory.py (BrokerClientFactory、paper_trading 用 Mock / 実ブローカーの生成)
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - position_sizing.py (株数計算・集約キャップ)
    - risk_adjustment.py (セクター制限・レジーム乗数)
  - research/
    - factor_research.py (Momentum/Volatility/Value ファクター計算)
    - feature_exploration.py (Forward Returns / IC / 統計サマリ)
  - ai/
    - news_nlp.py (ニュースセンチメント取得・ai_scores 書き込み)
    - regime_detector.py (市場レジーム判定)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート生成)

補足・開発メモ
--------------
- DB 初期化:
  - run_monitoring/run_execution 起動時に init_monitoring_db() が呼ばれ、監視用の SQLite テーブルが冪等に作成されます。
- Paper Trading:
  - paper_trading モードでは本番の monitoring.db とは別に paper_trading.db を使って発注ログ等を分離します。
- DuckDB:
  - 分析・リサーチ系の大規模クエリは DuckDB を利用します（パフォーマンス上の利点）。
- テスト:
  - 外部 API を呼ぶ部分（OpenAI 等）は内部で呼出しラッパーを分離しているため、ユニットテストでは該当関数をモックしやすく設計されています。

よく使うコマンドまとめ
-------------------
- .env ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースの主要な方針・使い方を短くまとめたものです。詳細な設計・仕様は各モジュールの docstring（ソース内コメント）を参照してください。運用時は特に KABUSYS_ENV、kill.flag、データベースパス、OpenAI API キー取り扱いに注意してください。