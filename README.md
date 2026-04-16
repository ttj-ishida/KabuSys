KabuSys — 日本株向け自動売買 / 監視フレームワーク
=================================================

概要
----
KabuSys は日本株の自動売買システム向けに設計された軽量フレームワークです。  
主な機能は発注実行、リコンシリエーション、監視（システム／注文／リスク）、ポートフォリオ構築、研究用ファクター計算、OpenAI を用いたニュース NLP などを含みます。  
SQLite（監視ログ等）と DuckDB（価格・財務データ等の分析）を併用する設計です。

主な特徴
--------
- ExecutionEngine：ブローカークライアントを介した発注管理・リスク制御・リコンシリエーション
- Monitoring：プロセス・データ鮮度・注文状態・ドローダウン等を定期監視しログおよびアラートを出力
- Kill Switch：条件（ドローダウン等）で ExecutionEngine 停止用のフラグファイルを書き込む仕組み
- Portfolio Construction：候補選定・重み付け・ポジションサイズ計算（純粋関数群）
- Research：DuckDB を用いたファクター計算・将来リターン・IC 計算
- AI モジュール：ニュースを LLM（OpenAI）でスコアリングし ai_scores に格納
- Tools：Paper Trading 検証レポート生成、Streamlit ダッシュボード等
- マルチ環境対応：development / paper_trading / live をサポート（KABUSYS_ENV）

セットアップ手順（開発用）
------------------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境（推奨）
   - Python 3.10+ を推奨（型ヒントで | を使用）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例: pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. data ディレクトリ作成（デフォルト DB/フラグ保存先）
   - mkdir -p data

5. 環境変数設定（.env）
   - プロジェクトルートに .env を作成すると自動で読み込まれます（優先順: OS 環境 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

代表的な環境変数（主要）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な場合あり）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

起動・使い方
------------

1) ExecutionEngine（発注エンジン）を起動
- 目的:
  - 本番時はブローカークライアントを使用
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、DB は data/paper_trading.db に分離されます
- 実行:
  - python -m kabusys.run_execution
- ポイント:
  - 起動時に PID ファイル（data/execution.pid）を作成します
  - data/stop_requested.flag が存在すると起動しません
  - 起動直後や実行中に kill.flag（Settings.kill_flag_path）を作成すると ExecutionEngine に停止シグナルを送れます

2) Monitoring（監視ループ）
- 目的: system / trade / risk の各監視を定期実行して monitoring DB（SQLite）にログを保存
- 実行:
  - python -m kabusys.run_monitoring
- オプション:
  - 環境変数 MONITOR_POLL_INTERVAL=秒数 でポーリング間隔を上書き（デフォルト 60 秒）
- ポイント:
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視ログは一元管理）
  - 停止は data/stop_requested.flag を作成することで行います（README: stop flow を参照）

3) Streamlit ダッシュボード（監視可視化）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - read-only モードで SQLite を開き、Positions / Orders / System / Overview を表示します

4) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- 出力:
  - 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等を集計して PASS/FAIL を判定

停止・フラグ関連
----------------
- data/stop_requested.flag
  - run_monitoring/run_execution が参照する停止フラグ。存在するとループを終了します。
- data/kill.flag
  - KillSwitch が生成する ExecutionEngine 強制停止フラグ（例: ドローダウン閾値超過）。存在すると実行エンジンは停止すべき旨を検出できます。
- PID ファイル
  - data/execution.pid に実行中の PID を書き出します。system_monitor は PID の有無／stale PID を検出してリスクログを残します。

OpenAI（AI モジュール）について
------------------------------
- news_nlp / regime_detector では OpenAI（gpt-4o-mini）を利用してニュースのセンチメントやマクロセンチメントを算出します。
- 動作には OPENAI_API_KEY が必要です（引数からも指定可）。
- API エラー（429・タイムアウト・5xx等）は指数バックオフでリトライし、最終的に失敗してもフェイルセーフなデフォルト（0.0 等）で継続します。

ディレクトリ構成（主要ファイル説明）
-----------------------------------
src/kabusys/
- __init__.py
  - パッケージメタ情報（__version__ 等）
- config.py
  - 環境変数読み込み・Settings クラス（.env 自動読み込み、KABUSYS_ENV 等）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading に応じて DB 切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- execution/
  - broker_api.py, broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, ...
  - 発注ロジック、Order 管理、リコンシリエーション等
- monitoring/
  - monitoring_db.py: SQLite テーブル初期化と永続化ラッパ
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 個別監視モジュール
  - kill_switch.py: フラグ生成・評価
  - alert_manager.py: LINE 通知送信
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定、重み付け、単元丸め、セクターキャップ等
- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター計算・IC 計算など
- ai/
  - news_nlp.py, regime_detector.py
  - OpenAI を使ったニュース/マクロセンチメントスコアリング
- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成スクリプト
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

注意・運用メモ
--------------
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成・カラム追加を行います。既存 DB に対する軽微なマイグレーション処理を含みます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注はモック実装（Broker の Mock）を使用し、DB は paper_trading 専用ファイルに切り離します（本番 DB と完全分離）。
- プロセス優先度:
  - 起動スクリプトはまず set_process_priority("high") を呼び出します。権限の問題で設定できない場合は警告が出ますが実行は継続します。
- ロギング:
  - 各スクリプトは基本的に logging.basicConfig(level=logging.INFO) を使用します。詳細ログは LOG_LEVEL 環境変数で制御できます（Settings.log_level）。
- テスト / 自動化:
  - .env 自動ロードはプロジェクトルート検出（.git または pyproject.toml）で行われます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

よくある操作コマンドまとめ
------------------------
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

補足
----
この README はコードベースの主要な使い方・設定をまとめたものです。実際の運用ではブローカー API の認証情報・手数料設定・スリッページ見積りなど詳細チューニングが必要です。変更・拡張の際は各モジュールの docstring を参照してください。

以上。必要ならサンプル .env.example（主要キー列挙）や簡単な運用手順書（起動順序、監視・ログ保存ポリシー）も作成します。どれが必要か教えてください。