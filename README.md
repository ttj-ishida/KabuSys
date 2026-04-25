README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究用フレームワークです。本リポジトリには以下の主要機能を提供するモジュール群が含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプト（発注処理）
- 監視ループ（Monitoring）起動スクリプト（プロセス監視・データ鮮度・リスク監視）
- ポートフォリオ構築（銘柄選定・重み付け・ポジションサイズ決定）
- 研究用ファクター計算・特徴量解析（DuckDB 上の時系列データ処理）
- AI 補助（ニュースのセンチメント / レジーム判定）— OpenAI を利用
- 各種ユーティリティ（ロギング設定、プロセス優先度設定、.env ウィザード 等）
- ペーパートレード用レポート生成ツール

主な特徴
--------
- 環境依存設定を .env で管理（対話式ウィザードと自動ロード機能）
- 本番・ペーパートレードの分離（KABUSYS_ENV により paper_trading モードを選択）
- DuckDB（分析）と SQLite（監視・発注ログ）を併用するデータ設計
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP とレジーム検出（フォールバック・リトライ実装あり）
- 監視側の Kill Switch（flag ファイル）による実行エンジン停止機能
- 日次ローテーションログ、プロセス優先度設定、CPU affinity サポート

セットアップ手順
----------------

1. Python 環境を用意する
   - 推奨: Python 3.10+（プロジェクトは型注釈や最新ライブラリを仮定）
   - 仮想環境を作成・有効化することを推奨します。

2. 依存パッケージをインストールする
   - requirements.txt はリポジトリに含めていない想定のため、主に以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（optional：validate_config が YAML 検証を行う場合）
   例:
     pip install duckdb psutil openai PyYAML

3. .env を作成する
   - 対話式ウィザードで .env を生成できます（プロジェクトルートに .env を作成します）:
     python -m kabusys.config_setup
   - 主要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要なオプション（デフォルト値あり）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY（AI 機能利用時に必要）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（本番のアラート用）

4. 設定検証（起動前チェック）
   - .env と config/*.yaml（存在する場合）を検証します:
     python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

5. データディレクトリ作成
   - デフォルトでは logs/ と data/ 下にファイルを作成します。必要に応じてディレクトリを作成してください（logging_setup が自動作成を試みます）。

基本的な使い方
--------------

エントリポイント（例）
- 監視ループ起動（SystemMonitor をポーリング）
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます。
  - 実行:
    python -m kabusys.run_monitoring
  - 停止方法:
    - 手動で Ctrl+C（KeyboardInterrupt）
    - プロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に書き込みます。
  - 実行:
    python -m kabusys.run_execution
  - 停止方法:
    - data/stop_requested.flag を作成すると、起動中のエンジンが停止します。
    - 実行エンジンは起動時 PID を data/execution.pid に書きます。

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）

注意点 / 運用上の挙動
- 監視モジュールは Settings.sqlite_path（監視用 SQLite）を環境にかかわらず使用します（monitoring は production DB を参照する設計）。
- 実行エンジンは KABUSYS_ENV によって DB を切り替えます（paper_trading 時は paper_sqlite_path を使用）。
- Kill Switch:
  - data/kill.flag を書き込むと ExecutionEngine に停止シグナルを送る設計です（KillSwitch モジュール）。
  - KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合は起動時に kill.flag を自動クリアします（ただし本番では 0 を推奨）。
- ログ:
  - ログは stdout（StreamHandler）と日次ローテートされるファイル（logs/<app_name>.log）に出力されます。
  - ログディレクトリは環境変数 LOG_DIR、引数で上書き可能。デフォルトは logs/。

主要コンポーネント説明（抜粋）
--------------------------------
- kabusys.config
  - .env 自動ロード・パース、Settings クラス（環境変数を集約）
- kabusys.config_setup
  - 対話式 .env 生成ウィザード
- kabusys.validate_config
  - 起動前の設定チェック CLI
- kabusys.utils.logging_setup
  - アプリ共通のロギング設定（stdout + 日次ファイルローテーション）
- kabusys.utils.process_priority
  - プロセス優先度（high/normal/low）と CPU affinity を設定
- kabusys.monitoring
  - monitoring_db: SQLite スキーマ作成 / 永続化 API
  - system_monitor: CPU/メモリ/ディスク/プロセス・データ鮮度チェック
  - trade_monitor / risk_monitor / kill_switch / monitoring_engine / alert_manager（監視・アラート・Kill Switch の統合）
  - run_monitoring.py：監視ポーリングループ起動スクリプト
- kabusys.execution
  - ExecutionEngine、OrderManager、RiskManager、BrokerClientFactory 等（発注ロジック）
  - run_execution.py：ExecutionEngine 起動スクリプト（paper_trading モード対応）
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment：銘柄選定とサイズ計算の純粋関数群
- kabusys.research
  - factor_research, feature_exploration：DuckDB 上でファクター計算と検証処理
- kabusys.ai
  - news_nlp: ニュースを LLM でスコアリングして ai_scores に書き込み
  - regime_detector: ETF とマクロセンチメントを組合せて market_regime を判定
- kabusys.tools
  - paper_verification_report: ペーパートレードの検証レポート生成ツール

ディレクトリ構成（主要ファイル）
-------------------------------
（プロジェクトルート / src/kabusys を基準）

- kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
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
    - alert_manager.py
    - monitoring_engine.py
  - execution/
    - execution_engine.py
    - broker_factory.py
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
  - monitoring/ (上と重複、監視関連)
  - tools/
    - __init__.py
    - paper_verification_report.py
  - data/      （ランタイムで作成されるファイル: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid 等）
  - logs/      （ログファイルが出力されるディレクトリ）

（注）リポジトリにより細かいファイルは異なる場合があります。上は本 README 作成時のソースコードに基づく主要構成です。

環境変数（主なもの）
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行関連:
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG|INFO|...)
  - LOG_DIR (ログ保存先)
- DB:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (monitoring 用、default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用、default: data/paper_trading.db)
- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector を利用する場合）
- 監視 / 制御:
  - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動削除する（テスト用）

運用上の推奨
------------
- 本番（KABUSYS_ENV=live）では .env を厳密に管理し、LINE の通知設定や Kill Switch 設定を確認してください。
- ログは daily ローテーションで 30 日保持されます。ログディレクトリのディスクサイズに注意してください。
- OpenAI を利用する機能は API コストとレイテンシに注意して運用してください（retry/backoff 実装あり）。
- paper_trading モードは本番用 DB と分離されるため、検証目的の運用に使いやすく設計されています。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ に定義されています（例: 0.1.0）。

問題・貢献
----------
- Issue / Pull Request は README とリポジトリの CONTRIBUTING に従ってください（該当ファイルがない場合はリポジトリ規約に従ってください）。

以上が本コードベースの概要・セットアップ・使い方です。必要であれば、各モジュールの詳細な API 使用例や実行ログの読み方、運用チェックリスト等の追加ドキュメントを作成します。どういった追加情報が欲しいか教えてください。