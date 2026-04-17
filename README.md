# KabuSys

KabuSys は日本株向けの自動売買／研究／監視を目的とした軽量なPythonモジュール群です。  
この README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語で説明します。

注意: リポジトリ実体は src/kabusys 以下にあり、環境変数は .env/.env.local や OS 環境変数から読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

プロジェクト概要
- 日本株自動売買の ExecutionEngine、モニタリング（稼働率・注文監視・リスク検知）、研究（ファクター計算・特徴量解析）、AI（ニュースセンチメント／レジーム判定）などのコンポーネントを含むモジュール群。
- DuckDB を使った時系列データ解析、SQLite を使った監視ログ/トレードログ永続化、OpenAI API を利用したテキスト解析を想定。
- 設定は環境変数経由（Settings クラス）で統一的に管理。

主な機能一覧
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（BrokerClientFactory）により実口座 / Paper Trading を切り替え可能
  - Reconciler による再起動時の自動リコンシリエーション（注文・ポジション差分の突合）
  - OrderManager / OrderRepository による注文状態管理
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス状態、データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とリスクイベント記録
  - KillSwitch / AlertManager: 条件に応じた停止フラグ作成および LINE プッシュ通知
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Research / Portfolio
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）評価、統計要約
  - 銘柄選定・重み算出、ポジションサイズ決定、セクター制約・レジーム乗数
- AI
  - news_nlp: raw_news を集約して OpenAI（gpt-4o-mini 等）で銘柄別センチメントを算出し ai_scores に保存
  - regime_detector: ETF (1321) の MA とマクロニュースの LLM センチメントを合成して市場レジーム判定
- ユーティリティ
  - 環境変数/ .env 自動読み込み（config.py）
  - プロセス優先度 / CPU affinity 設定（utils.process_priority）
  - Monitoring 用の SQLite 初期化 / 永続化層（monitoring_db）

セットアップ手順（ローカル開発向け）
1. 前提
   - Python 3.10+ を推奨
   - システムに必要なライブラリ（duckdb, psutil, requests, openai, streamlit 等）が必要

2. 仮想環境の作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを使用してください）

4. 環境変数の設定
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 主な環境変数（代表例）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
     - KABUSYS_ENV — 起動環境（development | paper_trading | live、デフォルト: development）
     - LOG_LEVEL — ログレベル（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH など（デフォルトは data/ 以下）
     - PAPER_FILL_MODE — paper_trading 時の約定モード（instant|partial|never|reject、デフォルト: instant）
   - .env/.env.local は自動読み込みされる（OS 環境変数を優先）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. データディレクトリ作成
   - mkdir -p data

使い方（実行例）
- 監視ループを起動（SystemMonitor 単体のポーリング）
  - python -m kabusys.run_monitoring
  - 振る舞い:
    - プロセス優先度を "high" に設定し、SQLite（settings.sqlite_path）および DuckDB に接続して SystemMonitor をポーリング
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60秒）
    - 停止はプロジェクトルート/data/stop_requested.flag が作成されると検知して終了

- ExecutionEngine を起動（実際の発注エンジン）
  - python -m kabusys.run_execution
  - 振る舞い:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 SQLite（data/paper_trading.db）を利用し、本番 DB と分離
    - 起動時に stop_requested.flag の存在を確認し、存在する場合は起動を行わない
    - エンジンの PID を data/execution.pid に書き出す（設定で変更可）
    - 停止は stop_requested.flag を作成するか、Execution 側が KillSwitch により kill.flag を検出して停止

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB ファイル指定:
    - --db PATH を使うか、PAPER_TRADING_SQLITE_PATH 環境変数を設定

- Streamlit ダッシュボード（監視ダッシュボード）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視ダッシュボードを表示し、ポートフォリオ集計、ポジション、ログなどを確認できます（読み取り専用で接続）。

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）が必要
  - news_nlp.score_news(conn, target_date, api_key=None) — ai_scores に書き込み
  - regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書き込み

