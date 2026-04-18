README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアライブラリ群です。  
このリポジトリは、以下の主要機能を含むモジュール群を提供します。

- 実行エンジン（ExecutionEngine）および監視プロセス（Monitoring）
- 発注／注文履歴の永続化（SQLite）および分析用ストレージ（DuckDB）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ）
- リサーチ（ファクター計算、特徴量解析）
- AI を使ったニュースセンチメント評価・レジーム検出（OpenAI）
- 各種ユーティリティ（設定管理、ログ設定、プロセス優先度）

本 README はローカルでのセットアップ、基本的な使い方、ディレクトリ構成の説明を日本語でまとめたものです。

主な特徴
--------
- モジュール設計により、発注ロジックと監視ロジックが分離
- Paper Trading（ペーパートレード）モード：MockBroker を用いて本番 DB と分離
- 監視 (Monitoring) は本番の sqlite_path を参照してシステム状態を永続化
- AI（OpenAI）を使ったニューススコアリング（ai/news_nlp.py）とレジーム判定（ai/regime_detector.py）
- DuckDB を利用した高速なリサーチ・ファクター計算モジュール
- .env による柔軟な設定管理と対話式設定ウィザード

前提（依存パッケージ）
--------------------
（必要に応じて仮想環境を作成してからインストールしてください）

主な Python ライブラリ（少なくとも以下が必要）:
- duckdb
- psutil
- openai
- SQLite 標準ライブラリは Python に同梱
- PyYAML（config/*.yaml の検証を行う場合に必要。ただし必須ではない）

例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. リポジトリを取得
   - git clone ... などで取得。

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

3. 必要パッケージのインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があればそれを使う）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードはプロジェクトルートの .env を生成または更新します。
   - 重要な環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

5. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

6. 初回のデータ準備（任意）
   - DuckDB に prices_daily / raw_financials / raw_news 等のテーブルをロードする必要があります（リサーチ・AI 機能を使う場合）。
   - 監視用テーブルは run_monitoring/run_execution の起動時に自動作成（init_monitoring_db）されます。

使い方（主要スクリプト）
------------------------

- 実行エンジン（ExecutionEngine）を起動
  - 本番／開発の区別は KABUSYS_ENV 環境変数で切り替え
  - paper_trading の場合は MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
  - 実行コマンド:
      python -m kabusys.run_execution

  - 停止方法:
    - data/stop_requested.flag を作成すると、エンジンは検知して停止を開始します。
    - kill.flag を作成すると ExecutionEngine に停止シグナルを送る仕組み（KillSwitch）があります。
    - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリア（本番では 0 推奨）。

- 監視プロセス（Monitoring）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔はデフォルト 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。
  - 監視は SystemMonitor / TradeMonitor / RiskMonitor を定期的に呼び出し、kill.flag を書く/通知を出す等の機能を担います。

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成・更新できます。

- 設定検証ツール
  - python -m kabusys.validate_config
  - --strict オプションで警告をエラー扱いにできます。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db でパス指定可能。

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging により設定されます。
- デフォルトでは stdout に出力され、logs/<app_name>.log に日次ローテーションで保存（30 日分保持）。
- LOG_DIR 環境変数でログ保存先を変更可能。LOG_LEVEL でログレベル指定。

停止・Kill Switch
-----------------
- stop_requested.flag (data/stop_requested.flag): run_* スクリプトはこのファイルを検知すると優雅に終了します。
- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag): KillSwitch が書き込み、ExecutionEngine の停止トリガーやアラートに利用されます。
- PID ファイル: run_execution は data/execution.pid を使います（PID 管理）。

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト data/paper_trading.db）
- OPENAI_API_KEY（AI 機能使用時に必要）
- LOG_LEVEL（デフォルト INFO）
- LOG_DIR（ログ出力ディレクトリ）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。デフォルト 60）
- PAPER_FILL_MODE（paper_trading のマッチングモード: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。0/1）

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
  - Settings クラス: 環境変数の解決と検証
- config_setup.py
  - .env 作成用対話ウィザード
- validate_config.py
  - 起動前チェック CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト（python -m kabusys.run_monitoring）

サブパッケージ:
- ai/
  - news_nlp.py: ニュースを OpenAI に投げて銘柄ごとの sentiment/ai_score を生成
  - regime_detector.py: ETF と LLM を組み合わせて市場レジームを判定
- monitoring/
  - monitoring_db.py: SQLite の監視テーブルの初期化と永続化 API
  - system_monitor.py: CPU/メモリ/Disk/データ鮮度等のチェック
  - trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py 等（監視ロジック一式）
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等（発注ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（銘柄選定・重み・サイズ計算）
- research/
  - factor_research.py, feature_exploration.py（ファクター計算・解析）
- data/
  - pipeline や stats（DuckDB 操作用ユーティリティ）が存在する想定
- tools/
  - paper_verification_report.py（ペーパートレード検証レポート生成）

開発者向け補足
---------------
- 監視 DB（monitoring.db）は init_monitoring_db() によって必要なテーブルを作成します。既存スキーマに対するマイグレーションもいくつかサポートしています（列追加など）。
- AI 周りの API 呼び出しはリトライ・バックオフやレスポンスバリデーションを備え、失敗時はフェイルセーフ（スコア 0.0 など）で継続します。
- process_priority と cpu_affinity 設定は utils/process_priority.py にまとめられ、Windows / POSIX を抽象化しています。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）はリサーチ/AI 機能で参照されます。これらのデータ準備は別途パイプラインが必要です。

よくある操作例
--------------
- .env を作る:
    python -m kabusys.config_setup

- 設定検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- 監視開始:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン開始:
    python -m kabusys.run_execution

- ペーパートレード検証レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    または
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

注意事項 / 運用上のポイント
-------------------------
- 本番運用（KABUSYS_ENV=live）の場合は .env を慎重に管理し、絶対に Git にコミットしないこと。
- KILL_FLAG_CLEAR_ON_START は本番では 0 推奨。1 にすると起動時に既存の kill.flag を自動クリアしてしまい、誤動作の原因になります。
- Paper Trading は production DB と完全分離される設計ですが、設定ミスで本番 DB を参照しないよう .env の内容を validate_config で確認してください。
- DuckDB に投入するデータは時系列の整合性（look-ahead の禁止）を守ること。リサーチ関数群はルックアヘッドバイアス防止の工夫をしていますが、データ準備側でも注意が必要です。

ライセンス
----------
（ここにプロジェクトのライセンス情報を記載してください）

おわりに
--------
この README はコードベースの主要な使い方・設定・構成を簡潔にまとめたものです。より詳しい設計やアルゴリズムの説明は各モジュール内の docstring / コメント（PortfolioConstruction.md、StrategyModel.md 等を参照）を参照してください。質問や追加のドキュメントが必要であれば教えてください。