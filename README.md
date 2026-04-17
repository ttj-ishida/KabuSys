KabuSys — 日本株自動売買システム（簡易 README）
=================================

概要
----
KabuSys は日本株向けの自動売買／研究／監視用モジュール群を含む小規模なプロジェクトです。本リポジトリには、
- 注文発行と実行を担当する Execution Engine（実運用 / paper trading 切替対応）
- システム・注文・リスクを監視する Monitoring モジュール（SQLite へ永続化）
- ポートフォリオ構築の純粋関数群（候補選定・重み付け・株数算出）
- リサーチ用のファクター計算・特徴量解析
- ニュースセンチメントやレジーム判定のための LLM 統合（OpenAI）
- 運用補助ツール（検証レポート生成、Streamlit ダッシュボード）

を含みます。設計方針としては「ビジネスロジックと永続化の分離」「ルックアヘッドバイアスの防止」「障害に対するフェイルセーフ」を重視しています。

主な機能
--------
- Execution
  - ブローカークライアントの抽象化（実運用 / モックの切替）
  - 注文状態管理（OrderManager）と再起動時のリコンシリエーション（Reconciler）
  - リスク管理（ポジション上限、ドローダウン等）

- Monitoring
  - システム状態監視（CPU / メモリ / ディスク、プロセスの生存確認）
  - 注文の滞留監視・約定異常検出
  - リスク監視（ドローダウン、ポジション数）
  - Kill Switch（閾値超過時に data/kill.flag を作成して Execution を停止）
  - LINE を用いたアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード表示

- Portfolio（純粋関数）
  - 候補選定（スコア順）
  - 等重・スコア加重配分
  - 単元株丸め・リスクベースの株数算出
  - セクター制限・レジーム乗数適用

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily 等を参照）
  - 将来リターン計算 / IC（Information Coefficient）等の解析ユーティリティ

- AI（OpenAI）
  - ニュース記事に基づく銘柄別センチメント付与（ai_scores へ書込み）
  - マクロニュース + MA200 乖離から日次の市場レジーム判定（market_regime へ書込み）
  - API 呼び出しはリトライ・バックオフ・レスポンス検証を行う

セットアップ（開発環境向け）
--------------------------
前提: Python 3.9+ を推奨。実行環境はプロジェクトルート（pyproject.toml / .git があるディレクトリ）で操作してください。

1. リポジトリをクローンし、作業ディレクトリを移動
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必要な主な依存:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements ファイルがあればそちらを使用してください）

4. 環境変数 / .env
   - プロジェクトは .env / .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を利用する場合必須）
     - KABUSYS_ENV: 起動環境（development / paper_trading / live、デフォルト development）
     - PAPER_FILL_MODE: paper_trading の模擬約定モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH: paper trading 専用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - .env の書き方は shell 形式です（export を使った行にも対応）。サンプルは .env.example を参照（リポジトリにある場合）。

初期化（DB）
- 監視用 DB のテーブルは run_monitoring / run_execution 起動時に自動で初期化（init_monitoring_db）されます。手動で作成する必要はありません。

使い方（主要スクリプト）
------------------------

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 説明:
    - SystemMonitor を定期（デフォルト 60 秒）に実行して監視ログを SQLite に永続化します。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能。
    - 停止制御: プロジェクトルート/data/stop_requested.flag を作成するとループを終了します（停止フラグ検知）。
    - 監視は本番用 sqlite_path を環境に関係なく使用（monitoring のデータは本番 DB を参照）。

- Execution Engine を起動
  - python -m kabusys.run_execution
  - 説明:
    - ExecutionEngine を立ち上げ、注文処理スレッドを起動します。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録して本番 DB と完全分離します。
    - 停止制御: data/stop_requested.flag が存在すれば起動を中止、実行中は同フラグで安全停止します。
    - PID ファイル: data/execution.pid（既定）に PID を書き、SystemMonitor がプロセス生存を確認します。

- Streamlit 監視ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明:
    - 監視用 SQLite を読み取り専用で開き、ダッシュボードを表示します。
    - MonitoringEngine を起動しておく必要があります（DB が存在しないとエラー表示されます）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
  - 出力: 期間中の稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL を表示します。

