README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を目的とした Python パッケージです。本コードベースはトレード実行のための ExecutionEngine、実行状況の監視コンポーネント群、ポートフォリオ構築・リスク制御ロジック、研究用ファクター計算、ニュースを用いた AI スコアリングなどを含みます。設計方針として「本番環境と検証（paper trading）を明確に分離」「DB はローカルファイル（SQLite / DuckDB）」、「外部 API 呼び出しはオプション（OpenAIなど）」となっています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 実際のブローカー／MockBroker を使った発注フローを実行
  - リコンシリエーション（起動時の注文・ポジション整合）
  - RiskManager / OrderManager / Reconciler 等の統合
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に書き込む（本番 DB から完全分離）

- Monitoring（run_monitoring.py, MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク・プロセス生存）を定期ロギング
  - 注文滞留 / 約定価格異常の検知（TradeMonitor）
  - ドローダウン・ポジション上限監視（RiskMonitor）と Kill Switch（kill.flag）
  - LINE でのアラート通知（AlertManager）
  - Streamlit ダッシュボード（監視データ可視化）

- ポートフォリオ構築モジュール（portfolio）
  - 候補選定、重み計算（等分配 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（lot 丸め、集約上限スケールダウン）

- リサーチ / ファクター計算（research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ

- AI（ai）
  - news_nlp: OpenAI を使ったニュースの銘柄別センチメントスコア化 ai_scores への書き込み
  - regime_detector: ETF の MA200 とマクロニュースを組合せた日次レジーム判定

- ユーティリティ
  - process_priority: プロセス優先度 & CPU affinity 設定ユーティリティ
  - 環境変数管理（.env の自動読み込みロジック）

セットアップ
----------
前提
- Python 3.10 以上を推奨（typing の一部機能を利用）
- DuckDB, psutil, requests, openai, streamlit 等の外部パッケージ

推奨手順（例）
1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （実運用では requirements.txt を用意して pip install -r requirements.txt を推奨）

環境変数 (.env)
- プロジェクトルートに .env（または .env.local）を置くことで自動的に読み込まれます（既存 OS 環境変数は上書きされません）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主要な環境変数（例）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な箇所で使用）
  - KABU_API_PASSWORD: kabuステーション API パスワード（Execution 時必須）
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）を使う場合に必要
  - PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
  - PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite パス（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - LOG_LEVEL, PID_FILE_PATH, KILL_FLAG_PATH なども設定可能

使い方（主要なコマンド）
---------------------
- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 監視は常に settings.sqlite_path（monitoring DB）を使用します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し paper_trading 用 DB に記録します:
    - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行中は data/execution.pid が作成され、停止シグナルは data/stop_requested.flag で行えます。

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは実行時に別 DB パスを指定可能（--db オプション）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプション または 環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラム内呼び出し）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # conn は DuckDB 接続
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

注意点 / 運用上のポイント
------------------------
- Paper Trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading の場合、paper_sqlite_path が使われます。
- .env の読み込み優先度: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを止められます。
- 実行スクリプトは起動直後にプロセス優先度を "high" に設定しようとします（psutil を利用）。権限不足等で失敗しても警告を出して継続します。
- AI（OpenAI）を利用する機能は API キーが必須です。外部 API 呼び出しはネットワーク／料金の観点で慎重に運用してください。
- kill.flag（Settings.kill_flag_path）を作成すると ExecutionEngine に停止シグナルを送る運用が可能です。KillSwitch は RiskMonitor の結果により自動で書き込む場合があります。

DB スキーマ（監視用 SQLite / monitoring.db）
-----------------------------------------
init_monitoring_db により次のテーブル等を作成します（冪等）:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code PRIMARY KEY, qty, avg_price, current_price, updated_at
- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id=1 固定行（updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

また、マイグレーション処理として既存 DB に peak_value や latency_ms がなければ自動でカラム追加します。

主要なディレクトリ構成
--------------------
（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env の読み込み・Settings
  - run_monitoring.py         — 監視ループ起動スクリプト
  - run_execution.py          — 実行エンジン起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading レポート生成 CLI
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 使用）
    - regime_detector.py      — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（init + MonitoringDB）
    - system_monitor.py       — システム状態監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン / ポジション数監視
    - kill_switch.py          — kill.flag の管理
    - alert_manager.py        — LINE 通知ラッパー
    - monitoring_engine.py    — 各モニタを束ねる実行ループ
    - streamlit_dashboard.py  — Streamlit ベースの監視 UI
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py
    - ...                     — BrokerFactory 等の発注関連実装（コードベース内）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity
  - data/ (実行時に使用する DB / フラグファイルを配置: data/*.db, data/*.flag, data/execution.pid 等)

開発 / テストに関する補足
------------------------
- DuckDB 接続を受け取る設計になっているため、ローカルの DuckDB ファイルにテスト用データをロードすることでオフライン検証が容易です。
- OpenAI やブローカーの呼び出しは依存注入/ラッパーが用意されている箇所があるため、ユニットテスト時は該当関数をモックに差し替えることを推奨します（コード内でも patch を使う想定のコメントあり）。
- .env のパースは独自実装が含まれており、シングル/ダブルクォートやエスケープ、コメントを一定のルールで処理します。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（暫定）。
- ライセンス情報はリポジトリのルートに記載してください（本 README には含めていません）。

問い合わせ / 参照
-----------------
- 追加の設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）はリポジトリに同梱される想定です。実運用や本番接続の前に十分なテストと検証を行ってください。

以上。必要であれば、各モジュールの使い方（API シグネチャ）や運用手順（systemd / supervisor でのデーモン化、ログローテーション、バックアップ方針など）について追記します。どの情報が欲しいか教えてください。