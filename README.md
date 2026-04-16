KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を行うための小規模なフレームワークです。本コードベースは次の主要機能を含みます。

- 実行エンジン（ExecutionEngine）: ブローカー連携、注文管理、リスク管理、再起動時のリコンシリエーション等
- 監視機能（MonitoringEngine）: システム稼働監視、注文監視、リスク監視、LINE 通知、kill フラグによる停止制御
- ポートフォリオ構築ロジック（候補選定・重み付け・ポジションサイズ計算・セクター制限等）
- 研究モジュール（ファクター計算、特徴量探索、フォワードリターン、IC 計算）
- AI モジュール（ニュース NLP による銘柄センチメント評価、レジーム検知）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）
- ユーティリティ（環境設定読み込み、プロセス優先度 / CPU affinity 設定 等）

特徴一覧
--------
主な機能・設計方針（抜粋）:

- 環境に応じた分離:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を用い、paper_trading 用 SQLite DB（デフォルト data/paper_trading.db）へ書き込む。
  - 監視（Monitoring）は環境に関わらず本番用 sqlite_path を参照して監視ログを記録する。
- フェイルセーフ:
  - API 呼び出し失敗時は安全側にフォールバック（例: LLM の失敗はスコア=0.0 等）し、処理を継続する設計。
- 冪等性 / マイグレーション対応:
  - monitoring DB 初期化は冪等（init_monitoring_db）。必要な列がなければ ALTER で追加する軽いマイグレーションを含む。
- テストしやすさ:
  - DuckDB 接続を受ける純粋関数群（research / ai など）は本番 API に依存しない。
- 運用のためのフラグファイル制御:
  - data/stop_requested.flag、data/kill.flag、data/execution.pid 等によるプロセス制御と安全停止。

前提条件
--------
- Python 3.10+（型注釈や構文からそれ以降を想定）
- 必要な外部パッケージ（主なもの）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリの sqlite3 を使用）
- インターネット接続（OpenAI API を使う機能を利用する場合）

インストール（例）
------------------
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

（注）実際のプロジェクトでは requirements.txt / poetry 等に依存をまとめてください。

環境変数 / 設定
----------------
アプリは .env/.env.local または環境変数から設定を読み込みます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

代表的な環境変数（主要項目）:

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィルモード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（Monitoring 設定）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアする(1=有効)

セットアップ手順（運用開始の基本例）
------------------------------------
1. プロジェクトルートに data ディレクトリを作成:
   - mkdir -p data

2. .env を作成して必要な環境変数を定義（.env.example がある場合は参照）。例:
   - KABUSYS_ENV=paper_trading
   - OPENAI_API_KEY=sk-...
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...

3. DuckDB / SQLite 用のデータファイル（必要に応じて）を準備または空ファイルを作成:
   - touch data/kabusys.duckdb
   - touch data/monitoring.db
   - touch data/paper_trading.db

4. 監視 DB の初期化は起動スクリプトが自動で行います（init_monitoring_db）。

起動方法 / 使い方
----------------

- 監視ループ（Monitoring）
  - 目的: システム状態・注文状況・リスクを定期的にチェックしログ/アラート/kill 判定を行う。
  - 実行:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止:
    - プロジェクトルートの data/stop_requested.flag を作成すると監視ループが次回ポーリング時に終了します。

- 実行エンジン（ExecutionEngine）
  - 目的: 注文発行、リスク管理、オーダー管理、リコンシリエーション、実行セッションの維持。
  - 実行:
    - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading を指定すると mock ブローカーを使い data/paper_trading.db に記録します。
  - 停止 / 強制停止:
    - KillSwitch により data/kill.flag が書き込まれると ExecutionEngine は安全停止を試みる設計。
    - data/stop_requested.flag の作成でも起動中の run_execution は停止処理を行います。
  - PID ファイル:
    - 実行時に data/execution.pid（デフォルト）が用いられ、SystemMonitor はこれを見てプロセス生存を判断します。

- Streamlit ダッシュボード
  - 監視データ（monitoring.db）を可視化します。
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - data/paper_trading.db のログから稼働率・注文成功率・レイテンシ等を集計して標準出力へレポートを出力できます。
  - 実行:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニュース NLP / レジーム検知）
  - OpenAI API を使用してニュース記事のセンチメント評価やマクロセンチメント（レジーム）判定を行います。
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意:
    - api_key が未設定のときは ValueError を投げます。
    - API エラーは内部でリトライ・フォールバック処理があるものの、API キーの管理には注意してください。

運用上のポイント / 挙動
-----------------------
- 環境読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml）を自動検出し .env と .env.local を読み込みます。OS 環境変数は上書きされないよう保護されています。
- Paper Trading 分離:
  - paper_trading モード時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視ログとは分離されます。
- kill.flag / stop_requested.flag:
  - KillSwitch がトリガされると data/kill.flag に理由を書き込み、ExecutionEngine は安全停止します。stop_requested.flag は単純に run_* スクリプトのループ終了トリガです。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。権限不足などで設定できない場合はログに警告が出ますが動作は継続します。

ディレクトリ構成
----------------
主要ファイル・フォルダ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成ツール
  - utils/
    - __init__.py
    - process_priority.py            — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py              — monitoring DB 初期化と永続化 API
    - system_monitor.py             — CPU / メモリ / データ鮮度 / PID 監視
    - trade_monitor.py              — 注文滞留 / 約定異常監視
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag の作成 / 管理
    - alert_manager.py              — LINE push 通知（クールダウン管理）
    - monitoring_engine.py          — 各 monitor を束ねるエンジン
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - ... (ExecutionEngine 周辺の実装ファイル群)
  - portfolio/
    - __init__.py
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数決定・カプ制御
    - risk_adjustment.py             — セクターキャップ / レジーム乗数
  - research/
    - __init__.py
    - factor_research.py             — Momentum / Volatility / Value 等
    - feature_exploration.py         — フォワードリターン / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの LLM ベース評点
    - regime_detector.py             — レジーム判定（MA200 + macro sentiment）
  - data/ (運用側に存在する想定)
    - monitoring.db (デフォルト)
    - kabusys.duckdb (デフォルト)
    - paper_trading.db (paper_trading の場合)

補足 / 開発者向けメモ
--------------------
- DuckDB を利用する研究モジュールは大型データ処理に向いており、prices_daily / raw_financials / raw_news 等のテーブルを前提としています。
- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できます。
- OpenAI 呼び出し部分はモジュール内でラップされており、ユニットテスト時は該当関数を patch して外部呼び出しをモックする設計です。

ライセンス / 貢献
-----------------
（この README にライセンス情報が含まれていないため、実際のプロジェクトでは LICENSE を追加してください）

おわりに
--------
この README はコードベースに含まれる主な機能と運用方法の概要を示します。運用前には .env の整備、適切な API キー管理、十分なテスト、本番環境用の監視設定（閾値など）の調整を行ってください。質問や追加ドキュメントの要望があれば教えてください。