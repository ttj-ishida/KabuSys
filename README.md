README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
主に次の機能群を含みます。

- 注文発行・注文管理・リコンシリエーション（Execution）
- 監視（System / Trade / Risk）とアラート（LINE 連携）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- ファクター計算・研究ユーティリティ（DuckDB を利用）
- ニュースの NLP スコアリング（OpenAI を利用）
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

主な設計方針として「本番 DB と Paper Trading の明確な分離」「ルックアヘッドバイアス防止」「外部 API 呼び出しは明示的な箇所に限定」といった点を重視しています。

主な機能
--------
- Execution
  - Broker クライアントの抽象化（本番 / Paper の切替）
  - OrderManager（状態遷移管理）、Reconciler（起動時照合）
  - リスク制御（RiskManager）やオーダーリポジトリ（SQLite）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度を監視
  - TradeMonitor: 滞留注文（stale）・約定異常を検出
  - RiskMonitor: ドローダウン / 保有上限の監視・kill flag 生成
  - AlertManager: LINE プッシュ通知（クールダウン制御）
  - MonitoringEngine：各 Monitor をまとめたポーリングループ
  - Streamlit ダッシュボードで可視化
- Research / AI
  - DuckDB を利用したファクター計算（momentum, volatility, value など）
  - 将来リターン・IC 計算、特徴量分布サマリー
  - ニュース記事の LLM ベースセンチメントスコアリング（OpenAI）
  - 市場レジーム判定（MA + マクロニュースの合成）
- Portfolio
  - 候補選定（スコア順ソート）
  - 等分配・スコア加重配分
  - ポジションサイズ計算（リスクベース / 比率ベース）、単元丸め、集約キャップ
- ユーティリティ
  - プロセス優先度 / CPU affinity の設定（psutil）
  - 設定読み込み（.env 自動読み込み、Settings クラス）

セットアップ
-----------
前提
- Python 3.9+（ソースは型ヒント等を利用）
- SQLite（組み込み） / DuckDB（パッケージインストール）
- OpenAI API を使う機能は OPENAI_API_KEY が必要

例: 仮想環境作成と必要パッケージ（例示）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt があればそちらを使用してください）

環境変数・.env
- プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- KABUSYS_ENV: 開発環境フラグ（development | paper_trading | live）デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須な箇所あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須な箇所あり）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject。デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

サンプル .env
- .env.example に合わせて必要値を設定してください。例:
  KABUSYS_ENV=development
  OPENAI_API_KEY=sk-...
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db
  PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
  KABU_API_PASSWORD=...
  JQUANTS_REFRESH_TOKEN=...
  LINE_CHANNEL_ACCESS_TOKEN=...
  LINE_USER_ID=...

使い方
------
実行スクリプト（モジュール実行）
- 監視ループ（Monitoring）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒）。
    - 監視は env に関わらず本番用 sqlite_path（Settings.sqlite_path）を使ってログを残します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知して終了します。

- ExecutionEngine（発注エンジン）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全に分離）。
    - 起動時に stop flag が既に立っていると起動せず終了します。
    - 実行中に data/stop_requested.flag が作成されるとエンジン停止を試みます。
    - 実行中は data/execution.pid に PID を書きます（SystemMonitor はこの PID ファイルを用いてプロセス生存を確認します）。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視 DB を読み取り専用で開いてダッシュボードを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD
    --to YYYY-MM-DD
    --db PATH  （PAPER_TRADING_SQLITE_PATH より優先して DB を指定）
  - 出力: システム稼働率、注文成功率、送信率、P95 レイテンシ等のサマリと PASS/FAIL 判定

停止・kill フラグ
- Execution を強制停止（Kill Switch）は監視側が評価して data/kill.flag を書き込みます。  
  - KillSwitch はリスクやドローダウン等の条件に従って kill.flag を作成します。  
  - kill.flag は Settings.kill_flag_path（デフォルト data/kill.flag）を通じて扱われます。  
- clear（削除）は KillSwitch.clear() を使うか手動でファイルを削除してください。  
- data/stop_requested.flag は run_monitoring/run_execution の両方で監視され、存在すると安全に終了処理を行います。

モード・DB の分離
- paper_trading モード:
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ書き込みます。
  - 本番の SQLITE_PATH / DUCKDB_PATH とは別に運用できるため、実運用 DB を汚しません。

監視 DB スキーマ（主なテーブル）
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok, ...)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id = 1 の単一行で集計保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value, ...)

ディレクトリ構成（主なファイル / モジュール）
-----------------------------------
src/kabusys/
- __init__.py              — パッケージメタデータ
- config.py                — Settings クラス（.env 自動ロード、環境変数ラッパ）
- run_monitoring.py        — SystemMonitor のポーリング起動スクリプト
- run_execution.py         — ExecutionEngine 起動スクリプト

パッケージ別主要ファイル
- ai/
  - news_nlp.py            — ニュースセンチメントの OpenAI ベース処理
  - regime_detector.py     — 市場レジーム判定（MA + マクロニュース）
- monitoring/
  - monitoring_db.py       — SQLite による永続化層（テーブル作成・CRUD）
  - system_monitor.py      — システム・データ鮮度監視
  - trade_monitor.py       — 注文滞留・約定異常監視
  - risk_monitor.py        — ドローダウン・ポジション数監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - alert_manager.py       — LINE 通知クライアント
  - monitoring_engine.py   — 各 Monitor の統合（ポーリングループ）
  - streamlit_dashboard.py — Streamlit での可視化
- execution/
  - order_manager.py       — 注文の作成・同期などの外向き API
  - reconciler.py          — 起動時の注文・ポジション照合
  - ...（Broker / Engine / repository などが含まれる）
- portfolio/
  - portfolio_builder.py   — 候補選定・重み計算
  - position_sizing.py     — 株数計算・集約キャップ処理
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — momentum / volatility / value 等の計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- utils/
  - process_priority.py    — psutil を使ったプロセス優先度・CPU affinity

補足・運用ノウハウ
-----------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に .env / .env.local を読み込みます。
  - OS 環境変数が優先され、.env.local は .env の上書きに使えます。
  - テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- ロギング:
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を使います。詳細ログは LOG_LEVEL を設定して制御できます（Settings.log_level）。

- OpenAI 呼び出し:
  - news_nlp / regime_detector は OpenAI を使います。API キー未設定時は例外または実行スキップ（モジュール方針に依存）となる箇所があります。
  - API 呼び出しはリトライ・バックオフを実装しており、失敗時にはフェイルセーフ（0.0 で継続等）を採る設計です。

- 同期待ち・停止:
  - run_execution は内部で daemon スレッドでエンジンを実行し、stop flag を監視して安全に engine.stop() を呼びます。強制終了は推奨されません。

よくある操作例
--------------
- 監視プロセスをデフォルト間隔（60秒）で起動:
  - python -m kabusys.run_monitoring

- ポーリング間隔を 30 秒にする:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution を Paper モードで起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート（2026-04-01 〜 2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス / 貢献
----------------
- （このリポジトリに付随するライセンス表記があればここに記載してください。）
- バグ報告・機能提案は Issue を立ててください。

以上が本リポジトリの README（日本語）です。必要であれば「導入手順の詳細」「CI設定」「docker-compose 例」などの追加ドキュメントを作成します。どの項目を優先して詳述しますか？