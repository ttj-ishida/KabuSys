KabuSys — 日本株自動売買システム（README）
========================================

概要
----
KabuSys は日本株自動売買のための基盤ライブラリ／実行コンポーネント群です。システム監視、注文実行（ExecutionEngine）、ポートフォリオ構築、リサーチ（ファクター計算）、AI を使ったニュースセンチメント／市場レジーム判定など、取引運用に必要な主要機能をモジュール化して提供します。

主な特徴
--------
- ExecutionEngine（注文生成・送信・リスク管理・リコンシリエーション）
  - 再起動後の自動同期（Reconciler）
  - RiskManager による各種リスク制御
- Monitoring（稼働監視・注文滞留検知・リスクアラート）
  - system_status / trade_logs / risk_logs / dashboard の永続化（SQLite）
  - LINE 通知サポート（AlertManager）
  - kill.flag による ExecutionEngine 停止指示
  - Streamlit ダッシュボード
- Portfolio construction（候補選定・重み計算・ポジションサイジング・セクター制限）
- Research（DuckDB ベースのファクター計算・特徴量解析）
- AI モジュール
  - ニュース記事のセンチメントを OpenAI で評価（news_nlp）
  - マクロ + 価格を組み合わせた市場レジーム判定（regime_detector）
- Paper Trading モード（本番 DB と完全分離された data/paper_trading.db を使用）

動作前提（推奨）
----------------
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード使用時）
- sqlite3（標準ライブラリ）
- その他プロジェクト依存ライブラリ（requirements.txt がある場合はそれを使用してください）

インストール（開発環境）
-----------------------
1. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合は少なくとも以下を入れてください:
     - pip install duckdb psutil requests openai streamlit

3. パッケージを editable インストール（任意）
   - pip install -e .

設定（環境変数 / .env）
----------------------
アプリケーションは環境変数（またはプロジェクトルートの .env / .env.local）から設定を読み込みます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主要な環境変数（既定値 / 備考）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を使う機能で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定なら通知は行わない）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: Execution PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定モード（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL: ログレベル（INFO 等）

簡易 .env 例:
    KABUSYS_ENV=development
    JQUANTS_REFRESH_TOKEN=your_jquants_token
    KABU_API_PASSWORD=your_kabu_password
    OPENAI_API_KEY=sk-...
    SQLITE_PATH=data/monitoring.db
    DUCKDB_PATH=data/kabusys.duckdb
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    LINE_CHANNEL_ACCESS_TOKEN=
    LINE_USER_ID=

起動方法（主要スクリプト）
--------------------------

- ExecutionEngine（取引実行）
  - 説明: 実際の注文発行・リスク管理・リコンシリエーションを行う。
  - 本番 / paper_trading 切り替え:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録します（本番 DB と完全分離）。
  - 実行:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - python -m kabusys.run_execution  (KABUSYS_ENV に応じて動作)

- Monitoring（SystemMonitor のポーリング）
  - 説明: SystemMonitor をポーリングして system_status 等を記録。MONITOR_POLL_INTERVAL でポーリング間隔を変更できます。
  - 実行:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは本番 DB を想定）。

- Streamlit ダッシュボード
  - 説明: 監視 DB を読み取り専用で可視化します。
  - 実行:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - 説明: data/paper_trading.db のログを集計して検証レポートを出力します。
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - --db オプションで DB ファイルを指定可能

- AI モジュール（ライブラリ関数）
  - news_nlp.score_news(conn, target_date, api_key=None) — DuckDB 接続を渡してニュースセンチメントを ai_scores に書き込む
  - ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime に書き込む
  - これらはライブラリ関数として呼び出します（CLI ラッパーは未提供）。OPENAI_API_KEY を環境に設定するか、api_key 引数を渡してください。

監視・停止制御の仕組み
-----------------------
- PID ファイル: ExecutionEngine が実行中は PID を data/execution.pid に書きます（Settings.pid_file_path）。SystemMonitor はこの PID をチェックしてプロセスが生きているか検証します。
- Kill Switch: RiskMonitor 等が閾値を超えると KillSwitch が data/kill.flag を書き込み、ExecutionEngine の停止シグナルとして使用できます。KillSwitch は冪等に動作します。
- kill.flag の自動消去: Settings.kill_flag_clear_on_start を利用して起動時に clear する挙動が設定可能（実装の使用箇所に依存）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はコードベース内の主要モジュールと役割（src/kabusys 以下）です。

- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - 環境変数 / .env 読み込み、Settings クラス（各種設定取得）

- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に依存）

- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト

- execution/
  - broker_api, broker_factory, execution_engine, order_manager, order_repository, order_record, reconciler, risk_manager 等
  - 注文の作成・送信、リスク管理、再同期（Reconciler）

- monitoring/
  - monitoring_db.py : SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, alert_manager.py
  - monitoring_engine.py : 複数モニタを束ねるオーケストレーション
  - streamlit_dashboard.py : Streamlit ダッシュボード

- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定・重み付け・株数計算・セクター調整

- research/
  - factor_research.py, feature_exploration.py
  - DuckDB を使ったファクター計算・将来リターン・IC 計算など

- ai/
  - news_nlp.py : OpenAI を用いたニュースセンチメント取得
  - regime_detector.py : マクロ+ETF を用いた市場レジーム判定

- tools/
  - paper_verification_report.py : Paper Trading ログの検証レポート出力

実運用上の注意
--------------
- 許可権限: set_process_priority / cpu_affinity は psutil を使ってプロセス操作を行います。環境によっては権限不足で警告が出ますが処理は継続します。
- DB の権限: monitoring DB / paper_trading DB は実行ユーザーが書き込みできる場所にしてください。
- OpenAI 使用: API 呼び出しの失敗は内部でリトライやフォールバックを行いますが、API キーは安全に管理してください。
- Paper Trading モードは本番資金に影響を与えないことを意図していますが、設定ミスにより本番ブローカーに接続されないか注意してください（BrokerClientFactory の設定を確認）。

開発・テストのヒント
--------------------
- .env.local を使ってローカル専用設定を上書き可能です（OS 環境変数が優先されます）。
- Settings クラスを通して設定値を取得すれば環境依存の切り替えが容易です。
- DuckDB 接続は読み取り専用 URI（Path.as_uri() + "?mode=ro"）で開けます。streamlit ではその手法を使っています。

ライセンス・貢献
----------------
（LICENSE ファイル等があればここに記載してください）

以上。開発・運用に関する詳細な仕様は各モジュールの docstring やコード内コメントに記載されています。必要であれば各機能の使い方サンプルやチュートリアルを追記します。