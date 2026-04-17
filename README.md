KabuSys — README
=================

概要
----
KabuSys は日本株自動売買プラットフォームのコアライブラリ群です。本リポジトリには以下の主要機能を持つモジュールが含まれます。

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- 監視（System/Trade/Risk モニタ、アラート、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイジング、セクター制約）
- リサーチ / ファクター計算（モメンタム、バリュー、ボラティリティ等）
- AI 支援（ニュースの NLP スコアリング、レジーム判定）
- 運用用ユーティリティ（プロセス優先度、Streamlit ダッシュボード、検証レポート）

設計方針（ポイント）
- DB は DuckDB（マーケットデータ等）と SQLite（監視・注文ログ等）を併用
- Paper Trading 環境は本番 DB と分離可能（PAPER_TRADING_SQLITE_PATH）
- LLM 呼び出し（OpenAI）はフェイルセーフ設計、部分失敗を許容
- 自動で .env/.env.local をロード（必要に応じて無効化可能）

主な機能一覧
--------------
- 実行（run_execution.py）
  - Broker クライアント生成（本番 or Mock/ペーパートレード）
  - OrderManager / RiskManager / Reconciler による注文実行と自動復旧
- 監視（run_monitoring.py / monitoring package）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - TradeMonitor: 滞留注文 / 約定価格異常監視
  - RiskMonitor: ドローダウン / ポジション上限監視
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - KillSwitch: 条件到達で実行エンジン停止用 flag ファイルを書込
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）
- ポートフォリオ（portfolio package）
  - 銘柄選定、等配分/スコア加重、リスクベースのポジションサイジング
  - セクターキャップ、レジーム乗数
- リサーチ（research package）
  - ファクター計算（momentum/volatility/value）および特徴量探索
- AI（ai package）
  - news_nlp.score_news(): Raw news をまとめて OpenAI に送り銘柄ごとの ai_score を書き込み
  - regime_detector.score_regime(): ma200 とマクロニュースを組み合わせて日次レジーム判定
- ツール（tools）
  - paper_verification_report: Paper Trading DB の指標（稼働率・成功率・レイテンシ等）を出力

セットアップ手順
----------------
1. Python とパッケージのインストール（例: Python 3.10+ 推奨）
   - requirements.txt があれば:
     - pip install -r requirements.txt
   - 主要な依存を個別にインストールする場合:
     - pip install duckdb psutil requests openai streamlit

2. プロジェクトルートに .env を用意（任意）
   - サンプル: .env.example をベースに作成してください（リポジトリに例ファイルがない場合は下記の環境変数を参照）

3. 主要な環境変数（代表）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （必須: J-Quants API 用）
   - KABU_API_PASSWORD: （必須: kabuステーション API）
   - OPENAI_API_KEY: （AI 機能を使う場合）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用、デフォルト instant）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
   - SQLITE_PATH: data/monitoring.db（監視用 DB のデフォルト）
   - DUCKDB_PATH: data/kabusys.duckdb（DuckDB のデフォルト）
   - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL / MONITOR_POLL_INTERVAL 等

   注意: .env / .env.local は自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

4. データディレクトリ
   - data/ 以下に DB やフラグファイルを作成します（自動で作られる場合あり）。
   - 例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag

使い方（主な実行例）
--------------------

1. 監視ループを起動（デフォルト: ポーリング間隔 60 秒）
   - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（1 以上）
   - 実行:
     - python -m kabusys.run_monitoring
   - 終了方法:
     - data/stop_requested.flag を作成するとループが検出して終了します（ファイル場所はスクリプトで固定）
     - または Ctrl+C

2. ExecutionEngine（発注エンジン）を起動
   - KABUSYS_ENV=paper_trading の場合は MockBroker が使われ、paper_trading 用 DB に記録されます
   - 実行:
     - python -m kabusys.run_execution
   - 停止:
     - data/stop_requested.flag を作成するとエンジンが安全停止します

3. Streamlit ダッシュボード（監視 UI）
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 注意: dashboard は監視プロセスが DB に書き込んでいることが前提

4. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - --db path/to/paper_trading.db または環境変数 PAPER_TRADING_SQLITE_PATH を利用

5. AI 機能（ニューススコアリング / レジーム判定）
   - OpenAI API キーが必要: OPENAI_API_KEY を設定
   - モジュール関数:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - これらは DuckDB 接続を受け取り、ai_scores / market_regime テーブルへ書き込みます
   - LLM の失敗は基本的にフェイルセーフ（スコア=0 など）で処理されます

運用上のファイル / フラグ
- data/execution.pid: 実行エンジン PID（SystemMonitor はこのファイルでプロセス生存を判定）
- data/kill.flag: KillSwitch が書き込む停止指示フラグ（手動で削除するか、KillSwitch.clear 相当でクリア）
- data/stop_requested.flag: スクリプト（run_*）が監視している停止要求フラグ（存在を検知すると安全終了）

設定ファイルの自動読み込み
- .env（プロジェクトルート）および .env.local を自動ロード（OS 環境変数が優先）
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

ディレクトリ構成
----------------
以下は主要なソース配置（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - run_monitoring.py        — SystemMonitor ポーリングスクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP / OpenAI 呼び出しロジック
    - regime_detector.py     — レジーム判定ロジック
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite の永続化 / MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 Execution 系モジュール: broker_factory 等)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py
  - data/                    — 実行時に使用する DB / フラグ類（リポジトリ外のディレクトリ）

補足・運用上の注意
------------------
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。環境変数で上書き可（デフォルト 60）。
- run_monitoring / run_execution は起動時に set_process_priority("high") を試みます（psutil の権限に依存）。
- Paper Trading と本番の DB は分離されます（settings.is_paper を参照）。
- OpenAI 使用箇所はリトライ・バックオフ・レスポンス検証を実装しているが、API 利用料とレート制限に注意してください。
- DuckDB / SQLite スキーマやマイグレーションはモジュール内に記載（init_monitoring_db など）。既存 DB に対するカラム追加処理も含む。

ライセンス・貢献
----------------
この README はコードベースの自動生成ドキュメントです。実際のライセンス／貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

以上。必要があれば README に含めるサンプル .env、起動コマンド集、または各モジュールの API 仕様（関数シグネチャ）を追記します。どの情報を追加しますか？