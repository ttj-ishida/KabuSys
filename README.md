KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのパッケージ化されたコードベースです。  
システム監視（Monitoring）、注文実行（Execution）、ポートフォリオ構築、ファクター計算・リサーチ、AI を使ったニュース評価などのコンポーネントを含みます。  
設計上、実行環境（development / paper_trading / live）に応じて挙動を切り替え、Paper Trading モードでは本番 DB と完全に分離された専用の SQLite を使って検証できます。

主な特徴
--------
- ExecutionEngine と Monitoring の起動スクリプト（run_execution, run_monitoring）
- Paper Trading と Live の明確な分離（paper_trading 用の専用 SQLite）
- 監視データ永続化（SQLite）と分析用 DuckDB（duckdb）
- Kill Switch（data/kill.flag）による安全停止機構
- RiskMonitor によるドローダウン / ポジション上限監視とアラート連携
- portfolio モジュール：候補選定・重み計算・ポジションサイズ算出（純粋関数）
- research：DuckDB を使ったファクター＆将来リターン計算、IC 等の統計関数
- ai モジュール：OpenAI を用いたニュースセンチメント評価・レジーム判定（フェイルセーフ実装）
- ユーティリティ群（ログ設定、プロセス優先度設定、.env ウィザード、設定検証、ツール類）
- 日次ローテート可能なログ（logs/<app_name>.log、TimedRotatingFileHandler）

セットアップ手順
----------------
以下は基本的なセットアップ手順です。実行する環境やパッケージ管理方法によって読み替えてください。

1. リポジトリをクローン／配置
   - パッケージは src/kabusys 配下にあります。プロジェクトルート（.git または pyproject.toml がある階層）を基準に .env の自動読み込み等が動作します。

2. 依存パッケージをインストール
   - 必要と思われる主要依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証時に有用）
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

3. データ / ログ ディレクトリを作成
   - デフォルトの SQLite / DuckDB / PID / flag は data/ 以下、ログは logs/ 以下に置かれます。多くのコードは自動で親ディレクトリを作成しますが、手動で用意しておくと安全です。
     - mkdir -p data logs

4. .env の作成（ウィザード推奨）
   - 環境変数を対話式に作成するには:
     - python -m kabusys.config_setup
   - 主要な必須変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY を設定（ai モジュール）

5. 設定検証
   - 作成後に設定を検証:
     - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする（本番前推奨）:
     - python -m kabusys.validate_config --strict

6. （任意）Paper Trading 用 DB 初期化
   - 実行・監視プロセスは起動時に監視用テーブルを自動作成します（init_monitoring_db）。Paper Trading のデータベースも同様に使用時に作られます。

使い方（主なコマンド）
---------------------
- 実行スクリプト
  - 監視ループ起動（Monitoring）
    - python -m kabusys.run_monitoring
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（デフォルト 60）
    - 監視は Settings の sqlite_path を常に本番パスで使用（監視は本番 DB を参照）
    - 停止はプロジェクトルート data/stop_requested.flag ファイルを作成すると検出して終了

  - ExecutionEngine 起動
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が既にある場合は起動を中止
    - 実行中に stop flag が作成されると Engine が停止するよう設計

- .env ウィザード / 設定検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- ツール
  - Paper Trading 検証レポート生成:
    - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
    - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ関数（プログラムからインポートして使用）
  - ai: kabusys.ai.score_news（OpenAI API キーが必要）
  - regime_detector: kabusys.ai.regime_detector.score_regime
  - research: kabusys.research.calc_momentum / calc_volatility / calc_value など

重要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- KABUSYS_ENV — 実行環境。development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API を使う機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading のフィル挙動（instant|partial|never|reject。デフォルト: instant）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1。デフォルト 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動ロードを抑止

自動 .env 読み込み
------------------
- プロジェクトルート（.git または pyproject.toml を基準）を探索して .env を自動でロードします。
- ロード順: OS 環境変数 > .env.local > .env
- テストなどで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

監視・停止フラグ
----------------
- stop_requested.flag
  - run_execution/run_monitoring はプロジェクトルートの data/stop_requested.flag を監視し、存在を検知すると安全に終了／停止します。
