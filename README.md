KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python コードベースです。  
主要機能は以下のとおりです。

- 注文管理・発注（ExecutionEngine）
- ポートフォリオ構築（候補選定・配分・株数決定・リスク調整）
- リサーチ用ファクター計算（モメンタム・バリュー・ボラティリティ等）
- ニュース NLP によるセンチメント評価（OpenAI を利用）
- 市場レジーム判定（MA + マクロニュースセンチメント）
- 監視コンポーネント（システム・注文・リスク監視、LINE 通知、kill フラグ）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

特徴
----
- DuckDB / SQLite を利用したデータ操作と永続化
- OpenAI（gpt-4o-mini 等）との連携によるニュースセンチメント評価
- paper_trading モードで本番 DB と分離して動作可能
- モジュールは純粋関数設計や冪等操作を意識した実装（再起動耐性を重視）
- プロセス優先度や CPU affinity 設定ユーティリティを内蔵

必要条件（想定）
----------------
- Python 3.10+（typing union 表記等を使用）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード使用時)
  - openai (AI 機能を使う場合)
- SQLite（標準で利用可能）

インストール（例）
-----------------
仮想環境を作成してからインストールすることを推奨します。

1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要ライブラリをインストール（代表的なパッケージ）:
   - pip install duckdb psutil requests streamlit openai

（プロジェクトで requirements.txt がある場合はそれを利用してください）

環境変数と設定
--------------
このプロジェクトは .env / .env.local あるいは環境変数で設定を読み込みます（config.Settings）。自動読み込みはルートの .git または pyproject.toml を起点に行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（抜粋）
- KABUSYS_ENV: 起動環境（development | paper_trading | live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須な場合）
- KABU_API_PASSWORD: kabuステーション API（必須な場合）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフォールバック挙動（instant|partial|never|reject）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

セットアップ手順（運用例）
------------------------
1. リポジトリをクローンし、プロジェクトルートに .env を配置（.env.example を参考に）。
2. 仮想環境を作成して依存ライブラリをインストール。
3. DuckDB / SQLite 用ディレクトリ data/ を作成（必要に応じて書き込み権限を設定）。
4. データの初期ロード（価格データや raw_news、raw_financials 等）を行う（本 README では詳細記載なし）。

使い方（実行例）
----------------

- 実行エンジン（発注処理）を起動:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV が paper_trading の場合は MockBroker として paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

- 監視ループ（SystemMonitor のみ）を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - run_monitoring は監視用 DB に対して常に sqlite_path（本番パス）を使用します（KABUSYS_ENV に依存せず）。

- Streamlit ダッシュボード（監視 UI）を起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（SQLite DB ファイルパス、PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可）

- AI 機能（スクリプトや REPL からの利用）:
  - 例: ニュースのスコア付け
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 1), api_key="YOUR_OPENAI_KEY")
  - 市場レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")

内部ユーティリティ
------------------
- プロセス優先度設定: kabusys.utils.process_priority.set_process_priority("high"|"normal"|"low")
- 設定ロード: kabusys.config.Settings を経由して .env / 環境変数を参照
- 監視 DB 初期化: kabusys.monitoring.monitoring_db.init_monitoring_db(sqlite_conn)

主要機能一覧（ファイルベース）
----------------------------
- run_execution.py: ExecutionEngine の起動スクリプト（発注エンジン）
- run_monitoring.py: SystemMonitor のポーリング起動スクリプト
- config.py: 環境変数 / .env 読み込みと Settings
- ai/
  - news_nlp.py: raw_news の解析 → OpenAI による銘柄別センチメント評価、ai_scores 書込
  - regime_detector.py: MA とマクロニュースで市場レジーム判定
- monitoring/
  - monitoring_db.py: SQLite による監視ログの永続化 API
  - system_monitor.py: CPU/メモリ/Disk/プロセス監視とデータ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常価格の検出
  - risk_monitor.py: ドローダウン・ポジション上限監視、Dashboard 更新
  - kill_switch.py: kill.flag の書き込みによる停止トリガ
  - alert_manager.py: LINE 通知（プッシュ）
  - monitoring_engine.py: 複数 Monitor を束ねた実行ループ
  - streamlit_dashboard.py: Streamlit による監視ダッシュボード
- execution/
  - reconciler.py: 起動時の注文・ポジションのリコンシリエーション
  - order_manager.py, order_repository.py, order_record.py 等（注文フロー実装）
- portfolio/
  - portfolio_builder.py: 候補選定 + ウェイト計算
  - position_sizing.py: 発注株数計算（リスクベース / 等配分 / スコア配分）
  - risk_adjustment.py: セクターキャップ、レジーム乗数
- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC・統計サマリー等
- tools/
  - paper_verification_report.py: paper_trading の検証レポート生成
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定

ディレクトリ構成（抜粋）
---------------------
src/
  kabusys/
    __init__.py
    config.py
    run_execution.py
    run_monitoring.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      reconciler.py
      order_manager.py
      order_repository.py
      ... (その他発注関連)
    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    tools/
      __init__.py
      paper_verification_report.py
    utils/
      __init__.py
      process_priority.py
    ...（data / strategy 等 他モジュールが想定）

運用上の注意
------------
- .env の内容には API キーや秘密情報が含まれるため取り扱いに注意してください。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使います（意図的な挙動）。
- OpenAI を利用する機能は API レート制限やコストに注意してください（内部でリトライ実装あり）。
- paper_trading モードは本番 DB と完全分離されるよう設計されています。テストや検証時は KABUSYS_ENV=paper_trading を利用してください。
- kill.flag による停止は冪等であり、既に存在するフラグの上書きは行いません。

貢献
----
バグ報告やプルリクエストは歓迎します。コードスタイルやテストの追加、ドキュメント改善にご協力ください。

ライセンス
----------
（本リポジトリのライセンス情報をここに記載してください）

付録：よく使うコマンドまとめ
---------------------------
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

以上。README の内容や補足の追記・修正希望があれば教えてください。