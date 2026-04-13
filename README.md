# KabuSys — README (日本語)

本ドキュメントは、提供されたコードベースに基づく README です。KabuSys は日本株向けの自動売買・研究・監視ツール群を含んだパッケージです。ここではプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

注意：実際の運用では各種 API キーや証券会社（ブローカー）設定、環境固有の調整が必要です。本 README はリポジトリ内コードから推定できる利用方法・操作例を示しています。

目次
- プロジェクト概要
- 機能一覧
- 必要要件 / 依存関係
- セットアップ手順
- 環境変数（主なもの）
- 使い方（実行例）
  - Monitoring（監視）
  - Execution（発注エンジン）
  - Streamlit ダッシュボード
  - Paper Trading 検証レポート
  - AI（ニュース / レジーム判定）関数
  - 研究用関数（ファクター等）
- 主要コンポーネント説明（簡易）
- ディレクトリ構成

------------------------------------------------------------
プロジェクト概要
------------------------------------------------------------
KabuSys は日本株自動売買システムのライブラリ群です。主な目的は以下の通りです。
- 戦略のためのファクター計算・リサーチ（DuckDB を使った過去株価・財務データ処理）
- ポートフォリオ構築・ポジションサイジング・リスク調整の純粋関数群
- ExecutionEngine（発注エンジン）と発注管理（OrderManager、OrderRepository、Reconciler 等）
- 監視機能（SystemMonitor / TradeMonitor / RiskMonitor）、LINE 通知、kill flag による外部停止
- Paper Trading の分離（専用 SQLite DB）と検証レポート生成
- AI を使ったニュース NLP（OpenAI）や市場レジーム判定の補助

------------------------------------------------------------
機能一覧
------------------------------------------------------------
- ファクター計算（momentum / volatility / value）: kabusys.research.factor_research
- 将来リターン、IC、統計サマリー: kabusys.research.feature_exploration
- ポートフォリオ構築: select_candidates, calc_equal_weights, calc_score_weights
- ポジションサイジング（単元丸め・リスクベース等）
- セクター集中制限、レジーム乗数適用
- Execution 層（ブローカーファクトリ、OrderManager、Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）、監視用 DB（SQLite）への永続化
- Streamlit ダッシュボード（監視データ可視化）
- Paper Trading 用検証レポート生成スクリプト
- AI ベースのニュースセンチメント評価（OpenAI）と市場レジーム判定
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

------------------------------------------------------------
必要要件 / 依存関係（推定）
------------------------------------------------------------
最低限の主要依存モジュール（コードから推定）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード使用時）
- sqlite3（標準ライブラリ）
- その他パッケージ（プロジェクトの実装による）

インストール例（仮）:
- 仮想環境を作成して pip でインストールすることを推奨します。
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install -U pip
  - pip install duckdb psutil requests openai streamlit

（本リポジトリが pip パッケージとして整備されている場合は pip install -e . などを利用）

------------------------------------------------------------
セットアップ手順
------------------------------------------------------------
1. リポジトリをクローンして、仮想環境を作成・有効化する。
2. 依存パッケージをインストール（上記参照）。
3. 環境変数を設定する:
   - 簡単な方法: プロジェクトルートに .env または .env.local を置く。
   - Settings モジュールは自動的に .env を読み込みます（OS 環境変数が優先、.env.local は .env を上書き）。
   - 自動読み込みを無効化したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
4. データベースファイル:
   - DuckDB データ: data/kabusys.duckdb（Settings.duckdb_path のデフォルト）
   - 監視用 SQLite: data/monitoring.db（Settings.sqlite_path のデフォルト）
   - Paper Trading SQLite: data/paper_trading.db（紙トレード時）
   - これらのファイルはコード実行時に自動で作成・初期化されるテーブルがあります（monitoring_db.init_monitoring_db）。
5. 必要な API キー:
   - OpenAI を使う機能: OPENAI_API_KEY 環境変数（または関数引数）を設定
   - J-Quants / kabu API 等: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等（Settings を参照）

------------------------------------------------------------
環境変数（主なもの）
------------------------------------------------------------
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- DUCKDB_PATH: DuckDBファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード（instant | partial | never | reject。デフォルト "instant"）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 各種外部 API の認証情報

（Settings クラス内にさらにプロパティがあります。詳しくは src/kabusys/config.py を参照してください。）

------------------------------------------------------------
使い方（主な実行例）
------------------------------------------------------------

1) 監視ループの起動（Monitoring）
- 概要: SystemMonitor をポーリングして監視ログを monitoring.db に保存します。MONITOR_POLL_INTERVAL 環境変数で間隔を調整できます。
- 実行例:
  - python -m kabusys.run_monitoring
- 補足:
  - process 優先度を High に設定（psutil を使います）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しません）。

