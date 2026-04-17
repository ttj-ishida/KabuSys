# KabuSys

日本株向け自動売買システムのコアライブラリ群（限定的に抽出された実装）。  
このリポジトリはトレード実行・監視・ポートフォリオ構築・リサーチ・簡易AI連携などのモジュールを含みます。

主な設計方針（抜粋）
- DuckDB / SQLite をデータ層に利用（prices, raw_financials, monitoring logs 等）
- KABUSYS_ENV による実行モード切替（development / paper_trading / live）
- Paper Trading ではブローカーをモックし DB を完全分離
- 監視 (Monitoring) は実行環境に関係なく本番監視 DB を使用
- 外部 API（LINE, OpenAI, kabuステーション 等）は抽象化／再試行・フォールバックを実装

---

## 機能一覧（抜粋）

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象化（実口座 / モック切替）
  - 注文管理（OrderManager）、再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）・OrderRepository（SQLite）

- Monitoring
  - System / Trade / Risk 各モニタ（SystemMonitor / TradeMonitor / RiskMonitor）
  - 監視 DB 層（MonitoringDB）と初期化ユーティリティ
  - Kill Switch（条件達成で ExecutionEngine を停止させるフラグ）
  - アラート送信（LINE push via AlertManager）
  - Streamlit ベースのダッシュボード（streamlit_dashboard.py）
  - 監視のポーリングランナー（run_monitoring.py）

- Portfolio（ポートフォリオ構築）
  - 候補選定、重み付け（等分配・スコア加重）
  - セクター制限、レジーム乗数の適用
  - 株数計算（リスクベース／等分配等）、単元丸め・aggregate cap 調整

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（OpenAI 経由）
  - ニュース NLP による銘柄別センチメントスコア取得（news_nlp.score_news）
  - マクロニュース＋ETF MA を使った市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しはリトライ、結果検証、部分書込などを実装

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

前提
- Python 3.10+ を想定（typing の表記等）
- OS により psutil の一部機能は権限を要する場合あり

手順（ローカル実行向け）
1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt があればそちらを使用）
   - 例（主要依存のみ）:
     pip install duckdb==0.8.* psutil requests openai streamlit
   - 実環境ではバージョンを固定した requirements.txt を用意してください。
4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効）。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PAPER_FILL_MODE（instant | partial | never | reject、デフォルト: instant）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
   - 設定漏れがあると Settings クラスで ValueError が発生します。

データディレクトリ
- デフォルトで DB 等は `data/` 配下に作成される想定です。必要に応じて手動で作成してください。

注意
- run_monitoring は常に production（settings.sqlite_path）を使って監視ログを記録します（KABUSYS_ENV に依らず）。
- run_execution は paper_trading の場合に paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）を使います。

---

## 使い方（代表例）

プロジェクトルートから `src` を PYTHONPATH に含めるか、パッケージとしてインストールして実行してください。

基本例（PYTHONPATH を使う）
- 監視ループ起動（デフォルト Poll=60s）
  - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
  - ストップはプロジェクトルートの `data/stop_requested.flag` を作成することで検知して終了します。

- ExecutionEngine 起動
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
  - paper_trading の場合は data/paper_trading.db に記録され、本番 DB と分離されます。
  - 実行中に `data/stop_requested.flag` を作成すると安全に停止します。

- Paper Trading 検証レポート
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション `--db PATH` で SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- Streamlit ダッシュボード（監視 DB を read-only で開く）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 起動時に DB が存在しないとエラー表示されます（MonitoringEngine を起動してください）。

- AI スコア/レジーム関係（Python から利用）
  - 例（簡易）:
    from pathlib import Path
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,10), api_key="sk-...")

  - regime_detector.score_regime も同様に duckdb 接続と API key を渡して実行できます。

運用上のファイル（監視・制御）
- data/execution.pid — ExecutionEngine の PID を記録（存在チェックでプロセス存否を判定）
- data/stop_requested.flag — run_*.py が監視している停止フラグ（作成で停止）
- data/kill.flag — KillSwitch が必要時に作成する停止理由（Execution 停止要求）

---

## Settings（主要な環境変数とデフォルト）

（Settings クラスに基づく抜粋）
- KABUSYS_ENV: development | paper_trading | live  (default: development)
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL (default: INFO)
- JQUANTS_REFRESH_TOKEN: 必須
- KABU_API_PASSWORD: 必須
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知で必要
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: "1" で起動時に kill.flag をクリア
- PAPER_FILL_MODE: instant | partial | never | reject (default: instant)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視しきい値（数値）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

サブパッケージ
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, broker_api.py, ...  
  - 注文ライフサイクル、ブローカー抽象化、再同期機能

- monitoring/
  - monitoring_db.py — SQLite ベースの監視ログ層
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — LINE 通知
  - kill_switch.py — フラグ作成ロジック
  - streamlit_dashboard.py — ダッシュボード

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算、aggregate cap
  - risk_adjustment.py — セクターキャップ、レジーム乗数

- research/
  - factor_research.py — モメンタム / ボラ / バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計

- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI）
  - regime_detector.py — マクロ + ETF MA によるレジーム判定

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート出力ツール

- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

- data/（実行時に使用）
  - monitoring.db（デフォルト SQLITE_PATH）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB）
  - execution.pid, kill.flag, stop_requested.flag など制御ファイル

---

## 運用時の注意点 / ヒント

- 監視と実行は別プロセスで動かす想定です。監視プロセスは実行プロセスの PID ファイルを参照して生存チェックを行います。
- Paper Trading は本番 DB と分離されます。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI 周りは API キーとコストに注意。news_nlp は記事ごとにまとめてバッチ送信します（デフォルト _BATCH_SIZE=20）。
- psutil による優先度設定は権限に依存します。権限不足でも安全にスキップする実装です。
- データ鮮度チェックは DuckDB の prices_daily を参照します。データがないとデータ鮮度異常となります。

---

この README はコードベースの主要点を抜粋したものです。実際の運用・拡張時は各モジュールの docstring / ソースコメントを参照してください。必要であれば環境変数の .env.example を作成するテンプレートや requirements.txt の草案作成も支援します。