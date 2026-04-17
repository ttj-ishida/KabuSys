KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株を対象とした自動売買システム（KabuSys）のコア部分をまとめたものです。
本 README はコードベース（src/kabusys 以下）をもとに、プロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

注意: この README は実装されたモジュール群の説明です。実行前に環境変数や依存ライブラリを正しく設定してください。

プロジェクト概要
---------------
KabuSys は下記の主要コンポーネントで構成される自動売買プラットフォームです。

- Execution: ブローカーとやり取りして注文を送信・管理するエンジン（ExecutionEngine, OrderManager, Reconciler 等）。
- Monitoring: システム稼働状況・注文状態・リスク（ドローダウンやポジション上限）を監視し、アラート発行や停止フラグ管理を行う（SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager 等）。
- Research / Data: DuckDB を用いたファクター計算・研究ユーティリティ（ファクター計算・将来リターン・IC 計算など）。
- Portfolio: 銘柄選定、重み算出、ポジションサイズ決定、セクター制限など、ポートフォリオ構築ロジック。
- AI: OpenAI（gpt-4o-mini）を用いたニュースセンチメントスコアリングと市場レジーム判定（news_nlp, regime_detector）。
- Tools: 検証レポート生成や Streamlit ベースの監視ダッシュボード。

主な特徴
--------
- 実運用・Paper Trading を環境で明確に分離（paper_trading 用の DB を使用）。
- DuckDB（履歴・時系列データ）と SQLite（監視ログ・オーダーログ）を組み合わせた設計。
- OpenAI を用いたニュース NLP とレジーム判定（API キー必須、失敗時のフェイルセーフあり）。
- 監視ループは flag ファイルで外部停止指示を受け付け（stop_requested.flag / kill.flag）。
- Streamlit による監視ダッシュボードや検証レポート生成スクリプト付き。
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil）。

セットアップ手順（開発向け）
-------------------------
1. Python 環境（推奨: 3.9+）を用意し、仮想環境を作成します。
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 必要パッケージをインストールします（リポジトリに requirements.txt が無い場合は主要依存を手動でインストール）。
   - pip install duckdb psutil openai requests streamlit

   追加で必要なパッケージがあれば適宜インストールしてください。

3. プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env ファイルを置いて環境変数を設定できます。
   - 自動で .env → .env.local を読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（代表）
---------------------
（Settings クラスにより参照されるキーの一部）

- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE アラート用（任意）
- KABUSYS_ENV: 実行モード（development, paper_trading, live）デフォルト: development
  - paper_trading の場合、発注は MockBrokerClient を使用し data/paper_trading.db に記録
- PAPER_FILL_MODE: paper_trading の fill 挙動（instant|partial|never|reject、デフォルト: instant）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル位置（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1" でクリア）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）

使い方
------

基本的な起動例
- 監視ループ（SystemMonitor のポーリング）を起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - run_monitoring は常に本番用 sqlite_path を使用して monitoring テーブルを記録します（KABUSYS_ENV に依らず）

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使いデータは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ保存され、本番 DB と分離されます
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に同フラグが作成されると安全にエンジン停止を要求します

停止とフラグ
- 外部から即時停止を伝えたい場合はプロジェクトルートの data/stop_requested.flag を作成してください。run_monitoring/run_execution はこのファイルを監視し停止します。
- 実行エンジンを安全に停止するための「Kill Switch」は data/kill.flag を書き込みます。KillSwitch は RiskMonitor の判定などにより kill.flag を生成します。
- ExecutionEngine の PID は data/execution.pid に書かれます。SystemMonitor はこの PID ファイルの有無・生存を監視します。

監視・ダッシュボード・レポート
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite DB を読み取り専用で開き、ポジション・注文履歴・最新システム状況・リスクログを表示します。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）等の概要と PASS/FAIL 判定

主要コンポーネントの説明（抜粋）
--------------------------------
- Settings (kabusys.config)
  - 環境変数の読み込み・検証を行う。自動で .env/.env.local をプロジェクトルートから読み込み（必要な場合は無効化可）。

