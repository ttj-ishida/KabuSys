KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。  
シグナルからポートフォリオ構築、注文管理、リコンシリエーション、監視（Monitoring）、Paper Trading 検証や研究用ファクター計算、LLM を使ったニュースセンチメント評価などの機能を提供します。

主要な設計方針（抜粋）
- 本番・検証（paper_trading）を環境変数 KABUSYS_ENV で切り替え（development / paper_trading / live）。
- DB: SQLite（監視ログ・paper trading）と DuckDB（時系列・ファクタ計算データ）を併用。
- LLM（OpenAI）呼び出しは冪等性・フェイルセーフを考慮して実装。
- 自動的に .env / .env.local をロード（プロジェクトルートが .git または pyproject.toml で検出される場合）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。

機能一覧
--------
- Execution エンジン起動（run_execution）: ブローカークライアント生成、注文管理、リスク管理、リコンシリエーション、PID 管理、停止フラグ監視。
- Monitoring エンジン（run_monitoring / MonitoringEngine）: システム状態・注文状態・リスク監視、LINE 通知、kill flag 発行。
- Monitoring DB 層（monitoring_db）: system_status, trade_logs, positions, risk_logs, dashboard の永続化と簡易マイグレーション処理。
- Risk / Trade / System モニタ（risk_monitor / trade_monitor / system_monitor）: ドローダウンアラート、滞留注文検出、データ鮮度チェック、stale PID 検出。
- AlertManager: LINE Messaging API を用いたプッシュ通知（クールダウン管理）。
- Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）: 監視ダッシュボード表示。
- Paper Trading 検証レポート（tools/paper_verification_report.py）: 稼働率・注文成功率・レイテンシ等のレポート出力。
- Portfolio 構築（portfolio パッケージ）: 候補選定、重み計算、セクター制限、ポジションサイズ計算（等金額・スコア・リスクベース）。
- Research（research パッケージ）: ファクター計算（momentum/volatility/value）、将来リターン、IC 計算、統計サマリ。
- AI（ai パッケージ）: ニュース NLP（score_news）、市場レジーム判定（score_regime） — OpenAI API を使用。

セットアップ手順
--------------
1. リポジトリをクローンしてプロジェクトルートへ移動。
2. 仮想環境を作成・有効化（推奨）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要なパッケージをインストール（requirements.txt がある前提）。
   - pip install -r requirements.txt
   推奨ライブラリ（主要なもの）:
   - duckdb, psutil, requests, openai, streamlit
4. 環境変数を設定（.env/.env.local または OS 環境変数）。代表的なキー（デフォルト値を併記）:
   - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
   - JQUANTS_REFRESH_TOKEN: （必須）
   - KABU_API_PASSWORD: （必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を有効化する場合
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
   - PAPER_FILL_MODE: instant | partial | never | reject （デフォルト: instant）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（必要に応じて）
5. data ディレクトリを作る:
   - mkdir -p data

使い方（実行例）
----------------

実行の基本
- パッケージ形式で実行する場合、プロジェクトルートから:
  - 監視ループ起動:
    python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト: 60）。
    - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（環境に依らず本番 DB に接続する設計）。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成すると検知してループを終了します。
  - Execution エンジン起動:
    python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録して本番 DB と分離します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
    - 実行中に stop flag が作成されると停止処理が始まります。
  - Streamlit ダッシュボード:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - Paper Trading 検証レポート:
    python -m kabusys.tools.paper_verification_report
    オプション:
      --from YYYY-MM-DD
      --to   YYYY-MM-DD
      --db   PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - AI 関連（コードから呼び出す例）:
    from kabusys.ai import score_news
    # DuckDB 接続を用意して score_news(conn, target_date, api_key=...)
    # または kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

