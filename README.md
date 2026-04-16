KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買を支援するためのモジュール群です。注文実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュースセンチメント評価などを備えています。設計方針として「本番 DB とテスト（Paper Trading）を分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しは明示的に管理（OpenAI 等）」が採用されています。

主な機能
--------
- Execution
  - ExecutionEngine を起動してブローカーへ発注（本番 / paper_trading 切替）
  - OrderManager / OrderRepository / Reconciler による注文管理・再同期
  - RiskManager による上限・サーキットブレーカー等
- Monitoring
  - SystemMonitor: システムリソース・プロセス・データ鮮度監視
  - TradeMonitor: 注文滞留・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: 各 Monitor をまとめてポーリング、KillSwitch/AlertManager 統合
  - Streamlit ダッシュボード（監視 DB を可視化）
- Portfolio construction
  - 銘柄選定・重み計算（等金額 / スコア加重）
  - セクターキャップ、レジーム乗数、ポジションサイジング（単元丸め・aggregate cap）
- Research
  - ファクター計算（Momentum / Volatility / Value）および特徴量解析（forward return, IC 等）
  - DuckDB を用いたオンメモリSQL・分析処理
- AI 統合
  - news_nlp: OpenAI（gpt-4o-mini）でニュースをセンチメント評価し ai_scores に書込
  - regime_detector: MA200 とマクロニュースセンチメントを合成して market_regime 判定
- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成
- ユーティリティ
  - 設定管理 (kabusys.config.Settings)：.env / .env.local / 環境変数から設定を取得
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ
  - Monitoring DB 層（SQLite）初期化・読み書きユーティリティ

要件（想定）
-----------
- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

セットアップ手順
----------------
1. リポジトリをクローン／作業ディレクトリへ移動
   - 例: git clone ... && cd repo

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトで requirements.txt を用意する場合は pip install -r requirements.txt）

4. 環境変数設定
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可能）。
   - 主要な環境変数例:
     - KABUSYS_ENV = development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN（通知用）
     - LINE_USER_ID（通知先）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用: data/paper_trading.db)
     - PAPER_FILL_MODE = instant | partial | never | reject
     - LOG_LEVEL = DEBUG|INFO|...
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等

   - 例 (.env):
     KABUSYS_ENV=paper_trading
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=secret
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     PAPER_FILL_MODE=instant

5. データディレクトリの作成
   - mkdir -p data

6. 監視 DB の初期化（オプション）
   - init_monitoring_db() は run_* スクリプト内で自動的に呼ばれます。手動で初期化する場合は Python REPL から:
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

使い方
------
- ExecutionEngine 起動（本番 / paper_trading を Settings.env で切替）
  - python -m kabusys.run_execution
  - 起動時に Settings.is_paper==True（KABUSYS_ENV=paper_trading）の場合、MockBrokerClient を使い data/paper_trading.db に記録します。
  - 停止は data/stop_requested.flag を作成すると検知して安全停止します。

- Monitoring 起動（常時ポーリング）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依らず本番 DB へ記録する挙動に注意）。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を read-only モードで開いてダッシュボードを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（環境変数 PAPER_TRADING_SQLITE_PATH に優先）。

- AI 関連関数の呼び出し（ライブラリ API）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date（datetime.date）を渡すと ai_scores に評価を保存します。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルに結果を書き込みます。
  - どちらも api_key を None にすると環境変数 OPENAI_API_KEY を参照します。

- 停止・キルフロー
  - デフォルトの停止フラグ:
    - data/stop_requested.flag — run_* スクリプトが監視している停止フラグ（存在で停止）
    - data/kill.flag — KillSwitch が書き込む停止指示（ExecutionEngine に伝達）
    - data/execution.pid — ExecutionEngine の PID ファイル
  - KillSwitch（監視側）が基準に達した場合 data/kill.flag を書き込みます。ExecutionEngine は起動時や実行中にこれをチェックして停止します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 設定（.env / 環境変数読み込み、Settings クラス）
- run_execution.py — ExecutionEngine 起動スクリプト（__main__）
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト（__main__）

サブパッケージ（主要モジュール）
- kobusys/execution/
  - execution_engine.py (エンジン本体)
  - order_manager.py (OrderManager)
  - order_repository.py (DB 現物)
  - reconciler.py (再同期ロジック)
  - broker_factory.py, broker_api.py など（ブローカー抽象）
- kabusys/monitoring/
  - monitoring_db.py — SQLite monitoring DB 層（テーブル定義 / CRUD）
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - kill_switch.py, alert_manager.py, monitoring_engine.py
  - streamlit_dashboard.py — streamlit ダッシュボード
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- kabusys/research/
  - factor_research.py, feature_exploration.py
- kabusys/ai/
  - news_nlp.py, regime_detector.py
- kabusys/tools/
  - paper_verification_report.py

監視 DB（SQLite）概要
--------------------
monitoring_db.init_monitoring_db() によって次のテーブルが作成されます（冪等）:
- system_status: CPU/MEM/DISK/プロセス状態・記録時刻
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled など、latency_ms を含む）
- positions: 現在保有ポジション
- risk_logs: リスクイベント（DRAWDOWN_ALERT, STALE_ORDER, PRICE_ANOMALY など）
- dashboard: ダッシュボード集計（id=1 の単一行保持）

注意点 / 運用上のヒント
---------------------
- KABUSYS_ENV によって挙動が変わります。paper_trading ではブローカーは Mock、DB は PAPER_TRADING_SQLITE_PATH に分離されます。
- Settings は OS 環境変数を優先して .env/.env.local を読み込みます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑制できます。
- OpenAI 周りは API エラーやレート制限に対してバックオフやフォールバックを行う設計ですが、運用時は API キーやコストに注意してください。
- process_priority や CPU affinity は psutil を使って設定します。権限不足で失敗する可能性があるためワーニングでスキップする実装です。
- 停止・キルはフラグファイル方式のため、外部からのプロセス終了指示を安全に行えます（ファイルを書き込むだけ）。

開発・テスト
-------------
- 単体関数群（portfolio/*.py、research/*.py、monitoring/*）は外部副作用が少なくテストしやすい設計です。
- news_nlp / regime_detector の OpenAI 呼び出し部分は内部で切り出され、ユニットテスト時は _call_openai_api を patch してモック可能です。
- MonitoringEngine.run_once() を使うと単発実行で各モニタの動作を確認できます。

ライセンス / その他
-------------------
- このリポジトリのライセンス情報はここには含まれていません。配布・導入前に LICENSE ファイルを確認してください。

この README はコードベースから抜粋・要約して記載しています。実際の運用・デプロイ時は .env の設定、DB バックアップ、API キー管理、運用手順（起動 / 停止 / ログ管理）を別途ドキュメント化してください。必要であれば各モジュールの詳細な使い方（API サンプルや設定例）を追加で作成します。