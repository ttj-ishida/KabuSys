# KabuSys (README)

このリポジトリは「KabuSys」— 日本株向けの自動売買／研究／監視システムのコア実装です。  
以下はコードベースの概要、機能、セットアップ方法、実行方法、ディレクトリ構成の説明です。

注意: 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。実運用前に各設定値や API キー、DB のバックアップなどを必ず確認してください。

---

## プロジェクト概要

KabuSys は、自動売買の Execution エンジン、システム監視モジュール、ポートフォリオ構築ロジック、リサーチ（ファクター計算／特徴量解析）、AI を使ったニュースのセンチメント評価などを含む統合システムです。主な設計方針は以下の通りです。

- 実行・監視・リサーチをモジュール化して分離（SQLite / DuckDB を利用）
- Paper Trading（テスト用）を本番データベースと完全分離
- LLM（OpenAI）をニュース分析やレジーム検出に利用（失敗時はフェイルセーフ）
- ログ・監視用の DB を用意し、Streamlit ダッシュボードで可視化可能

---

## 主な機能一覧

- Execution（発注）関連
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - ブローカー抽象化および Mock ブローカー（paper_trading）対応
  - OrderManager, Reconciler：注文の同期・再整合処理
  - リスク管理（RiskManager）やオーダーリポジトリ

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor によるポーリング監視
  - MonitoringDB（SQLite）による監視ログ永続化
  - KillSwitch / AlertManager（LINE プッシュ通知）連携
  - MonitoringEngine（ポーリングループ）
  - Streamlit ベースの監視ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
  - run_monitoring.py：監視プロセス起動スクリプト（MONITOR_POLL_INTERVAL でポーリング間隔を調整可能）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等重/スコア加重、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（lot 単位、コストバッファ、aggregate cap 対応）

- Research（リサーチ）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - DuckDB を用いた高速集計

- AI（LLM 連携）
  - news_nlp.score_news: ニュースを集約して OpenAI（gpt-4o-mini 等）でセンチメントを算出し ai_scores に格納
  - regime_detector.score_regime: ETF（1321）の MA200 とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定・格納
  - API 呼び出しはリトライ／クリップ／バリデーションなどフェイルセーフ実装

- ツール
  - paper_verification_report: Paper Trading DB（data/paper_trading.db 等）から検証レポートを生成

---

## 必要要件（主な依存ライブラリ）

ソース内で使用されている主要ライブラリ（バージョンは開発環境に合わせて調整してください）:

- Python 3.10+（typing に | が使われているため）
- duckdb
- psutil
- requests
- openai
- streamlit
- sqlite3（標準ライブラリ）

インストール例:
- requirements.txt がある場合:
  - pip install -r requirements.txt
- 個別インストール例:
  - pip install duckdb psutil requests openai streamlit

---

## 環境変数と設定

Settings クラス（src/kabusys/config.py）が環境変数を読み込みます。自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（CWD に依存しない検出）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（機能を使う際に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API（必要な機能時）
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — AI 機能を利用する場合

主要なオプション:
- KABUSYS_ENV — 利用モード: "development"（デフォルト）, "paper_trading", "live"
  - paper_trading モードでは MockBroker を使い、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録される
- LOG_LEVEL — ログレベル（"DEBUG"/"INFO"/...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading 時の約定シミュレーション（"instant"|"partial"|"never"|"reject"）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等監視関連設定
- MONITOR_POLL_INTERVAL — 監視スクリプトでポーリング間隔を上書き可能（秒、run_monitoring 起動時に参照）

.env の書式は shell 形式に準拠しており、.env.local は .env を上書きします（ただし OS 環境変数は保護されます）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - または: pip install duckdb psutil requests openai streamlit

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに .env を作成するか環境変数をエクスポート
   - 例（.env）:
     - KABUSYS_ENV=development
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

6. DB 初期化
   - run_monitoring.run_monitoring / run_execution が起動時に init_monitoring_db を呼びます。手動で初期化したい場合は Python REPL 等で init_monitoring_db を呼んでください。

---

## 使い方（主要な起動コマンド）

- 監視プロセス（Monitoring）
  - デフォルトポーリング 60秒（MONITOR_POLL_INTERVAL で上書き可能）
  - 実行:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - または: python src/kabusys/run_monitoring.py
  - 特徴:
    - プロセス優先度を高く設定（set_process_priority("high")）
    - 監視 DB は環境に関わらず本番 sqlite_path を使用（monitoring は本番 DB を参照）
    - 停止: プロジェクトルート/data/stop_requested.flag が存在するとループを抜けます

- Execution エンジン
  - 実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - または: python src/kabusys/run_execution.py
  - 特徴:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用し paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）を使用して完全分離
    - 起動時に data/execution.pid を使用して PID 管理
    - 停止: data/stop_requested.flag がある場合は起動しない／実行中に検知するとエンジンを停止
    - settings.kill_flag_path（デフォルト data/kill.flag）に KillSwitch が書き込まれると停止シグナルになる

- Streamlit ダッシュボード
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - MonitoringDB を読み取り専用で開き、Overview / Positions / Orders / System のタブを表示します

- Paper Trading 検証レポート
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間を指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）
  - 出力: 稼働率・注文成功率・送信率・レイテンシ等のレポートと PASS/FAIL 判定

- AI 機能（ニュース／レジーム）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡して ai_scores を書き込む。api_key 指定なしなら OPENAI_API_KEY を参照。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡して market_regime テーブルへ書き込む。

---

## 停止 / キル（オペレーション）

- stop_requested.flag
  - run_monitoring.py / run_execution.py はプロジェクト data 配下の stop_requested.flag（run_monitoring.py では上位 parents[2]/data/stop_requested.flag を参照）を監視し、存在すれば終了します。
- kill.flag
  - KillSwitch（監視ロジック）が条件を満たすと Settings.kill_flag_path（デフォルト: data/kill.flag）に理由を追記して、ExecutionEngine の停止トリガーとします。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag をクリアするオプションがあります。

---

## ディレクトリ構成（要約）

以下は src/kabusys 以下の主要ファイル／モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - run_monitoring.py — 監視ループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - monitoring_engine.py — 複数監視を束ねるエンジン
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE による通知
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (存在が示唆されるが省略)
    - broker_factory.py / broker_api.py（ブローカー関連）
    - order_record.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・リスク制限
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/  （アプリ実行時に作成）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - kabusys.duckdb（デフォルト）
    - execution.pid / stop_requested.flag / kill.flag

---

## 運用上の注意と設計上のポイント

- Paper Trading は本番 DB と完全分離する設計（PAPER_TRADING_SQLITE_PATH を使用）。実運用での誤混入に注意してください。
- AI（OpenAI）呼び出しは外部依存のため、API レート制限やネットワークエラーに備えてリトライ／フォールバックを実装していますが、API キーの管理、コスト管理を行ってください。
- run_monitoring / run_execution はプロセス優先度を上げようとします（psutil 利用）。権限不足で失敗することがあるためログに注意してください。
- monitoring_db のスキーマは init_monitoring_db で冪等に作成・マイグレーションされます。手動でスキーマ変更する場合は互換性に注意してください。
- Streamlit ダッシュボードは monitoring.db を読み取り専用で開くことを推奨します（起動時の表示メッセージ参照）。

---

## よく使うコマンドまとめ

- 監視起動（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- Execution 起動（Paper Trading モード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば、README にサンプルの .env.example、requirements.txt、運用手順（systemd ユニット例など）や DB スキーマドキュメントを追加できます。どの情報を追加したいか教えてください。