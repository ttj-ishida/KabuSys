KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の軽量実装です。本リポジトリは以下の主要機能を含みます。

- 注文発行・管理を行う ExecutionEngine（ブローカ抽象化を通じた実行）
- 監視（System / Trade / Risk）およびアラート（LINE 送信）
- Paper Trading 用の分離 DB と検証レポートツール
- DuckDB を用いたファクター計算／研究モジュール（Momentum／Value／Volatility 等）
- ニュースの NLP（OpenAI）を使ったセンチメント集計と市場レジーム判定
- Streamlit ベースの監視ダッシュボード
- プロセス優先度／CPU affinity のユーティリティ等のユーティリティ群

特徴
----
- 明確に分離された Paper Trading（data/paper_trading.db）と本番監視 DB（data/monitoring.db）
- DuckDB を用いた大容量時系列データの分析・ファクター計算
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（retry・バッチ処理・JSON バリデーション実装）
- 監視ループ（MonitoringEngine）と ExecutionEngine のプロセス管理（PID / kill フラグ）
- Streamlit による簡易ダッシュボードで稼働状況を可視化
- フェイルセーフ（API リトライ、エラー時のフォールバック処理）設計

セットアップ手順
----------------
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 環境（仮想環境）を作成して有効化
   - 推奨: Python 3.10+

   例:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 主な依存（コード参照）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit

   例:
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があればそれを利用してください）

4. data ディレクトリ作成（必要に応じて）
   - mkdir -p data

5. 環境変数を準備
   - プロジェクトルートに .env / .env.local を置けます（自動ロードされます）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 例の最小設定（.env）:

     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_api_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PAPER_FILL_MODE=instant
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     LOG_LEVEL=INFO

   - 詳細は Settings クラス（src/kabusys/config.py）を参照してください。

主な環境変数（抜粋）
-------------------
- KABUSYS_ENV: 起動環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（既定: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行管理用のファイルパス

使い方
-----

起動スクリプト
- 監視（SystemMonitor ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが終了します（run_monitoring 内で参照）。

- ExecutionEngine（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中に同ファイルを作成すると安全に停止をトリガーします。
  - PID ファイルはデフォルト data/execution.pid に書き出されます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System を表示します。

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で変更可能。
  - レポートでは稼働率、注文成功率、送信率、P95 レイテンシ等を算出して PASS/FAIL を判定します。

AI 関連
- ニュース NLP（銘柄別センチメント）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定
  - 実装は gpt-4o-mini を想定。バッチ処理、リトライ、JSON バリデーションを行います。

停止・キルスイッチ
- kill.flag（Settings.kill_flag_path、既定 data/kill.flag）
  - KillSwitch によりリスク条件（ドローダウンやポジション数超過）が検出されたときに書き込まれます。Execution 側はこのフラグを検出して安全に停止する設計です。
- stop_requested.flag（プロジェクト内 data/stop_requested.flag）
  - run_monitoring/run_execution で監視され、ファイルが存在するとループを抜けます（手動停止用）。

注意点 / 設計上の要点
- 環境自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env と .env.local を自動で読み込みます。OS 環境変数は .env に上書きされません。.env.local は上書きします。
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading の分離:
  - Paper Trading モード（KABUSYS_ENV=paper_trading）は発注処理をモック化し、データを paper_trading_sqlite に分離します。監視（monitoring_db）は環境にかかわらず本番 sqlite_path を使用する点に注意してください。
- OpenAI 呼び出し:
  - news_nlp と regime_detector で OpenAI を呼びます。429 / タイムアウト / 5xx のリトライ実装あり。API キーの管理に注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は必要なテーブルとインデックスを冪等に作成し、一部カラム（peak_value, latency_ms）を既存 DB に追加する簡易マイグレーション処理を含みます。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / 設定管理
    - run_monitoring.py             — SystemMonitor ポーリングループ起動
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート CLI
    - ai/
      - news_nlp.py                 — ニュース NLP（センチメント）処理
      - regime_detector.py          — 市場レジーム判定（MA + マクロセンチメント）
    - monitoring/
      - monitoring_db.py            — SQLite 永続化層（system_status / trade_logs / ...）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - ...（broker_factory, execution_engine, order_repository など）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - process_priority.py
    - data/ (実行時に使用するディレクトリ例)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - kill.flag
      - stop_requested.flag

開発者向けメモ
---------------
- ログレベルは Settings.log_level または logging.basicConfig の設定で制御できます。
- process_priority.set_process_priority() は起動時に呼ばれており、Windows/Linux の差分を吸収します（権限による失敗は警告で無視されます）。
- DuckDB 接続は研究／AI モジュールで SQL を直接実行する設計です。prices_daily / raw_financials / raw_news 等のテーブルスキーマに依存します。
- 単体テストや CI では .env の自動読み込みを無効化するか、テスト用の .env を用意してください。

ライセンス / 責務
-----------------
（このリポジトリのライセンスと法的注意書きがあればここに記載してください）

以上がこのコードベースの概要と利用方法のまとめです。必要であれば各モジュール（ExecutionEngine の起動方法、Broker 実装の差し替え、DuckDB のテーブルスキーマなど）についてより詳細なドキュメントを追加します。どの部分を深掘りしますか？