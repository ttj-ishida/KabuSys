README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視ツール群を含む小規模なプロジェクトです。本リポジトリは以下の主要機能を持ちます。

- 注文の管理と実行（ExecutionEngine、OrderManager、Broker クライアント）
- 監視（System / Trade / Risk の監視、LINE 通知、kill flag による安全停止）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ決定）
- リサーチ（ファクター計算、将来リターン、IC 等の統計）
- AI 支援（ニュースの NLP スコアリング、マクロレジーム判定）
- 運用補助ツール（Paper Trading の検証レポート生成、Streamlit ダッシュボード）

主な特徴
--------
- 環境別動作: KABUSYS_ENV により development / paper_trading / live を切り替え。
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
- 監視:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine。
  - kill.flag による ExecutionEngine 停止（KillSwitch）と LINE 通知（AlertManager）。
  - monitoring の永続化は SQLite（data/monitoring.db がデフォルト）。
- AI:
  - OpenAI（gpt-4o-mini を想定）を用いたニュースセンチメント（ai_scores）とレジーム判定（market_regime）。
  - API 呼び出しのリトライ、バッチ処理、レスポンス検証を実装。
- ポートフォリオ構築:
  - 候補選定、等金額／スコア加重配分、リスク調整（セクターキャップ、レジーム乗数）、単元株丸め、リスクベースの株数計算を提供。
- リサーチ:
  - DuckDB を使用して prices_daily / raw_financials などからファクターを計算（モメンタム、ボラティリティ、バリュー等）。
- 運用ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
  - Streamlit ベースの監視ダッシュボード（監視 DB を read-only で表示）。

セットアップ手順
--------------
前提:
- Python 3.8+（プロジェクトに合わせて適宜設定）
- OS により psutil の一部機能で権限が必要になることがあります。

1. リポジトリをクローン
   - git clone ... (省略)

2. 依存パッケージをインストール
   - 例（pip）:
     - pip install duckdb psutil requests openai streamlit

   ※ 実際のプロジェクトでは requirements.txt / poetry 等がある想定です。適宜追加してください。

3. 環境変数 / .env
   - プロジェクトルートに .env（または .env.local）を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（Settings により参照されるもの）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY
   - 任意（通知や設定）:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager 用）
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - PAPER_FILL_MODE (instant | partial | never | reject) — paper_trading の約定挙動
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
     - SQLITE_PATH — 監視用 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

4. データディレクトリ
   - data/ 以下に DB ファイルや PID / flag ファイルが作成されます（自動生成）。
   - 主要ファイル:
     - data/monitoring.db (SQLite, 監視ログ)
     - data/paper_trading.db (paper_trading 用 SQLite)
     - data/kabusys.duckdb (DuckDB)
     - data/execution.pid (ExecutionEngine の PID)
     - data/kill.flag (KillSwitch によって書き込まれる停止フラグ)
     - data/stop_requested.flag (外部停止フラグ、run_monitoring/run_execution が参照)

使い方（実行例）
----------------

1. 監視プロセス起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 動作概要:
     - プロセス優先度を "high" に設定（可能な範囲で）。
     - 設定から sqlite_path を読み取り、monitoring テーブルを初期化します（init_monitoring_db）。
     - SystemMonitor を定期（MONITOR_POLL_INTERVAL 秒）に実行。
     - data/stop_requested.flag を検知するとループを終了。
   - ポーリング間隔:
     - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（1 以上、デフォルト 60 秒）。

2. 実行エンジン起動（Execution）
   - python -m kabusys.run_execution
   - 動作概要:
     - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して paper_trading_db に記録（本番 DB と完全分離）。
     - 各コンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立て、ExecutionEngine.run_session をスレッドで実行。
     - data/stop_requested.flag を検知するとエンジン停止を試みる。
     - 実行中は data/execution.pid に PID が書かれる（設定でパス変更可）。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
   - 出力: stdout にレポート（稼働率、注文成功率、レイテンシ等）を表示します。

4. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を read-only で開き、Overview / Positions / Orders / System を可視化します。

5. AI 機能の使用例（プログラム的に）
   - ニュースのスコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, date(2026, 4, 1), api_key="...")

   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, date(2026, 4, 1), api_key="...")

注意点・運用メモ
----------------
- Monitoring（run_monitoring）は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 sqlite_path）を使用します。監視データは環境を問わず同一の監視 DB に記録されます。
- Execution は paper_trading 環境であれば paper_trading_db を使用（本番 DB と分離）。
- kill.flag / stop_requested.flag:
  - KillSwitch は条件成立時に data/kill.flag を書き込み、Execution エンジンに停止シグナルを送ります。
  - 管理者が手動で停止する場合は data/stop_requested.flag を作成すると監視プロセス・エンジンが検出して安全停止します。
- プロセス優先度設定や CPU affinity は psutil を使用します。権限がないと警告のみで続行します。
- OpenAI API を利用する機能は API キーが必要です。失敗時はフェイルセーフ（多くの場合スコア 0.0 を利用して継続）を採用していますが、運用前にキーの設定と制限を確認してください。
- .env のパースは bash 風のフォーマットをサポートしています（export 形式やクォート、コメント処理等）。

ディレクトリ構成
----------------
主要ファイル・モジュールを抜粋して示します（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（.env 自動ロード）
  - run_monitoring.py            — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py           — SQLite ベースの永続化層（テーブル初期化・CRUD ラッパ）
    - system_monitor.py          — システム / データ鮮度監視
    - trade_monitor.py           — 注文滞留・約定異常監視
    - risk_monitor.py            — ドローダウン・ポジション上限監視
    - kill_switch.py             — kill.flag 管理
    - alert_manager.py           — LINE 通知ラッパ
    - monitoring_engine.py       — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py     — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py        — （実行エンジン本体, ファイルは一部のみ掲載）
    - broker_factory.py
    - broker_api.py
    - ... (その他 Execution 関連モジュール)
  - portfolio/
    - __init__.py
    - portfolio_builder.py       — 候補選定・重み計算
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
    - position_sizing.py         — 株数決定・スケール調整・単元丸め
  - research/
    - __init__.py
    - factor_research.py         — モメンタム／ボラ／バリュー等の計算
    - feature_exploration.py     — 将来リターン / IC / 統計
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py         — マクロ + MA200 によるレジーム判定
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート出力スクリプト

付録：よく使う環境変数例 (.env 例)
---------------------------------
例:
    KABUSYS_ENV=development
    JQUANTS_REFRESH_TOKEN=xxxx
    KABU_API_PASSWORD=xxxx
    OPENAI_API_KEY=sk-...
    LINE_CHANNEL_ACCESS_TOKEN=xxxx
    LINE_USER_ID=Uxxxxxxxxxxxxxxxxx
    SQLITE_PATH=data/monitoring.db
    DUCKDB_PATH=data/kabusys.duckdb
    PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    MONITOR_POLL_INTERVAL=60

サポート・拡張
---------------
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）はプロジェクト外で用意する必要があります（データ取得パイプラインは kabusys.data.pipeline 等に実装想定）。
- Broker クライアント実装（実ブローカー接続 / Mock）は BrokerFactory を介して差し替え可能です。
- 監視ルールやアラートの閾値は Settings 経由で環境変数化されており、運用時に調整できます。

以上。README の内容やコマンドに関して不明な点、または追加したいセクション（例: API 仕様、DB スキーマの詳細、運用手順書など）があれば教えてください。必要に応じて追記・整形します。