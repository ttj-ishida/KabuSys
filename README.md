README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／サービス群です。
本リポジトリには以下の主要機能を提供するモジュール群が含まれます。

- 注文発行・管理（ExecutionEngine / OrderManager / Reconciler）
- リスク管理・レート制限・リコンシリエーション
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- ファクター計算・リサーチ用ユーティリティ（DuckDB を利用）
- ニュース NLP を用いたセンチメントスコアリング（OpenAI）
- 市場レジーム判定（MA200 + マクロセンチメントの合成）
- 監視（System / Trade / Risk の監視）、LINE へのアラート送信、Streamlit ダッシュボード
- Paper Trading 用の分離 DB と検証レポート生成ツール

設計方針のポイント:
- 本番データと paper_trading は SQLite ファイルで明確に分離
- DuckDB を用いた時系列・ファクター計算
- LLM（OpenAI）呼び出しはフェイルセーフ（失敗時は安全側にフォールバック）
- 自動的な .env ロード機構（プロジェクトルートを検出して読み込む）

主な機能一覧
--------------
- Execution
  - Order 管理: create / send / sync（OrderManager）
  - ブローカー抽象化: BrokerClientFactory / BrokerAPIProtocol（paper と live を切替）
  - 起動時リコンシリエーション（Reconciler）
  - RiskManager によるポジション・資金制約チェック
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジション数（単元丸め含む）計算（calc_position_sizes）
- Research / Data
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI
  - ニュース・センチメントスコアリング（kabusys.ai.news_nlp）
  - レジーム判定（kabusys.ai.regime_detector）
- Monitoring
  - system_status / trade_logs / risk_logs / dashboard テーブルを管理（monitoring_db）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - MonitoringEngine（ポーリングループ）
  - Streamlit ダッシュボード（read-only 接続）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提（Prerequisites）
--------------------
- Python 3.10 以上（typing, __future__ annotations を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite は標準の sqlite3 で利用

インストール（例）
-----------------
1. 仮想環境を作る（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール（必要なパッケージをプロジェクトに合わせて調整してください）
   - pip install duckdb psutil requests openai streamlit

設定（環境変数）
----------------
プロジェクトルートに .env / .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
主に使用する環境変数（抜粋）:

- KABUSYS_ENV: 起動環境
  - 候補: development / paper_trading / live
  - paper_trading を指定すると Execution は MockBrokerClient を使い data/paper_trading.db に書きます
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant | partial | never | reject）
- PID_FILE_PATH: Execution の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチ用フラグファイル（デフォルト: data/kill.flag）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
- JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD: 各 API 用必須トークン
- LOG_LEVEL: ログレベル（DEBUG / INFO / ...）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

セットアップ手順（ローカル実行の例）
---------------------------------
1. データディレクトリを作成
   - mkdir -p data

2. .env を作成して必要な環境変数を設定（例）
   - KABUSYS_ENV=paper_trading
   - OPENAI_API_KEY=sk-...
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - (必要に応じて) PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

3. Paper Trading 用 DB を初期化したい場合は、Execution や Monitoring を起動すると self-migration でテーブルが作成されます。

使い方（コマンド例）
-------------------

- ExecutionEngine を起動（通常は systemd 等でデーモン化）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると paper_trading DB を用います。

- Monitoring（SystemMonitor のポーリングループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）

- Streamlit ダッシュボード（監視 DB を read-only で参照）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  (PAPER_TRADING_SQLITE_PATH 環境変数が優先される)

- プログラムから AI / Research 機能を呼ぶ例（Python REPL）
  - from datetime import date
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, date(2026, 4, 1), api_key="sk-...")

注意事項・挙動
--------------
- Paper Trading は本番用 sqlite と分離されています（デフォルト: data/paper_trading.db）。
- Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計の箇所があります（run_monitoring の仕様に基づく挙動）。
- OpenAI 呼び出しは失敗時に安全側のフォールバックを行い、例外を投げずに処理を継続するよう設計されています（ログ出力あり）。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止指示を与えます。Execution 側でこのフラグを検知して停止する実装が前提です。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。

ディレクトリ構成（主要ファイル）
------------------------------
以下はリポジトリ内の主要モジュールの抜粋です（完全な一覧ではありません）。

- src/kabusys/
  - __init__.py
  - config.py                           — 環境変数 / 設定管理
  - run_execution.py                    — ExecutionEngine 起動スクリプト
  - run_monitoring.py                   — SystemMonitor ポーリング起動スクリプト
  - data/                                — （想定）データ関連モジュール（DuckDB 用）
  - execution/
    - execution_engine.py                — 実取引セッション管理（Engine）
    - order_manager.py                   — 注文の作成／送信／同期
    - order_repository.py                — Orders DB 操作
    - reconciler.py                      — 起動時リコンシリエーション
    - broker_factory.py                  — ブローカークライアント生成
    - broker_api.py                      — ブローカー API プロトコル
    - ...
  - monitoring/
    - monitoring_db.py                   — SQLite 監視 DB（テーブル定義・CRUD）
    - system_monitor.py                  — システム状態監視
    - trade_monitor.py                   — 注文滞留／約定チェック
    - risk_monitor.py                    — ドローダウン・ポジション上限監視
    - kill_switch.py                     — kill.flag 制御
    - alert_manager.py                   — LINE 通知
    - monitoring_engine.py               — 監視ループ統括
    - streamlit_dashboard.py             — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py               — 候補選定・重み付け
    - position_sizing.py                 — 株数決定・丸め・資金配分制御
    - risk_adjustment.py                 — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py                 — ファクター計算（momentum/value/vol）
    - feature_exploration.py             — 将来リターン、IC、統計サマリー
  - ai/
    - news_nlp.py                        — ニュース NLP / OpenAI 呼び出し & ai_scores 書込
    - regime_detector.py                 — 市場レジーム判定（MA200 + マクロ）
  - tools/
    - paper_verification_report.py       — Paper Trading レポート生成ツール
  - utils/
    - process_priority.py                — プロセス優先度 / CPU affinity 設定
  - その他の補助モジュールやテストコード等

開発上のヒント
----------------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）を準備しておくと research / ai モジュールが動作します。
- OpenAI のテストや CI では環境変数 OPENAI_API_KEY をモック化するか、kabusys.ai.news_nlp._call_openai_api 等を patch して外部呼び出しを防いでください。
- MonitoringDB は起動時に必要なマイグレーション（列追加）を行うため、古い DB でも互換性を保つように設計されています。

ライセンス・貢献
----------------
- この README はコードベースからの抜粋ドキュメントです。実運用に導入する前に、適切なテスト・セキュリティ審査を行ってください。
- 貢献はプルリクエストまたは Issue で受け付けてください（プロジェクトの LICENSE / CONTRIBUTING に従ってください）。

付録: よく使うコマンド（まとめ）
--------------------------------
- 実行（paper_trading 例）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution

- 監視（デフォルト 60 秒間隔）
  - python -m kabusys.run_monitoring
  - export MONITOR_POLL_INTERVAL=30

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要であれば、README に含めるトピック（環境変数の完全一覧、API 呼び出し例、データスキーマ、実運用手順書）を追加で作成します。どの項目を詳細化しますか？