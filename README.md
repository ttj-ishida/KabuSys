KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
主な機能は注文実行エンジン、監視（モニタリング）系、ポートフォリオ構築・サイズ決定、ファクター計算／リサーチ、AI（ニュース NLP）によるセンチメント評価などを含みます。  
設計上、実行（Execution）と監視（Monitoring）は分離され、ペーパートレード用 DB や安全策（Kill Switch / stop flag）を備えています。

特徴（抜粋）
--------------
- ExecutionEngine：実際のブローカークライアントまたは MockBrokerClient（KABUSYS_ENV=paper_trading）を使った発注処理
- Monitoring：システム状態・注文状態・リスク（ドローダウン、ポジション数）を定期ポーリングで監視し、Kill Switch を発動可能
- Portfolio construction：候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群
- Research：DuckDB を用いたファクター計算（Momentum/Volatility/Value 等）、将来リターン計算、IC 計算
- AI モジュール：OpenAI を用いたニュースのセンチメント評価（ai_scores / market_regime などへ書き込み）
- ツール：対話式 .env 作成ウィザード、設定検証 CLI、Paper Trading 検証レポート生成など
- ログ基盤：stdout ストリーム + 日次ローテートファイル（logs/ デフォルト）

セットアップ
------------
前提
- Python 3.9+（ソースは型ヒントを使用）
- SQLite は標準で利用可能
- 必要な外部パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能使用時)
  - PyYAML（config/*.yaml の構文チェック用、任意）
これらは pip でインストールしてください。例:
  pip install duckdb psutil openai PyYAML

初期ディレクトリ作成（任意）
  mkdir -p data logs

環境変数設定
- .env をルート（プロジェクトルート）に配置するか、環境変数で設定します。
- 用意された対話式ウィザードで .env を生成できます（下記参照）。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db に記録
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring で使用。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの注文約定挙動（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1。デフォルト 0）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動で .env を読み込むのを無効化（テスト用）

.env を対話式で作る
  python -m kabusys.config_setup
これは .env を上書き・生成し、保存前に確認を行います。

設定検証
  python -m kabusys.validate_config
--strict を付けると警告もエラー扱いになります。

使い方（主要コマンド）
---------------------
- ExecutionEngine を起動（通常は systemd/cron 等で管理）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を利用し paper_trading 用 DB に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中、停止させるには data/stop_requested.flag または data/kill.flag 等を用いる運用が想定されています。
  - PID ファイルの書き込みは Settings.pid_file_path（デフォルト data/execution.pid）で行われます。

- Monitoring を起動（監視ループ）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視テーブルに記録します。
  - 停止は data/stop_requested.flag により行います（検知したらループを抜けます）。

- Paper Trading 検証レポート生成（ツール）
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - --db を省略すると PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照します。

- AI（ニューススコアリング／レジーム判定）はモジュール関数として利用可能
  例（スクリプト内から）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  またはレジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

- Research / Portfolio 関数の利用例（Python REPL やスクリプトから）
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    rows = calc_momentum(duckdb_conn, date(2026,4,1))

停止・Kill Switch 運用
---------------------
- KillSwitch は RiskMonitor 等の評価結果に基づき data/kill.flag を書き込み、ExecutionEngine に停止指示を与えます。
- KillSwitch が書き込まれた場合、ExecutionEngine 側は起動停止や終了処理を行う実装となっています（flag 存在チェック）。
- 本番時は KILL_FLAG_CLEAR_ON_START を 0 に設定することを推奨します（誤って自動クリアされるのを防ぐため）。

ログ
----
- デフォルトは logs/ ディレクトリに日次ローテートファイル（app_name.log）を出力し、同時に stdout にも出力します。
- setup_logging 関数により全スクリプトで統一的に設定されます。

ディレクトリ構成（主要ファイル）
------------------------------
プロジェクトのルートに src/kabusys 以下が配置される想定です。主な構成は下記のとおり。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

  - execution/                — 実際の発注処理関連（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 層（スキーマ初期化・CRUD）
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — 発注/約定ロジック監視（ファイルに含む）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 書き込みロジック
    - alert_manager.py        — 通知（LINE など）管理（実装ファイルが存在する場合）
    - monitoring_engine.py    — 各 Monitor を束ねるループ

  - portfolio/
    - portfolio_builder.py    — 候補選定・重み付け
    - position_sizing.py      — 株数算出・資金配分・単元丸め
    - risk_adjustment.py      — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py      — Momentum/Volatility/Value 等ファクター計算（DuckDB 使用）
    - feature_exploration.py  — 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）によるスコアリング
    - regime_detector.py      — 市場レジーム判定（MA + LLM 合成）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力ツール
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

注意点 / 運用上のヒント
-----------------------
- DB 分離: paper_trading 用の SQLite は paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）で独立させ、本番 DB と混ざらないように設計されています。
- 自動 .env 読み込み: デフォルトでプロジェクトルートの .env、.env.local を自動読み込みします。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に便利）。
- モニタリングは本番の monitoring.db を使用して状態を記録します。run_monitoring は KABUSYS_ENV にかかわらず monitoring.db（Settings.sqlite_path）を使います。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（setup_logging 内でハンドリング）。
- OpenAI API を使う機能（news_nlp, regime_detector）は API 呼び出し失敗時にフォールバック処理を行うよう設計されていますが、API キーは必須です。テスト時はモック可能です（内部の _call_openai_api を patch）。

開発 / テスト
--------------
- モジュールは多くが純粋関数または外部接続（DB / broker client / OpenAI client）を注入する設計になっており、ユニットテストが書きやすくなっています。
- OpenAI / ブローカークライアント API 呼び出しは外部依存なので、ユニットテストではモックすることを推奨します。

ライセンス / 貢献
-----------------
（ここにプロジェクト固有のライセンス、貢献方法などを記載してください）

補足
----
詳細な実装や追加の CLI オプションはソースコード内の docstring / コメントを参照してください。README の内容はコードベースの主要な使い方と運用上の注意をまとめたものです。質問や利用方法の相談があれば教えてください。