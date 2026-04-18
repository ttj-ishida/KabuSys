KabuSys — 日本株自動売買システム
================================

本ドキュメントは、このリポジトリ（KabuSys）の概要、主要機能、セットアップ手順、使い方、およびディレクトリ構成をまとめた README です。コードは Python3 で記述されており、ローカル/ペーパートレード/本番の切替・監視・レポーティング機能を備えた設計になっています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買フレームワークです。主な目的は以下の通りです。

- データ取得・分析（DuckDB を用いたファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定・重み付け・位置サイズ計算）
- ExecutionEngine による発注（本番・ペーパートレード分離）
- 監視（プロセス/システム状態、注文・リスクの監視）と KillSwitch による安全停止
- AI 補助（ニュース NLP によるセンチメント評価・レジーム判定）
- 運用支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

主な機能一覧
--------------
- 環境設定
  - 対話式ウィザードで .env を生成（kabusys.config_setup）
  - 自動ロード機能（.env / .env.local。ただし無効化可）
- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV による動作切替（development / paper_trading / live）
  - paper_trading モードでは MockBrokerClient を使用し、専用 DB に記録
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視用 SQLite（monitoring.db）への永続化（monitoring.monitoring_db）
  - ポーリングループ起動スクリプト（run_monitoring.py）
  - KillSwitch（data/kill.flag）による安全停止シグナル
- ポートフォリオ構築（純粋関数群）
  - 候補選定、等金額／スコア加重、リスク調整（セクターキャップ／レジーム乗数）、ポジションサイズ計算
- リサーチ機能
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリ
- AI 機能（OpenAI）
  - ニュース記事を LLM で評価し銘柄ごとのスコアを ai_scores に保存
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定
- 運用ツール
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
-----------------
前提:
- Python 3.9+（プロジェクトの Python バージョン要件に合わせてください）
- OS：Linux / macOS / Windows（psutil がサポートしていれば優先度設定等が動作）

1. リポジトリをクローンしてソースルートへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須（プロジェクトで利用されている主なライブラリ）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - 注意: 実際の requirements.txt がある場合はそれを使用してください。

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 主要な環境変数（最低限設定すべきもの）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live。デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
     - LOG_LEVEL（例: INFO）
   - 自動読み込み:
     - config.Settings モジュールはプロジェクトルートに .env / .env.local があれば起動時に自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. DB やディレクトリの作成
   - スクリプト実行時に必要なディレクトリ（data/ や logs/）は自動作成される場合がありますが、権限等で失敗することがあるため事前に用意することを推奨します。

使い方（主要コマンド）
--------------------

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで終了コード 1 を返す

- 実行エンジン起動（ExecutionEngine）
  - 本番/ペーパートレード切替:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 特記事項:
    - paper_trading モードでは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します（本番 DB と分離）。
    - run_execution は起動時に data/stop_requested.flag（← stop を要求する外部フラグ）をチェックします。存在する場合は起動せず終了します。
    - プロセス優先度が起動時に "high" に設定されます（psutil の権限に依存して失敗する場合あり）。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒数）を上書き可能（デフォルト 60）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず本番向け監視 DB を使う仕様）。
  - run_monitoring は data/stop_requested.flag を検出するとループを終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数 PAPER_TRADING_SQLITE_PATH で DB を指定可能

- AI / リサーチ用関数（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡してニュース NLP を実行し ai_scores に保存します（OPENAI_API_KEY 必須）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 研究用関数は kabusys.research 以下にまとまっています（calc_momentum / calc_volatility / calc_value / calc_ic 等）。

運用時の注意点
--------------
- Kill Switch / Stop フラグ
  - ディレクトリ data/ に置かれる kill.flag（KillSwitch が書き込む）により ExecutionEngine 停止を指示できます。
  - run_monitoring / run_execution は stop_requested.flag を使ってループを終了させる仕組みを持ちます。
  - KILL_FLAG_CLEAR_ON_START=1 を .env に設定すると起動時に kill.flag を自動クリアしますが、本番では推奨されません。

- ログ
  - ログはデフォルト logs/<app_name>.log に日次ローテーションで保存（30日分保持）。
  - LOG_DIR 環境変数で出力先を変更可能。ログ設定は kabusys.utils.logging_setup.setup_logging で統一。

- 環境分離
  - paper_trading は DB を分ける等、発注ロジックの分離を意識した実装になっています。実行前に env の設定を必ず確認してください（特に KABUSYS_ENV=live の場合）。

- OpenAI / 外部 API
  - AI 機能は OPENAI_API_KEY が必要です。API エラーやレート制限の扱いは実装に組み込まれていますが、API 使用量には注意してください。

ディレクトリ構成（主なファイル・モジュール）
-----------------------------------------
以下は src/kabusys 配下の主要モジュールと簡単な説明です（抜粋）：

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（.env 自動読み込み機能）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度・CPU affinity 設定
  - monitoring/
    - monitoring_db.py — 監視ログ用 SQLite 層（テーブル作成・CRUD）
    - system_monitor.py — システム状態・データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — KillSwitch 実装（kill.flag 書込み）
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py (参照) — 通知用（LINE 等）※実装ファイルが含まれる可能性あり
    - trade_monitor.py (参照) — 注文監視（滞留・異常約定検出）※実装ファイルあり
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など
      - ExecutionEngine と注文周りの実装（run_execution から起動）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 単元丸め・ポジションサイズ計算
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - data/
    - pipeline.py, stats.py など（DuckDB 連携のユーティリティ）
  - ai/
    - news_nlp.py — OpenAI を用いたニューススコアリング
    - regime_detector.py — レジーム判定（ETF MA + マクロセンチメントの合成）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

補足：環境変数一覧（主要）
-------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API（必須）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API（AI 機能使用時）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — instant | partial | never | reject（paper_trading の約定挙動）
- LOG_LEVEL — ログレベル（例: INFO）
- LOG_DIR — ログ保存先ディレクトリ
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（"1"/"0"。本番では推奨しない）

ライセンス・コントリビュート
---------------------------
- 本リポジトリのライセンス等は別途 LICENSE ファイルを参照してください。
- コントリビュートする場合は PR 前に動作確認・テストを推奨します。

問い合わせ
----------
- 実装や挙動についての質問があれば、リポジトリの Issue を作成してください。実運用に関する質問・アドバイスが必要な場合は事前に設定ファイル（.env）や使用する DB のバックアップを行ってください。

以上。必要であれば README にチュートリアル（実際の起動例、Dockerfile、systemd ユニット例など）を追加できます。希望があれば追記します。