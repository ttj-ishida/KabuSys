# KabuSys

KabuSys は日本株の自動売買システムです。本リポジトリは売買実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ/ファクター計算、ニュースの NLP スコアリングなどの主要コンポーネントを含みます。

以下はコードベース（src/kabusys）の主要機能と使い方のまとめです。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 実行方法（使い方）
- 環境変数（主要）
- ディレクトリ構成

---

プロジェクト概要
- 日本株自動売買システム（KabuSys）の内部ライブラリ群と起動スクリプトを含みます。
- 主な役割:
  - ExecutionEngine: ブローカーとやり取りして注文を作成・管理・実行する。
  - Monitoring: システム状態（CPU/メモリ/ディスク）、注文滞留、約定異常、ドローダウンなどをポーリングしてログ・アラート・キルスイッチを提供する。
  - Portfolio construction: 候補選定、重み計算、ポジションサイズ決定、セクター制約適用などの純粋関数群。
  - Research: DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）や IC 計算。
  - AI モジュール: OpenAI を使ったニュースのセンチメントスコアリング（news_nlp）と市場レジーム判定（regime_detector）。
  - Tools: Paper Trading 検証レポート生成、監視用 Streamlit ダッシュボード等。

機能一覧（抜粋）
- 起動スクリプト
  - run_execution.py: ExecutionEngine を開始（KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading DB を使用）
  - run_monitoring.py: SystemMonitor 単体の簡易ポーリング起動（MONITOR_POLL_INTERVAL で間隔指定）
- 監視（monitoring）
  - SystemMonitor: プロセス PID ファイル監視、データ鮮度、CPU/メモリ/ディスク計測
  - TradeMonitor: 注文滞留（stale order）、約定価格異常検出
  - RiskMonitor: ドローダウン検出、ポジション数上限監視、dashboard 更新と risk_logs 記録
  - KillSwitch: 指定条件で data/kill.flag を作成して ExecutionEngine に停止シグナルを送る
  - AlertManager: LINE Messaging API を用いた通知（クールダウン管理）
  - MonitoringDB: SQLite ベースの永続化（system_status / trade_logs / positions / risk_logs / dashboard）
  - streamlit_dashboard.py: 監視データを可視化する Streamlit アプリ
- 実行（execution）
  - Reconciler: 再起動時の注文・ポジション照合
  - OrderManager / OrderRepository: 注文状態管理と DB 永続化
  - BrokerFactory: 実ブローカー or MockBroker の生成（env に依存）
- ポートフォリオ（portfolio）
  - 候補選定、等配分・スコア配分、リスク乗数、セクターキャップ、ポジションサイズ算出（lot 単位で丸め、aggregate cap のスケールダウン等）
- リサーチ（research）
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算 / IC / 統計サマリー等
- AI（ai）
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、銘柄別に -1.0〜1.0 のスコアを ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime を決定し永続化

セットアップ手順（開発環境向け）
1. リポジトリをクローンし、仮想環境を作成・有効化します（任意）。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - 必須の主要パッケージ（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit（ダッシュボードを使う場合）
   - もし requirements.txt / pyproject があるならそちらを利用してください。
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. データディレクトリの準備
   - デフォルトはプロジェクト内の data/ を使用するようになっています（SQLite / DuckDB ファイルや PID / flag をこの下に置きます）。
   - 必要なら作成:
     - mkdir -p data

4. 環境変数（.env）
   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.env.local は上書き）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数は次節参照。実行前に必要なキー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY など）を設定してください。

主要な環境変数（抜粋）
- KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - paper_trading のとき run_execution は MockBroker を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込む
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールを使う際に必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用（任意）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- SQLITE_PATH: data/monitoring.db（監視用 DB、monitoring は env にかかわらず本番 sqlite_path を使用）
- DUCKDB_PATH: data/kabusys.duckdb（リサーチ・price 等の永続化）
- PID_FILE_PATH: data/execution.pid（ExecutionEngine の PID ファイル）
- KILL_FLAG_PATH: data/kill.flag（KillSwitch が書き込む停止フラグ）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

実行方法（例）
- 監視プロセスを起動（プロダクションの監視には run_monitoring を使う）
  - MONITOR_POLL_INTERVAL を変更してポーリング間隔指定可能（秒）
  - python -m kabusys.run_monitoring
  - run_monitoring はプロセス優先度を上げ、monitoring DB（settings.sqlite_path）と DuckDB に接続して SystemMonitor の poll ループを実行します。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- 実行エンジンを起動
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading DB に記録される（本番 DB と分離）。
  - 例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - run_execution は高優先度設定、DB 初期化、リコンシリエーション、ExecutionEngine の起動を行い、data/execution.pid を利用 / 管理します。
  - 停止: data/stop_requested.flag を作成すると安全に停止を試みます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - monitoring.db を読み取り専用で開いてダッシュボード表示をします（MonitoringEngine を先に起動してデータを作成してください）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（プログラム呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None) — OpenAI API キーは引数または OPENAI_API_KEY 環境変数で提供
  - regime_detector.score_regime(conn, target_date, api_key=None)

注意点 / 実運用のポイント
- Monitoring の DB 初期化は init_monitoring_db() により自動で行われます（テーブル作成・マイグレーション含む）。
- run_monitoring は MONITOR_POLL_INTERVAL（環境変数）で間隔を上書きできます。値が不正だとデフォルト 60 秒にフォールバックします。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用するため本番 DB と分離されます。
- kill/stop フラグ:
  - data/kill.flag: KillSwitch が書き込む停止理由（Execution 停止トリガ）
  - data/stop_requested.flag: run_* スクリプトが監視している「停止要求」フラグ（手動停止用）
- PID ファイルの stale 判定: SystemMonitor は PID ファイルを確認し、既に終了している PID の場合は stale として削除・アラートします。
- OpenAI 利用: API 呼び出しはリトライ、バリデーション、レスポンス検査、スコアクリップ等の実装が入っています。API キーの管理に注意してください。
- 権限: プロセス優先度や CPU affinity の設定はプラットフォーム・権限に依存します。設定に失敗してもワーニングでスキップされます。

ディレクトリ構成（抜粋）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
    - run_monitoring.py        — SystemMonitor 単体起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（OpenAI + MA200）
      - __init__.py
    - monitoring/
      - monitoring_db.py       — SQLite テーブル定義・MonitoringDB API
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
      - __init__.py
    - execution/
      - reconciler.py
      - order_manager.py
      - order_repository.py     — （一部実装ファイルが存在）
      - execution_engine.py    — （実行コア）
      - broker_factory.py
      - order_record.py
      - broker_api.py
      - ...
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
- data/                        — デフォルトの DB / PID / flag 保存先（手動作成を推奨）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

補足（開発者向け）
- .env のパースは config._parse_env_line にて細かく実装済みで、export 句やクォート内のエスケープ、コメント等に対応します。
- DuckDB を使ったリサーチ関数群は prices_daily / raw_financials 等のテーブルを前提にしています（外部 API 呼び出しは行わない設計）。
- tests（単体テスト）がある場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを無効化すると安定します。

問題や追加情報が必要であれば、どの機能（監視、実行、AI、ポートフォリオ等）について詳しく知りたいか教えてください。README の補足（インストール手順の詳細、例 .env.example、実行フロー図 など）を作成します。