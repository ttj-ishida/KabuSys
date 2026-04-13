KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向け自動売買システム「KabuSys」の主要モジュール群を含みます。  
以下はコードベースの概要、機能、セットアップと実行方法、ディレクトリ構成の説明です。

プロジェクト概要
----------------
KabuSys は日本株のシグナル生成〜発注〜監視までを想定したモジュール群です。主な機能は次のとおりです。

- 取引実行（ExecutionEngine / OrderManager / Broker インタフェース）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- ポートフォリオ構築（候補選定・重み・ポジションサイズ）
- リサーチ（ファクター計算・特徴量解析）
- AI を使ったニュースセンチメント評価（OpenAI 経由）
- 運用検証ツール（Paper Trading 検証レポート）
- Streamlit ベースの監視ダッシュボード

設計上のポイント
- 設定は環境変数あるいは .env / .env.local から読み込み（自動ロードはプロジェクトルートを .git または pyproject.toml で検出）。
- Paper Trading（KABUSYS_ENV=paper_trading）は実アカウントと完全に分離され、専用の SQLite DB を使用。
- 監視・ログ永続化には SQLite（monitoring.db）を使用。分析用には DuckDB（kabusys.duckdb）を利用。
- OpenAI API を使う機能は API キーを必要とし、失敗に対してはフェイルセーフ設計（必要に応じてスキップやフォールバック）になっています。

主な機能一覧
----------------
- run_monitoring.py
  - SystemMonitor を定期ポーリングして system_status/risk_logs/trade_logs 等に記録
  - MONITOR_POLL_INTERVAL でポーリング間隔を指定可能（デフォルト 60 秒）
  - プロセス優先度を "high" に設定（可能な環境で）
- run_execution.py
  - ExecutionEngine の起動エントリポイント
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録
  - 起動時に各コンポーネント（OrderRepository, OrderManager, RiskManager, Reconciler 等）を組み立ててセッション実行
- monitoring/*.py
  - MonitoringDB: 監視用 SQLite スキーマ初期化と CRUD
  - SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager, streamlit_dashboard
- execution/*
  - OrderManager, Reconciler 等。発注の状態管理と再同期ロジック
- portfolio/*
  - 候補選定、重み計算、セクター制限、ポジションサイズ計算などの純粋関数群
- research/*
  - ファクター計算（momentum / volatility / value）、将来リターン・IC 計算など
- ai/*
  - news_nlp: ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector: マクロセンチメント + 1321 の MA200 乖離で市場レジーム判定
- tools/paper_verification_report.py
  - Paper Trading 用の実行検証レポート生成（期間指定可）

セットアップ手順
----------------
1. Python 環境を用意
   - Python 3.9+（ソースは typing や型ヒントを多用しているため 3.9 以上が望ましい）

2. 依存パッケージのインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - それ以外に必要なパッケージがあればプロジェクトの requirements ファイルに合わせてください。

3. 環境変数・.env
   - プロジェクトルート（.git または pyproject.toml がある場所）に .env / .env.local を置けば自動で読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（主な例）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 外部 API 認証に必要
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知送信用
     - PAPER_FILL_MODE: paper_trading のフィルモード（instant/partial/never/reject）
   - .env のパーサはシェル風の記法（export 付き行やコメント・クォート等）に対応しています。

4. データディレクトリ作成
   - デフォルトの data/ ディレクトリを作成しておく:
     - mkdir -p data

使い方（代表的な実行コマンド）
----------------
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を変更可能: MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring

- Execution Engine 起動
  - python -m kabusys.run_execution
  - Paper Trading（テスト用）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper トレードは PAPER_TRADING_SQLITE_PATH（またはデフォルト data/paper_trading.db）へ書き込みます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード起動（監視 DB を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュール実行（プログラムから呼ぶ）
  - kabusys.ai.score_news(conn, target_date, api_key=...) など（OpenAI API キーが必要）

運用時の注意点
- プロセス優先度設定: 起動スクリプトは set_process_priority("high") を呼びます。権限不足や OS 非対応時は警告を出してスキップします（psutil に依存）。
- データ鮮度: SystemMonitor は DuckDB の prices_daily から最終日付を取得し鮮度チェックを行います。DuckDB に正しい価格データが必要です。
- KillSwitch: RiskMonitor が閾値超過を検出すると data/kill.flag を書き込み、Execution 側で停止シグナルとして扱う設計です（Execution 側は kill.flag を検出して停止する前提）。
- OpenAI 呼び出し: RateLimit や 5xx 等に対してエクスポネンシャルバックオフとリトライを実装していますが、API キーの管理に注意してください。
- Paper Trading は本番 DB と分離されます。必ず KABUSYS_ENV を適切に設定してください。

よく使う環境変数（まとめ）
- KABUSYS_ENV=development|paper_trading|live
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- OPENAI_API_KEY
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
- MONITOR_POLL_INTERVAL (秒、default: 60)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

ディレクトリ構成（主なファイル）
----------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env の自動読み込みと Settings クラス
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）

src/kabusys/monitoring/
- monitoring_db.py
  - SQLite スキーマ初期化と永続化 API（MonitoringDB）
- system_monitor.py、trade_monitor.py、risk_monitor.py
  - それぞれの監視ロジック
- monitoring_engine.py
  - 各 Monitor を束ねるエンジン
- kill_switch.py
  - kill.flag 書き込みロジック
- alert_manager.py
  - LINE へのアラート送信
- streamlit_dashboard.py
  - Streamlit ダッシュボード

src/kabusys/execution/
- order_manager.py、reconciler.py、（および他の execution 関連モジュール）
  - 発注管理、再同期ロジックなど

src/kabusys/portfolio/
- portfolio_builder.py、position_sizing.py、risk_adjustment.py
  - 候補選定・配分・セクター制限・ポジションサイズ計算など

src/kabusys/research/
- factor_research.py
  - momentum / volatility / value 等のファクター計算
- feature_exploration.py
  - 将来リターン計算、IC、統計サマリー

src/kabusys/ai/
- news_nlp.py
  - ニュースの LLM によるセンチメント評価と ai_scores への書き込み
- regime_detector.py
  - 市場レジーム判定（MA200 + マクロセンチメント）

src/kabusys/tools/
- paper_verification_report.py
  - Paper Trading の検証レポート生成

src/kabusys/utils/
- process_priority.py
  - プロセス優先度・CPU affinity 設定ユーティリティ

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報がリポジトリルートに含まれている場合はそちらを参照してください。
- コード修正・拡張を行う場合はユニットテストとローカルでの Paper Trading 環境で充分に検証してください。

補足（開発者向けメモ）
- .env パーサは export 付きの行、シングル/ダブルクォート、インラインコメント等の扱いに対応しており、OS 環境変数を保護する仕組みがあります。
- DuckDB を使ったクエリは価格データ（prices_daily）や raw_financials 等を前提にしています。研究モジュールを動かすには事前にデータ投入が必要です。
- OpenAI 周りのテストは API 呼び出しラッパーをモックすることで可能（モジュール内で _call_openai_api を patch する設計を用意）。

以上がこのコードベースの概要と基本的な使い方です。必要であれば、環境変数テンプレート（.env.example）や依存関係の requirements.txt のサンプル、運用手順（systemd / supervisor 用の unit ファイル例）なども作成できます。希望があれば追加で用意します。