AI 機能
-------
- OpenAI を用いる機能（ニューススコアリング / レジーム判定）は OPENAI_API_KEY が必要です。未設定時は ValueError を発生させるか、フォールバック（macro_sentiment=0.0）で続行する設計になっている箇所があります。
- レートリミット・一時的なネットワーク障害に対しては指数バックオフでリトライします。

重要なファイル・フラグ
---------------------
- data/stop_requested.flag — run_* スクリプトが検出して安全に停止するためのフラグ
- data/kill.flag — KillSwitch が書き込む停止理由（Execution 停止用）
- data/execution.pid — 起動中の ExecutionEngine の PID（SystemMonitor が確認）

監視DB（主なテーブル）
---------------------
init_monitoring_db により以下のテーブルが作成されます（冪等）:
- system_status: cpu_percent, memory_percent, disk_percent, process_ok, recorded_at
- trade_logs: 発注イベントログ（event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: 保有ポジション（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスクイベント（event_type, metric_name, metric_value, threshold, detail）
- dashboard: 集計表示用（id=1 の 1 行のみ保持）

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                        — 環境変数 / Settings
- run_monitoring.py                — SystemMonitor ポーリングループの起動スクリプト
- run_execution.py                 — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py                     — ニュースから銘柄別センチメントを生成（OpenAI）
  - regime_detector.py              — マクロ + MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py                — SQLite 永続化層（テーブル作成・CRUD ユーティリティ）
  - system_monitor.py               — システム / データ鮮度監視
  - trade_monitor.py                — 注文滞留 / 約定異常監視
  - risk_monitor.py                 — ドローダウン / ポジション上限監視
  - kill_switch.py                  — kill.flag 制御
  - alert_manager.py                — LINE 通知
  - monitoring_engine.py            — モニタ群を束ねる実行ループ
  - streamlit_dashboard.py          — Streamlit ダッシュボード (CLI)
- execution/
  - order_manager.py
  - reconciler.py
  - (その他: broker_factory, execution_engine, order_repository 等)
- portfolio/
  - portfolio_builder.py
  - risk_adjustment.py
  - position_sizing.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py    — Paper Trading レポート生成 CLI
- utils/
  - process_priority.py             — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (実行時に使用/生成)
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading モード用)
  - *.flag / *.pid

運用上の注意
------------
- KABUSYS_ENV を正しく設定してください（development / paper_trading / live）。paper_trading を使うと本番 DB と分離された専用 SQLite に記録されます。
- AI 系機能は OpenAI API キーが必要です。API 利用料やレートに注意してください。
- Process priority / CPU affinity の設定は実行 OS に依存し、権限不足や未サポート OS では警告が出てスキップされます。
- 監視ループは MONITOR_POLL_INTERVAL により調整できます（デフォルト 60 秒）。0 以下は無効としてデフォルトにフォールバックします。
- kill.flag / stop_requested.flag を使ってプロセスを安全に停止できます。削除は手動または KillSwitch.clear() で行えます。

トラブルシューティング
----------------------
- SQLite / DuckDB ファイルが見つからない場合、該当スクリプトはエラーログを出します。monitoring は起動時に必要なテーブルを自動生成しますが、DuckDB の prices_daily 等のテーブルは外部データ投入が前提です。
- OpenAI API 呼び出しが失敗する場合、モジュールはリトライやフォールバック値を用いる設計ですが、ログを確認して API キーやネットワーク状況を確認してください。
- PID ファイルが残っているがプロセスが存在しない場合、SystemMonitor が stale PID を検出して削除し、risk_logs に記録します。

開発者向けメモ
---------------
- 環境変数読み込みは config._find_project_root() でプロジェクトルートを検出し .env / .env.local をロードします。テスト時に自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 多くのコンポーネントは DB 接続（sqlite3 / duckdb）や broker クライアントを引数で受け取る設計のためユニットテストしやすくなっています。OpenAI 呼び出しや time.sleep などは patch してテスト可能です。

ライセンス / 貢献
-----------------
（ライセンスや貢献方法があればここに記載してください）

以上。必要であれば README に含めるコマンドの具体例（.env.example のテンプレート、requirements.txt の推奨内容、systemd サービスファイルのサンプル等）を追加します。どの情報を優先的に詳しく載せたいか教えてください。