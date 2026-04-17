# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はリポジトリ内の主要モジュールを基に作成した概要、機能、セットアップと実行方法、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムで、以下の主要機能を含みます：

- 注文生成・発注・状態管理（ExecutionEngine / OrderManager）
- 監視（System / Trade / Risk）および監視ログの永続化（SQLite）
- Paper Trading と本番（live）の分離（専用 DB / モックブローカー）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング）
- リサーチ（ファクター計算、特徴量探索）
- AI を使ったニュースセンチメント（OpenAI 経由）と市場レジーム判定
- Streamlit ベースの監視ダッシュボード
- ユーティリティ（プロセス優先度設定、レポート生成など）

設計上のポイント：
- 設定は環境変数または .env / .env.local で読み込み（自動ロードはプロジェクトルートを探索）
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- 重要処理は冪等に設計（DB 初期化・Upsert 等）
- 外部 API 呼び出し（OpenAI 等）はフェイルセーフ化（失敗時はフォールバック）

---

## 機能一覧（主要モジュール）

- src/kabusys/run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時に MockBroker を使用。
  - 停止は data/stop_requested.flag または監視側の kill.flag により制御。

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（デフォルト 60 秒）で上書き可能。

- src/kabusys/config.py
  - 環境変数 / .env 読み込み、Settings クラスによりアプリ設定を提供。
  - 主な設定例: KABUSYS_ENV, OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, PAPER_FILL_MODE, SQLITE_PATH, DUCKDB_PATH など。

- src/kabusys/monitoring/
  - system_monitor, trade_monitor, risk_monitor, monitoring_db, alert_manager, kill_switch, monitoring_engine
  - SQLite に監視ログを保存（init_monitoring_db でテーブル作成）。LINE 通知対応。

- src/kabusys/portfolio/
  - portfolio_builder, position_sizing, risk_adjustment — 候補選定、重み、株数計算、セクター制限など。

- src/kabusys/research/
  - factor_research, feature_exploration — DuckDB を用いたファクター計算、将来リターン、IC 等。

- src/kabusys/ai/
  - news_nlp.py: raw_news を OpenAI に投げて銘柄単位のセンチメントを ai_scores テーブルへ記録
  - regime_detector.py: MA200 とマクロニュースの LLM センチメントを合成して market_regime を決定

- src/kabusys/tools/paper_verification_report.py
  - Paper Trading のログを解析して検証レポートを標準出力に出力

- src/kabusys/monitoring/streamlit_dashboard.py
  - Streamlit による監視ダッシュボード（read-only 接続で監視 DB を表示）

---

## 必要な依存パッケージ（代表）

下記はコード内で使用されている主要ライブラリです。プロジェクトに requirements.txt が無ければ手動でインストールしてください。

- Python 標準ライブラリ: sqlite3, logging, argparse, threading, datetime, pathlib, os, time, math, json など
- 外部ライブラリ:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード)
  - openai (OpenAI API クライアント)
  - （必要に応じて）その他

例:
```sh
pip install duckdb psutil requests streamlit openai
```

---

## セットアップ手順

1. リポジトリをクローン / 配置
   - プロジェクトルートが `.git` または `pyproject.toml` のいずれかで検出されると .env 自動読み込みが有効になります。

2. 環境変数の準備
   - .env（または .env.local）をプロジェクトルートに作成。主なキー例:

     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=<...>
     - KABU_API_PASSWORD=<...>
     - OPENAI_API_KEY=<...>         # AI 機能を使う場合
     - LINE_CHANNEL_ACCESS_TOKEN=   # AlertManager を使う場合
     - LINE_USER_ID=
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant     # instant | partial | never | reject
     - MONITOR_POLL_INTERVAL=60    # run_monitoring 用（秒）
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag

   - 自動読み込みを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. データディレクトリの作成（必要に応じて）
   - data/ ディレクトリを作成しておくと便利（DB ファイル、PID/flagファイル等）。

