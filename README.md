KabuSys — 日本株自動売買システム (抜粋)
====================================

このリポジトリは日本株の自動売買、監視、リサーチ、AI 補助処理を行うためのモジュール群（抜粋実装）です。
以下はコードベース（src/kabusys 以下）に基づく README（日本語）です。

前提
----
- Python 3.10 以上（型注釈の | 記法、typing の挙動のため）
- SQLite（組み込み）
- DuckDB（prices_daily 等の時系列 / マスタデータ参照に使用）
- 実行時に環境変数を利用します（.env/.env.local を自動読み込みする仕組みあり。詳細は config.py 参照）。

主な機能（ハイライト）
-------------------
- ExecutionEngine 起動 / 注文管理
  - run_execution.py: ブローカークライアントを生成して Execution エンジンを起動。KABUSYS_ENV=paper_trading の場合は Paper Trading 用 DB と Mock ブローカーを使用。
  - Reconciler による再起動時の注文同期 / ポジション差分検出
  - OrderManager / OrderRepository による注文状態管理

- 監視機能
  - run_monitoring.py: SystemMonitor をポーリングして system_status / risk_logs / trade_logs / positions / dashboard を更新
  - MonitoringEngine：SystemMonitor / TradeMonitor / RiskMonitor を束ね、Alert（LINE）や KillSwitch を評価
  - Streamlit ダッシュボード（監視の可視化）

- ポートフォリオ構築（純粋関数）
  - 候補選定（select_candidates）、重み付け（calc_equal_weights / calc_score_weights）
  - リスク調整（セクターキャップ apply_sector_cap、レジーム乗数 calc_regime_multiplier）
  - 発注株数決定（calc_position_sizes）

- リサーチ
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（将来リターン、IC、統計サマリー）

- AI 支援
  - news_nlp.score_news：OpenAI（gpt-4o-mini）でニュースをセンチメント評価し ai_scores に保存
  - regime_detector.score_regime：ETF（1321）の MA200 とマクロニュースセンチメントを合成して市場レジーム判定を行い market_regime に保存

- ツール
  - tools.paper_verification_report：Paper Trading の検証レポートを生成

セットアップ手順
----------------

1. リポジトリ取得
   - この README は src/kabusys 配下のコードに基づきます。リポジトリをクローンし、作業ルートをプロジェクトルートにしてください。

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt が無い場合は上記を参考に必要パッケージをインストールしてください）

4. 環境変数 / .env
   - プロジェクトルートの .env / .env.local に環境変数を置けます（config.py が自動で読み込みます）。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 主要な環境変数（一部）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD: kabu API 用パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH: PID / kill flag のパス
     - LOG_LEVEL
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用

5. データディレクトリ
   - デフォルトの DB やフラグファイルは data/ 配下に置かれます。必要に応じてディレクトリを作成してください。
   - 例: mkdir -p data

使い方（起動・実行例）
--------------------

- 監視ループを起動（SystemMonitor 単体）
  - 環境を設定してから:
    - PYTHONPATH=src python -m kabusys.run_monitoring
  - 補足:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）
    - run_monitoring は Monitoring 用 SQLite（settings.sqlite_path）を常に使用します（KABUSYS_ENV に依らず）

- ExecutionEngine を起動（注文実行）
  - PYTHONPATH=src python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 実行中に data/stop_requested.flag が作成されるとエンジン停止を試みる

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視状態・ポジション・トレードログ・リスクログを確認できます

- Paper Trading 検証レポート
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別 DB を指定可能（優先度: --db > 環境変数 PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI / リサーチ用 API（プログラム的利用）
  - news_nlp:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意点 / 運用上のポイント
-----------------------
- run_monitoring.py は Monitoring のためのスクリプトで、モニタリング DB（settings.sqlite_path）を常に使用します。開発環境でも監視対象 DB を間違えないよう注意してください。
- run_execution.py は KABUSYS_ENV に応じて paper_trading 用 DB を分離します（テストと本番をわける意図）。
- データ鮮度チェックは DuckDB の prices_daily テーブルを参照します。DuckDB 側のデータ投入パイプラインが必要です。
- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。API キーの設定、レート制限、エラーハンドリング（リトライやフォールバック）に注意してください。
- kill.flag / stop_requested.flag: 制御用フラグファイル。KillSwitch により kill.flag が生成されると ExecutionEngine に停止シグナルが送られます。flag は実行環境でのオペレーション手順に従って管理してください。

ディレクトリ構成（主要ファイルのみ）
----------------------------------
- src/
  - kabusys/
    - __init__.py
    - config.py                    — 環境変数 / .env ロード、Settings
    - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
    - run_execution.py             — ExecutionEngine 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py                — ニュース NLP（OpenAI）スコアリング
      - regime_detector.py         — 市場レジーム判定（MA200 + マクロセンチメント）
    - monitoring/
      - monitoring_db.py           — monitoring DB スキーマ + 永続化 API
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - reconciler.py
      - order_manager.py
      - order_repository.py
      - execution_engine.py (実装抜粋がある前提)
      - broker_factory.py
      - ...（その他 execution 関連）
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - data/
      - pipeline.py（get_last_price_date 等）
    - utils/
      - process_priority.py
    - monitoring/、execution/、research/、portfolio/、ai/ など多数の補助モジュール

付録：よく使う環境変数（抜粋）
-----------------------------
- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY
- PAPER_FILL_MODE (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- SQLITE_PATH (data/monitoring.db)
- DUCKDB_PATH (data/kabusys.duckdb)
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- LOG_LEVEL (DEBUG|INFO|...)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数)

最後に
-----
この README は src/kabusys 以下のコード（抜粋）をもとに作成しています。実運用・ローカル実行の前に環境変数、DB ファイル配置、使用する OpenAI キーや LINE トークン等を正しく設定してください。各モジュールの詳細実装や追加のユーティリティが必要な場合は該当ファイルの docstring / コメントを参照してください。