監視・停止関連ファイル
- stop flag: data/stop_requested.flag — run_monitoring / run_execution が監視して処理を終了するための外部フラグ。
- kill flag: data/kill.flag — KillSwitch が書き込み、ExecutionEngine に対する停止シグナルとして使用。
- execution PID: data/execution.pid — ExecutionEngine が起動時に書き出す PID。SystemMonitor はこの PID を見て実行プロセスの稼働をチェックし、stale PID を検出するとファイルを削除してイベントを記録します。

設定（Settings）について
- 設定は kabusys.config.Settings で提供され、環境変数から読み取ります。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env を読み込み、続けて .env.local を読みます。
  - OS 環境変数は保護され、.env.local の override は OS 環境変数を上書きしません（ただし .env.local は OS 環境変数より優先）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 重要な Settings プロパティ:
  - sqlite_path, duckdb_path, paper_sqlite_path, pid_file_path, kill_flag_path, cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct, paper_fill_mode 等。

注意点・実装上のポイント
- init_monitoring_db は冪等にテーブル作成・簡易マイグレーション（カラム追加）を行います。初回起動時にテーブルが作成されます。
- Monitoring はデータ鮮度（prices_daily の最終日）を DuckDB からチェックします（SystemMonitor）。
- AI 呼び出し（news_nlp, regime_detector）は OpenAI API のエラー（429 / ネットワーク / 5xx 等）に対して指数バックオフでリトライし、最終的に失敗時はフェイルセーフ（例: macro_sentiment=0.0）で継続します。
- process_priority ユーティリティ（kabusys.utils.process_priority）を使い、run_monitoring/run_execution は起動時にプロセス優先度を "high" に設定しようと試みます（psutil が必要）。失敗しても警告を出して続行します。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py              — 環境変数 / 設定管理
    - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py       — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading 検証レポート生成
    - monitoring/
      - __init__.py
      - monitoring_db.py     — SQLite 永続化層
      - monitoring_engine.py — 各 Monitor を束ねるエンジン
      - system_monitor.py    — システム状態・データ鮮度チェック
      - trade_monitor.py     — 注文滞留・約定異常検出
      - risk_monitor.py      — ドローダウン・ポジション上限監視
      - kill_switch.py       — kill.flag 制御
      - alert_manager.py     — LINE 通知
      - streamlit_dashboard.py — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py  (想定)
      - broker_factory.py    (想定)
      - broker_api.py        (想定)
      - order_record.py      (想定)
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
    - utils/
      - __init__.py
      - process_priority.py
    - data/  (実行時に利用する SQLite / DuckDB 等のファイル置き場)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用, デフォルト)
      - kabusys.duckdb (デフォルト)

テスト・開発上のヒント
---------------------
- ローカル開発・ユニットテストの際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化し、テストごとに環境を制御するのが便利です。
- OpenAI を使う機能のテストは、_call_openai_api のラッパーや client をモックすることでネットワーク依存を切り離せます（実装内にもテストで差し替えやすい注記あり）。
- streamlit ダッシュボードでは DB を read-only URI で開いているため、Monitoring が起動していないと接続できない旨のエラーを出します。

よく使うコマンド例
------------------
- 監視ループ（デフォルト 60 秒間隔）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution エンジン（Paper Trading）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート（2026-04-01 〜 2026-04-11）:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張案
-----------------
- broker クライアントの実装を追加することで実際の証券会社 API と接続可能（Kabu API 用のクライアントは KABU_API_PASSWORD と KABU_API_BASE_URL を使用）。
- Portfolio の lot_size を銘柄毎に管理する拡張、手数料・スリッページのモデル化、複雑なリスクルールの追加。
- AlertManager に Slack / PagerDuty など別チャネルの統合。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）を用意するデータパイプラインの実装。

ライセンス・著作権
------------------
本リポジトリのライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください。

最後に
------
この README はコードベース内の docstring / コメントを基に作成しました。実行前に .env の設定と依存ライブラリのインストールを必ず確認してください。質問や追加のドキュメント化が必要であれば教えてください。