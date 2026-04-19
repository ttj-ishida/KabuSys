KabuSys
======
日本株自動売買システム（KabuSys）のコードベース説明書。  
この README はローカル環境での起動・運用・開発に必要な概要、セットアップ、実行例、ディレクトリ構成をまとめたものです。

要点
------
- 言語: Python
- 永続化: DuckDB（分析用）および SQLite（監視・発注ログ）
- 一部機能は OpenAI API（gpt-4o-mini）を利用（ニュース NLP / レジーム判定）
- Paper Trading（ペーパートレード）モードあり（本番 DB と分離）
- ログ: コンソール + 日次ローテーション（logs/<app_name>.log）

プロジェクト概要
----------------
KabuSys は日本株の自動売買に関わる以下の主要機能を含むシステムです：
- シグナル生成（research モジュール：ファクター計算・特徴量解析）
- ポートフォリオ構築（portfolio モジュール：候補選定・重み算出・ポジションサイズ決定）
- 注文実行エンジン（execution） — 本番・ペーパートレード切替
- モニタリング（monitoring） — システム状態・注文・リスク監視、Kill Switch
- AI 連携（ai） — ニュースのセンチメント評価 / 市場レジーム判定（OpenAI）
- 開発用ツール（tools） — Paper Trading 検証レポートなど
- 設定管理（config / config_setup / validate_config）

