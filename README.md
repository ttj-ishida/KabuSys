KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 監視フレームワークです。  
主に以下の機能を持つモジュール群で構成されています。

- 注文の作成・管理・再同期（ExecutionEngine / OrderManager / Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- ニュースの NLP による銘柄センチメント評価（OpenAI API 経由）
- Paper Trading の検証レポート生成ツール
- Streamlit による監視ダッシュボード

主要な設計方針
- 本番と Paper Trading を DB レベルで分離（data/paper_trading.db を使用）
- DuckDB を用いた時系列・ファクター計算（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini 等）を用いたテキスト処理はフェイルセーフ設計（API失敗時は中立値で継続）
- .env / .env.local による環境変数自動読み込み（必要に応じて無効化可能）

主な機能一覧
---------------
- Execution
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントの切り替え（本番 / Mock for paper_trading）
  - 起動時の自動リコンシリエーション（Reconciler）
  - Order 管理（OrderManager / OrderRepository / OrderRecord）
  - リスク管理（RiskManager）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス PID、データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数監視
  - KillSwitch: 条件に応じた停止フラグ (data/kill.flag) 書き込み
  - AlertManager: LINE Push 通知（クールダウン付き）
  - Streamlit ダッシュボード（監視DBの閲覧）

- Portfolio / Strategy ユーティリティ
  - 銘柄選定 (select_candidates)
  - 重み計算 (equal / score)
  - セクター制約の適用 (apply_sector_cap)
  - ポジションサイズ計算（リスクベース等）

- Research / AI
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）計算
  - ニュースの NLP スコアリング（OpenAI 経由: score_news）
  - 市場レジーム判定（score_regime）

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントに Python 3.10 の構文を使用）
- Git, SQLite（標準ライブラリで可）
- ネットワーク接続（OpenAI API を使う場合）

推奨ライブラリ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

例: 仮想環境作成と依存インストール
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（requirements.txt がない場合は手動インストール）
   - pip install duckdb psutil openai requests streamlit

環境変数
- .env / .env.local をプロジェクトルートに置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
- 主要な環境変数（必要に応じて設定）:
  - KABUSYS_ENV: 起動環境 (development | paper_trading | live) — デフォルト: development
  - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
  - KABU_API_PASSWORD: （必須）kabuステーションAPIパスワード
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード (instant|partial|never|reject) — デフォルト: instant
  - LOG_LEVEL: ログレベル（DEBUG|INFO|...）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH 等（必要なら上書き）

初期 DB 準備
- run_monitoring や run_execution は起動時に init_monitoring_db() を呼び、必要なテーブルを作成・マイグレーションします。特別な初期化は不要です（data ディレクトリを作る必要は起動時に自動作成される場合があります）。

使い方
-------

実行・監視プロセス

- 監視プロセス起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に settings.sqlite_path（production 相当）を使用する設計。

- ExecutionEngine 起動（売買実行プロセス）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録します（本番 DB と分離）。
  - 実行プロセスは data/execution.pid に PID を書き込み、停止は data/stop_requested.flag を作成すると検知して終了します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視用 SQLite を read-only URI で開いて表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能。

- AI / リサーチ機能（スクリプト的に使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB コネクション＋ target_date を渡すと ai_scores に結果を保存します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込みます。

停止と Kill / Stop フラグ
- data/stop_requested.flag: run_monitoring / run_execution が監視している「外部からの即時停止要求」用フラグ。存在するとプロセスは安全に終了します。
- data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止シグナル（リスク上限など）を送ります。KillSwitch は設定した条件（ドローダウンやポジション上限）でこのファイルを書きます。
- KillSwitch の reason はファイル内容として保存されます。clear() により削除可。

注意点 / トラブルシューティング
- Process priority の設定（set_process_priority('high')）はプラットフォーム依存で権限が必要な場合があります。失敗してもログに警告が出てスキップされます。
- OpenAI API 呼び出しはネットワーク/レート制限などで失敗することがあります。本実装はリトライやフォールバックを行いフェイルセーフを目指していますが、APIキーの有効性・レート制限に注意してください。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 の有無を確認してください。
- SQLite / DuckDB のファイルパスは Settings で上書きできます。Paper Trading 用 DB は本番監視 DB と分離してください。

ディレクトリ構成（抜粋）
-----------------------
src/ 以下の主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py           — 優先度 / CPU Affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 監視テーブル定義 / DBアクセス（init, MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - (broker_factory, execution_engine, risk_manager 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — 市場レジーム判定（OpenAI + MA 合成）
  - data/                            — デフォルトの DB / flag 等（実行時に作成されることが多い）
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト

（ファイルは上記以外にも多くの補助モジュールを含みます。ここでは主要部分を抜粋しています。）

開発者向けメモ
---------------
- DuckDB 接続を渡す関数群（research / ai）は副作用を最小にする設計です。テスト時は DuckDB のインメモリ接続を使ってください。
- OpenAI 呼出し部分はユニットテストで差し替え可能（モジュール内の _call_openai_api をモックする設計）。
- monitoring_db.init_monitoring_db() は冪等で実行可能。既存 DB に対して必要なマイグレーションを行います。

ライセンス / 貢献
----------------
- 本リポジトリに LICENSE ファイルがある場合はそちらに従ってください。  
- バグ報告やプルリクエストは issue/PR でお願いします。

以上。必要であれば README に「環境変数の例（.env.example）」や「起動スクリプトの systemd ユニット例」などの具体例を追記できます。どの情報を補足希望か教えてください。