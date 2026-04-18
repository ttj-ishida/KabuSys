# KabuSys

日本株向け自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、注文実行エンジン、監視（モニタリング）、ポートフォリオ構築、ファクター研究、AI（ニュースNLP／レジーム判定）などを含む自動売買基盤のコア部分を収めています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要条件（依存関係）
- セットアップ手順
- 使い方（主要スクリプト／コマンド）
- 環境変数（重要な設定）
- ファイル／ディレクトリ構成

---

プロジェクト概要
- 実運用を想定した日本株自動売買の基盤ライブラリ群。
- ExecutionEngine による発注ロジック、RiskManager によるリスク制御、Monitoring による稼働監視と Kill Switch、DuckDB を用いたリサーチ用データ処理、OpenAI を使ったニュースセンチメント評価などを備えます。
- 設定は .env（および .env.local）で管理。環境ごとに paper_trading（ペーパートレード）／live（本番）／development（開発）を切替可能。

主な機能一覧
- Execution
  - ExecutionEngine（発注エンジン）、OrderManager、OrderRepository、RiskManager、Reconciler 等
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード DB に記録（本番 DB と完全分離）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス状態・データ鮮度の監視と永続化
  - TradeMonitor / RiskMonitor / MonitoringEngine: 各種チェックとアラート、Kill Switch 連携
  - monitoring DB 初期化ユーティリティ
- Portfolio construction
  - 候補選定、重み計算（等金額・スコア加重）、ポジションサイジング、セクター上限調整、レジーム乗数
- Research
  - DuckDB を用いたファクター計算（Momentum/Value/Volatility）、将来リターン計算、IC 計算など
- AI
  - ニュース NLP（OpenAI）で銘柄ごとのセンチメントスコアを生成して ai_scores に格納
  - レジーム判定（ETF + マクロニュース + LLM）を market_regime に永続化
- ユーティリティ
  - .env 対話型ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ロギング設定、プロセス優先度・CPU affinity 設定ユーティリティ

必要条件（依存関係）
- Python 3.10+（型注釈に `X | Y` を使用）
- 推奨パッケージ（最低限動かすためのもの）
  - duckdb
  - psutil
  - openai （AI 機能を使う場合）
  - PyYAML（config/*.yaml 検証を行う場合、install しなくても動作するが警告が出る）
- インストール例:
  - pip install duckdb psutil openai PyYAML

セットアップ手順
1. リポジトリをクローン／展開する
2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   - pip install duckdb psutil openai PyYAML
4. .env の準備
   - 対話型ウィザードで作成:
     - python -m kabusys.config_setup
   - または、現行の .env.example を参照して手動作成
   - 重要な必須変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （必要に応じて）OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など
   - 自動読み込み:
     - パッケージの config モジュールはプロジェクトルートに .env/.env.local があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. データディレクトリ（デフォルト: data/）とログディレクトリ（logs/）の確認
   - 多くのスクリプトはデフォルトで data/*.db と logs/*.log を使用します。必要なら事前に作成してください（logging_setup が存在しなければ自動作成を試みます）。

主要なデフォルトパス（Settings）
- DuckDB: data/kabusys.duckdb （環境変数 DUCKDB_PATH で変更可能）
- SQLite（監視 DB）: data/monitoring.db （SQLITE_PATH で変更可能）
- Paper trading SQLite: data/paper_trading.db （PAPER_TRADING_SQLITE_PATH で変更可能）
- PID / Kill flag: data/execution.pid, data/kill.flag
- ログ: logs/<app_name>.log（daily ローテーション）

使い方（主要スクリプト／コマンド）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き（デフォルト 60）
  - 監視用 DB は Settings.sqlite_path（monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用）
  - 停止: リポジトリルート/data/stop_requested.flag ファイルを作成するとループが終了します
- ExecutionEngine（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます
  - 起動時に data/stop_requested.flag が存在する場合は起動をスキップします
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能
- AI 関連（ライブラリ関数として使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュースセンチメントを ai_scores テーブルに保存
    - api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム判定を実行して market_regime に書き込む
- ログ
  - 全スクリプトは kabusys.utils.logging_setup.setup_logging を使用して logs/<app_name>.log に日次ローテーション出力します
- 停止／Kill Switch
  - KillSwitch は条件に応じて data/kill.flag を書き込みます（ExecutionEngine はこれを検知して停止する設計）
  - 手動で ExecutionEngine を停止したい場合: data/stop_requested.flag を作成（スクリプト側でチェックして安全に停止します）

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
- LOG_LEVEL（デフォルト INFO）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔。run_monitoring で使用）

ディレクトリ構成（主なファイルと説明）
- src/kabusys/
  - __init__.py — パッケージ初期化（__version__）
  - config.py — 環境変数読み込み・Settings 定義（.env 自動ロードロジックを含む）
  - config_setup.py — .env 対話式ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — 統一ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログの永続化層（初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - trade_monitor.py — （存在する想定の）取引監視ロジック
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — （アラート送信仕組み）
  - execution/ (発注に関する実装群)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数・資金割当計算
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Value / Volatility などのファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC 計算、統計サマリー
  - ai/
    - news_nlp.py — ニュース記事のセンチメントスコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF + マクロ + LLM）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

補足・運用上の注意
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- 本番（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0 にすることを推奨します。自動クリア（1）は危険です。
- Monitoring は監視用 DB を初期化するためのスクリプトを含みますが、実運用前に python -m kabusys.validate_config で設定チェックを行ってください。
- OpenAI を利用する機能は API 呼び出しに失敗した場合もフォールバックを行う設計ですが、API キーの管理・コストに注意してください。
- 各モジュールはユニットテストや運用ログを通して動作を確認することを推奨します。DuckDB／SQLite のスキーマやマイグレーションは monitoring_db.init_monitoring_db に実装されています。

問い合わせ・貢献
- この README はコードベースの主要な使い方と設計をまとめたものです。実装詳細や拡張（ブローカ実装追加、アラートチャネル追加等）については該当モジュールの docstring を参照してください。
- バグ報告やプルリクエストはリポジトリの issue/PR を通じてお願いします。

以上。