KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買（バックテスト／ペーパートレード／本番運用）を想定した小規模なフレームワークです。  
主な設計方針は「安全性（フェイルセーフ）」「環境分離（paper_trading と live の DB 分離）」「ログ／監視の一元化」「外部 API 呼び出しの疎結合」です。

主な機能
--------
- 環境設定ウィザード（.env 生成 / 更新）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の簡易チェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト（発注ロジックの本体を起動）: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、paper_trading 専用 DB に記録
- System / Trade / Risk の監視コンポーネントとポーリングエンジン: monitoring/*
  - run_monitoring.py で SystemMonitor のポーリングループを起動
  - Kill Switch（データ駆動で ExecutionEngine を停止するためのフラグファイル）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）: portfolio/*
- リサーチ（ファクター計算、特徴量探索）: research/*
- AI（ニュース NLP、レジーム検出）: ai/*
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントや市場レジーム判定（API キー必須）
- ユーティリティ
  - ログ設定: utils/logging_setup.py（stdout + 日次ローテートファイル）
  - プロセス優先度・CPU affinity 設定: utils/process_priority.py
- ツール
  - Paper Trading の検証レポート生成スクリプト: tools/paper_verification_report.py

セットアップ手順
----------------
1. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境作成（例）:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - 必要なライブラリの例:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定ファイル検証を行う場合は推奨）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 自動生成ウィザードを使う:
     - python -m kabusys.config_setup
   - .env のサンプル（最低限必要な必須環境変数）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development  # development / paper_trading / live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
   - 注意: 自動ロード機能により、プロジェクトルートに .env / .env.local があればモジュール import 時に読み込まれます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 引数 --strict を付けると警告もエラー扱いになります。

5. データディレクトリ / ログディレクトリの作成
   - 通常はコード側で自動作成されますが、必要に応じて手動で作成してください。
   - デフォルト DB / フラグ / PID ファイル:
     - data/monitoring.db (SQLITE_PATH のデフォルト)
     - data/paper_trading.db (paper_trading 用デフォルト)
     - data/kabusys.duckdb (DuckDB デフォルト)
     - data/execution.pid, data/kill.flag, data/stop_requested.flag

使い方
------
- 実行コンポーネント
  - ExecutionEngine（注文実行）
    - python -m kabusys.run_execution
    - 動作:
      - Settings を読み取り、KABUSYS_ENV が paper_trading の場合は paper_trading 用 SQLite を使用（デフォルト: data/paper_trading.db）。
      - BrokerClientFactory を使ってブローカークライアントを生成（実口座またはモック）。
      - engine.run_session() を別スレッドで実行し、stop フラグ（data/stop_requested.flag）を監視して終了。
    - PID / stop フラグ:
      - 起動時に data/execution.pid を使います。停止したい場合は data/stop_requested.flag を作成するか Kill Switch（監視側）で data/kill.flag を書き込ませます。

  - Monitoring（システム監視）
    - python -m kabusys.run_monitoring
    - 動作:
      - SystemMonitor のポーリングループを起動し、system_status / trade_logs / risk_logs / dashboard を更新
      - モニタリングは常に本番 sqlite_path を参照（KABUSYS_ENV に関係なく Settings.sqlite_path）
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
      - 停止: data/stop_requested.flag を作成すると監視ループが終了します

- 設定検証 / ウィザード
  - ウィザード:
    - python -m kabusys.config_setup
  - 検証:
    - python -m kabusys.validate_config [--strict]

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI モジュール（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を操作。OpenAI API キーが必要（api_key 引数または OPENAI_API_KEY 環境変数）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースからレジーム判定し market_regime テーブルへ書き込む。

環境変数（主なもの）
--------------------
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API へのパスワード

- 運用 / 任意
  - KABUSYS_ENV — 実行環境 (development / paper_trading / live)（デフォルト: development）
    - paper_trading の場合、Execution は paper_sqlite_path を使用します（本番 DB と切り離し）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
  - LOG_DIR — ログ出力先（デフォルト logs/）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — 本番でのアラート通知（任意）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）を上書き（デフォルト 60）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1 で有効。production では 0 推奨）

注意事項 / 運用上のポイント
--------------------------
- DB 分離:
  - paper_trading 用の SQLite を使用することで本番 DB と完全に分離できます。必ず KABUSYS_ENV を確認してください。
- Kill Switch:
  - リスク条件を検出した監視側は data/kill.flag を書き込み、ExecutionEngine を安全に停止させる仕組みがあります（冪等性あり）。
- ロギング:
  - setup_logging により stdout と日次ローテートファイルへログが出力されます。LOG_DIR/LOG_LEVEL で制御可能。
- AI 呼び出し:
  - OpenAI を用いる機能は API の呼び出し制限・料金に依存します。retry/backoff の実装はありますが、API キーとコスト管理を行ってください。
- 自動 .env ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）に .env/.env.local があればインポート時に自動で読み込まれます。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — Settings クラス（環境変数 / .env 自動読み込み・検証）
  - config_setup.py — .env ウィザード CLI
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — マクロ + MA200 で市場レジーム判定

  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・DB ラッパー
    - system_monitor.py — CPU/MEM/DISK / データ鮮度 / プロセス監視
    - trade_monitor.py —（注文関連監視、ファイル上に実装あり）
    - risk_monitor.py — ドローダウン・ポジション上限のチェック
    - kill_switch.py — data/kill.flag を操作するユーティリティ
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py —（通知管理。LINE 等の実装が想定）

  - execution/
    - execution_engine.py — 実際の注文実行ロジック（Engine）
    - broker_factory.py — ブローカークライアント生成
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理・リスク制御等

  - portfolio/
    - portfolio_builder.py — 候補抽出・重み計算
    - position_sizing.py — 株数計算（単元丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - __init__.py — 公開 API

  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定

  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート出力

その他
-----
- ドキュメント参照:
  - 各モジュール内に詳しい docstring と設計ノートが含まれています。実装やパラメータの意味は該当ファイルの docstring を参照してください。
- ライセンス / 責任:
  - 実際の発注を行うシステムは重大なリスクを伴います。本リポジトリのコードをそのまま資金投入で利用する際は十分なテストと監査を行ってください。

問題が発生したり README の補足を希望する点があれば教えてください。必要に応じてコマンド例や .env のテンプレートを追加します。