主な機能一覧
--------------
- 設定ウィザード: python -m kabusys.config_setup により .env を対話生成
- 設定検証: python -m kabusys.validate_config で .env / config/*.yaml の事前チェック
- ExecutionEngine 起動: python -m kabusys.run_execution（本番 or paper_trading 切替）
  - ペーパートレード時は MockBrokerClient を使用し data/paper_trading.db に記録
- Monitoring 起動: python -m kabusys.run_monitoring（ポーリングで各種監視を実行）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
- News NLP / Regime Detector（AI）: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- Portfolio utilities: 候補選定、スコア重み・等金額重み、リスク調整、ポジションサイズ算出
- Logging 設定ユーティリティ: kabusys.utils.logging_setup.setup_logging（アプリ共通）

前提・依存パッケージ（例）
-------------------------
最低限必要そうなパッケージ（プロジェクトに requirements ファイルがある場合はそちらを使用してください）：
- duckdb
- psutil
- openai (AI 機能利用時)
- pyyaml (validate_config による YAML 検証は任意)

例:
pip install duckdb psutil openai pyyaml

環境変数（主要）
-----------------
主な環境変数（.env ファイルで管理）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI 機能利用時に必須）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）

設定の自動ロード:
- プロジェクトルート (.git または pyproject.toml のある場所) を基に .env/.env.local を自動ロードします。
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

セットアップ手順
----------------
1. リポジトリをチェックアウト
   - git clone ... && cd <repo>

2. Python 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （あれば）
   - ない場合例: pip install duckdb psutil openai pyyaml

4. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - 生成後、設定内容を確認: python -m kabusys.validate_config
   - --strict を付けると警告を FAIL 扱いにできます

5. データディレクトリ作成
   - 一部スクリプトは data/ 以下のファイル（DB / pid / flag）を参照します。自動作成されますが明示的に作る場合:
     mkdir -p data logs

6. DuckDB / SQLite DB の初期化
   - monitoring 用 SQLite は起動スクリプト内で必要テーブルを冪等で作成します（init_monitoring_db）。
   - 分析用 DuckDB は tools / research モジュールで使用されます。必要に応じて prices_daily / raw_financials 等のテーブルを準備してください。

基本的な使い方
----------------

1) 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力に従って .env / config/*.yaml を修正

2) モニタリング起動
   - デフォルトポーリング 60 秒:
     python -m kabusys.run_monitoring
   - ポーリング間隔を変更:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 停止方法:
     - デーモン化している場合は data/stop_requested.flag を作成すると監視ループが検知して安全停止します
     - Ctrl+C（KeyboardInterrupt）でも停止します

3) ExecutionEngine（注文エンジン）起動
   - 本番/開発/ペーパートレードは KABUSYS_ENV に従う:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 起動前に data/stop_requested.flag が存在すると起動を行わず終了します（安全機構）
   - 実行中は data/execution.pid に PID を書きます。終了時に削除されます（若干のタイムアウト処理あり）

4) Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) AI 関連処理（ニュース NLP / レジーム判定）
   - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で指定）
   - プログラムから呼ぶ例:
     from kabusys.ai import score_news
     score_news(duckdb_conn, target_date, api_key=os.environ["OPENAI_API_KEY"])
   - レジーム判定:
     from kabusys.ai.regime_detector import score_regime
     score_regime(duckdb_conn, target_date, api_key=...)

停止・Kill Switch
-----------------
- KillSwitch は監視ロジック（RiskMonitor 等）により条件を満たした場合 data/kill.flag を書き込み、
  ExecutionEngine に対して停止シグナルを送る仕組みです。
- kill.flag のパスは Settings.kill_flag_path により指定（デフォルト data/kill.flag）。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START が 1 に設定されていると自動クリアされる設定がありますが、本番では 0 を推奨します。

ログ
----
- ログは logs/<app_name>.log に日次ローテーションで保存されます（30日間保存）。
- すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一されたログ設定を行います。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 内の主要モジュールと役割（抜粋）です。

- run_execution.py
  - ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じてペーパートレード DB を切替。

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔調整。

- config.py
  - 環境変数 / 設定の読み取りユーティリティ（Settings クラス）。

- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）。

- validate_config.py
  - 設定検証 CLI（python -m kabusys.validate_config）。

- utils/
  - logging_setup.py : ログ設定ユーティリティ
  - process_priority.py : プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py : SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py : CPU / メモリ / データ鮮度などの監視
  - trade_monitor.py : 注文滞留・約定異常検知（コードベース内に存在）
  - risk_monitor.py : ドローダウン・ポジション数上限監視
  - kill_switch.py : Kill Switch 実装
  - monitoring_engine.py : モニタを束ねるエンジン
  - alert_manager.py : アラート送信（LINE 等、実装に依存）

- execution/
  - BrokerClientFactory, ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager, 等（発注フロー）

- portfolio/
  - portfolio_builder.py : 候補選定・重み計算
  - position_sizing.py : 発注株数決定ロジック
  - risk_adjustment.py : セクターキャップ・レジーム乗数

- research/
  - factor_research.py : モメンタム / バリュー / ボラティリティ等ファクター計算（DuckDB）
  - feature_exploration.py : 将来リターン・IC計算・統計サマリー

- ai/
  - news_nlp.py : ニュース記事を OpenAI でスコアリングして ai_scores に書き込む
  - regime_detector.py : ETF ma200 とマクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py : ペーパートレード検証レポート生成スクリプト

運用上の注意
--------------
- 実際の発注（KABUSYS_ENV=live）を行う前に、validate_config とペーパートレードで十分に検証してください。
- OpenAI の利用は API キー・コストに注意してください。API 呼び出し失敗時にはフェイルセーフ（スコア 0 やスキップ）となる実装になっていますが、期待する挙動とコストは確認してください。
- プロセス優先度設定や CPU affinity は psutil の権限に依存します。権限不足で警告が出ますが処理は継続します。
- .env ファイルは機密情報を含むため絶対に Git に含めないでください（config_setup も警告を出す設計）。

開発者向けメモ
----------------
- auto .env 読み込みは Settings モジュール起動で行われますが、テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring_db.init_monitoring_db は冪等なので複数回呼んでも安全です。スキーママイグレーション処理も含まれます。
- DuckDB を利用した分析 / 研究コードは外部テーブル（prices_daily や raw_financials）を前提にしているため、データ準備が必要です。

サポート / 追加情報
--------------------
- README の補足や実運用に関するドキュメント（設計書・運用手順書）が別途ある場合はそちらを参照してください（本 README はコードベースに含まれる主要ポイントの要約です）。
- 問い合わせ・バグ報告はリポジトリの issue を使用してください。

以上。必要であれば各スクリプトの具体的な引数例や、.env のサンプルテンプレート（機密部分はマスク）を別途追加します。どの情報を詳しく載せたいか教えてください。