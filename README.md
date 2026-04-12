KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を想定した Python コードベースです。
主な目的は以下の通りです。

- 日次・リアルタイムのファクター計算やリサーチ（DuckDB を利用）
- Execution エンジン（ブローカークライアント経由で発注管理・リコンシリエーション）
- Paper Trading モード（実環境と分離した SQLite へ記録）
- 監視（プロセス生存、データ鮮度、滞留注文、ドローダウン等の監視・通知）
- ニュース NLP による銘柄センチメント／市場レジーム判定（OpenAI を利用）
- Streamlit ダッシュボード、各種ツール（検証レポート生成など）

機能一覧
--------
主な機能（モジュール別）

- kabusys.config
  - .env 自動ロード（.env / .env.local）、環境変数ラッパー（Settings クラス）
  - KABUSYS_ENV（development / paper_trading / live）や各種パス・閾値設定

- kabusys.execution
  - ExecutionEngine（起動・セッション実行）
  - OrderManager / OrderRepository：発注状態管理・DB 永続化
  - Reconciler：起動時の自動復旧（ブローカーとローカルの同期）
  - BrokerClientFactory（paper_trading のときは MockBroker を使用）

- kabusys.monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセスの存在確認、データ鮮度チェック
  - TradeMonitor：滞留注文 / 約定異常価格の検出
  - RiskMonitor：ドローダウン・ポジション上限監視（ダッシュボード集計の更新）
  - KillSwitch：フラグファイルを作成して ExecutionEngine を停止させる
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringDB：SQLite ベースの監視ログ永続化（テーブル初期化・マイグレーション含む）
  - MonitoringEngine：上記モニターを束ねるポーリングループ
  - Streamlit ダッシュボード：監視結果の簡易可視化

- kabusys.portfolio
  - 銘柄選定、重み計算、セクターキャップ適用、ポジションサイジング等（純粋関数群）

- kabusys.research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC 計算、統計サマリー、zscore 正規化ユーティリティのエクスポート

- kabusys.ai
  - news_nlp.score_news：OpenAI を用いた銘柄別ニュースセンチメントの計算・ai_scores 書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースセンチメントを合成してレジーム判定

- tools
  - paper_verification_report：Paper Trading の検証レポートを生成（稼働率、注文成功率、レイテンシ等）

セットアップ手順
----------------
※ 以下はリポジトリの一例セットアップ手順です。実環境に合わせて調整してください。

1. Python 環境
   - Python 3.9+ を推奨（DuckDB・依存ライブラリの互換性に注意）

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （実際の依存はプロジェクトに合わせて requirements.txt を用意している場合はそれを使用してください）

4. 環境変数 / .env
   - プロジェクトルート（.git / pyproject.toml のあるディレクトリ）に .env を置くと自動ロードされます。
   - 主要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用、デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB、デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject", デフォルト "instant")
     - KABUSYS_ENV ("development" | "paper_trading" | "live")
     - LOG_LEVEL (DEBUG/INFO/...)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - MONITOR_POLL_INTERVAL (監視ループの秒間隔、デフォルト 60)
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動 .env ロードを無効化できます。

5. ディレクトリ / DB の作成
   - data フォルダを作成しておくと良いです（SQLite / DuckDB のデフォルトファイル位置）。
   - 初回起動時に monitoring の初期テーブルは自動作成されます（init_monitoring_db を参照）。

使い方
------
エントリポイントの例（モジュールとして実行）

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - 監視ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）
    - 監視 DB は KABUSYS_ENV に依らず本番 sqlite_path を使用します（監視は本番 DB を参照）

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します
    - 起動時にプロセス優先度を "high" に上げようとします（psutil の権限に依存）

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視用 SQLite（読み取り専用 URI）を指定

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH でデータベースファイルを指定可能（なければ PAPER_TRADING_SQLITE_PATH 環境変数やデフォルトを参照）

- AI / レジーム関連（スクリプト的利用）
  - kabusys.ai.score_news(conn, target_date, api_key) を呼び出す（DuckDB 接続が必要）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key)
  - これらは OpenAI API キー（OPENAI_API_KEY）を参照します。キーがない場合は例外になります。

運用時のポイント
- Paper Trading モードは本番データベースと完全に分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を利用）。
- kill.flag（Settings.kill_flag_path）へ書き込むと ExecutionEngine に停止シグナルを与える設計です（KillSwitch）。
- モニタリングは監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）を SQLite に保存します。
- MonitoringEngine / run_monitoring はプロセス優先度変更や duckdb 接続、SQLite の初期化等を行います。
- OpenAI 呼び出し箇所（news_nlp / regime_detector）はリトライやフォールバックを備え、API 失敗時は安全側の既定値（例: macro_sentiment=0）で継続します。

ディレクトリ構成（主要ファイル）
------------------------------
以下はコードベース内の主要なファイル・モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py

  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py

  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py

  - execution/
    - execution_engine.py (エンジン本体: 起動・セッション処理)
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - broker_factory.py
    - broker_api.py (プロトコル / エラー定義)

  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py

  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

  - data/
    - pipeline.py (DuckDB を使ったデータ取り出しユーティリティ)
    - stats.py (zscore 等)

  - tools/
    - __init__.py
    - paper_verification_report.py

  - utils/
    - __init__.py
    - process_priority.py

補足（設定・挙動の注意）
---------------------
- Settings クラスがプロジェクトの設定をラップしています。.env からの読み込みは自動（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- PAPER_FILL_MODE は paper_trading 時のモック執行挙動を決める（instant / partial / never / reject）。
- run_monitoring は Monitoring のために常に「本番」sqlite_path を使用します（監視は実データを監視するため）。
- sqlite / duckdb の接続は各スクリプトで自動的に初期化され、終了時にクローズされます。
- process_priority や cpu_affinity 設定は psutil によるため権限・OS に依存します。

ライセンス・貢献
----------------
この README はコードベースの動作説明を補助するための要約です。実際に運用する際はセキュリティ（API キー管理）、テスト、監査ログ、バックアップ等を別途整備してください。

問題や改善点があれば issue を立てるか、PR を送ってください。