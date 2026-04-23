# KabuSys

日本株自動売買システムのサンプル実装。戦略の研究・ファクター計算、ポートフォリオ構築、発注実行（本番/ペーパー分離）、監視・アラート、AI を使ったニュースセンチメント評価などの機能を提供します。

以下はこのコードベースに基づく README です。

概要
- 本リポジトリは、株式自動売買の主要コンポーネントをモジュール化した Python パッケージ（kabusys）です。
- DuckDB を分析用 DB として、SQLite を監視/発注ログ用 DB として使用します。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切り替え可能。
- OpenAI を利用したニュース NLP（センチメント）やレジーム判定をサポート（API キー必須）。

主な機能一覧
- 環境設定管理
  - .env 自動読み込み（プロジェクトルートの .env/.env.local）
  - 対話式設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行エンジン（ExecutionEngine）
  - 実取引/ペーパートレード切替（KABUSYS_ENV）
  - 発注管理、リスク管理、再整合（reconciler）等（実装ファイル群は execution 配下）
  - ペーパー環境は専用 SQLite（data/paper_trading.db）に分離
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリングして DB に記録
  - Kill Switch（条件に応じて data/kill.flag を書き、ExecutionEngine を停止）
  - run_monitoring スクリプトでポーリングループ起動
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純関数群
- 研究用モジュール（research）
  - ファクター計算（momentum / volatility / value）
  - Forward returns、IC（Information Coefficient）、統計サマリ等
- AI 機能（ai）
  - news_nlp: ニュース記事の LLM（OpenAI）によるセンチメント評価 → ai_scores テーブルへ保存
  - regime_detector: ETF の MA200 乖離と LLM によるマクロセンチメントを組み合わせて市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポート生成（稼働率・成功率・レイテンシ等）
- 共通ユーティリティ
  - ログ設定（TimedRotatingFileHandler、コンソール出力統一）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）
  - MonitoringDB: 監視テーブル作成/読み書きのラッパー（SQLite）

セットアップ手順（開発用）
1. Python と仮想環境
   - Python 3.10+ を推奨
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存関係をインストール
   - 必須: duckdb, psutil, openai
   - 推奨/状況依存: PyYAML（config ファイル検証用）
   - 例:
     - pip install duckdb psutil openai
     - pip install pyyaml  # config/*.yaml の内容検証を行いたい場合

3. プロジェクトルートの確認
   - リポジトリ直下に .git または pyproject.toml があると自動でプロジェクトルートと判定されます。

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 生成後、設定の妥当性を検証:
     - python -m kabusys.validate_config
     - 必要に応じて --strict を付けて警告も失敗扱いにできます。

主要な環境変数（重要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）デフォルト: development
  - paper_trading の場合、MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で必須）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR）
- LOG_DIR: ログ出力先（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（コマンド例）
- 環境作成・編集（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - 注意: KABUSYS_ENV によって実行挙動が異なります。
    - ペーパー (paper_trading) 時は MockBrokerClient を使用します。
    - 実行中に data/stop_requested.flag が存在すると起動を中止または停止します。
    - ExecutionEngine は data/execution.pid（デフォルト）に PID を書きます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でループ間隔を変更可能（秒、デフォルト 60）
    - 監視は常に production の sqlite_path（Settings.sqlite_path）を使用して監視テーブルを初期化します。
    - stop_requested.flag を作るとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数: PAPER_TRADING_SQLITE_PATH でも指定可能

- AI 機能（要 OPENAI_API_KEY）
  - news_nlp.score_news(conn, target_date, api_key=None)  # api_key 未指定時は OPENAI_API_KEY を参照
  - regime_detector.score_regime(conn, target_date, api_key=None)

ログ・監視・停止
- ログ:
  - logs/<app_name>.log に日次ローテーションで出力（TimedRotatingFileHandler、30日保持）。
  - すべての起動スクリプトは setup_logging を呼び出して統一的にログ出力します。
- プロセス優先度:
  - 起動スクリプトは開始時に set_process_priority("high") を呼びます（権限により失敗することがあります）。
- 停止フラグ / キルフラグ:
  - Stop 依頼: data/stop_requested.flag を作成すると run_monitoring や run_execution が検知して終了/停止します。
  - Kill Switch: KillSwitch は条件を満たすと data/kill.flag を書き込み、ExecutionEngine 停止のシグナルとなります（Settings.kill_flag_path で指定可能）。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動で kill.flag を消去する動作を許す設定になります（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理、.env 自動ロード
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py      — 監視用 SQLite テーブル作成 & DB 操作ラッパー
    - system_monitor.py     — システム状態・データ鮮度チェック
    - trade_monitor.py      — （trade 監視ロジックファイル）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - monitoring_engine.py  — 各モニタをまとめるポーリングエンジン
    - kill_switch.py        — kill.flag 管理
    - alert_manager.py      — （アラート送信管理）
  - execution/
    - execution_engine.py   — ExecutionEngine 本体（run_session 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py     — ブローカークライアントの生成（本番/Mock の切替）
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュースの LLM によるスコアリング
    - regime_detector.py    — 市場レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py

補足 / 運用上の注意
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブルを作成し、既存 DB に列が無い場合の簡易マイグレーション処理を行います。
- OpenAI API:
  - news_nlp と regime_detector は OpenAI API を呼び出します。API キー・レート制限・レスポンスの不整合に注意してください。リトライ・フォールバックの仕組みを組み込んでいますが、運用では API 料金や障害を考慮してください。
- 本番取り扱い:
  - KABUSYS_ENV=live の場合は設定を慎重に（validate_config は live の場合に追加警告を出します）。
  - kill.flag 自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番では推奨されません。

ライセンス / バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現在 0.1.0）。

以上が本コードベースの README 相当の説明です。必要であれば README に記載する具体的な .env のサンプル、systemd / Supervisor 用のサービスユニット例、または各コンポーネントのより詳細な使用例（API 呼び出し例やテスト方法）を追加できます。どの情報が欲しいか教えてください。