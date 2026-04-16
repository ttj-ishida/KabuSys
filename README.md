# KabuSys

日本株向け自動売買システムの一部を構成するモジュール群のリポジトリ。  
この README はリポジトリ内の主要コンポーネントと使い方、セットアップ手順、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- リスク監視（RiskMonitor）
- システム監視（SystemMonitor）・監視ログ永続化（SQLite）
- 監視ダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- 研究用ファクター計算（DuckDB を用いたファクター計算）
- ニュースを用いた AI スコアリング（OpenAI API 経由）
- Paper Trading（本番 DB と分離して模擬注文を行う）
- 各種ユーティリティ（プロセス優先度設定など）

設計方針の要点：
- DuckDB を分析用に利用、SQLite を監視ログや発注ログの永続化に使用
- 環境変数 / .env ファイルで設定管理（自動ロードあり）
- Paper Trading は本番 DB と分離（デフォルト data/paper_trading.db）
- OpenAI 呼び出しは失敗時にフォールバックする等、堅牢性を考慮

---

## 主な機能一覧

- run_monitoring.py: SystemMonitor をポーリングし監視ログを記録するデーモン（MONITOR_POLL_INTERVAL で間隔変更可）
- run_execution.py: ExecutionEngine を起動して発注処理を実行（paper_trading モード時は MockBrokerClient を使用）
- monitoring:
  - MonitoringDB: SQLite テーブル作成・読み書き（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - AlertManager: LINE push による通知（channel token / user id 必須）
  - KillSwitch: kill.flag を書き込み ExecutionEngine に停止シグナルを送る
  - streamlit_dashboard: Streamlit による監視ダッシュボード
- portfolio: 候補選定・重み計算・リスク調整・株数決定ロジック（純粋関数）
- research: DuckDB ベースのファクター計算・将来リターン計算・IC 等の統計処理
- ai:
  - news_nlp.score_news: raw_news を LLM（OpenAI）でスコアリングして ai_scores に保存
  - regime_detector.score_regime: MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- tools.paper_verification_report: Paper Trading のログ分析・検証レポート生成

---

## セットアップ手順

前提
- Python 3.9+ を想定（duckdb, psutil, openai, requests, streamlit 等の依存ライブラリが必要）
- OS によってはプロセス優先度 / CPU affinity の設定で追加権限が必要になる場合があります

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit

   必要に応じてプロジェクトの requirements.txt / pyproject.toml に従ってください。

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
   - 主要な環境変数（一例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants API
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring のデフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH: 実行管理用ファイルパス

4. 初回 DB 作成
   - run_monitoring.py や run_execution.py は起動時に init_monitoring_db() を呼び DB テーブルを冪等に作成します。
   - 明示的に作成したければ Python REPL で init_monitoring_db を呼び出しても良いです。

---

## 使い方

以下はよく使うコマンドの例です。プロジェクトルートで実行してください。

1. 監視ループ（SystemMonitor）を起動
   - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を変更:
     - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

   特記事項:
   - 監視は常に本番用の sqlite_path を使用する設計（KABUSYS_ENV にかかわらず）。
   - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行えます（スクリプトは起動時に親ディレクトリを基準に探索）。

2. ExecutionEngine を起動（発注処理）
   - python -m kabusys.run_execution
   - Paper trading モード:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
     - この場合は MockBrokerClient を使い、デフォルトで data/paper_trading.db に記録します。

   停止:
   - data/stop_requested.flag が検知されるとエンジンを停止します。
   - 「kill.flag」を作成すると ExecutionEngine に停止要求（KillSwitch 経由）を送る一方的な手段になります（KillSwitch は条件により自動生成される場合あり）。

3. Streamlit ダッシュボード起動
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB を read-only モードで参照します。MonitoringEngine を先に起動しておくとデータが見られます。

4. Paper Trading 検証レポートを生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - データベースを指定:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI スコアリング関数の利用（Python から）
   - news_nlp.score_news / regime_detector.score_regime は Python API として利用できます。例:

     from datetime import date
     import duckdb
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     count = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")

   - OpenAI API キーは引数で指定するか、環境変数 OPENAI_API_KEY を設定してください。

---

## 環境変数と自動ロードの挙動

- 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を検出）を基準に .env を自動ロードします。
  - ロード順: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- 主要な設定（要約）
  - KABUSYS_ENV: development | paper_trading | live（必須ではないが有効値のみ許容）
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - DUCKDB_PATH: 分析 DB（デフォルト data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH: Paper 用 DB（デフォルト data/paper_trading.db）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH: 実行管理ファイル

---

## 実装上の注意点・挙動

- DB マイグレーション:
  - init_monitoring_db() は既存テーブルの存在チェックと必要なカラム追加（例: peak_value, latency_ms）を行います（簡易マイグレーション）。

- プロセス優先度:
  - run_monitoring / run_execution は起動時に set_process_priority("high") を試みます（psutil を利用）。権限不足等で失敗する場合は警告を出して続行します。

- Kill / Stop フラグ:
  - data/stop_requested.flag により run_* スクリプトのループを終了できます（運用者が手動で作成する想定）。
  - KillSwitch は一定条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検出されることにより停止を誘導します。

- Paper Trading:
  - KABUSYS_ENV=paper_trading により broker クライアントは MockBrokerClient を使い、paper_trading 用 SQLite に記録されます。本番データと完全に分離されます。

- OpenAI 呼び出し:
  - AI 関連処理は外部 API に依存するため、429 / タイムアウト / 5xx などに対してリトライやフォールバック（ゼロスコア）処理を備えています。
  - レスポンスのバリデーションを厳格に行い、不正応答はスキップします。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル・モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
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
    - (その他の実装ファイルが存在する想定)
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
  - data/ (実行時に使用される既定ディレクトリ)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading 用、デフォルト)

各モジュールはコメントとドキュメント文字列で設計意図や使用法を明示しています。関心のある機能ごとに該当ファイルを参照してください。

---

## 開発時のヒント

- DuckDB のクエリは分析処理の中心です。ローカルで小さな DuckDB ファイルを作り、REPL から関数を試すと開発効率が上がります。
- OpenAI 呼び出し部はユニットテストしやすいように _call_openai_api を切り出してあり、テスト時にモック差替えが可能です。
- .env のパースは独自実装で、export 形式やクォート・コメントを扱います。特殊な値を使う場合は .env の文法に注意してください。

---

もし README に追加したいチュートリアル（例: 初期 DB のダミーデータ投入や ExecutionEngine の挙動確認手順）や、環境固有のセットアップ手順（systemd サービス定義例 など）があれば教えてください。必要に応じて追記します。