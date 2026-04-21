KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。
戦略（リサーチ）、ポートフォリオ構築、ポジションサイズ計算、発注実行、
監視・アラート、AI ベースのニュース評価等の機能をモジュール化しています。

この README はソースコードから読み取れる設計意図・起動方法・設定手順をまとめたドキュメントです。

主な特徴
--------
- 戦略・リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）: kabusys.research
  - 将来リターン・IC・統計サマリー（特徴量探索）
- ポートフォリオ構築
  - 候補選定、等配分/スコア加重、セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分、集計上限スケーリング）
- 実行エンジン（Execution）
  - Broker クライアント抽象化（paper_trading 環境では MockBroker を使用）
  - リスク管理、注文管理、照合（reconciler）
- 監視（Monitoring）
  - System / Trade / Risk モニタで定期チェック
  - MonitoringDB（SQLite）にログを永続化
  - Kill Switch（データ上の閾値を満たすと data/kill.flag を書き込み、Execution を停止）
- AI（OpenAI）
  - ニュースのセンチメント集約（OpenAI により銘柄ごとの ai_score を生成）
  - マクロニュース + ETF MA200 を用いた市場レジーム判定
- 運用ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール

前提・依存
----------
主な Python ライブラリ（pip でインストールしてください）:
- python >= 3.9+
- duckdb
- psutil
- openai
- PyYAML（config/*.yaml の構文チェック用。必須ではない）

例:
pip install duckdb psutil openai pyyaml

設定（.env）
-----------
実行に必要な環境変数は .env（または環境変数）で指定します。便利な対話式ウィザードが提供されています。

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主なオプション（デフォルト）
- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
- KILL_FLAG_CLEAR_ON_START: 0/1（本番で 0 推奨）

.env を作成する手順（推奨）
1. ウィザードで作成:
   python -m kabusys.config_setup
   → 対話形式で .env を生成できます。
2. 設定検証:
   python -m kabusys.validate_config
   → 必須項目・ファイルパス等のチェックを実行します。
   --strict を付けると警告も失敗扱いになります。

起動・実行方法
--------------

1) Monitoring（監視ループ）
- 役割: System/Trade/Risk の定期チェックを行い、監視ログを SQLite に保存、必要であれば kill.flag を書く等を行う。
- 起動:
  python -m kabusys.run_monitoring
- オプション（環境変数）:
  MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
- 備考:
  - monitoring は KABUSYS_ENV に関係なく sqlite_path（デフォルト: data/monitoring.db）を使用します。
  - 停止方法: プロジェクトルートの data/stop_requested.flag を作成すると監視ループは安全に終了します。

2) Execution（発注エンジン）
- 役割: ブローカ接続、リスク管理、注文送信、照合の実行
- 起動:
  python -m kabusys.run_execution
- 動作モード:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。本番 DB と完全分離。
  - 本番（live）では実ブローカーを使用（環境変数による設定が必要）。
- 停止方法:
  - data/stop_requested.flag を作成するとエンジンを停止するよう指示できます。
  - Kill Switch（監視側が data/kill.flag を作成）により外部から停止されることがあります。
- PID ファイル:
  - data/execution.pid（デフォルト）はエンジン起動時に書かれます。

3) Paper Trading 検証レポート
- 使い方:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  --db PATH（指定がなければ env/PAPER_TRADING_SQLITE_PATH、なければ data/paper_trading.db を使用）

運用ファイル・フラグ
-----------------
- data/stop_requested.flag
  - 実行スクリプト（run_monitoring/run_execution）がこのファイルの存在を検知すると安全終了します（ローカル運用 shutdown 用）。
- data/kill.flag
  - KillSwitch が書き込むファイル。存在すると ExecutionEngine を停止する外部シグナルとして機能します（本番で重要）。
- data/execution.pid
  - ExecutionEngine の PID を格納するファイル（起動時作成）。

ログ
---
- ロギングは kabusys.utils.logging_setup.setup_logging を起動スクリプトで呼び出して統一的に管理します。
- デフォルトログディレクトリ: logs/
- 各アプリケーションは logs/<app_name>.log に日次ローテートで出力されます（30日保持）。

監視 DB（SQLite）
----------------
- monitoring_db.init_monitoring_db が起動時に呼ばれ、必要なテーブル群（system_status, trade_logs, positions, risk_logs, dashboard 等）とマイグレーションを自動化します。
- monitoring のテーブルは監視・運用指標の永続化に使います。

AI 機能（OpenAI）
----------------
- kabusys.ai.news_nlp.score_news: raw_news を集約して OpenAI に送信し銘柄ごとの ai_score を ai_scores テーブルに書き込みます。
  - API キー: OPENAI_API_KEY（または関数引数）
  - バッチサイズ、リトライ、レスポンス検証等が組み込まれています。
- kabusys.ai.regime_detector.score_regime: ETF 1321 の MA200 とマクロニュースを統合して market_regime テーブルに判定を書き込みます。
- 運用時は OPENAI_API_KEY の管理に注意してください（安全に保管し .env は決して git にコミットしない）。

よく使う環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- OPENAI_API_KEY
- MONITOR_POLL_INTERVAL (監視のポーリング間隔秒)
- PAPER_FILL_MODE (paper_trading の約定モード: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (起動時 kill.flag を自動クリアするか: 0/1)

コード構成（主要ファイル / ディレクトリ）
----------------------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / 設定の読み取り・検証ロジック
- config_setup.py          — .env 対話式ウィザード（CLI）
- validate_config.py       — 設定検証 CLI
- run_monitoring.py        — Monitoring の起動スクリプト
- run_execution.py         — ExecutionEngine の起動スクリプト

サブパッケージ:
- kabusys/monitoring/
  - monitoring_db.py       — SQLite 永続化層
  - system_monitor.py      — システム / データ鮮度監視
  - trade_monitor.py       — 注文ログ監視（ファイルは参照元を確認）
  - risk_monitor.py        — ドローダウン・ポジション上限監視
  - kill_switch.py         — kill.flag の評価・書き込み
  - monitoring_engine.py   — 各 Monitor を束ねる
  - alert_manager.py       — （通知管理。詳細は実装参照）
- kabusys/execution/
  - 各種実行エンジン、OrderManager, Reconciler, RiskManager, BrokerFactory 等
- kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- kabusys/research/
  - factor_research.py
  - feature_exploration.py
- kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- kabusys/utils/
  - logging_setup.py
  - process_priority.py
- kabusys/tools/
  - paper_verification_report.py

運用上の注意
------------
- .env は絶対にリポジトリにコミットしないこと（config_setup でも警告あり）。
- 本番（KABUSYS_ENV=live）では LINE 通知設定や kill_flag の扱いを慎重に確認してください（validate_config の live 用チェックを参照）。
- Monitoring は常に監視用の sqlite_path を使用するため、監視 DB のバックアップ/保護を行ってください。
- OpenAI の利用にはコスト・利用制限があるため、rate-limit や失敗時のフォールバックが組み込まれていますが、API キーの管理・使用量監視は必要です。
- process_priority/set_cpu_affinity を使って優先度や CPU Affinity を設定しますが、OS 権限により失敗する場合があります（ログに警告）。

トラブルシュート
----------------
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します。logs/ の書き込み権限を確認してください。
- DuckDB / SQLite のファイルパスは .env で指定できます。デフォルトは data/ 内のファイルです。親ディレクトリが無い場合は起動時に自動作成されますが、権限に注意してください。
- validate_config をまず実行し、不足・警告を潰してから運用を開始するのを推奨します。

参考コマンド一覧
----------------
- .env 作成:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
- 監視起動:
  python -m kabusys.run_monitoring
- 実行エンジン起動:
  python -m kabusys.run_execution
- PaperTrading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
-----
この README はリポジトリ内のソースコードから仕様・操作方法を抜粋したものです。実環境での運用前に必ず設定検証（validate_config）を行い、ログ・DB のバックアップ方針を決めてください。必要があれば README に追記して運用手順書を整備してください。