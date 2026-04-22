KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なコードベースです。  
主な機能は以下の通りです：バックテストや実取引の ExecutionEngine（発注制御）、システム監視／アラート、ポートフォリオ構築ロジック、ファクター計算・リサーチ、ニュース NLP による LLM ベースのセンチメント評価（OpenAI 使用）、ペーパートレード検証レポート生成など。

主要な設計方針（抜粋）
- 環境（.env / 環境変数）中心の設定管理（自動ロードあり）。
- DuckDB を分析用 DB、SQLite を監視・発注履歴用に使用。
- Paper Trading（分離された SQLite）をサポートし、本番 DB とデータ分離。
- LLM 呼び出しはフェイルセーフ設計（リトライ・部分失敗時の保護）。
- ロギング・プロセス優先度設定・Kill Switch など運用周りのユーティリティを提供。

機能一覧
--------
- 実行（Execution）
  - ExecutionEngine（発注、リコンシリエーション、リスク制御） — run_execution.py で起動
  - Paper trading モードの分離（PAPER_TRADING_SQLITE_PATH を使用）
- 監視（Monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor を束ねる MonitoringEngine — run_monitoring.py で起動
  - Kill Switch（条件で data/kill.flag を書き込み Execution を停止）
  - 監視ログの永続化（SQLite; monitoring_db）
- ポートフォリオ構築
  - 候補選定、配分（等金額／スコア加重）、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元丸め、利用可能現金でのスケール）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、特徴量サマリ
- AI（OpenAI）
  - ニュース NLP による銘柄別センチメントスコア生成（ai.news_nlp）
  - 市場レジーム判定（ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- 開発／運用ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ログ設定ユーティリティ（utils.logging_setup）
  - プロセス優先度設定 / CPU affinity（utils.process_priority）

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 記法などを使用）
- システムに DuckDB/SQLite/psutil をインストール可能であること

1. リポジトリをクローン／配置
   - ソースは src/kabusys 以下に配置されています。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係のインストール
   - 最低限:
     - duckdb
     - psutil
     - openai (AI機能を使用する場合)
     - PyYAML（config の YAML 検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合はそれを使ってください。）

4. .env の初期作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）。

   重要な環境変数（抜粋）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development | paper_trading | live） — デフォルト: development
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
   - OPENAI_API_KEY（AI 機能を使う場合）
   - LOG_LEVEL（DEBUG/INFO/...）
   - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject）
   - MONITOR_POLL_INTERVAL（監視ループの秒間隔、run_monitoring 用）

   自動ロード
   - 実行時にプロジェクトルートの .env（および .env.local）を自動で読み込みます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - すべて確認したければ --strict を付けて警告も失敗扱いにできます。

6. DB 初期化
   - run_monitoring / run_execution は起動時に必要なテーブルを（冪等で）作成します。
   - 手動での準備は原則不要。

使い方（よく使うコマンド）
-------------------------
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 SQLite に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID を書く（設定に依存）。
    - プロセス優先度を "high" に設定します（可能な環境で）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は常に（KABUSYS_ENV にかかわらず）本番用の sqlite_path を使用します（monitoring 用 DB）。
  - 停止制御:
    - プロジェクトルート/data/stop_requested.flag を作成すると監視ループは終了します。
    - Kill Switch として data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります（KillSwitch により書き込み）。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH で既定 DB を変更可能。

運用上のファイル / フラグ
-------------------------
- data/stop_requested.flag
  - 監視・実行スクリプトがループを終了するための外部停止フラグ（存在を検知して停止）。
- data/kill.flag
  - Kill Switch が条件を満たしたときに書き込まれ、ExecutionEngine に停止を促す。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動的にクリアされる（本番では 0 推奨）。
- data/execution.pid
  - ExecutionEngine の PID を記録するファイル（存在すれば再起動や stale PID の検出に使われる）。

ディレクトリ構成（主要ファイル）
-----------------------------
以下は src/kabusys 内の主要モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン情報など）
  - config.py — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

- src/kabusys/utils/
  - logging_setup.py — ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
  - process_priority.py — プロセス優先度／CPU affinity 設定ユーティリティ

- src/kabusys/monitoring/
  - monitoring_db.py — SQLite テーブルの作成・読み書き API
  - monitoring_engine.py — 各 Monitor の束ね・ポーリングループ
  - system_monitor.py — システム／データ鮮度監視
  - trade_monitor.py — 発注ログ・滞留注文検出（コードベースに含まれる想定）
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — フラグ書き込みによる停止判定
  - alert_manager.py — アラート（LINE 等）送信管理（コードベースに含まれる想定）

- src/kabusys/execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py 等
    （Execution の実装とブローカー抽象化）

- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ等

- src/kabusys/ai/
  - news_nlp.py — ニュースセンチメントの LLM スコアリング（OpenAI）
  - regime_detector.py — マクロ + ETF MA によるレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

注意事項 / 運用メモ
------------------
- 本番環境（KABUSYS_ENV=live）の設定は慎重に扱ってください。validate_config は live 環境に関するいくつかのガードを出します（LINE 設定や KILL_FLAG_CLEAR_ON_START の警告など）。
- AI 機能（news_nlp / regime_detector）を使用するには OPENAI_API_KEY が必要です。キーの扱いは .env にて管理してください。
- monitoring はデフォルトで MONITOR_POLL_INTERVAL=60 秒です。環境変数で上書き可能です。
- Paper Trading は production DB と完全分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ログは logs/<app_name>.log に日次ローテートで保存されます。LOG_DIR を指定するかデフォルトの logs ディレクトリを使用します。
- process_priority など OS 権限の関係で設定に失敗する場合があるため、ログの警告を確認してください。

付録：よく使うコマンド一覧
--------------------------
- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

質問やドキュメントの追加希望があれば教えてください。README に追記すべきサンプル .env や運用手順（systemd ユニット例・Dockerfile など）も作成できます。