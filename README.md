# KabuSys

日本株向けの自動売買システム（ライブラリ／ランタイムコンポーネント群）のリポジトリ用 README（日本語）。

以下はコードベースから抽出した概要・使い方・セットアップ手順等です。

---

## プロジェクト概要

KabuSys は日本株自動売買のためのコンポーネント群を提供します。主な機能は次の通りです。

- 注文発行・ExecutionEngine（本番／ペーパートレード切り替え）
- システム監視（CPU/メモリ/ディスク、データ鮮度、プロセス生存監視）
- リスク監視（ドローダウン、ポジション上限検出・アラート）
- Kill Switch（条件を満たしたときに Execution を停止させるフラグ）
- ポートフォリオ構築、ポジションサイジング、セクター制限
- リサーチ用ファクター計算・特徴量探索（DuckDB 経由）
- AI（OpenAI）を使ったニュースセンチメント評価・市場レジーム判定
- 各種ツール（設定ウィザード、設定検証、Paper Trading 検証レポート生成）
- ログ設定ユーティリティ、プロセス優先度設定ユーティリティ等のユーティリティ群

設計上の留意点:
- 設定は `.env`（または環境変数）で管理。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
- 本番 DB（監視用）は SQLite、分析用は DuckDB を想定。Paper Trading は本番 DB と完全分離された専用 SQLite を使用します。

---

## 機能一覧（主なモジュール）

- kabusys.config: 環境変数／設定管理（Settings クラス）
- kabusys.run_monitoring: SystemMonitor ポーリングループ起動スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL（秒）で間隔指定（デフォルト 60）
- kabusys.run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）
- kabusys.monitoring: system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / monitoring_db（監視ログ永続化）
- kabusys.execution: ブローカーファクトリ、注文管理、リスク管理、実行エンジン（コード参照）
- kabusys.portfolio: 候補選定・重み計算・ポジションサイジング・セクター制限等の純関数群
- kabusys.research: ファクター計算（momentum/value/volatility）、特徴量探索（IC, forward returns, summary）
- kabusys.ai: news_nlp（ニュースセンチメント取得）、regime_detector（市場レジーム判定）
- kabusys.tools: paper_verification_report（Paper Trading の検証レポート出力）
- kabusys.utils: logging_setup（ログ設定）、process_priority（優先度・CPU affinity 設定）

---

## セットアップ手順（ローカル実行向け）

1. Python 環境準備
   - Python 3.10+ 推奨（プロジェクトの type hints に基づく想定）
   - 仮想環境を作成して有効化することを推奨します。

2. 必要パッケージのインストール（例）
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（config ファイルの検証を使う場合）
   - 例:
     pip install duckdb psutil openai pyyaml

   ※ 実際のプロジェクトに requirements.txt があればそれを利用してください。

3. 環境変数（.env）作成
   - プロジェクトルートに `.env` を作成するか、`python -m kabusys.config_setup` のウィザードを実行して生成してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 代表的な設定（例 .env 抜粋）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_api_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

   - 自動ロードはデフォルトで有効（.env / .env.local）。無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. データディレクトリ作成（ログ・DB 等）
   - 一部処理は自動で作成しますが、手動で作っておくと安全:
     mkdir -p data logs

5. 設定の検証（任意）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict

---

## 使い方（起動・主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告をエラー扱いにできます。

- 監視プロセス起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - オプション: MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き。デフォルト 60 秒。
  - 監視プロセスはプロセス優先度を "high" に設定します。
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず）。

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）へ書き込みます（本番 DB と分離）。
  - 実行中は data/execution.pid 等の pid ファイルを使用します。
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db path/to/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH も利用可）

- AI 機能（ニュース評価 / レジーム判定）
  - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY または各関数へ引数で指定
  - 実行例はモジュール API を直接呼ぶ形になります（score_news, score_regime 等）。

停止・Kill Switch:
- ExecutionEngine を停止させたい外部トリガーは 2 種類:
  - KillSwitch: monitoring 側の判定によって data/kill.flag が書き込まれると Execution 側で参照して停止する設計（Settings.kill_flag_path によりパス指定可）。
  - stop_requested.flag: run_monitoring / run_execution は stop_requested.flag（project_root/data/stop_requested.flag）を検出するとループ停止／起動中止します。
- kill.flag は KillSwitch.clear() または手動で削除してクリアできます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされる挙動がありますが、本番では 0 を推奨します。

ログ:
- logs/<app_name>.log に日次ローテーションで出力（デフォルト logs ディレクトリ、30 日保持）。
- ルートロガーは setup_logging() により StreamHandler（stdout）と TimedRotatingFileHandler を設定します。

---

## 環境変数一覧（代表）

基本的な変数（抜粋）:
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

詳しい項目・バリデーションは kabusys.config.Settings を参照してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要なファイルおよびディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / .env 自動読み込み / Settings
    - config_setup.py                — 対話式 .env 作成ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - monitoring/
      - monitoring_db.py             — SQLite 永続化レイヤ
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
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
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

---

## 運用上の注意

- .env ファイルは機密情報を含むため、決して Git 等へコミットしないでください（config_setup のヘッダにも注意書きがあります）。
- 本番環境（KABUSYS_ENV=live）での設定は慎重に。validate_config は live 時に注意喚起を行います。
- AI（OpenAI）呼び出しは API 利用制限や料金が発生します。エラーやレート制限に対するリトライやフォールバックが実装されていますが、利用に当たっては十分に検討してください。
- Paper Trading は本番 DB と完全分離されます。paper_trading モードでは PAPER_TRADING_SQLITE_PATH を確認してください。
- ログディレクトリ作成に失敗した場合はファイル出力が無効になり stdout のみ出力されます。運用時は logs/ を作成しておくことを推奨します。

---

## 参考コマンドまとめ

- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

README に書かれている以外の詳細は各モジュールの docstring を参照してください（各ファイルに実装注釈・設計方針が記載されています）。必要であれば README を整備してドキュメント生成やセットアップスクリプトを追加する提案もできます — どうしますか？