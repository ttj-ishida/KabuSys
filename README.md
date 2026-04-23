README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。
主な目的は以下です。

- 注文実行エンジン（ExecutionEngine）および監視（Monitoring）用途のユーティリティ群
- ポートフォリオ構築 / ポジションサイジング / リスク制御の純粋関数群
- DuckDB/SQLite を使ったリサーチ・永続化レイヤ
- OpenAI を使ったニュース NLP（センチメント）および市場レジーム判定の試験的実装
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポートなど）

主な特徴
--------
- 実行環境分離: KABUSYS_ENV によって development / paper_trading / live を切り替え可能。paper_trading 時は発注がモック化され、専用 DB に記録される。
- モニタリング: System / Trade / Risk の監視を行い、条件に応じて kill.flag を書き込む KillSwitch 機能を備える。
- ポートフォリオ構築モジュール: 候補選定・重み計算・セクター制約・ポジションサイズ計算を純粋関数として提供。
- リサーチ機能: DuckDB 接続を受けてファクター計算・将来リターン・IC 計算などを行う。
- AI 機能（オプション）: OpenAI API を利用したニュースセンチメント（ai_scores）と市場レジーム判定（market_regime）。
- ロギング: 統一的な logging 設定（コンソール + 日次ローテートファイル）。

必須 / 主要な環境変数
--------------------
最低でも以下の環境変数を設定してください（.env を推奨）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (省略時: development) — 有効値: development, paper_trading, live
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
- LOG_LEVEL (デフォルト: INFO)

AI 機能を使う場合:
- OPENAI_API_KEY

（.env の自動読み込みはプロジェクトルートが検出できる場合に実行されます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）

セットアップ手順
--------------
1. Python 環境を用意（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイル検証に必要（任意）: pip install PyYAML

   （requirements.txt がある場合はそれを使用してください）

3. プロジェクトルートに .env を配置
   - 対話的に作成する: python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参照して必要キーを設定してください

4. 初期化（必要に応じて）
   - data/ ディレクトリを作成（ログ / DB 保存先など）
   - sqlite/duckdb ファイルは初回実行時に自動作成・マイグレーションされます

設定検証
--------
起動前に設定・ファイル群を検証できます。

- 設定検証 CLI:
  - python -m kabusys.validate_config
  - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

主要な使い方
-----------

1) Execution（発注エンジン）を起動
- 実行例:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 起動時に data/execution.pid が使われます。data/stop_requested.flag が存在すると起動を中止します。
  - 停止は stop flag（data/stop_requested.flag）を作ることで行えます。ExecutionEngine は定期的にこのフラグを確認して安全に停止します。

2) Monitoring（監視ループ）を起動
- 実行例:
  - python -m kabusys.run_monitoring
- 挙動:
  - 監視ループは SystemMonitor.check_once() を定期実行し、MonitoringEngine のアラートや KillSwitch の評価を行います。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用します（監視 DB は実環境の状態を監視するため）。

3) .env の対話式セットアップ
- python -m kabusys.config_setup
  - 対話で .env を生成・更新します。

4) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - PAPER_TRADING_SQLITE_PATH 環境変数または --db で DB パスを指定できます。
  - 注文成功率、稼働率、レイテンシ等の指標を表示し PASS/FAIL を判定します。

5) AI 機能（プログラム的利用）
- ニューススコアリング:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
    - api_key が None の場合は環境変数 OPENAI_API_KEY を参照する
- レジームスコア:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30 日保持）。
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されています。
- app_name の例: "execution", "monitoring"（run_* スクリプトは起動時にそれぞれ設定します）

停止・Kill Switch
-----------------
- 手動停止フラグ（run scripts 共通）:
  - data/stop_requested.flag — 存在すると監視/実行ループは終了します（run_execution/run_monitoring が参照）。
- KillSwitch（リスク基準で自動停止）:
  - monitoring が条件を満たした場合 Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine は起動中にこの kill.flag を参照して停止します。
  - kill.flag を手動でクリアするにはファイルを削除してください（例: rm data/kill.flag）。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動でクリアされる振る舞いがありますが、本番では 0 を推奨します。

内部 DB スキーマ（監視用）
------------------------
monitoring_db.init_monitoring_db によって以下テーブルが作成されます（一部抜粋）:

- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (単一行の集計: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

主なモジュール（ファイル）説明
----------------------------
- run_execution.py — ExecutionEngine 起動スクリプト（実行/ペーパートレード分離）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- config_setup.py — .env 対話的ウィザード
- validate_config.py — 起動前検証 CLI（env / config/*.yaml / path 等）
- monitoring/ — 監視関連コンポーネント群（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine, monitoring_db）
- portfolio/ — ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群
- research/ — DuckDB を用いたファクター計算・IC・特徴量探索
- ai/ — OpenAI を用いたニュース NLP（news_nlp）・レジーム判定（regime_detector）
- utils/ — logging_setup, process_priority（プロセス優先度設定）、その他ユーティリティ
- tools/ — paper_verification_report 等の運用ユーティリティ

ディレクトリ構成（要約）
---------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / Settings クラス（.env 自動ロード含む）
- config_setup.py               — .env ウィザード
- validate_config.py            — 設定検証 CLI
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — Monitoring 起動スクリプト

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py (実装が存在する想定)
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py (実装が存在する想定)

- execution/ (発注関連コンポーネント: Engine, BrokerFactory, OrderManager など)
- portfolio/ (portfolio_builder.py, position_sizing.py, risk_adjustment.py, __init__.py)
- research/ (factor_research.py, feature_exploration.py, __init__.py)
- ai/ (news_nlp.py, regime_detector.py, __init__.py)
- tools/ (paper_verification_report.py, __init__.py)

注意事項 / 運用上のヒント
------------------------
- paper_trading モードは本番 DB とデータを完全に分離する設計になっています。ペーパートレードを行う場合は必ず KABUSYS_ENV=paper_trading を設定してください。
- 本番モード（KABUSYS_ENV=live）では LINE などの通知設定や Kill Switch の扱いを事前に確認してください（validate_config で警告が出ます）。
- process priority の設定は psutil を使用します。アクセス権限による失敗は警告になり、処理は継続します。
- DuckDB への書き込み（ai_scores や market_regime 等）は executemany の空リストバインドなどの互換性に注意した実装になっています。DuckDB バージョンに依存する問題が出た場合はバージョン確認を行ってください。
- ロギングは logs/ に出力されます。ログディレクトリが作成できない場合はコンソール出力のみになります。

貢献
----
バグ報告や機能追加は issue / PR を歓迎します。コードのスタイルやテストを追加していただけると助かります。

ライセンス
---------
（ここにプロジェクトのライセンス情報を記載してください）

以上。必要に応じて README の補足（実行例、systemd ユニット例、詳細な API 仕様）を追加します。どの部分を詳しく書いて欲しいか教えてください。