4. DB 初期化
   - 監視用 SQLite は自動的にテーブル作成（init_monitoring_db）。
   - DuckDB は prices / raw_financials 等のテーブルを用意する必要がある（データ投入は別途実施）。

---

## 使い方（よく使うコマンド）

- 監視ループ起動（SystemMonitor 単体）
  - デフォルトで監視は本番の sqlite_path を使用（KABUSYS_ENV に依らない）。
  - 環境変数でポーリング間隔を変更可能（MONITOR_POLL_INTERVAL）。
  - 実行例:
    ```sh
    # 環境変数を指定して実行（例: 30秒間隔）
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
    ```
  - 停止:
    - data/stop_requested.flag を作成するとループを終了します（または Ctrl+C）。

- ExecutionEngine 起動（発注エンジン）
  - Paper Trading モード:
    - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、データは PAPER_TRADING_SQLITE_PATH に保存されます（本番 DB と完全分離）。
  - 実行例:
    ```sh
    # 本番モード（例）
    export KABUSYS_ENV=live
    python -m kabusys.run_execution

    # Paper Trading
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 停止:
    - data/stop_requested.flag を作成すると ExecutionEngine は検出して停止します。
    - 監視側の KillSwitch がトリガーすると data/kill.flag が作成され、外部から停止させる仕組みがあります。

- Paper Trading 検証レポート
  - スクリプトで Paper Trading の SQLite を解析してレポートを出力します。
  - 実行例:
    ```sh
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    # または DB 指定
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- Streamlit 監視ダッシュボード
  - 実行例:
    ```sh
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - dashboad は監視 DB に read-only で接続します（存在しない場合は起動失敗メッセージを表示）。

- AI（ニューススコアリング / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要です。
  - ライブラリ関数として使用可能:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 例（Python REPL 内）:
    ```python
    import duckdb
    from datetime import date
    from kabusys.ai import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="YOUR_KEY")
    ```

---

## 設定の詳細（主な環境変数）

- KABUSYS_ENV: development | paper_trading | live（Settings.env）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: paper_trading の約定挙動（instant, partial, never, reject）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB のパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行時の PID / kill flag のパス

注意: config.py はプロジェクトルートで `.env` / `.env.local` の自動読み込みを行います（OS 環境変数が優先）。自動読み込み無効化は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## 停止・制御ファイル

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py が存在を検知して安全に停止します（外部からの即時停止用）。

- data/kill.flag
  - KillSwitch（監視側）が条件に合致した際に作成。ExecutionEngine の停止シグナル用途に想定。

- data/execution.pid
  - ExecutionEngine が PID を書き込む想定のファイル（SystemMonitor が存在チェックを行う）。

---

## ディレクトリ構成（抜粋）

リポジトリの主要なファイル・モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - __init__.py
    - process_priority.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - execution_engine.py
    - reconciler.py
    - broker_factory.py
    - (その他 execution 関連モジュール)
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
  - data/ (実行時に作成・使用するディレクトリ、ソースには含まれない可能性あり)
  - tools/
    - __init__.py
    - paper_verification_report.py

（注）実プロジェクトではさらに data、strategy、execution の詳細実装、tests、ドキュメント等が含まれる想定です。

---

## 運用上の注意・補足

- Paper Trading と本番 DB は明確に分離してください（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しや外部 API の失敗は多くの箇所でフェイルセーフ化されていますが、API キーやレート制限には注意してください。
- process priority の設定には psutil が使用されます。権限不足や未対応 OS の場合は警告が出ますがプロセスは継続します。
- DuckDB / SQLite のスキーマは init_monitoring_db によって必要テーブルを作成します（マイグレーションロジックあり）。
- ログレベルは環境変数 LOG_LEVEL で制御できます（Settings.log_level）。

---

この README はコードベースの説明と実行のための最小事項をまとめたものです。追加で API 詳細、設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）や運用手順を整備すると運用・開発がより安全になります。必要であれば README に載せる具体的な .env.example や運用フロー、起動システムd / supervisor のサンプルユニットも作成できます。希望があれば教えてください。