- kill.flag
  - KillSwitch は data/kill.flag を書き込んで ExecutionEngine に停止シグナルを送ります（Settings.kill_flag_path によりパスを変更可能）。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアできますが、本番では 0 を推奨します。

ログ
---
- ロギング設定は kabusys.utils.logging_setup.setup_logging で統一されます。
- コンソール出力（stdout）および日次ローテートされたファイル出力（logs/<app_name>.log）を組み合わせます。ファイルは既定で 30 日分保持されます。

ディレクトリ構成
----------------
（src/kabusys をルートとした主要ファイル／パッケージ。省略形で表示）

- src/kabusys/
  - __init__.py                      — パッケージ定義（__version__ 等）
  - config.py                        — Settings クラス（環境変数の読み取り・検証・デフォルト）
  - config_setup.py                  — .env 対話式作成ウィザード
  - validate_config.py               — 起動前設定検証 CLI
  - run_monitoring.py                — Monitoring ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading の検証レポート生成スクリプト
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py               — 監視用 SQLite テーブル定義・永続化 API
    - system_monitor.py              — システム状態・データ鮮度監視
    - trade_monitor.py               —（注文監視）※実装あり
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag 管理
    - monitoring_engine.py           — 各 Monitor を束ねる実行ロジック
    - alert_manager.py               —（アラート送信・管理）※実装あり
  - execution/
    - execution_engine.py            — ExecutionEngine 本体（run_session 等）
    - order_manager.py               — 注文管理
    - order_repository.py            — 注文の DB 永続化
    - broker_factory.py              — ブローカークライアント生成（Mock含む）
    - reconciler.py                  — 注文履歴再整合処理
    - risk_manager.py                — 発注時リスク制約チェック
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み算出
    - position_sizing.py             — 株数決定・単元丸め・利用可能現金へのスケーリング
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py         — forward return / IC / 統計サマリ等
  - ai/
    - news_nlp.py                    — ニュースを LLM で評価して ai_scores に書き込む
    - regime_detector.py             — MA + マクロセンチメントで市場レジーム判定
  - data/                             — 実行時に使うファイル（例: monitoring.db, paper_trading.db, kill.flag, execution.pid）
  - logs/                             — ログファイル出力先（デフォルト）

実装上の注意 / トラブルシューティング
---------------------------------
- 環境変数の未設定は Settings クラスで ValueError を投げる場合があります。必須変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を .env に設定してください。
- run_monitoring の MONITOR_POLL_INTERVAL は正の整数で指定してください。不正値はデフォルト 60 秒にフォールバックします。
- OpenAI を使う機能は OPENAI_API_KEY が必要です。API 呼び出しはリトライ・フォールバックを備えていますが、キーがない場合はエラーになります。
- プロセス優先度の設定は OS に依存し、権限不足で失敗する場合があります（警告ログが出ますが処理は続行します）。
- DuckDB / SQLite のパスは Settings で指定可能。Paper Trading では paper_sqlite_path が使用され、本番 sqlite_path とは分離されます。
- ログディレクトリが作成できない場合、ファイルハンドラは無効化されコンソール出力のみになります（警告が出ます）。
- monitoring_db.init_monitoring_db は冪等的にテーブルと必要なカラムを作成・マイグレーションします。既存 DB に対して実行しても安全な設計です。

開発・拡張について
------------------
- research / portfolio の多くの関数は純粋関数（副作用なし）で設計されており、ユニットテストが容易です。
- OpenAI 呼び出し部分は一箇所に集約され、テスト時にはモックへ差し替えられるよう設計されています（_call_openai_api を patch）。
- 将来的に銘柄ごとの lot_size や手数料モデルを拡張する余地がある設計です（position_sizing に TODO コメントあり）。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"

最後に
------
本 README はコードベースの主要部分を俯瞰するための概要です。各モジュールにはドキュメントストリングと詳細な実装コメントが付与されています。運用環境での本番稼働前には config_setup → validate_config --strict → ステージングでの検証 を必ず実行してください。