2) 実行エンジン起動（ExecutionEngine）
- 概要: 発注エンジンを起動します。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading.db に記録します（本番 DB と分離）。
- 実行例:
  - python -m kabusys.run_execution
- 補足:
  - process 優先度を High に設定します。
  - Paper Trading の場合は settings.is_paper が true になり PAPER_TRADING_SQLITE_PATH を使用します。
  - RiskManager などの初期設定値はコード内に記載（max_position_pct, max_utilization など）。

3) Streamlit ダッシュボード（監視可視化）
- 概要: monitoring.db を読み取り専用で表示する簡易ダッシュボード。
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 補足:
  - データベースが存在しない、または読み取り不可の場合はエラー表示されます。

4) Paper Trading 検証レポート生成
- 概要: Paper Trading の SQLite（デフォルト data/paper_trading.db）から期間指定で各種指標（稼働率、注文成功率、P95 レイテンシなど）を集計して標準出力にレポートします。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）

5) AI（ニュース NLP / レジーム判定）関数の利用
- news_nlp.score_news(conn, target_date, api_key=None)
  - raw_news / news_symbols を参照し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを ai_scores に書き込む。
  - api_key が渡されない場合は OPENAI_API_KEY 環境変数を参照。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込む。
- 注意:
  - OpenAI 呼び出しには API キーが必要です。失敗時はフェイルセーフ（0.0 等にフォールバック）する実装が多いですが、API キー未設定では ValueError が発生する関数もあります。

6) 研究用 API（ファクター・IC 等）
- kabusys.research.calc_momentum / calc_volatility / calc_value
  - DuckDB 接続と target_date を渡すとファクターを計算してリストを返します。
- feature_exploration.calc_forward_returns / calc_ic / factor_summary 等も利用可能。

------------------------------------------------------------
主要コンポーネント（簡易説明）
------------------------------------------------------------
- config.Settings: 環境変数読み込み・設定ラッパ。 .env / .env.local 自動読み込み機能あり。
- monitoring:
  - monitoring_db.py: 監視 DB 初期化と CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/プロセス・データ鮮度監視
  - trade_monitor.py: 滞留注文や約定異常の検出
  - risk_monitor.py: ドローダウン・ポジション数監視
  - kill_switch.py: kill.flag を書き込むことで ExecutionEngine 停止を促す
  - alert_manager.py: LINE push による通知（クールダウン管理あり）
  - monitoring_engine.py: 各 Monitor を束ねてポーリング（run / run_once）
  - streamlit_dashboard.py: Streamlit ベースの簡易ダッシュボード
- execution:
  - order_manager.py, order_repository.py, reconciler.py 等（発注・同期・再起動復旧ロジック）
- portfolio:
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（候補選定、配分、セクター制限、レジーム乗数）
- research:
  - factor_research.py, feature_exploration.py（ファクター生成、IC、統計）
- ai:
  - news_nlp.py: raw_news をまとめて OpenAI に投げ、銘柄ごとの ai_scores を書き込む
  - regime_detector.py: マクロニュース + ETF マクロ指標で市場レジーム判定
- utils:
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）

------------------------------------------------------------
ディレクトリ構成（コードベースの要約）
------------------------------------------------------------
（主要ファイルのみ抜粋、src/kabusys 以下）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
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
      - order_manager.py
      - reconciler.py
      - (その他 broker / engine / repository 関連ファイル)
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
    - data/ (推奨配置; 実際はプロジェクトルートに data/ を配置)
      - kabusys.duckdb
      - monitoring.db
      - paper_trading.db

（上記はリポジトリ中の主要モジュールを反映しています。実際の追加ファイルや未列挙のモジュールが存在する場合があります。）

------------------------------------------------------------
運用上の注意 / Tips
------------------------------------------------------------
- Paper Trading は本番データベースと完全に分離する設計です（PAPER_TRADING_SQLITE_PATH を使います）。
- monitoring_db.init_monitoring_db は冪等的にテーブルを作成し、既存 DB に対する軽微なマイグレーション（カラム追加）を行います。
- pid_file（ExecutionEngine）と kill.flag により外部から安全にプロセス制御を行います。kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START で制御できます。
- MONITOR_POLL_INTERVAL は環境変数で秒数を指定可能（正の整数）。不正値はデフォルト 60 秒にフォールバックします。
- OpenAI 呼び出し部分はリトライやバックオフの実装を持ちますが、API レートやコストに注意してください。
- process 優先度設定は psutil の API を使います。権限が足りない場合は警告が出ますが処理は継続されます。

------------------------------------------------------------
最後に
------------------------------------------------------------
この README はコードベースから読み取れる仕様を元に作成しました。実際の利用・本番運用にあたっては、各種設定（API キー、ブローカー設定、資金/リスクパラメータ）を慎重に検討し、テスト環境で十分検証を行ってください。

質問や README の補足を希望される場合は、どの項目を詳しく知りたいかを教えてください。