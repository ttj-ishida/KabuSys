KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ/実行コンポーネント群です。本リポジトリは以下を含みます。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（プロセス・データ鮮度・注文状況の監視、Kill Switch）
- Portfolio 構築（銘柄選定、重み付け、株数決定）
- Research（ファクター計算・将来リターン・IC 等）
- AI 補助（ニュース NLP によるセンチメント評価 / レジーム判定）
- 各種ユーティリティ（設定ウィザード・設定検証・レポート生成）

主な設計方針
- 本番/ペーパーは明確に分離（paper_trading 用 DB を用意）
- ルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない等）
- フェイルセーフ：外部 API 失敗時はフォールバック動作を行う
- DuckDB を分析用 DB、SQLite を監視・ログ用に使用

機能一覧
--------
- 実行（ExecutionEngine）
  - BrokerClientFactory により本番/モックの切替（KABUSYS_ENV=paper_trading）
  - OrderManager / Reconciler / RiskManager を組み合わせた発注・再整合処理
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度の監視
  - TradeMonitor: 注文滞留・約定異常の検出（trade_logs を参照）
  - RiskMonitor: ドローダウン・ポジション数上限の監視とリスクログ記録
  - KillSwitch: 条件到達で data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 各 Monitor を統合したポーリングループ
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重配分、リスクベースのポジションサイズ計算
  - セクターキャップ・レジーム乗数適用
- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB 経由）
  - 将来リターン・IC 計算・統計サマリー
- AI
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメントの銘柄別スコア化
  - regime_detector: ETF MA とマクロニュースの LLM 評価を合成した市場レジーム判定
- ツール
  - 設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート（tools/paper_verification_report.py）
- ユーティリティ
  - ログ設定（utils.logging_setup）
  - プロセス優先度設定 / CPU affinity（utils.process_priority）
  - Monitoring DB（SQLite）初期化 / 永続化層（monitoring.monitoring_db）

前提 / 必要な依存
----------------
最低限の依存（実行環境に合わせて適宜インストールしてください）:
- Python 3.10+
- duckdb
- psutil
- openai （AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証をする場合、オプション）

例（pip）:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml

（requirements.txt がある場合はそちらを利用してください）

セットアップ手順
--------------
1. リポジトリを取得
   - git clone ... && cd <repo>

2. 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージのインストール:
   - pip install duckdb psutil openai pyyaml

4. .env の作成（対話式ウィザード推奨）:
   - python -m kabusys.config_setup
     ウィザードは .env を生成します。必須項目は JQUANTS_REFRESH_TOKEN と KABU_API_PASSWORD です。

   主要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
   - KABUSYS_ENV           : 実行環境 ("development" | "paper_trading" | "live")
   - DUCKDB_PATH           : DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH : ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY        : OpenAI を使う機能を使う場合に設定
   - LOG_LEVEL             : ログレベル（例: INFO）

5. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - 厳格モード（警告も失敗として扱う）: python -m kabusys.validate_config --strict

基本的な使い方
------------

起動スクリプト
- ExecutionEngine（発注エンジン）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に書き込みます（本番 DB と分離）。
  - 起動時に data/stop_requested.flag があると起動しません。
  - プロセスは data/execution.pid を書きます。

- Monitoring（監視ループ）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒単位に設定可能（デフォルト: 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを記録します。

ツール / CLI
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）

AI 機能（プログラムから呼び出す）
- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="...")  # api_key を省略すると環境変数 OPENAI_API_KEY を使用
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

監視 / Kill Switch の仕組み
- RiskMonitor / SystemMonitor / TradeMonitor が定期的にチェックを行い、KillSwitch が条件（例: ドローダウン超過）を満たした場合 data/kill.flag を生成します。ExecutionEngine は起動時・実行中にこのフラグを検査し、検出時に停止します。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30 日分保持）。
- 起動スクリプトは setup_logging(app_name="execution" or "monitoring") を呼び出します。

ファイル・ディレクトリ構成
------------------------
以下は主要なファイル・ディレクトリの抜粋（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - execution/               — ExecutionEngine 関連（BrokerFactory, Engine, OrderManager, RiskManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

- data/
  - monitoring.db (デフォルト)      — 監視ログ（SQLite）
  - kabusys.duckdb (デフォルト)     — 分析用 DuckDB
  - paper_trading.db                — ペーパートレード用 DB（KABUSYS_ENV=paper_trading）
  - kill.flag / stop_requested.flag — 制御フラグ
  - execution.pid                    — ExecutionEngine の PID ファイル

運用上の注意
------------
- 本番環境では KABUSYS_ENV=live を設定する前に validate_config で設定を慎重に確認してください（validate_config は live での追加警告を出します）。
- .env は絶対にバージョン管理にコミットしないでください。
- OpenAI 等外部 API を利用する処理は API キーやレート制限に注意して運用してください。AI 呼び出しはリトライ・バックオフを実装していますが、過度の負荷を与えない運用が必要です。
- Monitoring はデフォルトで監視 DB（SQLITE_PATH）を使用します。Monitoring のデータは運用上重要です。バックアップや保全を検討してください。

開発者向け
----------
- モジュールはできる限り副作用を避ける設計（.env 自動読み込みは Settings 内で制御）になっています。テスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動読み込みを無効化できます。
- logging_setup.setup_logging() を各スクリプトで使うことでログ出力を統一できます。
- DuckDB を用いたリサーチ関数は SQL を中心に実装されており、テスト用に小さな DuckDB を用意すると良いです。

サンプルコマンドまとめ
--------------------
- .env 作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution
  (KABUSYS_ENV=paper_trading を指定するとペーパー用 DB を使用)

- Monitoring 起動（ポーリング間隔 30 秒に設定）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 拡張
-----------------
- 新しいブローカーを追加する場合は execution/broker_factory と broker クライアント実装を追加してください。
- AI モデルの入れ替えやプロンプト修正は ai/news_nlp.py と ai/regime_detector.py を編集してください（API のレスポンスバリデーションに注意）。
- DuckDB のスキーマや config/*.yaml の生成はプロジェクト内の scripts やドキュメント（別途用意）に従ってください。

以上。必要であれば README にサンプル .env のテンプレートや起動例の詳細（systemd ユニット、Dockerfile、CI 設定等）を追加できます。どの情報を追記したいか教えてください。