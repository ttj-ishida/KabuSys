README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ライブラリ群です。  
本リポジトリは発注エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築・リスク制御、リサーチ（ファクター計算・特徴量解析）、ニュース NLP / レジーム判定（OpenAI を利用）などの主要モジュールで構成されています。モジュールはできる限り純粋関数や副作用の少ないインターフェースで設計されており、実運用（live）・ペーパートレード（paper_trading）・開発（development）での使い分けが可能です。

主な特徴
--------
- ExecutionEngine（発注処理）と Monitoring（システム監視・Kill Switch）を分離して運用可能
- Paper trading 用に本番 DB と分離された SQLite（data/paper_trading.db 等）をサポート
- 環境変数 / .env による柔軟な設定管理、対話式の .env 生成ウィザード
- DuckDB を利用したファクター計算・リサーチ機能（prices_daily / raw_financials 参照）
- OpenAI を用いたニュースセンチメント（news_nlp）・マクロセンチメント合成による市場レジーム判定
- 監視用 DB（SQLite）とロギング（stdout + 日次ローテーションファイル）を備えた運用向け設計
- ペーパートレードの検証レポート生成ツール

必要要件
--------
- Python 3.10+
- 推奨（主要ライブラリ）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証に任意）
- ファイルシステムに logs/ および data/ ディレクトリへの書き込み権限

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Linux / macOS)
     - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストールします（環境に合わせて必要パッケージのみインストールしてください）。
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 必要ディレクトリを作成します（ログ・DB・フラグファイル等）。
   - mkdir -p data logs

4. 環境変数を設定します。対話式ウィザードで .env を生成することを推奨します（下記参照）。

環境設定（.env）ウィザード
-------------------------
対話式で .env を作成・更新できます:
- 実行:
  - python -m kabusys.config_setup
- 生成される主な設定例（.env）:
  - KABUSYS_ENV (development | paper_trading | live)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL
  - DUCKDB_PATH (例: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, 例: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB)
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用、任意）
  - LOG_LEVEL（DEBUG/INFO/...）
  - KILL_FLAG_CLEAR_ON_START（0/1）

自動読み込み:
- デフォルトではプロジェクトルートの .env/.env.local が自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

設定検証
--------
起動前に設定の妥当性を検証できます:
- python -m kabusys.validate_config
- --strict を付けると警告も FAIL 扱い（exit 1）になります:
  - python -m kabusys.validate_config --strict

実行方法（主要スクリプト）
-------------------------
- Execution Engine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db を使用します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動しません。
    - 停止は data/stop_requested.flag を作成することでシグナルを送れます。
    - エンジンは別スレッドで run_session を実行し、メインスレッドがフラグ検知で停止させます。
    - PID は data/execution.pid に書き込まれます（settings.pid_file_path を参照）。

- Monitoring（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - Monitoring は Settings.env に関わらず本番用 sqlite_path を使用して監視ログを永続化します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH で SQLite DB を指定（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI 関連（ニュースセンチメント / レジーム判定）:
  - ニューススコア生成（プログラム的呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - 注意: OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

主要モジュール / API の概要
--------------------------
- kabusys.config
  - Settings クラス: 環境変数をラップして提供（KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
  - .env 自動読み込みロジックを含む。

- kabusys.config_setup
  - .env の対話式ウィザード。

- kabusys.validate_config
  - 環境変数・config/*.yaml 等の起動前検証ツール。

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト（プロセス優先度設定・DB 接続・BrokerFactory 組み立て等）。

- kabusys.run_monitoring
  - SystemMonitor をポーリングして監視ログを記録するスクリプト。

- kabusys.monitoring
  - monitoring_db: SQLite テーブル作成 / 永続化 API
  - system_monitor: CPU/メモリ/ディスク/データ鮮度/プロセス生存確認
  - trade_monitor: 発注・約定ログの監視（滞留注文・価格異常など）（実装ファイルあり）
  - risk_monitor: ドローダウン・ポジション上限の監視
  - kill_switch: risk 条件に応じた kill.flag 書き込み
  - monitoring_engine: 各 monitor を束ね、アラート送信や kill switch 評価を行う

- kabusys.execution
  - BrokerFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler 等（発注系コンポーネント）

- kabusys.portfolio
  - portfolio_builder: 候補選定・スコア順ソート・等重み/スコア重み計算
  - position_sizing: 株数決定・単元株丸め・集約キャップ処理（risk_based / equal / score）
  - risk_adjustment: セクターキャップ適用・レジーム乗数

- kabusys.research
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB 使用）
  - feature_exploration: 将来リターン計算・IC（Spearman）計算・統計サマリー等

- kabusys.ai
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルへ書き込み
  - regime_detector: ETF (1321) の MA 乖離とマクロニュース LLM スコアを合成して日次レジームを判定

- kabusys.utils
  - logging_setup: 標準化されたログ設定（stdout + TimedRotatingFileHandler）
  - process_priority: Windows / POSIX に応じたプロセス優先度・CPU affinity 設定

重要な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（paper_trading モード時に使用）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- LOG_LEVEL / LOG_DIR: ログ出力制御
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリア（1 にするとクリア）

ディレクトリ構成
----------------
(重要なファイルのみ抜粋)

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定
    - process_priority.py          — 優先度設定
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
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

運用上の注意
------------
- 本番環境 (KABUSYS_ENV=live) 設定時は特に kill switch・LINE 通知などの設定を確認してください（validate_config でチェックできます）。
- .env は機密情報を含むため絶対に Git に含めないでください（config_setup は .env を生成しますが README ヘッダーにも注意喚起を出します）。
- OpenAI を使用するモジュールは API コストが発生します。API キーと利用上限に注意してください。
- monitoring はデフォルトで本番 sqlite_path を使用します。モニタリング DB を分離する場合は SQLITE_PATH を調整してください。
- プロセス優先度設定は OS の許可が必要です。psutil による操作で権限不足の警告が出る場合がありますが動作継続します。

貢献 / 開発
-----------
- 追加の依存を requirements.txt にまとめる場合は project ルートに配置してください。
- ユニットテストや CI の導入は推奨します（AI 部分や外部 API 呼び出しはモックでのテストを想定）。

参考コマンドまとめ
------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はリポジトリ内のコード構成と実行フローの要点をまとめたものです。詳細な設計やアルゴリズムの説明（PortfolioConstruction.md や StrategyModel.md 等 referenced）はコード内の docstring コメントや別途提供される設計ドキュメントを参照してください。質問や追加のドキュメント要望があれば教えてください。