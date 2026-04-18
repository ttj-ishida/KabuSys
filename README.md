README
=====

概要
----
KabuSys は日本株の自動売買とそれを支える分析・監視ツール群を含む Python パッケージです。本リポジトリは以下の主要機能を備えます。

- 発注エンジン（ExecutionEngine）と監視ループ（Monitoring）
- ペーパートレード用の分離された DB サポート
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- ファクター計算・研究ユーティリティ（DuckDB を想定）
- ニュース NLP による銘柄センチメント集計（OpenAI API）
- 監視 / リスク検知（稼働率、データ鮮度、ドローダウン、滞留注文等）
- 各種 CLI ツール（.env ウィザード、設定検証、Paper Trading レポート）

主な提供物
-----------
- 実行スクリプト
  - run_execution.py — ExecutionEngine の起動
  - run_monitoring.py — SystemMonitor のポーリングループ起動
- 設定管理
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前チェック
  - config.py — Settings クラス（環境変数 / .env の読み取りロジック）
- 監視
  - monitoring/* — SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, SQLite 永続層
- ポートフォリオ構築（純粋関数）
  - portfolio/* — 銘柄選定、重み計算、リスク調整、株数決定
- 研究/分析
  - research/* — ファクター計算、特徴量探索
- AI（OpenAI 連携）
  - ai/news_nlp.py — ニュース記事を LLM でスコアリングして ai_scores へ書き込み
  - ai/regime_detector.py — マーケットレジーム判定
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成
- ユーティリティ
  - utils/logging_setup.py — 統一ログ設定
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定

機能一覧
--------
- 環境変数ベースの柔軟な設定（.env/.env.local の自動ロード、無効化オプションあり）
- ExecutionEngine と MonitoringEngine の起動・停止（フラグファイル経由の停止）
- paper_trading モードでは Mock ブローカー & 専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
- 監視ログ・発注ログの SQLite 永続化（schema は init_monitoring_db で自動作成/マイグレーション）
- DuckDB を利用した時系列データ分析・ファクター計算
- OpenAI を用いたニュースセンチメント & マクロセンチメント集計（リトライ・バリデーション実装）
- ログは stdout と日次ローテートファイルに出力（logs/<app_name>.log）

セットアップ手順
----------------

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - openai (AI 機能利用時)
     - PyYAML（設定検証で YAML 検証を有効にする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. .env の作成
   - 対話型ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に .env をプロジェクトルートに置く
   - 自動ロードを無効にする場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数で設定

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 厳格モード（警告を失敗扱い）:
     - python -m kabusys.validate_config --strict

主要な環境変数と既定値
-----------------------
（代表的なもの）

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
- KABU_API_PASSWORD: 必須（kabuステーション API）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db（paper_trading モード用）
- LOG_LEVEL: デフォルト INFO
- OPENAI_API_KEY: OpenAI を利用する場合は設定が必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（'1' で有効、デフォルト '0'）

使い方（主要コマンド）
--------------------

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 起動前に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中は data/execution.pid に PID を書きます。

- Monitoring 起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（本番 DB）を参照します（監視は環境に関係なく本番 DB を使用する設計）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db）

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  または OPENAI_API_KEY 環境変数を使用
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

監視と停止（Kill Switch / フラグ）
--------------------------------
- 実行制御はファイルフラグ方式を採用しています。
  - data/kill.flag — KillSwitch により ExecutionEngine を停止させるためのフラグ（存在すると停止シグナル）
  - data/stop_requested.flag — run_execution / run_monitoring 停止のためのローカルフラグ
  - data/execution.pid — 実行中の PID 保存
- Run スクリプトはループ内で stop_requested.flag の存在を監視し、検出したら穏やかに停止します。
- KillSwitch は RiskMonitor 等から呼ばれ、条件に合致すれば kill.flag を生成します（冪等）。

ログ
----
- setup_logging で stdout と logs/<app_name>.log（日次ローテーション）に出力します。
- 環境変数:
  - LOG_LEVEL（デフォルト INFO）
  - LOG_DIR（デフォルト logs/）
- ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。

データベース
-----------
- monitoring の永続化は SQLite（Settings.sqlite_path）を使用します。init_monitoring_db() がテーブル作成・簡易マイグレーションを行います。
- 分析／研究用の時系列データは DuckDB（Settings.duckdb_path）を使う設計です。
- paper_trading モードでは paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を利用して本番 DB と完全に分離します。

注意事項 / トラブルシューティング
---------------------------------
- OpenAI 機能を使う場合は OPENAI_API_KEY を設定してください。未設定だと例外になります。
- psutil によるプロセス優先度設定は管理者権限が必要な場合があります。失敗時は警告が出て処理は継続します。
- MONITOR_POLL_INTERVAL には 1 以上の整数を指定してください。不正値の場合はデフォルトの 60 秒にフォールバックします。
- .env は絶対にリポジトリにコミットしないでください（config_setup が警告を出します）。
- DuckDB / SQLite ファイルの親ディレクトリが存在しない場合、validate_config は警告を出しますが起動時に自動作成されることがあります。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトの主要ファイル・ディレクトリ例:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - tools/
      - __init__.py
      - paper_verification_report.py
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
- data/            # DB・flag・pid などのランタイムファイル配置場所（デフォルト）
- logs/            # ログ出力先（デフォルト）

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスや貢献ルールを追記してください）

補足
----
- 本 README はコードベース内の docstring・コメントをもとに作成しています。実際の運用では config/*.yaml や .env を必ず確認の上、KABUSYS_ENV=live 設定時には特に注意してデプロイしてください。
- さらなる詳細（API 仕様や内部アルゴリズムの理論）は各モジュールの docstring や設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）を参照してください。