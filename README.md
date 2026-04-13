KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買（Execution）および稼働監視（Monitoring）を目的とした小規模なシステム基盤です。  
主な機能は戦略向けのファクター計算、ポートフォリオ構築、注文管理（ブローカー連携と再突合）、監視・アラート、Paper Trading 検証、LLM を使ったニュースセンチメント評価などを含みます。

特徴
----
- Execution（発注）エンジン（実ブローカー or Paper Trading モックを切替）
- Monitoring（システム状態・注文・リスク監視）と kill.flag による停止シグナル
- DuckDB を使ったファクター計算（prices_daily / raw_financials 等参照）
- Portfolio construction（候補選定 / 重み付け / ポジションサイズ算出）
- Research ツール（ファクター計算・IC 計測・forward returns 等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定（AI モジュール）
- Streamlit ベースの監視ダッシュボード
- Paper Trading 検証レポート生成スクリプト

動作環境（推奨）
----------------
- Python 3.10+
  - コードベースで PEP 604 の型記法（X | Y）を使用しているため 3.10 以降を想定
- 必要な主要ライブラリ（例）:
  - duckdb, psutil, requests, openai, streamlit

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成・有効化します:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（requirements.txt が無い場合の例）:
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリを作成:
   - mkdir -p data

4. 環境変数を設定（.env / .env.local をプロジェクトルートに置くことが可能）。
   - 自動で .env / .env.local を読み込みます（プロジェクトルートは .git または pyproject.toml を基準）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（Settings で参照されるもの）
--------------------------------------------
（設定可能 / デフォルトがあるものは併記）

- 必須（未設定時はエラー）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- オプション / デフォルト:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: "instant"）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH: 実行中プロセス PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: start 時に kill.flag をクリア（"1" で true）
  - LOG_LEVEL: DEBUG|INFO|...（デフォルト: INFO）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）

実行方法
--------
- ExecutionEngine（発注エンジン）起動:
  - 環境: KABUSYS_ENV を切り替えることで本番 / Paper Trading を選択
    - Paper Trading: export KABUSYS_ENV=paper_trading
    - Live: export KABUSYS_ENV=live
  - 実行:
    - python -m kabusys.run_execution
  - 備考:
    - Paper Trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH にデータを記録します（本番DBとは分離）。
    - プロセス優先度を "high" に設定します（可能な場合）。

- Monitoring（SystemMonitor ポーリング）起動:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - 実行:
    - python -m kabusys.run_monitoring
  - 備考:
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを記録します。
    - プロセス優先度を "high" に設定します（可能な場合）。

- Streamlit 監視ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開きます。MonitoringEngine を先に起動していないとデータがない旨のエラー表示になります。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を手動指定可能。

AI 関連（ニュース NLP / レジーム判定）
------------------------------------
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で指定）。
- 提供関数:
  - kabusys.ai.score_news (news_nlp.score_news): raw_news を集約し LLM により銘柄別センチメントを ai_scores に書き込む。
  - kabusys.ai.regime_detector.score_regime: ETF(1321) の MA200 とマクロニュースの LLM 評価を合成して market_regime に保存。
- レート制限・一時エラーに対してはリトライ（指数バックオフ）処理を行います。API 失敗時はフォールバック（例: macro_sentiment=0.0）で継続する設計です。

ツール / スクリプト一覧
------------------------
- run_execution.py: ExecutionEngine 起動スクリプト
- run_monitoring.py: SystemMonitor 単体起動（ポーリング）
- monitoring/streamlit_dashboard.py: Streamlit ダッシュボード
- tools/paper_verification_report.py: Paper Trading の検証レポート生成ツール

主要モジュール説明（概略）
-------------------------
- kabusys.config: 環境変数 / .env 管理、Settings クラス
- kabusys.monitoring:
  - monitoring_db: SQLite スキーマ初期化と永続化 API
  - system_monitor / trade_monitor / risk_monitor: 各監視ロジック
  - monitoring_engine: 複数モニタのまとめ・ポーリングループ
  - alert_manager: LINE Push による通知（channel token / user id が必要）
  - kill_switch: kill.flag による ExecutionEngine 停止トリガ
- kabusys.execution:
  - order_manager / order_repository / reconciler: 注文発行・管理・再突合
  - broker_factory: ブローカークライアント生成（本番 / mock 切替）
- kabusys.portfolio:
  - portfolio_builder / position_sizing / risk_adjustment: 候補選定、重み付け、株数計算、セクター制限、レジーム乗数
- kabusys.research:
  - factor_research / feature_exploration: ファクター計算、forward returns、IC、統計サマリ
- kabusys.ai:
  - news_nlp / regime_detector: LLM を用いたニュース評価・レジーム判定

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py
- run_execution.py
- run_monitoring.py
- tools/
  - __init__.py
  - paper_verification_report.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- monitoring/
  - __init__.py
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...（broker 関連等）
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- utils/
  - process_priority.py
  - __init__.py
- data/ (想定: data ディレクトリに DB ファイル等を置く)

運用上の注意
------------
- Settings は .env/.env.local/OS 環境変数の優先順位で値を取得します。プロジェクトルートが検出できない場合は自動ロードをスキップします。
- run_monitoring は監視用 DB（SQLite）に必ず本番の sqlite_path を使うため、Paper Trading と混同しないよう注意してください。
- run_execution は KABUSYS_ENV=paper_trading のときに Paper Trading 用 DB を使って本番 DB と分離します。
- OpenAI 利用箇所は API 呼び出し失敗に対してフェイルセーフ（スコア 0.0 やスキップ）する設計ですが、API キーや通信環境の管理は運用側で行ってください。
- PID ファイルや kill.flag の扱いでプロセス制御・停止を行います。kill.flag を手動で削除すると再稼働が可能です。

ライセンス / 貢献
-----------------
（この README には現状ライセンス情報は含まれていません。必要に応じて LICENSE を追加してください。）

補足
----
- 実運用前に DuckDB / SQLite のテーブル・データ整備、ブローカー API の接続確認、LINE 通知設定、OpenAI API のクォータ確認を行ってください。
- 開発時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してテスト環境での環境変数干渉を防げます。

必要であれば README にサンプル .env のテンプレートや起動時の具体的な systemd / supervisor の設定例、docker-compose 構成例を追記できます。必要な内容を教えてください。