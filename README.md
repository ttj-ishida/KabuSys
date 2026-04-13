KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買フレームワーク（プロトタイプ）です。  
このリポジトリには、以下の主要機能群が含まれます。

- 注文・発注の管理と実行（ExecutionEngine / OrderManager）
- モニタリング（System / Trade / Risk）の常時監視とアラート
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチ用ファクター計算・特徴量解析（DuckDB を用いる）
- AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
- Paper Trading 向け分離動作・検証レポート出力ツール
- Streamlit ベースの監視ダッシュボード

設計のポイント
- 設定は環境変数（.env/.env.local）で管理。自動ロード機能あり（必要に応じて無効化可）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db を使用）。
- DuckDB を分析用 DB として利用し、prices_daily / raw_financials 等の表から計算。
- OpenAI API は外部依存（API キーは環境変数で指定）。失敗時はフェイルセーフで継続する設計。

主な機能一覧
- 実行
  - run_execution.py: ExecutionEngine を起動して発注セッションを実行
  - Paper Trading モードで MockBrokerClient を利用（本番 DB と分離）
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループを起動
  - MonitoringEngine: System/Trade/Risk の統合ポーリング、KillSwitch/Alert 管理
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（期間指定可）
- ポートフォリオ構築
  - portfolio: 候補選定、重み計算、リスク調整、ポジションサイズ計算
- リサーチ
  - research: ファクター計算（momentum/value/volatility）、将来リターン、IC 計算 等
- AI
  - ai.news_nlp: ニュース記事を OpenAI でスコアリングして ai_scores に格納
  - ai.regime_detector: ma200 とマクロニュースを融合して市場レジーム判定

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（typing の構文等を使用）
- システムに以下ライブラリをインストールしてください:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
（必要に応じて pip install を使用してください）

例:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai requests streamlit

環境変数
- 自動 .env ロード:
  - パッケージはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探して .env/.env.local を自動で読み込みます。
  - 自動ロードを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 代表的な環境変数（デフォルト値・説明）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
  - SQLITE_PATH — 監視用 SQLite（monitoring）DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — Paper Trading の約定挙動（デフォルト: instant）
  - PID_FILE_PATH — ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill flag ファイル（デフォルト: data/kill.flag）
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE 通知）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- .env の読み込み順:
  1. OS 環境変数（保護される）
  2. .env （未設定のキーのみセット）
  3. .env.local （上書き可能。ただし OS にあるキーは保護）

初期 DB 作成
- 起動時に monitoring のテーブルは init_monitoring_db() により作成されます（冪等）。
- マイグレーション的に不足カラムがあれば自動的に追加されます（例: dashboard.peak_value, trade_logs.latency_ms）。

基本的な使い方
----------------

1) 監視ループを起動（常駐）
- デフォルト 60 秒間隔で SystemMonitor を実行し monitoring DB に記録します。プロセス優先度を可能な限り高くします。
  python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数で秒数を調整（1 以上）。不正値は 60 秒にフォールバック。

2) 実行エンジンを起動（注文処理）
- 通常（本番/開発）:
  python -m kabusys.run_execution
- Paper Trading（DB 分離・MockBroker 使用）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Execution 起動時は ExecutionEngine が依存コンポーネント（BrokerClient, OrderRepository, RiskManager, Reconciler など）を組み立ててセッションを実行します。
- 起動直後、kill flag の初期化動作（設定によりクリア）や Reconciler による注文同期が行われます。

3) Streamlit ダッシュボード（監視画面）
- 監視 DB（読み取り専用）を指定して起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading の検証レポート
- 対象 DB（デフォルト: data/paper_trading.db）から集計してレポートを stdout に出力します:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

5) AI ベース処理
- ニューススコアリング:
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY を環境変数に設定しておくか、api_key を引数で渡します。
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意: API 呼び出しはレート制限・ネットワークエラー等に対してリトライやフォールバック（0.0）を行う設計です。

運用上の注意
- Process priority の設定はプラットフォーム依存です。権限不足で設定に失敗する場合がありますが、例外は安全に扱われログ出力されます。
- kill.flag（KILL_FLAG_PATH）を作成すると ExecutionEngine に停止シグナルを送ります。KillSwitch は主に drawdown・ポジション上限をトリガーとしてファイル出力します。Execution 側は起動時にこのフラグのクリアを行うオプション設定があります。
- LINE 通知はトークン・ユーザーID が未設定だとスキップされます。通知は同一レベル/カテゴリでクールダウン制御されます。
- Paper Trading を使用する場合、PAPER_TRADING_SQLITE_PATH を設定して本番 monitoring DB と明確に分離してください。

ディレクトリ構成（概要）
---------------------
以下は src/kabusys 以下の主要ファイル・モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / .env のロードと Settings クラス
  - run_monitoring.py             -- SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py              -- ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py -- Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py            -- SQLite 永続化層（schema / MonitoringDB）
    - system_monitor.py           -- CPU/Mem/Disk/データ鮮度 / PID チェック
    - trade_monitor.py            -- 注文滞留・約定異常の監視
    - risk_monitor.py             -- ドローダウン・ポジション上限監視
    - kill_switch.py              -- kill.flag 操作
    - alert_manager.py            -- LINE 通知ラッパー
    - monitoring_engine.py        -- 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py      -- Streamlit ダッシュボード
  - execution/
    - order_manager.py            -- 注文状態遷移と Broker 呼び出しのラッパー
    - order_repository.py         -- orders DB（別ファイル、OrderRepository）
    - reconciler.py               -- 再起動時の注文/ポジション同期
    - ...                         -- BrokerFactory, EngineConfig, RiskManager 等
  - portfolio/
    - portfolio_builder.py        -- 候補選定・重み計算
    - position_sizing.py          -- 株数決定・スケーリング
    - risk_adjustment.py          -- セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py          -- momentum/volatility/value の計算
    - feature_exploration.py      -- forward returns / IC / summary
    - __init__.py
  - ai/
    - news_nlp.py                 -- ニュースの LLM スコアリング（ai_scores へ書込）
    - regime_detector.py          -- マクロ + MA200 によるレジーム判定
    - __init__.py
  - utils/
    - process_priority.py         -- プロセス優先度 / CPU affinity 設定
    - __init__.py

（注）上の一覧は主要実装の抜粋です。実際のツリーはこの README のあるリポジトリでご確認ください。

補足・開発者向けメモ
-------------------
- DuckDB は分析用に使われ、ファクター計算やニュース集約で SQL を直接実行します。テーブル名（prices_daily, raw_financials, raw_news 等）を想定しています。
- monitoring_db.init_monitoring_db() は起動時に呼び出すことでテーブルと必要カラムを確保します。既存 DB に対するマイグレーション処理（カラム追加）も組み込まれています。
- OpenAI を使う機能はレスポンスのバリデーションやリトライロジックが充実していますが、API のバージョンや SDK に依存する部分があるため実運用前に十分な検証を推奨します。
- .env のパースは export 形式やクォート・インラインコメントに対応しています。OS 環境変数を保護する仕組みがあるため、開発環境で .env.local を使って上書き管理できます。

ライセンス
---------
（本リポジトリにライセンスファイルがある場合はそちらを参照してください）

お問い合わせ / 開発
------------------
不具合報告や改善提案はリポジトリの Issue をご利用ください。開発に参加する場合は、まずはローカルで DuckDB / SQLite にテスト用データを入れて各モジュールを実行してみてください。