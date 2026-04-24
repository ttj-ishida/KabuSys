README
======

プロジェクト概要
------------
KabuSys は日本株向けの自動売買システム向けユーティリティ／ライブラリ群です。
戦略のファクター計算、ポートフォリオ構築、注文発行（ExecutionEngine）、
監視（Monitoring）、AI を使ったニュースセンチメント評価などを含みます。
本リポジトリはライブラリおよび起動用スクリプト群を提供し、ローカル開発から
ペーパートレード、本番運用までを想定しています。

主な特徴
-------
- ExecutionEngine（発注エンジン）とペーパートレード分離（KABUSYS_ENV=paper_trading）  
  ペーパートレード時は MockBrokerClient を使用し、別 DB（data/paper_trading.db）に記録。
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）  
  システム稼働状況、データ鮮度、滞留注文、ドローダウン等を監視しログやアラートを出力。
- Kill Switch（data/kill.flag）による安全停止機構。
- Portfolio モジュール：候補選定、等配分/スコア配分、リスク調整、ポジションサイズ計算（単元株丸め等）。
- Research モジュール：DuckDB を使ったファクター計算（モメンタム/ボラティリティ/バリュー等）、IC 計算、特徴量探索。
- AI モジュール：OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・市場レジーム判定（LLM 呼び出しはオプション）。
- ツール：対話式 .env 作成ウィザード、設定検証 CLI、Paper Trading 検証レポート生成など。
- ロギングユーティリティ：統一的なログ設定（コンソール＋日次ローテーションファイル）。

動作要件（主要）
----------------
- Python 3.10+
- ランタイムライブラリ（代表例）:
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（config 検証を行う場合に推奨）
- SQLite（標準ライブラリ）

※ requirements.txt は本リポジトリに含まれない場合があります。上記パッケージを適宜インストールしてください。

セットアップ手順
-------------
1. リポジトリをクローン／展開。
2. 仮想環境を作成して有効化（任意）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb psutil openai
   - （設定検証に YAML を使う場合）pip install pyyaml
4. ディレクトリ作成（必要に応じて）:
   - mkdir -p data logs
5. 環境変数ファイルの準備:
   - 対話式ウィザード: python -m kabusys.config_setup
     → .env を生成／更新します（.env は絶対に Git にコミットしないでください）。
   - 生成後、設定検証: python -m kabusys.validate_config
6. （ペーパートレードを使う場合）PAPER_TRADING_SQLITE_PATH を確認（デフォルト: data/paper_trading.db）。

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

有用（デフォルト値や説明を付記）:
- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能利用時）
- PAPER_FILL_MODE: ペーパートレードの fill モード（instant | partial | never | reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動的にクリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

自動 .env ロードの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まない。

起動・使い方
----------

主要スクリプト（モジュール実行）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）として扱う

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中に停止させたい場合は data/stop_requested.flag を作成してください（監視スクリプト等で検知します）。
    - 実行中は PID が data/execution.pid に書き出されます。

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定できます（デフォルト 60）。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用して監視ログを記録します。
    - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを明示的に指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

AI 機能
- ニュースセンチメント評価（ai.news_nlp）
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY（または api_key 引数）必須。DuckDB 接続を渡し ai_scores テーブルへ書き込みます。
- 市場レジーム判定（ai.regime_detector）
  - 関数: score_regime(conn, target_date, api_key=None)
  - OpenAI を使った補助を行い、market_regime テーブルへ冪等書き込みします。
- 注意: API 呼び出しはリトライとフォールバックを実装していますが、API キーと料金には注意してください。

停止フラグ / Kill Switch
-----------------------
- data/stop_requested.flag: run_execution / run_monitoring が監視する外部停止フラグ。ファイルが存在すると Engine の起動やループ実行を停止します。
- data/kill.flag: KillSwitch（リスク違反時）により作成され、ExecutionEngine に停止を促します。KILL_FLAG_CLEAR_ON_START=1 により起動時自動クリアが可能（本番では推奨しません）。

ロギング
--------
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます（TimedRotatingFileHandler により日次ローテーション、30 日保持）。
- setup_logging(app_name="execution") のように各スクリプトで初期化されます。ログディレクトリは環境変数 LOG_DIR で上書き可能。

データベース（監視 DB 初期化）
------------------------------
- init_monitoring_db(conn: sqlite3.Connection) を呼ぶことで監視に必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard 等）を冪等に作成します。
- run_execution / run_monitoring は起動時に自動で init_monitoring_db を呼びます。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 以下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード等）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（OpenAI 連携）
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite による永続化レイヤ（テーブル作成／CRUD）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （滞留注文・約定異常等のチェック）（実装参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - monitoring_engine.py   — 各 Monitor を束ねる実行エンジン
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （アラート送信管理）（実装参照）

  - execution/
    - execution_engine.py    — ExecutionEngine（実行セッション管理）
    - broker_factory.py      — ブローカークライアント生成（モック／実装切替）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文永続化（SQLite 等）
    - reconciler.py          — 注文と約定の突合せ
    - risk_manager.py        — 発注前リスクチェック

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み付け
    - risk_adjustment.py     — セクター制限・レジーム乗数
    - position_sizing.py     — 株数計算・資金配分

  - research/
    - factor_research.py     — ファクター計算（Momentum, Volatility, Value）
    - feature_exploration.py — 将来リターン/IC/統計サマリ

  - data/
    - pipeline.py            — prices_daily 等の取り回し（参照用）

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

補足 / 運用注意
--------------
- .env は秘匿情報（API キー等）を含むため絶対にリポジトリにコミットしないでください。
- 本番運用時は KABUSYS_ENV=live を設定すると本番モードになります。LINE 通知等の設定が重要です（validate_config でチェック）。
- AI 機能（OpenAI）は外部 API を呼びます。API キー、レート、料金に注意してください。失敗時のフェイルセーフロジックは実装されていますが、運用方針を事前に決めてください。
- ファイルベースの停止フラグ（stop_requested.flag / kill.flag）はシンプルで確実ですが、運用上の扱い（作成／削除の権限やオートクリア設定）に注意してください。

ライセンス / バージョン
------------------------
- パッケージバージョンは kabusys.__version__（現在 0.1.0）。
- ライセンス情報はリポジトリの LICENSE を参照してください（存在する場合）。

問い合わせ・拡張
---------------
- 新しいブローカークライアント、アラートチャネル、バックテストやメトリクス拡張などは各モジュールを実装して差し替える設計になっています。各モジュールの docstring を参照して実装してください。

以上。README に不足している点、特にコマンド例や環境変数の追加説明が必要であれば教えてください。