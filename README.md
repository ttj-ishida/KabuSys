KabuSys — README
================

概要
----
KabuSys は日本株自動売買システムのコアライブラリ群です。  
ポートフォリオ構築、ポジションサイジング、発注管理、監視・アラート、研究用ファクター計算、LLM を用いたニュースセンチメント評価などの機能を持ちます。  
本リポジトリは主にライブラリ／バッチスクリプト群を提供しており、ExecutionEngine（発注実行）や Monitoring（監視）を CLI / スクリプトとして起動できます。

主な特徴
--------
- Execution: 発注/注文管理（OrderManager / Reconciler 等）
- Paper trading モード: 本番 DB と分離して data/paper_trading.db に記録（KABUSYS_ENV=paper_trading）
- Monitoring: システム状態、データ鮮度、滞留注文、約定異常、ドローダウン監視
- Kill switch: しきい値超過時にフラグファイルを書いて ExecutionEngine 停止を誘発
- Alerting: LINE Messaging API を用いたプッシュ通知（クールダウンあり）
- Research: DuckDB を使ったファクター計算（Momentum/Value/Volatility など）、IC 等の統計ツール
- AI モジュール: OpenAI（gpt-4o-mini 等）によるニュースセンチメント評価 / レジーム判定（書込みは DuckDB）
- Tools: Paper Trading 検証レポート生成スクリプト、Streamlit ダッシュボード

セットアップ手順
----------------
前提
- Python 3.10 以上（コード内の型ヒントに | 演算子を使用）
- SQLite（組み込み）、DuckDB、外部パッケージ（以下参照）

仮想環境作成（例）
- python -m venv .venv
- source .venv/bin/activate  または .venv\Scripts\activate

必須パッケージ例
- pip install duckdb psutil requests openai streamlit

（プロジェクトによっては追加パッケージが必要になる場合があります。requirements.txt がある場合はそれを使ってください。）

環境変数
- .env（プロジェクトルート）または環境変数で設定します。自動ロードが有効（既定）です。
- 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数
- KABUSYS_ENV: 起動環境。development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチ用フラグファイル（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring はこの値を参照、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定時は送信せずログのみ）

簡単な .env の例
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_jquants_token
- KABU_API_PASSWORD=your_kabu_password
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

使い方
-----
エントリポイント（主なスクリプト）

- 実行エンジン（発注実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離します。
  - 起動時にプロセス優先度を "high" に設定しようとします（権限により失敗することがあります）。

- 監視ループ（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用してログを永続化します。

- Streamlit ダッシュボード（ローカルで監視結果を参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いてダッシュボードを表示します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH により上書き可）

ライブラリの利用（Python API）
- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- リサーチ:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- AI:
  - from kabusys.ai import score_news
  - kabusys.ai.regime_detector.score_regime を直接利用してレジーム判定と書込が可能（APIキーが必要）
- Monitoring DB 操作:
  - from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db
  - MonitoringDB は system_status / trade_logs / positions / risk_logs / dashboard の CRUD を提供

注意点 / 運用上のポイント
- Paper trading モードは本番 DB と分離されています。KABUSYS_ENV=paper_trading を必ず設定してください。
- OpenAI API 呼び出しはレート制限や一時エラーに対してリトライ実装がありますが、API キーが必須です。失敗時はフェイルセーフでスコア 0 を使うなどの設計になっています（モジュールにより異なる）。
- monitoring の kill switch はファイル（KILL_FLAG_PATH）を作成することで ExecutionEngine 停止を促します。ExecutionEngine 側でこのフラグの検知・停止処理を実装している必要があります。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を探索して行います。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
-----------------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数と Settings クラス。.env 自動ロードロジックを含む。
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 分離対応）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py
    - Paper Trading 検証レポート生成スクリプト
- ai/
  - __init__.py
  - news_nlp.py
    - OpenAI を使ったニュースセンチメント取得と ai_scores への書込み
  - regime_detector.py
    - ETF + マクロニュースを併せた市場レジーム判定と market_regime テーブル書込み
- monitoring/
  - __init__.py
  - monitoring_db.py
    - monitoring 用 SQLite DB 初期化と MonitoringDB クラス（CRUD）
  - system_monitor.py
    - システム状態・データ鮮度チェック
  - trade_monitor.py
    - 注文滞留・約定異常チェック
  - risk_monitor.py
    - ドローダウン・ポジション上限チェック
  - kill_switch.py
    - フラグファイルによる停止シグナル生成
  - alert_manager.py
    - LINE プッシュ通知クライアント（クールダウン付）
  - monitoring_engine.py
    - 各 Monitor を束ねる実行ループ
  - streamlit_dashboard.py
    - Streamlit を使ったダッシュボード表示用スクリプト
- execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, ...
  - 発注ワークフロー・ブローカー抽象等（OrderRecord / OrderState の扱い）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - ポートフォリオ構築・重み付け・ポジションサイズ計算
- research/
  - factor_research.py
  - feature_exploration.py
  - ファクター計算・IC / 統計ユーティリティ
- utils/
  - process_priority.py
  - プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (想定される出力パス、リポジトリには含まれない可能性あり)
  - kabusys.duckdb（DuckDB データベース、デフォルト）
  - monitoring.db（監視ログ SQLite）
  - paper_trading.db（paper trading 用 SQLite）

開発 / テスト
-------------
- 各モジュールは可能な限り副作用を抑えた純粋関数（research / portfolio など）と、DB 書込を行う永続層（monitoring_db / order_repository）で分離されています。ユニットテストは純粋関数を中心に書くのが容易です。
- OpenAI など外部 API 呼び出しは関数を分離しており、テスト時にモック（unittest.mock.patch）で置き換え可能です。

ライセンス / コントリビューション
---------------------------------
- 本 README にはライセンス情報は含まれていません。実際のリポジトリの LICENSE ファイルを参照してください。  
- バグ報告 / プルリクエストは各自の開発ルールに従ってください。

お問い合わせ
------------
- リポジトリの issue 機能、またはプロジェクトの連絡先に従ってください。

以上がこのコードベースの概要と基本的な使い方です。必要であれば、特定モジュール（例: ExecutionEngine の起動オプションや OrderRepository のスキーマ）についての詳細なドキュメントも作成します。どの部分を詳しく知りたいか教えてください。