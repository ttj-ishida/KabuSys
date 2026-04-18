KabuSys — 日本株自動売買システム
================================

この README はコードベース（src/kabusys 以下）を前提に、導入・起動方法や主要コンポーネントの概要を日本語でまとめたものです。

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。主要機能をモジュール化して実装しており、以下を含みます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理を行うランタイム
- 監視（Monitoring）: システム状態・注文状況・リスク指標の定期チェックとアラート／Kill Switch
- ポートフォリオ構築: 候補選定、重み算出、ポジションサイズ決定、セクター制約等の純粋関数群
- リサーチ（Research）: DuckDB 上の時系列データからファクター計算・特徴量探索
- AI モジュール: ニュースを LLM でスコアリング・市場レジーム判定（OpenAI API を利用）
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード、設定検証 など

主な機能一覧
-------------
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話的に作成
- 設定検証: python -m kabusys.validate_config で必須環境変数・config/*.yaml のチェック
- Execution 起動: python -m kabusys.run_execution — KABUSYS_ENV により paper_trading / live 挙動切替
  - paper_trading: MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
- Monitoring 起動: python -m kabusys.run_monitoring — 監視ループ、監視 DB に記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 停止フラグ data/stop_requested.flag を検知してループを終了
- Kill Switch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine 停止を促す
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report でレポート生成
- ポートフォリオ構築ユーティリティ:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（ロット調整・aggregate cap 等）
  - apply_sector_cap, calc_regime_multiplier
- Research:
  - calc_momentum, calc_volatility, calc_value（DuckDB ベース）
  - calc_forward_returns, calc_ic, factor_summary
- AI:
  - score_news（ニュースの LLM スコアリング）
  - score_regime（レジーム判定）

セットアップ手順
----------------
前提:
- Python 3.9+（少なくとも typing に Union/Annotated 等をサポートするバージョン）
- pip 等でパッケージをインストール可能な環境

1. リポジトリをクローン・配置
   - ソースのルートに `src/` と `.env`（未作成なら config_setup で作る） がある想定

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は validate_config の YAML 検証を有効にする場合に必要: pip install PyYAML

4. .env の作成
   - 推奨: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して以下の必須値を設定:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 必要に応じて:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: python -m kabusys.validate_config --strict

使い方（起動例）
----------------

- ExecutionEngine を起動（標準）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使い paper_trading 用 DB に記録

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（なければ環境変数 PAPER_TRADING_SQLITE_PATH を参照）

- 停止方法
  - 実行中プロセスはプロジェクトルートの data/stop_requested.flag の存在を監視します。
    - 停止したい場合はこのファイルを作成（空ファイルで可）。監視・実行スクリプトは検知して終了します。
  - Kill Switch は条件を満たすと data/kill.flag を書き込みます（ExecutionEngine は起動時にこれを検出して起動しない / 停止処理を行う仕組み）。

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV: development | paper_trading | live（実行モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用）
- PAPER_FILL_MODE: paper_trading の注文約定動作（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START: 本番での kill flag 自動クリアの有無（"1" でクリアする）

ログ・DB・PID/フラグファイル
---------------------------
- ログ: logs/<app_name>.log（TimedRotatingFileHandler で日次ローテーション、30世代保持）
  - setup_logging() を各起動スクリプトが呼び出します（app_name に "monitoring" や "execution" を指定）
- SQLite（監視）: data/monitoring.db（Settings.sqlite_path）
- DuckDB（分析）: data/kabusys.duckdb（Settings.duckdb_path）
- Paper Trading DB: data/paper_trading.db（paper_trading 環境）
- PID / flag:
  - data/execution.pid（ExecutionEngine の PID ファイル）
  - data/stop_requested.flag（停止要求 — run_* スクリプトで監視）
  - data/kill.flag（Kill Switch が書き込む停止理由）

ディレクトリ構成
----------------
以下は主要なファイル／ディレクトリの抜粋（src/kabusys をルートとしたツリー）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading レポート
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 利用）
    - regime_detector.py     — 市場レジーム判定（AI + MA）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル定義 / 永続化層
    - system_monitor.py
    - trade_monitor.py       — （注文ログ監視等、実装参照）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — （通知の抽象化）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・発注ループ）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                   — 実行時に使う DB / flag / pid（プロジェクトルート直下に存在）
  - config/                 — YAML 設定ファイル群（system_config.yaml 等）

注意事項・運用上のポイント
------------------------
- 本番運用（KABUSYS_ENV=live）の場合は .env の内容を慎重に扱ってください。validate_config は live 時に追加警告を出します。
- .env は決してバージョン管理にコミットしないでください（config_setup でも注意書きを出しています）。
- OpenAI を使うモジュールは API のレート制限・費用に注意して運用してください（リトライ・バックオフ実装あり）。
- paper_trading モードは本番 DB と完全に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- 監視系は Kill Switch（data/kill.flag）を用いた安全停止機構を提供します。運用ルールを定めてください。

開発・拡張のヒント
-------------------
- DuckDB を用いた計算モジュール（research/*）は副作用を持たない純粋関数設計が基本です。テストしやすく拡張しやすい構成です。
- ロギングは setup_logging() 経由で統一されているため、新しいスクリプトでは必ず呼び出してください。
- process_priority と CPU affinity は utils/process_priority.py に抽象化されています。プラットフォーム差異を気にせず呼べます。
- AI 周りは API 呼び出し部分をモックしてテストしやすいよう分離しています（テスト用に _call_openai_api を patch することを想定）。

ライセンス・貢献
----------------
この README に含まれる情報はコードベースのコメントと実装から抽出したものであり、実際のリポジトリの LICENSE や貢献ルールが別にある場合はそちらに従ってください。

付録 — よく使うコマンド例
------------------------
- .env を作る（対話）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- OpenAI を使う機能実行時は環境変数 OPENAI_API_KEY を設定してください。

必要であれば README にサンプル .env のテンプレート、システム図（アーキテクチャ図）、ユニットテストの実行方法や CI 設定の説明も追加できます。どの情報を追記するか指示してください。