停止／制御の仕組み（フラグ）
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring.py と run_execution.py が定期的に存在確認して、存在するとループを抜ける・エンジンを停止します（運用時の安全シャットダウン用途）。
- kill.flag（Settings.kill_flag_path / data/kill.flag デフォルト）
  - KillSwitch が書き込むフラグ。ExecutionEngine 側で検出して安全に停止させる目的。KillSwitch はドローダウン等の重大なリスク検知時に作成される。
- PID ファイル（data/execution.pid）
  - ExecutionEngine の PID を書き込み。SystemMonitor はこの PID ファイルからプロセス生存を確認し、stale PID を検出した場合は削除してリスクログに記録します。

データベース / マイグレーション
- monitoring_db.init_monitoring_db(conn) により監視用 SQLite のテーブル（system_status, trade_logs, positions, risk_logs, dashboard）を冪等に作成／マイグレーションします（必要に応じて列追加を行う実装あり）。
- DuckDB は時系列価格・生データの解析用に使用（デフォルト: data/kabusys.duckdb）。

設定・重要な環境変数まとめ（代表）
- JQUANTS_REFRESH_TOKEN (必須)：J-Quants API 用
- KABU_API_PASSWORD (必須)：kabu API 用
- OPENAI_API_KEY：OpenAI API（AI 機能で必須）
- KABUSYS_ENV：development | paper_trading | live（デフォルト development）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
- PAPER_FILL_MODE（paper_trading 約定モード: instant|partial|never|reject）

ディレクトリ構成（src/kabusys 以下の主要ファイル/ディレクトリ）
- __init__.py — パッケージ定義（__version__ など）
- config.py — 環境変数 / Settings 管理、.env 自動読み込み
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
- ai/
  - news_nlp.py — ニュースセンチメント取得 / ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント合成）
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 / MonitoringDB クラス
  - system_monitor.py — CPU/メモリ/ディスク / データ鮮度 / プロセス検査
  - trade_monitor.py — 滞留注文・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の管理
  - alert_manager.py — LINE 通知
  - monitoring_engine.py — 複数モニタを束ねるエンジン（テスト用 run_once / 本番用 run）
  - streamlit_dashboard.py — Streamlit 監視ダッシュボード
- execution/
  - reconciler.py — 起動時リコンシリエーション
  - order_manager.py — 注文発行 / 状態遷移管理
  - order_repository.py 等（OrderRecord, OrderRepository などは存在）
  - broker_factory / broker_api — ブローカー抽象化
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出、最大投資額スケーリング等
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 計算（DuckDB 経由）
  - feature_exploration.py — 将来リターン、IC、統計サマリなど
- utils/
  - process_priority.py — プロセス優先度・CPU affinity 設定
- data/（運用時に作成するディレクトリ）
  - monitoring.db（SQLite, default）
  - paper_trading.db（Paper Trading 用 SQLite）
  - kabusys.duckdb（DuckDB）
  - execution.pid / stop_requested.flag / kill.flag などのフラグ・PID ファイル

運用上の注意
- Paper Trading と本番 DB は分離されています（KABUSYS_ENV=paper_trading の場合 paper_sqlite_path を使用）。
- AI 系機能は OpenAI API キーを必要とし、ネットワーク/API の失敗に対してはリトライやフェイルセーフ動作が組み込まれていますが、運用時はレート制限やコストに注意してください。
- Production ではログレベル、MONITOR_POLL_INTERVAL、リスク閾値などを適切に設定してください。
- .env ファイルをリポジトリに含めない（機密情報の管理に注意）。

貢献 / 開発
- 新しい機能追加や修正はモジュール単位でテストを追加してください（本リポジトリには pytest 等の設定は含まれていませんが、関数設計は純粋関数化・依存注入を意識してあります）。
- .env.example を用意して、必須環境変数をドキュメント化すると運用が容易になります。

---

以上が本リポジトリの概要と基本的な使用方法です。必要であれば各モジュール（ExecutionEngine の詳細な起動オプション、Broker の実装切替方法、DuckDB のスキーマ仕様など）に関する追加のドキュメントを作成します。どの部分をより詳しく説明すればよいか教えてください。