README
======

概要
----
KabuSys は日本株自動売買のためのモジュール群です。本リポジトリは以下の機能を含みます: データ処理（DuckDB）、ファクター計算・研究、ポートフォリオ構築、発注管理（ExecutionEngine / Broker 抽象）、監視（MonitoringEngine / system/trade/risk モニタ）、及び AI を用いたニュースセンチメント / レジーム判定のユーティリティ群。設計は本番環境・ペーパートレード環境を分離し、安全性（リコンシリエーション・キルスイッチ・リスク監視）を重視しています。

主な特徴
--------
- モジュール分割されたポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）
- OpenAI を使ったニュース NLP（銘柄別センチメント）とマクロセンチメントによる市場レジーム判定
- ExecutionEngine（発注・リスク管理・再同期処理）と Reconciler（起動時の自動復旧）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor）と通知（LINE）機能
- Streamlit ダッシュボードによる監視表示
- Paper trading 用の専用 DB と検証レポート生成ツール

動作要件（推奨）
----------------
- Python 3.10 以上（型ヒントで | 演算子を使用）
- 必要なパッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
- SQLite（標準ライブラリ）

セットアップ手順
----------------
1. リポジトリをクローン・作業ディレクトリへ移動:
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール:
   - pip install duckdb psutil requests streamlit openai

   （実際の requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数 / .env の設定:
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS 環境変数を優先）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   主要な環境変数例:
   - KABUSYS_ENV=development | paper_trading | live
     - paper_trading のときは paper_trading 専用 SQLite に記録され、本番 DB と分離されます。
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
   - PID_FILE_PATH (デフォルト: data/execution.pid)
   - KILL_FLAG_PATH (デフォルト: data/kill.flag)
   - PAPER_FILL_MODE (paper_trading のフィルモード: instant|partial|never|reject)
   - LOG_LEVEL (DEBUG/INFO/...)
   - MONITOR_POLL_INTERVAL (監視ループの秒間隔、デフォルト 60)

   サンプル .env（例）:
   - KABUSYS_ENV=paper_trading
   - JQUANTS_REFRESH_TOKEN=your_token
   - KABU_API_PASSWORD=your_password
   - OPENAI_API_KEY=sk-xxxx
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db

5. データディレクトリ作成:
   - mkdir -p data

使い方
------
- 監視ループを起動（SystemMonitor 単体起動スクリプト）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で指定可能（例: MONITOR_POLL_INTERVAL=120）

  監視は Settings から sqlite_path を読み、本番用の SQLite にログを保存します（環境に関係なく本番 sqlite_path を使用する設計）。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution

  KABUSYS_ENV=paper_trading の場合は Broker の Factory が MockBrokerClient を返し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。起動時に PID ファイル（Settings.pid_file_path）を使用してプロセス生存をトラッキングします。

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

  引数 --db で別ファイルを指定できます。ダッシュボードは読み取り専用 URI で DB を開きます。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合: --db path/to/paper_trading.db

- AI 関連（プログラムから呼ぶ）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を参照し、銘柄別センチメントを ai_scores に書き込みます。
    - api_key を None にすると環境変数 OPENAI_API_KEY を使用します（未設定なら ValueError）。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 1321 の MA200 乖離とマクロニュースを合成して market_regime テーブルへ書き込みます。

- Kill Switch / フラグ:
  - KillSwitch は監視側で評価し、条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。
  - ExecutionEngine 側は起動時に KILL_FLAG_CLEAR_ON_START が 1 に設定されていればフラグをクリアする挙動が期待されます（Settings で構成）。

設定 / 動作に関する注意
-----------------------
- .env の読み込み:
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
  - .env → .env.local の順で読み込みされ、.env.local は .env を上書きします（ただし OS 環境変数は保護されます）。

- DB 初期化:
  - run_monitoring/run_execution は起動時に init_monitoring_db() を呼び出して監視用テーブルを作成（冪等）します。data ディレクトリと DB ファイルの権限に注意してください。

- Paper trading 分離:
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離されます。

- プロセス優先度:
  - run_monitoring と run_execution は起動時に set_process_priority("high") を呼びます。psutil による権限不足等で設定できない場合は警告ログに留まります。

- AI 呼び出しの堅牢性:
  - OpenAI 呼び出しはレート・ネットワークエラー・5xx に対するリトライ（指数バックオフ）を行い、失敗時はフォールバック（例: macro_sentiment = 0）します。API キーは扱いに注意してください。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py — .env / 環境変数管理（Settings クラス）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（銘柄センチメント→ai_scores）
  - regime_detector.py — マクロ + ETF MA200 によるレジーム判定
- monitoring/
  - monitoring_db.py — SQLite 監視ログ層（init + CRUD）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねてポーリング
  - alert_manager.py — LINE 通知機能
  - kill_switch.py — kill.flag 制御
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - reconciler.py — 起動時の発注・ポジション再同期
  - order_manager.py — 発注フロー管理（OrderManager）
  - （その他 execution 関連モジュール: broker_factory, execution_engine, order_repository 等が存在します）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・リスク制限・単元丸め
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - process_priority.py — プロセス優先度 & CPU affinity ユーティリティ

補足（開発者向け）
-----------------
- コード設計はフェイルセーフ性と冪等性を重視しています（DB マイグレーション、部分失敗時の保護、リトライ戦略など）。
- DuckDB / SQLite のスキーマやテーブル操作はモジュール内に定義されています（monitoring_db.init_monitoring_db 等）。
- テストを書く際は Settings の自動 .env 読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化すると便利です。また、AI 呼び出し部分は _call_openai_api をモック可能なように作られています。

ライセンス / 貢献
-----------------
（必要に応じてここにライセンスと貢献方法を追記してください）

以上。プロジェクト固有の運用手順や本番移行ルール（資金管理や Broker 設定など）は別途運用ドキュメントにまとめることを推奨します。