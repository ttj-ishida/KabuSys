KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けのアルゴリズム取引・研究用フレームワークです。  
主な機能は次の通りです。

- 実際の発注／ペーパートレードを切り替えられる ExecutionEngine
- システム稼働状況・注文ログ・リスク監視を行う Monitoring（Kill Switch を含む）
- ポートフォリオ構築・配分・ポジションサイズ計算の純粋関数群（Portfolio）
- DuckDB を使ったファクター計算・研究モジュール（Research）
- OpenAI を使ったニュース NLP / レジーム判定モジュール（AI）
- .env 生成ウィザード / 設定検証ツール / ペーパートレード検証レポート等の CLI ユーティリティ
- ログ設定・プロセス優先度等のユーティリティ

このリポジトリはライブラリと起動スクリプト群を提供し、運用・検証用のツールを含みます。

主な機能一覧
--------------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により本番/ペーパートレードを切替。
  - paper_trading 環境では MockBrokerClient を使い data/paper_trading.db に記録。
- run_monitoring.py
  - SystemMonitor をポーリングして system_status / trade_logs / risk_logs / dashboard を更新。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- config_setup.py
  - 対話式ウィザードで .env を生成・更新。
- validate_config.py
  - .env と config/*.yaml の存在・簡易検証を行う CLI。--strict オプションで警告を失敗扱いに。
- tools/paper_verification_report.py
  - ペーパートレード DB（data/paper_trading.db）から期間指定でレポートを生成し PASS/FAIL 判定。
- portfolio/*
  - 候補選定、重み計算、セクター制限、ポジションサイズ算出などの純粋関数群。
- research/*
  - DuckDB 上でのファクター計算（momentum/value/volatility）や特徴量解析ユーティリティ。
- ai/*
  - news_nlp.py: OpenAI を使ってニュースをスコア化し ai_scores に書き込む処理。
  - regime_detector.py: 指標と LLM によるマクロセンチメントを合成して market_regime を算出。
- monitoring/*
  - monitoring_db: SQLite ベースの永続化（テーブル作成・マイグレーション含む）。
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager（アラートは別実装想定）。
- utils/*
  - logging_setup: 統一的なログ設定（コンソール + 日次ローテーション）。
  - process_priority: プラットフォーム差異を吸収してプロセス優先度 / CPU affinity を設定。

セットアップ手順
----------------
1. Python 仮想環境を作成（推奨）
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML (config 検証を行う場合)
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt は本リポジトリに含まれていない想定です。プロジェクトで使用するバージョンを lock して管理してください。

3. データ・ログディレクトリを作成
   - mkdir -p data logs

4. .env の用意
   - 対話式で作る:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照すること）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱う

6. （AI 機能を使う場合）OpenAI API キーを設定
   - 環境変数 OPENAI_API_KEY を設定するか、score_news/score_regime の api_key 引数で渡す

実行方法 / 使い方
-----------------

- ExecutionEngine 起動（本番／ペーパーは KABUSYS_ENV で切り替え）
  - python -m kabusys.run_execution
  - デフォルトで Settings から DB パスや環境を読みます。
  - ペーパートレード: KABUSYS_ENV=paper_trading とすると MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL (秒) でポーリング間隔を上書き可（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用の sqlite_path を使用（環境に関わらず）。

- .env の作成・更新
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニューススコア・レジーム判定）
  - ai.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date を受け取り、DB に書き込みます。
  - 実行には OpenAI API キーが必要（OPENAI_API_KEY）。

重要な環境変数（主なもの）
----------------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API 用）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）デフォルト: INFO
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

運用上の注意
--------------
- run_monitoring/run_execution は停止を検知するために data/stop_requested.flag や data/kill.flag を参照／操作します。運用時はこれらフラグファイルの扱いに注意してください。
- run_execution は pid ファイル（data/execution.pid）を生成・参照します。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を探す）から行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Logging は kabusys.utils.logging_setup.setup_logging を通して統一しているため、各スクリプトはこれを最初に呼びます。ログは logs/<app_name>.log に日次ローテーションで保存されます。

ディレクトリ構成
----------------
（主要ファイル / モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定読み込みロジック
    - config_setup.py          # .env 対話式ウィザード
    - validate_config.py       # 設定検証 CLI
    - run_execution.py         # ExecutionEngine 起動スクリプト
    - run_monitoring.py        # Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py         # （コード省略）取引関連の監視
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py        # （アラート実装はプロジェクトに依存）
    - execution/                # 発注関連の実装（Engine / BrokerFactory / OrderManager 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/                     # デフォルトの data ファイル（実行時に作成）
      - monitoring.db (デフォルト SQLite)
      - paper_trading.db
      - stop_requested.flag (運用で使用)
    - logs/                     # ログ出力先（デフォルト）
    - config/                   # YAML 設定群（system_config.yaml など）

補足（開発者向け）
-----------------
- DuckDB を利用してファクターや AI 前処理を行います。DuckDB 接続を渡すことで SQL と Python を組み合わせた処理が可能です。
- AI 関連は外部 API に依存するため、API エラーやレート制限に対するリトライ・フェイルセーフ実装が各モジュールに含まれていますが、実運用ではキー管理・コストに注意してください。
- monitoring_db.init_monitoring_db は冪等にテーブル作成と簡易マイグレーションを実行します。既存 DB がある場合でも安全に実行できます。

ライセンス・その他
------------------
本 README はコードベースの要約および使い方ガイドです。ライセンスや詳細な運用手順（CI/CD、デプロイ、バックアップ、監視設定など）は別途プロジェクトのポリシーに従ってください。

問題が発生した場合
------------------
- 設定検証: python -m kabusys.validate_config
- ログ: logs/<app_name>.log を確認
- .env 生成/編集: python -m kabusys.config_setup

以上。必要であれば README に含めるコマンド例や .env のテンプレート（.env.example 形式）を追加できます。どの情報を詳細化したいか教えてください。