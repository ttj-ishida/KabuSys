README — KabuSys (日本株自動売買システム)
====================================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量な Python コードベースです。本リポジトリは主に以下を提供します。

- 注文実行エンジン（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- 監視サブシステム（System/Trade/Risk モニタ、Kill Switch、通知）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチ用ファクター計算モジュール（Momentum / Volatility / Value 等）
- AI ベースのニュース NLP（OpenAI を使ったニュースセンチメント）
- 検証ツール（Paper Trading レポート生成、Streamlit ダッシュボード）

主な特徴
--------
- 環境分離：KABUSYS_ENV により development / paper_trading / live を切り替え。paper_trading は専用 SQLite DB で本番 DB と分離。
- 監視と自動停止：定期的にシステム・注文・リスクをチェックし、kill.flag による停止シグナル発行や LINE での通知が可能。
- DuckDB を用いたローカル分析：prices_daily / raw_financials などのテーブルを用いてファクター計算や検証を行う。
- OpenAI 統合：ニュースのセンチメントやマクロセンチメントを LLM で評価し、market_regime / ai_scores に書き込み。
- テストしやすい純粋関数群：ポートフォリオ構築やポジション計算は DB に依存しない純粋関数で実装。

セットアップ
-----------
1. Python 環境（推奨: 3.10+）を用意します。
2. 仮想環境を作る（例）。
   - python -m venv .venv
   - source .venv/bin/activate
3. 依存ライブラリをインストールします（requirements.txt がない場合の例）。
   - pip install duckdb psutil openai requests streamlit
4. 環境変数を用意します（.env または .env.local をプロジェクトルートに置くことができます）。
   主要な環境変数（代表例）:
   - KABUSYS_ENV=development | paper_trading | live
   - OPENAI_API_KEY=sk-...
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - PAPER_FILL_MODE=instant | partial | never | reject
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - MONITOR_POLL_INTERVAL=60  （秒）
   .env の自動読み込みはデフォルトで有効。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

初期化メモ
- SQLite / DuckDB のファイルは初回接続時に作成され、監視のためのテーブル（monitoring_db.init_monitoring_db）は起動時に自動で作成されます。
- paper_trading モードでは PAPER_TRADING_SQLITE_PATH に取引ログ等が保存され、本番 DB と分離されます。

使い方（主要スクリプト）
-----------------------
- 監視ループ（SystemMonitor）
  - 実行:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 概要:
    - プロセス優先度を上げ、SQLite（monitoring DB）と DuckDB に接続して SystemMonitor を定期実行します。
    - 停止: プロジェクトルートの data/stop_requested.flag にファイルが存在するとループを抜けます。

- 注文実行エンジン（ExecutionEngine）
  - 実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 概要:
    - BrokerClientFactory により環境に応じたブローカークライアント（実運用またはモック）を生成。
    - paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用。
    - 起動時に data/stop_requested.flag があると起動をスキップします。
    - 停止は data/stop_requested.flag の作成、または KillSwitch により data/kill.flag が書かれるとエンジンが停止します。

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 概要:
    - PAPER_TRADING_SQLITE_PATH（または --db オプション）を読み取り、稼働率・注文成功率・レイテンシ等を算出して標準出力にレポートを表示します。

- Streamlit 監視ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 概要:
    - monitoring.db を読み取り、ダッシュボード（Overview / Positions / Orders / System）を表示します（読み取り専用モードで開く）。

- AI／レジーム評価
  - ニューススコア付与（Python から呼び出す例）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, date(2026, 4, 10), api_key="sk-...")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, date(2026, 4, 10), api_key="sk-...")

停止・安全装置
----------------
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring / run_execution の外側からプロセスを優雅に停止するために使います（存在検知でループを終了・エンジン停止）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch が条件（例: ドローダウン超過・ポジション上限超過）を満たすと書き込まれ、ExecutionEngine を停止させます。
- PID ファイル（data/execution.pid）
  - ExecutionEngine は PID を書き、SystemMonitor はその PID を監視してプロセス生存チェックを行います。古い（stale）PID は自動削除されアラートを記録します。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py
- config.py                      — 環境変数 / .env のロードと Settings
- run_monitoring.py              — SystemMonitor ポーリング起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py                   — ニュースセンチメント（OpenAI）
  - regime_detector.py            — マクロ＋MA によるレジーム判定

- monitoring/
  - monitoring_db.py              — SQLite 監視テーブル定義・CRUD
  - system_monitor.py             — システム状態・データ鮮度監視
  - trade_monitor.py              — 注文滞留・約定異常監視
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — kill.flag 制御
  - alert_manager.py              — LINE 通知
  - monitoring_engine.py          — 各モニタの統合ループ
  - streamlit_dashboard.py        — Streamlit 監視 UI

- execution/
  - order_manager.py              — 発注フロー制御
  - reconciler.py                 — 起動時の同期・復旧
  - （そのほか：broker_factory, order_repository 等が存在）

- portfolio/
  - portfolio_builder.py          — 候補選定・重み計算
  - position_sizing.py            — 発注株数計算
  - risk_adjustment.py            — セクターキャップ・レジーム乗数

- research/
  - factor_research.py            — ファクター計算（momentum/volatility/value）
  - feature_exploration.py        — 将来リターン・IC・統計

- tools/
  - paper_verification_report.py  — Paper Trading 検証レポート生成

- utils/
  - process_priority.py           — プロセス優先度・CPU affinity 設定ユーティリティ

補足
----
- DB マイグレーションやスキーマの追加（例：monitoring_db が起動時に列を追加する処理）は安全に実行されます。
- OpenAI / ブローカー API 呼び出しは例外処理・再試行ロジックが実装されていますが、API キー等の設定は運用環境で慎重に管理してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を検出して実行されます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

ライセンスや貢献方法、詳細な設計ドキュメント（PortfolioConstruction.md、StrategyModel.md 等）は別途参照してください。質問や追加のドキュメント化が必要であれば知らせてください。