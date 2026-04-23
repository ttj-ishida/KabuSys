KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのライブラリ兼ランタイムです。
主な目的は以下のとおりです。

- 注文発行・執行管理（ExecutionEngine）
- モニタリング（System / Trade / Risk）と Kill Switch（停止フラグ）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量探索）
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント評価）
- Paper Trading の検証やレポート生成

プロジェクトはモジュール設計されており、運用スクリプト（起動スクリプト）とプログラム的 API の両方を提供します。

主な機能
--------
- ExecutionEngine（run_execution.py）:
  - 実際の発注ロジックを組み立て、BrokerClient（本番/モック）経由で発注を実行
  - Paper Trading 環境では MockBrokerClient を使い、本番 DB と分離して data/paper_trading.db に記録
  - PID ファイル管理、停止フラグ検出による安全停止処理

- Monitoring（run_monitoring.py / monitoring パッケージ）:
  - SystemMonitor: CPU/メモリ/ディスクの監視、データ鮮度チェック、Execution プロセス生存確認
  - TradeMonitor: 注文滞留・約定異常などの監視（詳細は該当実装ファイルを参照）
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送付
  - MonitoringEngine: 上記を束ねてポーリング運用

- Portfolio（portfolio パッケージ）:
  - 候補選定（select_candidates）、等金額/スコア加重の重み計算
  - セクター集中制限（apply_sector_cap）、レジーム基準の乗数（calc_regime_multiplier）
  - 発注株数計算（calc_position_sizes）: リスクベース / 等分配 等の算出と lot 単位丸め、aggregate cap 調整

- Research（research パッケージ）:
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）: DuckDB を用いた SQL ベース実装
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（ai パッケージ）:
  - news_nlp.score_news: raw_news を OpenAI（gpt-4o-mini）で評価して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA乖離とマクロニュースを合成して market_regime を判定
  - API 呼び出しは堅牢なリトライ・検証ロジックを持つ（OpenAI API キー必須）

- ユーティリティ:
  - 設定管理（config.py）: .env の自動読み込み、Settings クラス経由の設定取得
  - .env ウィザード（config_setup.py）: 対話式で .env を生成
  - 設定検証 CLI（validate_config.py）: .env と config/*.yaml の事前検証
  - ログ設定ユーティリティ（utils.logging_setup）: stdout と日次ローテートファイル出力
  - プロセス優先度設定（utils.process_priority）: cross-platform に優先度を調整

セットアップ手順
--------------
以下は基本的なセットアップ手順です（環境に合わせて調整してください）。

1. リポジトリをクローン・ソース配置
   - 本 README は src/kabusys 以下のコードを前提としています。

2. Python 環境を用意
   - Python 3.10+ を推奨
   - 必要なパッケージ（代表例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例（pip）:
     - pip install duckdb psutil openai PyYAML

3. .env の作成（対話式ウィザード推奨）
   - 以下コマンドでウィザードを実行:
     - python -m kabusys.config_setup
   - 最低限設定が必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI 機能を利用する場合:
     - OPENAI_API_KEY を環境変数に設定（または score_news/score_regime を呼ぶ際に渡す）

4. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いになります。

5. ディレクトリ / データベース
   - デフォルトで以下のファイル/ディレクトリを使用します:
     - data/monitoring.db (SQLite, monitoring)
     - data/paper_trading.db (Paper Trading 用、KABUSYS_ENV=paper_trading 時)
     - data/kabusys.duckdb (DuckDB)
     - logs/ （ログファイル）
   - 必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。
   - monitoring 起動時に monitoring DB テーブルは自動で初期化されます（冪等）。

基本的な使い方
--------------
コマンドラインから実行する主なスクリプト:

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用してモックブローカーで実行
    - 起動前に data/stop_requested.flag があれば起動せず終了
    - 実行中に data/stop_requested.flag が作成されると安全に停止

- 監視ループ（Monitoring）を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は Settings.sqlite_path を使ってデータを永続化（監視は環境にかかわらず本番 sqlite_path を参照）

- .env の対話生成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db で DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

プログラム的 API（呼び出し例）
- ニューススコア付与（DuckDB 接続と target_date を渡して呼ぶ）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
- ポートフォリオ関数群:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes, ...
  - （これらは純粋関数なのでテストや組み込みが容易）

重要な環境変数（主な抜粋）
--------------------------------
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — run_monitoring でのポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

停止フラグ / Kill Switch の仕組み（運用注意）
--------------------------------------------
- モニタリングが KillSwitch の条件（ドローダウン超過やポジション上限超過）を検出すると data/kill.flag を書き込みます。これにより ExecutionEngine 側で停止処理を行います。
- 運用者が手動で停止を要求する場合は data/stop_requested.flag を作成しておくと、run_execution/run_monitoring のループが検知して停止します（run_execution は起動前に存在すれば起動しません）。
- 本番運用では KILL_FLAG_CLEAR_ON_START を 0 に設定しておくことを推奨します（誤って自動でクリアしないため）。

ディレクトリ構成
----------------
（src/kabusys 配下の主なファイル・モジュール抜粋）

- src/kabusys/
  - __init__.py
  - run_execution.py            # ExecutionEngine 起動スクリプト
  - run_monitoring.py          # Monitoring ポーリング起動スクリプト
  - config.py                  # .env 自動読み込み・Settings クラス
  - config_setup.py            # .env 対話式ウィザード
  - validate_config.py         # 設定検証 CLI
  - data/                      # （実行時に利用する data/* ファイルを想定）
  - logs/                      # ログ出力先（デフォルト）
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py

運用上の注意
------------
- 本システムは本番口座での発注を行う機能を含みます。KABUSYS_ENV を正しく設定し（特に live モード）、API キーやパスワードの管理を厳重に行ってください。
- .env（機密情報）を Git にコミットしないでください（config_setup.py のヘッダに注意書きがあります）。
- OpenAI API を利用する機能は API コストが発生します。使用前にクォータ/課金設定をご確認ください。
- psutil によるプロセス優先度変更は権限が必要な場合があります。権限エラーは警告に留まり、実行は継続します。

貢献 / 拡張ポイント
-------------------
- BrokerClient の具体実装（kabuステーションとの連携）や mock の拡充
- データ取得パイプライン（prices_daily / raw_financials / raw_news の作成）
- アラートチャネル（LINE 通知）の実装強化
- strategy / execution_config に基づく戦略の実装追加

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE 等を参照してください（このスナップショットには含まれていません）。

問い合わせ
----------
- この README に記載の動作やコードの詳細は各モジュールの docstring を参照してください。
- 実運用に移す前に、config_setup → validate_config → ローカル Paper Trading での十分な検証を行ってください。

以上。必要があれば運用手順（systemd / cron / Supervisor によるデーモン化等）のテンプレートや、よくあるトラブルシュート項目も追加します。どの情報が欲しいか教えてください。