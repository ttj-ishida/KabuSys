# KabuSys

日本株向け自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要モジュールを元に、概要・機能・セットアップ・使い方・ディレクトリ構成を日本語でまとめたものです。

注意: 実運用（LIVE）環境での使用は自己責任で行ってください。本リポジトリには実際の発注処理を含むコンポーネントがあります。必須環境変数（API トークン等）は必ず適切に管理してください。

---

プロジェクト概要
- KabuSys は日本株の自動売買を想定したシステムで、戦略・ポートフォリオ構築・発注（ExecutionEngine）・監視（Monitoring）・研究（Research）・AI（ニュース NLP / レジーム検出）などのコンポーネントを含みます。
- SQLite / DuckDB をデータ永続化に使用し、環境変数および .env による設定をサポートします。
- Paper Trading（ペーパートレード）モードを用意しており、本番 DB と分離して動作させられます。
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント評価やマクロセンチメントを行うモジュールを含みます。

主な機能一覧
- Execution Engine
  - Broker クライアントの抽象化（本番/モック化で切替）
  - 注文管理、リスク管理、照合（reconciler）など
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパーデータベースに記録
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存確認、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常価格チェック
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 上記モニタを束ねて定期ポーリング、Alert 通知の呼び出し
- Portfolio（純粋関数群）
  - 候補選定、等重/スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（情報係数）・統計要約
- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとの sentiment を ai_scores に保存
  - regime_detector: ETF (1321) の MA200 とマクロニュースを合成して daily market_regime を判定
- ユーティリティ
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report）

セットアップ手順（ローカル開発用）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - 本 README は requirements.txt を含めていません。主要な依存は以下の通りです：
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で YAML チェックをする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml
   - 実際はプロジェクト配布パッケージや requirements.txt があればそちらを使ってください。
4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABUSYS_ENV (development | paper_trading | live)
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH, SQLITE_PATH（必要に応じて）
   - 生成後、設定の検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告も失敗扱いになります
5. データフォルダを作成（必要に応じて）
   - デフォルト DB / PID / フラグ等は data/ 以下を参照します。存在しない場合はコード内で自動作成される箇所もありますが、手動で作成しておくと安全です。

基本的な使い方（実行例）
- 実行エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト data/paper_trading.db）へ記録し、MockBrokerClient が使用されます。
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
    - 実行中に同フラグを作成すると終了処理が走ります（run loop で定期チェック）。
    - 実行プロセスは PID を data/execution.pid（デフォルト）に書きます。
- 監視プロセスを起動（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 挙動:
    - 監視用 DB は Settings.sqlite_path（デフォルト data/monitoring.db）を常に使用します（環境に依らず本番監視 DB を使用）。
    - SystemMonitor がプロセス生存やデータ鮮度をチェック、TradeMonitor / RiskMonitor と連携して KillSwitch を評価します。
    - 停止は data/stop_requested.flag を作成することで行えます（両 run_* スクリプトでチェック）。

停止・フラグについて
- data/stop_requested.flag
  - run_execution/run_monitoring が起動中にこのファイルの存在をチェックし、見つかればループを終了またはエンジンを停止します（外部からの停止指示）。
- data/kill.flag
  - KillSwitch がリスク条件（大きなドローダウンやポジション上限超過）を検出したときに書き込み、ExecutionEngine 側で kill.flag を検出して停止する等の仕組みを想定しています（Settings.kill_flag_path 参照）。
- KILL_FLAG_CLEAR_ON_START
  - Settings で起動時に kill.flag を自動でクリアするかどうかを設定できます（本番では 0 推奨）。

ツール／ユーティリティ
- 環境ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 引数によりレポート期間・DB パスを指定可能。デフォルト DB はデータフォルダの paper_trading.db。
- AI 関連（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニューススコアを ai_scores テーブルへ書き込みます。api_key が None の場合は環境変数 OPENAI_API_KEY を参照。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定を行い market_regime テーブルに書き込みます。

主要設定（環境変数）
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 役立つ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - OPENAI_API_KEY: AI 機能利用時
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: Monitoring DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用監視 DB（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレード時の約定モード（instant|partial|never|reject）
  - LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - MONITOR_POLL_INTERVAL: run_monitoring でのポーリング秒数（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数ロード・Settings クラス（.env 自動ロード機能を含む）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py (実装途中の可能性あり)
  - execution/ (発注関連: order_manager, order_repository, execution_engine 等 — 本リポジトリの一部抜粋に依存)
  - utils/
    - process_priority.py
  - data/ (実行時に使用する DB / PID / flag を配置する想定)

設計上の注意点 / 運用メモ
- Monitoring は monitoring.sqlite（Settings.sqlite_path）を常に参照します。環境にかかわらず監視 DB に書き込みます。
- ExecutionEngine は KABUSYS_ENV により本番 DB と Paper Trading DB を切り替えます（分離設計）。
- AI API（OpenAI）利用時は API キーと利用料に注意。API 通信はリトライ／バックオフ処理があるものの、失敗時は安全側のフォールバック（0.0 等）を行う設計です。
- process priority / CPU affinity 設定を行うユーティリティがあり、起動時に優先度を "high" に設定する処理が入っています（set_process_priority）。
- .env は絶対に Git にコミットしないでください（config_setup 画面やファイルヘッダにも注意書きあり）。

追加情報・拡張
- config/*.yaml（system_config.yaml 等）が参照される想定の箇所があります。validate_config はそれらの存在・YAML パースの確認を行います（PyYAML がインストールされている場合）。
- DuckDB を分析用に用意し、research モジュールは prices_daily / raw_financials 等のテーブルを前提にしています。データ準備パイプラインは kabusys.data.pipeline 系に実装されている想定です（本 README に含まれるコード抜粋外のモジュールに依存します）。

以上がこのコードベースの概要・導入・基本的な運用手順です。必要であれば以下についてさらに詳しいドキュメント（例: 各モジュールの API、ExecutionEngine の起動引数・設定項目、データベーススキーマ定義、運用チェックリスト）を作成します。どの項目を詳細化したいか指示してください。