- Monitoring
  - monitoring_db: monitoring 用の SQLite スキーマ初期化と永続化 API（system_status, trade_logs, positions, risk_logs, dashboard）。
  - SystemMonitor: CPU/メモリ/ディスク、PID 生存確認、データ鮮度（DuckDB 内の最終価格日）をチェックしログを残す。
  - TradeMonitor: 滞留注文・約定異常価格の検出を実装。
  - RiskMonitor: ダローダウンやポジション上限の判定、ダッシュボード更新、必要に応じて risk_logs にログ。
  - KillSwitch: リスクトリガーに応じて kill.flag を作成し、ExecutionEngine 側へ停止シグナルを送る。
  - AlertManager: LINE Messaging API を用いた通知（チャンネル設定がある場合のみ送信）。同一レベル／カテゴリのクールダウン管理あり。
  - MonitoringEngine: 上記各 Monitor を束ね、ポーリング実行（run/run_once）。

- Execution
  - OrderManager: 注文の作成・状態管理・重複検知などの外向け API。
  - Reconciler: 起動時にブローカーと注文／ポジションの突合を行い自動復旧。
  - ExecutionEngine（実装ファイルはここに含まれていない箇所もあるが run_execution から起動される）: ブローカーとのセッション実行ロジックを管理。
  - BrokerClientFactory: 環境に応じて本番 or Mock ブローカークライアントを生成。

- Research / Portfolio
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算。DuckDB の prices_daily / raw_financials を参照。
  - research.feature_exploration: 将来リターン計算、IC（Information Coefficient）や統計サマリー。
  - portfolio: 銘柄選定（select_candidates）、重み計算（equal/score）、ポジションサイズ計算（risk_based / equal / score）、セクター制限、レジーム乗数など。

- AI
  - ai.news_nlp: raw_news を OpenAI に投げて銘柄別センチメントを計算し ai_scores に書き込む。リトライ・バッチ送信・レスポンス検証を実装。
  - ai.regime_detector: ETF（1321）とマクロニュースを組み合わせて市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む。
  - OpenAI を利用する部分は API の失敗時に安全にフォールバックするよう設計されています（例: macro_sentiment=0.0）。

運用上の注意
-------------
- paper_trading を利用する場合、必ず PAPER_TRADING_SQLITE_PATH を設定して本番 DB と分離してください。
- OpenAI を使う機能を有効にする場合は OPENAI_API_KEY を必ず設定してください。API 呼び出しには課金が発生します。
- psutil を使ったプロセス優先度・CPU affinity 設定はプラットフォーム依存で、権限不足により失敗することがあります（ログに警告が出ます）。
- monitoring_db.init_monitoring_db はマイグレーションを含み冪等に実行可能です。既存テーブルにカラムがない場合は追加する処理があります。
- streamlit ダッシュボードは DB を読み取り専用で開くことを推奨します（URI に ?mode=ro を付けて起動スクリプト内で利用しています）。

ディレクトリ構成（概要）
----------------------
以下は主要ファイルとモジュールの抜粋です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - run_monitoring.py            — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py           — monitoring DB schema と MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (一部)
    - ...                       — ブローカー API/クライアント等（省略部分あり）
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - data/                        — 実行時に使用する DB / flag / pid 等（例: monitoring.db, paper_trading.db, kabusys.duckdb, stop_requested.flag, kill.flag, execution.pid）

（実際のリポジトリではさらに細かなモジュールと実装ファイルが存在します。上記は主要なファイルの一覧です。）

補足（よくある操作）
-------------------
- 監視ループのポーリング間隔変更:
  - MONITOR_POLL_INTERVAL 環境変数（秒）で指定。無効値や 0 以下は 60 秒にフォールバックします。

- kill.flag / stop_requested.flag のクリア:
  - KillSwitch.clear() やファイル削除で手動クリアできます。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアする挙動があります（Settings.kill_flag_clear_on_start を参照）。

- Paper トレード検証:
  - paper_verification_report により paper_trading DB の各種指標（稼働率・注文成功率・P95 レイテンシ等）を集計して PASS/FAIL 判定が可能です。

最後に
------
この README はコード内のドキュメント文字列と設定クラスをもとに作成しています。実際に運用する際は .env.example（存在する場合）を参考に環境変数を適切に設定し、必須の API キーやパスワードの管理に注意してください。必要に応じてテスト環境（paper_trading）で十分に検証してから live 環境へ切り替えてください。