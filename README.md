# KabuSys

日本株自動売買システムのコアライブラリ / 実行スクリプト群です。本リポジトリは、監視・発注エンジン、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニューススコアリング等を含みます。

以下はこのコードベースの概要、機能、セットアップ方法、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を支援するパッケージ群です。主なコンポーネントは以下です。

- ExecutionEngine（発注エンジン）／Broker クライアント（paper_trading モードあり）
- Monitoring（System / Trade / Risk）による稼働監視・Kill Switch（停止フラグ）
- Portfolio 構築（候補選定、重み付け、ポジションサイズ計算、セクター制限等）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュースのセンチメントスコアリング、レジーム判定）
- ユーティリティ（環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定）
- ツール（Paper Trading 検証レポート生成など）

設計方針の一部：
- DuckDB / SQLite を使ってデータ保存・分析を行う
- 環境変数 / .env による設定管理（自動ロード）
- Paper Trading（テスト用）は本番 DB と完全分離

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading モード切替）
  - run_monitoring.py: SystemMonitor をループで実行（監視ログを SQLite に記録）
- 環境管理
  - config_setup.py: 対話式 .env ウィザード（.env の初期作成・更新）
  - validate_config.py: 環境変数および config/*.yaml の事前検証 CLI
- 監視
  - monitoring/ : SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
  - monitoring_db: SQLite テーブルの初期化・読み書きユーティリティ
- ポートフォリオ構築
  - portfolio/: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- リサーチ
  - research/: ファクター計算（momentum/value/volatility）、特徴量解析（IC 等）
- AI（OpenAI）
  - ai/news_nlp.py: ニュース記事を LLM でスコアリングして ai_scores に保存
  - ai/regime_detector.py: ETF MA + マクロニュースで市場レジーム判定
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成
- ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定（stdout + 日次ローテーション）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定

---

## セットアップ手順（開発 / 実行環境）

前提
- Python 3.10 以上（型注釈の union 演算子等を使用）
- git クローン済みのプロジェクトルートを想定

1. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限必要なパッケージ例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証を有効にする場合）
   - 例:
     pip install duckdb psutil openai pyyaml

   ※ 実運用用の requirements.txt がある場合はそちらを利用してください。

3. .env を作成
   - 対話式ウィザードを利用:
     python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）

4. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱いたい場合:
     python -m kabusys.validate_config --strict

5. DB / ディレクトリの準備
   - デフォルトでは次のパスが使われます（.env で上書き可能）
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じてディレクトリ作成はスクリプト側で自動作成されます（ログ等）。

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境
  - 有効値: development / paper_trading / live
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する場合の API キー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" = クリア）

.env は自動ロードされます（プロジェクトルートが特定できる場合）。自動ロードを無効にするには:
- export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 使い方（主要スクリプト・コマンド）

プロジェクトルートから各モジュールを -m で実行します。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に依存（paper_trading の場合は MockBroker を使い data/paper_trading.db に書き込む）
  - 実行中、data/stop_requested.flag が存在すると早期停止します
  - PID ファイル: data/execution.pid（デフォルト）

- Monitoring（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を使ってログを永続化します（KABUSYS_ENV に関わらず本番 DB を使用）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ライブラリ関数の利用（Python スクリプトや REPL から）
  - Portfolio:
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - Research:
    from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - AI（ニューススコア）、レジーム:
    from kabusys.ai import score_news
    # score_news(conn, target_date, api_key=...)
    # または kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

注意点:
- OpenAI を使う機能は OPENAI_API_KEY が必要です。未設定時は ValueError を送出する場合があります。
- run_execution は data/stop_requested.flag や data/kill.flag により外部から停止できます（KillSwitch で自動的に kill.flag を書くこともあります）。

---

## Kill / Stop フラグ

- data/stop_requested.flag: スクリプト（run_execution/run_monitoring）が存在を確認して安全に終了するためのローカル停止フラグ（CI 等で利用）
- data/kill.flag: Monitoring の KillSwitch が書き込むことで ExecutionEngine に停止シグナルを送る（本番保護用）

KillSwitch はドローダウンやポジション上限などの条件を満たしたときに理由をファイルに書き込みます。Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨します。

---

## ログ

- setup_logging(app_name="...") を全スクリプトから呼び出しており、stdout（StreamHandler）と日次ローテートのファイル（logs/<app_name>.log）に出力されます。
- ログディレクトリは環境変数 LOG_DIR で変更できます。
- ログレベルは LOG_LEVEL または setup_logging の引数で設定可能。

---

## デフォルトパス一覧

- DuckDB: data/kabusys.duckdb
- SQLite (monitoring): data/monitoring.db
- SQLite (paper trading): data/paper_trading.db
- PID: data/execution.pid
- Kill flag: data/kill.flag
- Stop flag: data/stop_requested.flag
- ログ: logs/<app_name>.log

これらは Settings クラス（kabusys.config.Settings）を通して取得・上書き可能です。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装あり)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py
  - data/ (実行時に生成されるファイル群: DB, pid, flag, ...)

（上記は実際のリポジトリの階層を簡略化して示しています）

---

## 開発メモ / 注意点

- .env は決して Git にコミットしないでください（機密情報が含まれます）。
- validate_config で早期に設定不備を検出できます。特に本番（KABUSYS_ENV=live）では追加の警告が出ます。
- Paper Trading モードは本番 DB とは分離されるためテスト運用が容易です。
- OpenAI 等外部 API のエラーに対してはリトライ／フェイルセーフ処理を実装していますが、API キーやレート制限には注意してください。
- process_priority（優先度設定）や CPU affinity の変更はプラットフォームの権限制約により失敗する場合があります（警告を出してスキップします）。

---

必要であれば、README にサンプル .env、よくあるトラブルシュート、さらに詳細な API 使用例（関数一覧および引数例）を追加できます。どの情報を拡張したいか教えてください。