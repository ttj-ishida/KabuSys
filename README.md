KabuSys — 日本株自動売買システム
================================

本ドキュメントは、提示されたコードベースに基づく README です。ローカル開発・実行のための概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株の自動売買／運用支援のためのモジュール群です。主な機能群は以下のとおりです。

- 発注エンジン（ExecutionEngine）・Order 管理（OrderManager / OrderRepository）
- 監視・アラート（SystemMonitor / TradeMonitor / RiskMonitor / AlertManager）
- 市場・ファクター研究（ファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- AI を用いたニュースセンチメント評価（OpenAI）
- Paper Trading 用の検証ツール・レポート生成
- Streamlit ベースの監視ダッシュボード

設計上のポイント
- 環境変数または .env ファイルから設定を読み込む Settings モジュールを提供。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全に分離（data/paper_trading.db）。
- 監視ロガーは SQLite（デフォルト data/monitoring.db）を使用し、DuckDB は市場データ等の集計に使用。
- OpenAI API を使用するモジュール（ニュース NLP / レジーム判定）は API キーが必要で、失敗時は安全側フォールバックする実装。

主な機能一覧
---------------
- Execution
  - Order 作成 / 送信 / 状態同期 / リコンシリエーション（Reconciler）
  - Broker クライアント抽象化（実運用とモックの切替）
- Monitoring
  - システム状態監視（CPU / メモリ / ディスク / プロセス生存）
  - 注文滞留 / 約定異常の検出
  - ドローダウン / ポジション上限監視（KillSwitch による停止信号出力）
  - LINE Push によるアラート送信（AlertManager）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定（スコア・ランク）・重み算出（等金額 / スコア加重）
  - セクターキャップ適用・レジーム乗数
  - ポジションサイズ計算（単元株丸め・利用可能資金キャップ）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース記事の LLM によるセンチメントスコア付与（ai_scores テーブルへ書込）
  - マクロニュース + ETF MA200 乖離を用いた市場レジーム判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定可）
  - Streamlit ダッシュボード起動スクリプト

必要条件（主要パッケージ）
------------------------
以下は本プロジェクトで使用されている主なライブラリ例です（環境に合わせてバージョン指定してください）。

- Python 3.10+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード利用時)
- openai (OpenAI クライアント)
- sqlite3（標準ライブラリ）
- その他（プロジェクトに応じた追加依存）

セットアップ手順
---------------
1. リポジトリをクローン / 取得し、プロジェクトルートへ移動
   - 本コードは src 配下にパッケージが配置される構成を想定しています。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (UNIX)
   - .venv\Scripts\activate (Windows)

3. 必要ライブラリをインストール
   - pip install duckdb psutil requests streamlit openai
   - （必要に応じて requirements.txt を用意して pip install -r requirements.txt）

4. data ディレクトリ作成（SQLite / DuckDB のデフォルト位置）
   - mkdir -p data

5. 環境変数の設定
   - PROJECT ルートに .env または .env.local を置くと自動で読み込まれます（ただし OS 環境変数が優先・KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI モジュール使用時必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - SQLITE_PATH (監視用 DB、デフォルト data/monitoring.db)
     - DUCKDB_PATH (DuckDB ファイル、デフォルト data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の fill 動作: instant|partial|never|reject、デフォルト instant）
     - PID_FILE_PATH（デフォルト data/execution.pid）
     - KILL_FLAG_PATH（デフォルト data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループのポーリング間隔秒数、デフォルト 60）

使い方
------

基本的な起動・操作例を示します。プロジェクトルートで実行するか、src を PYTHONPATH に含めて実行してください（python -m を推奨）。

1) Execution Engine を起動（本番 / paper_trading に応じて挙動が変わります）
- 通常実行
  - python -m kabusys.run_execution
- 補足
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に書き込みます。
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority を呼ぶ）。

2) Monitoring（SystemMonitor のポーリング）を起動
- python -m kabusys.run_monitoring
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
- 監視は常に Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（monitoring は本番 DB を利用する設計意図あり）。

3) Streamlit ダッシュボードを起動
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードから positions / recent orders / system status / risk logs を可視化できます（読み取り専用で DB を開きます）。

4) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定（例）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
- DB を明示する場合:
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI モジュール（ニュース NLP・レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必要です。関数ベースで呼び出すことを想定（例: kabusys.ai.score_news）。
- score_news / score_regime は DuckDB 接続と target_date を引数に取って呼び出します。
- 失敗時はフェイルセーフ（スコア 0.0 にフォールバックするなど）の振る舞いをしますが、API キー未設定時は例外になります。

重要な挙動・運用メモ
---------------------
- Settings モジュールは .env/.env.local を自動読み込みします（ただし OS 環境変数が優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- Monitoring 用の DB 初期化は init_monitoring_db() で行われ、スキーママイグレーション（カラム追加等）も含まれています。
- KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組みです。kill.flag は冪等性を保って書き込まれます。ExecutionEngine 側はこのファイルの存在を監視して停止する設計が想定されています。
- PID ファイル（デフォルト data/execution.pid）は SystemMonitor が存在・生存確認を行います。不正な PID ファイルは自動削除してログ出力します。
- process priority / CPU affinity の設定はプラットフォーム差（Windows / POSIX）を吸収するユーティリティ（kabusys.utils.process_priority）を提供しています。権限不足時はスキップして警告ログに留まります。

ディレクトリ構成（抜粋）
-----------------------
提示されたファイル群をベースにした主要なディレクトリ構成（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / Settings
    - run_execution.py                 — ExecutionEngine 起動スクリプト
    - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py   — Paper Trading 検証レポートツール（CLI）
    - ai/
      - __init__.py
      - news_nlp.py                    — ニュースセンチメント（OpenAI 連携）
      - regime_detector.py             — レジーム判定（ETF MA200 + マクロ）
    - monitoring/
      - __init__.py
      - monitoring_db.py               — SQLite 永続層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (broker_factory, execution_engine, order_repository 等 — 一部ファイルは参照されます)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - utils/
      - __init__.py
      - process_priority.py
    - (data/ パッケージやその他モジュールは別途存在する想定)

（注）提示コードはプロジェクトの一部を抜粋したものです。実際の実行には execution_engine や broker 実装、data パッケージ等の追加モジュールが必要になる可能性があります。

環境変数（主な一覧）
-------------------
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト development）
- SQLITE_PATH — 監視 DB（SQLite）パス（デフォルト data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定挙動（instant|partial|never|reject）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須な箇所あり）
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合に必須）
- PID_FILE_PATH — PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

トラブルシューティング
---------------------
- DB ファイルが見つからない・開けない場合、MonitoringEngine や Streamlit は起動エラーを出力します。パスやファイルパーミッションを確認してください。
- OpenAI 連携で 4xx・5xx・ネットワークエラーが発生する場合、内部でリトライ・フォールバック処理が行われます。API キーや使用量制限を確認してください。
- process priority 設定で AccessDenied が出る場合、権限不足のため設定がスキップされます（ログに警告）。

ライセンス・貢献
----------------
- 本 README はコード断片に基づく説明です。実際のライセンス表記や貢献ガイドはプロジェクトルートに LICENSE / CONTRIBUTING を用意してください。

最後に
------
実行前に必ず .env（または環境変数）で必要な値を設定し、data ディレクトリや DB ファイルの初期化を行ってください。開発・テストでは KABUSYS_ENV=paper_trading を利用すると本番 DB と分離して安全に動作確認できます。必要があれば README をプロジェクトの実ファイル構成に合わせて追記してください。