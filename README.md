KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株の自動売買システム（KabuSys）のコアライブラリと起動スクリプト群を含みます。戦略・ポートフォリオ構築・実行・監視・研究・AI 補助（ニュース NLP / レジーム判定）などの機能をモジュール化して提供します。

主な特徴
--------
- 実行エンジン（ExecutionEngine）と監視（Monitoring）を分離した設計
- ペーパートレードモード（本番 DB と完全分離）をサポート
- DuckDB を使った日次のファクター計算・研究環境
- OpenAI を使ったニュースセンチメント（AI スコア）・市場レジーム判定
- ログ出力はコンソール + 日次ローテートファイル（logs/*.log）
- .env による設定管理、対話式ウィザードと事前検証ツールを提供
- 監視（Monitoring）での Kill Switch / Risk Monitor による自動停止機能

機能一覧
--------
- 実行関連
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV によりペーパー/本番挙動を切替）
  - BrokerClientFactory により実稼働ブローカーと MockBroker（paper_trading）を切替
- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔を設定）
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ね、アラート発生や Kill Switch 評価を行う
  - monitoring_db: 監視ログを保持する SQLite の永続層（テーブル作成・マイグレーション含む）
  - KillSwitch: kill.flag により ExecutionEngine を停止させる仕組み
- ポートフォリオ構築
  - portfolio.*: 候補選定、重み計算、セクター制約、ポジションサイズ計算（等）
- リサーチ / ファクター計算
  - research.calc_momentum / calc_volatility / calc_value：DuckDB 上でファクターを計算
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）等の統計処理
- AI（OpenAI）
  - ai.news_nlp.score_news: ニュース記事のセンチメントを取得して ai_scores テーブルへ保存
  - ai.regime_detector.score_regime: ETF + マクロニュースから市場レジームを判定して保存
- 設定/ユーティリティ
  - config_setup.py: .env を対話式に生成・更新するウィザード
  - validate_config.py: 環境変数 / config/*.yaml の事前検証 CLI
  - tools.paper_verification_report: ペーパートレード結果の簡易検証レポート生成
  - utils.*: ロギング設定・プロセス優先度・CPU affinity 等のユーティリティ

セットアップ手順
----------------
1. Python 環境の準備（仮想環境推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存モジュールのインストール
   - 必要なライブラリ（少なくとも）:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config ファイルの検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを利用してください）

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - 直接作成する場合は .env.example を参考にして .env をプロジェクトルートに配置してください。
   - 自動ロード:
     - kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env を自動読み込みします。
     - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も致命扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリの準備（必要に応じて自動作成）
   - デフォルト DB / PID / フラグファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視用): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - これらは環境変数で上書き可能（下記参照）。

主な環境変数
--------------
- 必須（少なくとも設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨
  - KABUSYS_ENV: execution 環境（development | paper_trading | live）、デフォルト: development
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading モード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
  - OPENAI_API_KEY: OpenAI 呼び出しに使用
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject、デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START: 本番で危険なためデフォルト 0（1 にすると起動時に kill.flag をクリア）

使い方（起動・操作）
--------------------
- .env をセットアップして設定を確認した後、以下のように実行します。

1) 実行エンジン（Execution）
   - 起動:
     - python -m kabusys.run_execution
   - 特記事項:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に注文を記録します（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在すると起動を中止します。
     - 実行中に同ファイルが作成されると正常終了を試みます。

2) 監視（Monitoring）
   - 起動:
     - python -m kabusys.run_monitoring
   - 設定:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）。
     - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは常に本番監視 DB に書きます）。
   - 停止:
     - data/stop_requested.flag を作成すると監視ループは次のポーリングで終了します。

3) 設定関連 CLI
   - 対話式 .env 生成:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config [--strict]

4) レポート / ツール
   - ペーパートレード検証レポート:
     - python -m kabusys.tools.paper_verification_report
     - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
     - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

5) AI / Research 実行例（Python インタプリタ）
   - DuckDB 接続を受けて関数を呼び出します。例:
     - from kabusys.research import calc_momentum
     - import duckdb, datetime
     - conn = duckdb.connect("data/kabusys.duckdb")
     - calc_momentum(conn, datetime.date(2026, 4, 10))

監視・停止フラグについて
-----------------------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring / run_execution はこのファイルの存在を監視し、存在すると安全に終了します（運用上の緊急停止用）。
- kill.flag（Settings.kill_flag_path）
  - KillSwitch が発動すると data/kill.flag を書き込み、ExecutionEngine に対して停止シグナルを送ります（ExecutionEngine は起動時にこのフラグのクリア設定を尊重します）。
  - 本番環境では KILL_FLAG_CLEAR_ON_START=0 を推奨（自動でクリアされない）。

ログ
---
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一されています。
- デフォルトログディレクトリ: logs/
- 各アプリ名ごとに logs/<app_name>.log が日次ローテーションされます（30日分保持）。
- コンソール出力は stdout に出ます（cron 等での一括リダイレクトを想定）。

主要ディレクトリ構成
--------------------
（src/kabusys 以下を簡易的に示します）

- kabusys/ (パッケージルート)
  - __init__.py
  - config.py                 — 環境変数 / .env ロードロジック、Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前チェック CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ロギング設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - execution/                — 発注/エンジン関連（BrokerFactory 等）
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite テーブル / MonitoringDB クラス
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
    - news_nlp.py             — ニュースセンチメント取得（OpenAI）
    - regime_detector.py      — 市場レジーム判定（OpenAI）
  - tools/
    - paper_verification_report.py

実運用上の注意・ベストプラクティス
---------------------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup でヘッダに注意書きがあります）。
- OpenAI API 呼び出しを行う機能を使う場合は OPENAI_API_KEY を安全に管理してください。
- run_execution/run_monitoring 起動前に python -m kabusys.validate_config で設定の事前検証を行ってください。
- データベースファイルはバックアップ・権限管理を行ってください（特に本番 SQLite / DuckDB）。

ライセンス・バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE（存在する場合）をご参照ください。

補足: さらに知りたい場合
-----------------------
- 個々のモジュール（portfolio/*.py、research/*.py、ai/*.py、monitoring/*.py）はドキュメント文字列（docstring）で仕様・前提・設計方針が詳細に説明されています。実装やテストを書くときはソース内 docstring を参照してください。

この README はコードベースの主要点をまとめたものです。使用中に不明点が出た場合は該当モジュールの docstring を先に確認してください。