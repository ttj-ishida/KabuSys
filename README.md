KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株自動売買システム「KabuSys」の実装です。  
本 README はコードベース（src/kabusys/**）を基に、プロジェクト概要・主要機能・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は以下の主要機能を持つ自動売買プラットフォームです。

- 注文実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレードの切替
  - ブローカークライアント抽象化（BrokerClientFactory）
  - 注文管理・リスク管理・レコンシリエーション
- 監視（Monitoring）
  - システムリソース監視、データ鮮度チェック、取引ログ監視、リスク監視
  - Kill Switch（条件を満たすと ExecutionEngine 停止フラグ書き込み）
  - 監視データ永続化（SQLite）
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み付け・ポジションサイズ算出・セクター制限・レジーム乗数
- リサーチ（DuckDB を使ったファクター計算 / 特徴量解析）
  - モメンタム、バリュー、ボラティリティ等のファクター
  - 将来リターン・IC（Information Coefficient）計算
- AI モジュール（OpenAI を利用）
  - ニュース NLP（銘柄ごとセンチメント算出）→ ai_scores へ保存
  - 市場レジーム判定（ETF + マクロニュースの LLM 評価）
- ツール類
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成スクリプト

主な機能一覧
-------------
- run_execution: ExecutionEngine 起動（KABUSYS_ENV により paper_trading / live 切替）
- run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL 環境変数で間隔変更可）
- config_setup: .env を対話的に作成・更新
- validate_config: .env / config/*.yaml の事前検証（--strict オプションあり）
- tools.paper_verification_report: ペーパートレード結果の検証レポート出力
- portfolio.*: 候補選定・重み付け・ポジションサイズ算出・リスク調整の純粋関数
- research.*: DuckDB を使ったファクター計算・解析
- ai.*: OpenAI を使ったニュースセンチメント、レジーム判定
- monitoring.*: MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine
- utils: ロギング設定・プロセス優先度・CPU affinity 等のユーティリティ

セットアップ手順
----------------
1. Python 環境
   - Python 3.9 以降を推奨（コードは型注釈で modern Python を想定）
2. 依存パッケージ（例）
   - pip install duckdb psutil openai
   - PyYAML は validate_config の YAML 検証で任意（インストールされていない場合は YAML 検証をスキップ）
   - 例: pip install duckdb psutil openai pyyaml
3. リポジトリのルートで初期ファイル配置
   - データ・ログ用ディレクトリは実行時に作成されますが、手動で作る場合:
     - mkdir -p data logs
4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（下にサンプルを記載）
5. 設定検証（実行前に推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合: python -m kabusys.validate_config --strict
6. 実行
   - 監視: python -m kabusys.run_monitoring
   - 実行エンジン: python -m kabusys.run_execution
   - Paper レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD --to YYYY-MM-DD --db PATH]

必須 / よく使う環境変数（.env 例）
---------------------------------
必須:
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_kabu_password_here

その他（デフォルト値あり）:
- KABUSYS_ENV=development  # development | paper_trading | live
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- LOG_LEVEL=INFO
- LOG_DIR=logs
- OPENAI_API_KEY=（AI 機能を使う場合に指定）

簡単な .env サンプル:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

運用上の注意
-------------
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて data/paper_trading.db に記録します（本番 DB と完全分離）。
- run_monitoring は監視用の本番 sqlite_path（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用）を参照します。
- Kill Switch: data/kill.flag を書き込むことで ExecutionEngine に停止信号を送ります。kill.flag は Settings.kill_flag_path で指定できます。
- 停止フラグ: run_execution / run_monitoring は data/stop_requested.flag の存在を監視して安全に終了します。
- ログ:
  - デフォルトディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: execution.log, monitoring.log）
  - 日次ローテーション（30日分保持）

使い方（コマンド例）
-------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL は秒（デフォルト 60）。1 未満や不正値は無視されデフォルトにフォールバック。
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合: python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

主要コンポーネントの概要
------------------------
- run_execution.py
  - Settings 読込 → DB 接続（paper_trading 時は専用 DB）→ BrokerClient 作成 → OrderRepository / OrderManager / RiskManager / Reconciler 準備 → ExecutionEngine.run_session をスレッドで起動
- run_monitoring.py
  - Settings 読込 → 本番 sqlite に接続 → SystemMonitor 初期化 → ポーリングループで monitor.check_once() を定期実行
- monitoring/monitoring_db.py
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを管理・マイグレーション
- monitoring/system_monitor.py / trade_monitor.py / risk_monitor.py / kill_switch.py / monitoring_engine.py
  - 各種チェックを実行し、必要に応じて kill.flag を書き込んだりアラート通知を呼ぶ（AlertManager 実装に依存）
- portfolio/*
  - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier（全て副作用なしの純粋関数）
- research/*
  - DuckDB 接続を受けてファクターを計算。prices_daily / raw_financials 等のテーブルのみ参照。
- ai/*
  - news_nlp: OpenAI（gpt-4o-mini）を使ったニュースセンチメント集約 → ai_scores へ書込
  - regime_detector: ETF の MA とマクロニュース（LLM）を合成して日次レジーム判定 → market_regime テーブルに保存

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数 / .env 自動ロードロジック
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

src/kabusys/ai/
- news_nlp.py
- regime_detector.py
- __init__.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py (想定、実装により有無あり)

src/kabusys/execution/
- execution_engine.py
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py
- broker_factory.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py

データ / ログ / フラグ（既定パス）
--------------------------------
- DuckDB: data/kabusys.duckdb (DUCKDB_PATH)
- Monitoring SQLite: data/monitoring.db (SQLITE_PATH)
- Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- PID / kill / stop フラグ:
  - data/execution.pid, data/kill.flag, data/stop_requested.flag
- ログ: logs/<app_name>.log

補足・運用ヒント
----------------
- .env の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 機能を利用する場合は OPENAI_API_KEY を設定してください。AI API 呼び出しは外部サービスに依存するため、ネットワークエラーやレート制限を想定したリトライロジックが組み込まれています（それでも運用者側でレート管理が必要）。
- 本番環境（KABUSYS_ENV=live）では特に kill flag / LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を確認してから起動してください。validate_config にて live 時の追加警告が出ます。

ライセンス・貢献
----------------
- この README はコードからの抽出説明です。実際のライセンスや貢献フローはリポジトリのトップレベルファイル（LICENSE, CONTRIBUTING.md 等）を参照してください。

フィードバック・不明点
--------------------
実行方法や特定モジュールの挙動についてさらに詳細が必要であれば、どの部分（例: ExecutionEngine の設定項目、RiskManager のパラメータ、AI モジュールの API 呼び出し挙動など）を深掘りしたいか教えてください。必要に応じてサンプル .env や運用チェックリストも作成します。