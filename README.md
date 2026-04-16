KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を目的とした Python コードベースです。
主な機能としてシグナルに基づく発注・リコンシリエーション、ポートフォリオ構築、ファクター計算、
ニュース NLP を用いた銘柄スコアリング、そして実行プロセスの監視・アラート送信を提供します。

本 README はリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

主な特徴
--------
- Execution Engine
  - ブローカークライアントとの発注、OrderManager / OrderRepository を使った状態管理
  - リコンシリエーション (Reconciler) による起動時の自動同期
  - Paper Trading モード（本番 DB と分離された data/paper_trading.db を使用）
- Portfolio Construction
  - 候補選定、等重・スコア重み付け、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算
- Research
  - DuckDB 上で動くファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC 計算、ファクター統計サマリ
- AI（OpenAI）連携
  - ニュース記事を LLM でセンチメント評価し ai_scores テーブルへ書き込み
  - マクロニュースと ETF MA を組み合わせた市場レジーム検出
  - API コールはリトライ・フェイルセーフ実装済み
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db.init_monitoring_db）
  - LINE 連携による一方向アラート（AlertManager）
  - Streamlit ダッシュボード（data/monitoring.db を参照して表示）
- 管理ユーティリティ
  - kill.flag / stop_requested.flag による外部停止制御
  - process priority / CPU affinity の設定ユーティリティ（psutil）

前提（推奨）
------------
- Python 3.10+
- pip / venv 等による仮想環境
- 利用する機能に応じた外部パッケージ（下記参照）

セットアップ
-----------
1. リポジトリをクローンし、仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要パッケージ（手動インストール例）:
     - pip install duckdb psutil openai requests streamlit

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動読み込みされます。
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 重要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う際に必須）
     - KABUSYS_ENV — 動作環境: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — paper_trading の MockBroker 挙動（instant|partial|never|reject）（デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラート用（任意）
     - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）
   - サンプル .env（最低限）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

4. データディレクトリ
   - data/ 以下に各種 DB / PID / flag ファイルが作成されます。
   - 例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag, data/stop_requested.flag

基本的な使い方
--------------

1. 監視プロセスの起動（Monitoring）
   - 監視ループを起動するスクリプト:
     - python -m kabusys.run_monitoring
   - 挙動:
     - Settings から設定を読み取り（.env 自動ロードあり）
     - sqlite (Settings.sqlite_path) に接続し monitoring テーブルを初期化（init_monitoring_db）
     - duckdb に接続（Settings.duckdb_path）
     - SystemMonitor.check_once() をポーリング実行して system_status / risk_logs 等を記録
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒）
     - 停止: data/stop_requested.flag が存在するとループを抜けて終了（または Ctrl+C）

2. 実行エンジンの起動（Execution）
   - 実行エンジン起動スクリプト:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（Settings.paper_sqlite_path）を使用して本番 DB と完全分離
     - ブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動
     - data/execution.pid に PID を書き込む（停止時や stale PID の検出処理あり）
     - 起動前に data/stop_requested.flag が存在する場合は起動せず終了
     - 停止は data/stop_requested.flag を作成することで行えます（KillSwitch とは別）

3. Paper Trading 検証レポート生成
   - スクリプト:
     - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
   - デフォルト DB: data/paper_trading.db（--db でパス指定可）
   - レポート内容: 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数 等
   - 閾値に基づき PASS/FAIL を判定

4. Streamlit ベース監視ダッシュボード
   - 起動コマンド:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは monitoring DB を読み取り、Overview / Positions / Orders / System タブを表示

5. AI 機能
   - ニュース NLP スコアリング:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
     - OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）
   - 市場レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - API 呼び出しはリトライや JSON バリデーションを行い、失敗時はフェイルセーフ（スコア 0.0 等）で継続します。

運用に関する注意
----------------
- Monitoring は Settings.env の値にかかわらず monitoring 用 SQLite（Settings.sqlite_path）を使用します（監視データは本番 DB に保存されます）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper DB を使用して本番と分離します。
- process priority の設定には psutil を使います。high に設定する際は OS 権限が必要な場合があります（AccessDenied が起こり得るため警告ログでスキップします）。
- kill.flag / stop_requested.flag
  - KillSwitch は監視側から評価して data/kill.flag を書き込み、ExecutionEngine 停止をトリガする運用設計になっています（Settings.kill_flag_path を参照）。
  - 外部から停止したい場合は data/stop_requested.flag を作成すると監視・実行スクリプトが検知して終了します。
- DuckDB / SQLite のファイルパスは Settings でカスタマイズ可能です。DuckDB はリサーチ・ファクター計算で使用されます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数・設定管理 (.env 自動ロード)
- run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py        — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py       — SQLite 永続化層 (init / MonitoringDB)
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...（Broker / ExecutionEngine / repositories 等。省略）
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
- data/（実行時に生成されるファイル群）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

補足・開発メモ
--------------
- Settings クラスは各種環境変数をラップしており、値の検証・デフォルト設定を行います。KABUSYS_ENV の許容値は development|paper_trading|live です。
- DuckDB 接続は research / ai モジュールで使われます。prices_daily / raw_financials / raw_news 等のテーブルが前提です。
- AI 系は OpenAI SDK（openai パッケージ）に依存します。API レスポンスは厳密な JSON を期待しますが、若干の冗長テキストを復元するロジックも実装しています。
- 監視 DB のスキーマ変更は monitoring_db.init_monitoring_db がマイグレーション（簡易）を行います（例: カラム追加判定→ ALTER TABLE）。

トラブルシュート
----------------
- psutil.AccessDenied（プロセス優先度設定失敗）は権限不足のため警告が出ますが、処理は続行します。
- SQLite / DuckDB のファイルが開けない場合はパスや権限を確認してください。Streamlit は DB を読み取り専用で開くオプションを使います（URI + mode=ro）。
- OpenAI API 呼び出しで 429 や 5xx が返る場合はリトライ後、最終的にフェイルセーフ動作（スコア 0.0）になります。API キー設定を確認してください。

ライセンス / 貢献
-----------------
本リポジトリのライセンス情報やコントリビュートガイドは該当ファイル（LICENSE / CONTRIBUTING）を参照してください（存在する場合）。

以上が本プロジェクトの README です。必要であれば、環境ごとの .env.example、requirements.txt、起動用 systemd / supervisor 用のユニット例などの追記も作成します。どの情報を優先して追加しますか？