KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模フレームワークです。  
主な目的は次のとおりです。

- 戦略（ファクター・ポートフォリオ構築・ポジションサイズ計算）に基づく銘柄選定と発注ロジック
- 実行エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネント
- DuckDB を用いたリサーチ / ファクター計算
- OpenAI を使ったニュース NLP や市場レジーム判定（任意）
- Paper Trading 用の分離された DB を利用した検証機能

主な機能一覧
-------------
- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（paper_trading モード時は MockBroker を使用し DB を分離）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（監視ログを SQLite に保存）
- 設定関連
  - config_setup.py: .env を対話式に作成/更新するウィザード
  - validate_config.py: 環境変数と config/*.yaml を起動前に検証
- 監視
  - monitoring/*: SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine（アラート発火や kill.flag による安全停止）
  - monitoring_db: 監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）永続化
- リサーチ / ファクター
  - research/*: モメンタム、ボラティリティ、バリューなどのファクター計算、IC計算、将来リターン計算
  - DuckDB 接続を受け取り prices_daily / raw_financials などのテーブルを参照
- ポートフォリオ構築
  - portfolio/*: 候補選定、重み計算（等金額 / スコア加重）、セクター制約、ポジションサイズ計算（単元丸め・上限・スケーリング）
- AI（任意）
  - ai/news_nlp.py: ニュースを LLM でスコアリングし ai_scores に保存
  - ai/regime_detector.py: ETF / マクロニュースを組み合わせて市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成（稼働率・成立率・レイテンシ等の判定）

前提・依存
-----------
必須（最低限）:
- Python 3.9+
- sqlite3（標準ライブラリ）
推奨 / 任意パッケージ:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（validate_config の YAML 検証を使う場合）

例:
pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリをクローン（あるいは src 以下を配置）
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. 環境変数の初期化
   - 対話式ウィザードで .env を作成（推奨）:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants 用）
     - KABU_API_PASSWORD（kabuステーション API 用）
   - 代表的な設定（.env に記載される例）:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=（AI機能使用時）
     - LOG_LEVEL=INFO
5. 設定の検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict
6. ディレクトリ準備
   - data/ と logs/ は多くの処理で自動作成されますが、権限等に注意してください。

使い方（主要コマンド例）
-----------------------
- 実行エンジン起動（本番/ペーパートレード判定は KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - ペーパートレード用 DB を使う: KABUSYS_ENV=paper_trading を .env に設定
  - 実行中停止: data/stop_requested.flag を作成すると安全に停止します
  - ExecutionEngine の PID は data/execution.pid に書き込まれます

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 0 以下は無効でデフォルト 60 秒にフォールバック
  - 監視は常に本番 sqlite_path を使って監視ログを記録します（環境にかかわらず）

- .env の作成・更新（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると warning を fail と見なす

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY または関数呼び出し時に渡す）
  - モジュール関数を直接呼ぶ（例: kabusys.ai.score_news）
  - 注意: API 呼び出しはリトライ・バックオフを組んであるが、キーが無いと例外が発生します

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、発注は MockBrokerClient に流れ、data/paper_trading.db を使用
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能で必須）
- LOG_LEVEL（デフォルト: INFO）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒単位）

ログ・データ
------------
- ログ: デフォルト logs/<app_name>.log（logging_setup で日次ローテーション・30日保持）
- 監視 DB: SQLite（data/monitoring.db）
- Paper Trading DB: data/paper_trading.db
- DuckDB: data/kabusys.duckdb
- Kill switch: data/kill.flag（KillSwitch が書き込む）
- 停止リクエスト（監視/実行停止用）: data/stop_requested.flag

ディレクトリ構成（主要ファイル）
-------------------------------
以下はパッケージ内の主要なファイル/ディレクトリ構成（src/kabusys 配下を想定）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — 監視 DB テーブル定義・アクセス
    - system_monitor.py
    - trade_monitor.py       (実装あり)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       (実装あり)
  - execution/               — Execution 系（エンジン・注文管理・broker_factory 等）
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
  - data/                    — 実行時に生成されることがある（DB・flag・pid 等を格納）
  - logs/                    — ログ出力先（デフォルト）

設計上の注意点 / 運用上のヒント
-----------------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも警告あり）。
- KABUSYS_ENV=live の場合は特に設定を慎重に確認してください（validate_config が追加警告を出します）。
- ExecutionEngine 停止は kill.flag の書き込みではなく、Monitoring の KillSwitch から kill.flag を生成して停止させます。data/stop_requested.flag を監視しているスクリプトもあります（手動で停止させる際は用途に応じて正しくファイルを操作してください）。
- Logging は setup_logging を通して統一されます。cron / systemd 等から実行する場合でもログは logs/ に日次ローテーションで保存されます。
- AI （OpenAI）呼び出しはコストとレイテンシがかかります。API キーの管理とレート制御に注意してください。

開発・拡張
------------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）を充実させることで research/ai 機能が活用できます。
- portfolio/ の各関数は副作用なしの純関数にしてあり、ユニットテストが書きやすい構造になっています。
- validate_config は YAML の内容検証を行います（PyYAML がインストールされている場合）。config/*.yaml が必要な場合は scripts/generate_config.py 等で生成してください（リポジトリに含まれる想定のスクリプトを参照）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期バージョン）
- ライセンス情報はリポジトリのルートにある LICENSE 等を参照してください（無ければプロジェクトポリシーに従って追加してください）。

問い合わせ / 開発者向けメモ
-------------------------
- 監視・実行まわりの機能は障害耐性（ログの永続化、フェイルセーフ、リトライ）を重視して設計されています。運用前に validate_config → config_setup → 実行（paper_trading で十分に検証）を行ってください。
- AI 関連は外部 API（OpenAI）に依存するため、テスト時は _call_openai_api をモックしてテストすることを推奨します。

以上。必要であれば README にサンプル .env、systemd ユニット例、docker-compose 例などの運用ドキュメントを追加で作成します。どの情報を優先して追加しますか？