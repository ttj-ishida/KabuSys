KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システム「KabuSys」のコードベース（部分）です。
README はローカルでのセットアップ、主要機能、使い方、ディレクトリ構成を簡潔にまとめたものです。

要点
- Python >= 3.10 を想定（型ヒントで | 演算子を使用）。
- 必須外部ライブラリ（機能によって必須/任意）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config YAML 検証を行う場合)
- デフォルトで使用するデータファイル:
  - data/kabusys.duckdb (DuckDB)
  - data/monitoring.db (監視用 SQLite)
  - data/paper_trading.db (ペーパートレード用 SQLite、KABUSYS_ENV=paper_trading の場合に利用)

プロジェクト概要
----------------
KabuSys は以下の主要機能を持つ自動売買フレームワークの一部を実装しています（提供コードの範囲）:

- Execution Engine 起動/監視スクリプト（run_execution, run_monitoring）
- 環境設定ウィザード（config_setup）と設定検証 CLI（validate_config）
- 監視サブシステム（system / trade / risk モニタ、kill switch、アラート連携）
- ポートフォリオ構築ユーティリティ（候補選定、配分計算、ポジションサイズ決定、リスク調整）
- リサーチ用関数（ファクター計算、特徴量探索、IC 計算）
- AI 補助機能（ニュース NLP によるセンチメント評価、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定など）
- Paper Trading 検証レポート生成スクリプト

主な機能一覧
-------------
- 環境設定
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- 実行 / 監視
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading.db に記録
    - 停止はファイルベースのフラグ (data/stop_requested.flag / data/kill.flag) で制御
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - システム・注文・リスク監視を定期実行し、監視ログを SQLite に保存
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
- ポートフォリオ構築
  - 候補選定 (select_candidates)
  - 等重・スコア重み (calc_equal_weights, calc_score_weights)
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ決定（lot 単位丸め、aggregate cap 参照）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリ
- AI（OpenAI）
  - ニュースを LLM（gpt-4o-mini 等）で評価して ai_scores に記録（kabusys.ai.score_news）
  - マクロニュース + ETF MA200 に基づく市場レジーム判定（kabusys.ai.regime_detector）
- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo>
   - cd <repo>

2. Python 環境を準備
   - Python 3.10 以上を推奨
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限（機能による）:
     - pip install duckdb psutil
   - AI 機能を使う場合:
     - pip install openai
   - YAML 検証を使う場合:
     - pip install PyYAML
   - 推奨: requirements.txt があればそれを利用:
     - pip install -r requirements.txt

4. .env を作成
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成する（.env.example を参照）
   - 重要な環境変数（一部）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - OPENAI_API_KEY (AI 機能を使う場合)
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
     - PAPER_FILL_MODE ("instant"|"partial"|"never"|"reject") — paper_trading 時の約定挙動
     - KILL_FLAG_CLEAR_ON_START (0|1) — 起動時に kill.flag を自動クリアするか

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備
   - デフォルトでは data/ と logs/ にファイルが作られます。パーミッション等を確認してください。

基本的な使い方
---------------

- 実行エンジン起動（デフォルト）
  - python -m kabusys.run_execution
  - 挙動:
    - Settings に基づき SQLite / DuckDB に接続
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使用し実際の発注は行わない
    - 起動中は data/stop_requested.flag を監視し、存在すれば安全に停止します

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔(秒)を指定可能:
    - export MONITOR_POLL_INTERVAL=30
  - 監視は monitoring DB（Settings.sqlite_path）にログを残します
  - Monitoring は KABUSYS_ENV にかかわらず設定された sqlite_path を使用します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も利用可能）

- AI 機能（ニューススコア／レジーム判定）
  - Python から直接呼び出す:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続が必要
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")
  - OPENAI_API_KEY が環境変数にセットされていれば api_key を省略可能

- ログ
  - logs/<app_name>.log に日次ローテーションでログが出力されます（TimedRotatingFileHandler）。
  - 起動スクリプトは共通の setup_logging を呼び出してルートロガーを設定します。

運用・管理に関する注意
---------------------
- 停止・Kill Switch
  - 実行停止は data/stop_requested.flag を作成することで行います（run_execution/run_monitoring はこれを見て終了します）。
  - kill.flag は KillSwitch によって書き込まれ、ExecutionEngine の停止トリガになります（Settings.kill_flag_path）。
  - 本番環境 (KABUSYS_ENV=live) で KILL_FLAG_CLEAR_ON_START=1 は危険です（自動クリアに注意）。

- データベース分離
  - paper_trading 実行時は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

- 環境変数の優先順位
  - OS 環境変数 > .env.local > .env
  - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テスト時など）

- MONITORING の挙動
  - run_monitoring は Settings で指定した sqlite_path（production path）を使います。監視は実稼働 DB を想定しています。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys を基準とした主要ファイル・モジュールの一覧（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 起動前設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py       — 共通ログ設定
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       — monitoring SQLite 操作層
      - monitoring_engine.py   — 各 Monitor を束ねるランナー
      - system_monitor.py
      - trade_monitor.py       — （参照されるがコード断片で省略されている部分あり）
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py       — （アラート送信をまとめる想定モジュール）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py

（注）リポジトリ全体のファイルはここに全て示していません。実際のプロジェクトでは execution、data、strategy 等のサブパッケージが存在します。

環境変数一覧（主要）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用・推奨:
  - KABUSYS_ENV: development | paper_trading | live
  - DUCKDB_PATH (default data/kabusys.duckdb)
  - SQLITE_PATH (default data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default data/paper_trading.db)
  - OPENAI_API_KEY (AI 用)
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
  - MONITOR_POLL_INTERVAL (run_monitoring 用、秒)
  - PAPER_FILL_MODE (instant|partial|never|reject)
  - KILL_FLAG_CLEAR_ON_START (0|1)

よくある操作例
---------------
- .env を生成:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config
- 実行エンジン開始:
  - python -m kabusys.run_execution
- 監視開始（ポーリング間隔 30 秒）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

追加情報 / 開発者向けメモ
-----------------------
- DuckDB を使うリサーチ機能は prices_daily / raw_financials / raw_news 等のテーブルを前提とします。これらのテーブルはデータパイプラインで事前に取り込む必要があります。
- AI 関連は OpenAI の JSON Mode を想定したレスポンス処理を実装しています。API レスポンスの不備やエラーはフェイルセーフ（0.0 など）で対応する設計です。
- ログ設定は kabusys.utils.logging_setup.setup_logging を呼ぶことで統一されます。ログディレクトリ作成に失敗した場合は標準出力のみで継続します。
- 実運用時は kill_flag / stop_requested.flag の取り扱いに注意してください（自動クリア設定や cron による誤削除など）。

貢献・改修
---------
バグ修正・機能追加は Pull Request をお願いします。重要な設計決定やマイグレーション（DB スキーマ変更等）は README または docs に追記してください。

ライセンス
----------
プロジェクトのライセンス情報に従ってください（リポジトリルートの LICENSE ファイル参照）。

以上。必要であれば README に導入コマンドの具体的な例（requirements.txt を使ったインストール手順や systemd ユニット例、Dockerfile など）を追加で作成します。どの情報を優先して追記しましょうか。