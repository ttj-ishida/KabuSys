KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買パイプラインの研究・実行・監視を目的とした Python ベースのプロジェクトです。
主要な機能群は以下のとおりです。

- Execution（ExecutionEngine）: 注文作成・送信・リコンシリエーション・リスク管理
- Monitoring: システム健全性、注文滞留、ドローダウン等の監視、kill flag による停止シグナル
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約
- Research: ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量探索（IC 等）
- AI モジュール: ニュースのセンチメントスコアリング（OpenAI）と市場レジーム判定
- Tools: Paper Trading 検証レポート生成、Streamlit ダッシュボードなど

主な機能一覧
-------------
- 注文管理（OrderManager）
  - 重複防止、状態遷移の管理、ブローカー同期
- 自動復旧（Reconciler）
  - OrderSent 状態の照合、ブローカー/ローカルのポジション差分検出
- リスク管理（RiskManager / RiskMonitor）
  - ドローダウン監視、ポジション数上限監視、ログ記録
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor）
  - CPU/メモリ/ディスクやデータ鮮度の監視、滞留注文/約定異常検出
- 通知（AlertManager）
  - LINE Messaging API を使った通知（クールダウン管理あり）
- AI/LLM の利用
  - ニュースを LLM で評価して ai_scores に書込む（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA200 を組み合わせて市場レジーム判定（kabusys.ai.regime_detector）
- 研究用ユーティリティ
  - DuckDB を使ったファクター計算（prices_daily / raw_financials を参照）
- 開発用ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）
  - Streamlit ベースの監視ダッシュボード

セットアップ手順
----------------

1. Python 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

2. 依存パッケージのインストール
   プロジェクトの requirements.txt はここに含まれていませんが、主要依存は次の通りです:
   - duckdb
   - psutil
   - requests
   - openai (openai SDK)
   - streamlit (ダッシュボード用)
   - sqlite3（Python 標準組込）
   例:
     pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env
   プロジェクトはプロジェクトルートの .env / .env.local を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   主な環境変数（必要に応じて .env に記載）:

   - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
   - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須な処理では設定を要求）
   - KABU_API_PASSWORD: kabuステーション API のパスワード
   - OPENAI_API_KEY: OpenAI API キー（AI 関係機能で使用）
   - LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン（任意）
   - LINE_USER_ID: LINE 通知先ユーザ ID（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
   - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant|partial|never|reject）
   - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill flag ファイル（デフォルト: data/kill.flag）
   - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化

4. データベース初期化
   - Monitoring に必要なテーブルは run_monitoring / run_execution 実行時に自動で作成（init_monitoring_db）。
   - DuckDB のテーブル（prices_daily 等）は別途データ取り込みが必要です（研究 / ファクター計算で利用）。

使い方
------

- 実行エンジン（ExecutionEngine）を起動
  - 本番/紙運用の切り替え:
    - KABUSYS_ENV=paper_trading を設定すると、MockBrokerClient を使用し paper_trading 用の SQLite に記録されます。
  - 実行:
    - python src/kabusys/run_execution.py
    - （あるいは環境に合わせてモジュールとして）python -m kabusys.run_execution

- 監視ループを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60 秒）。
  - 実行:
    - python src/kabusys/run_monitoring.py
    - （ログレベル等は Settings.log_level / 環境変数で調整）

- Streamlit ダッシュボード（監視画面）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開き、ダッシュボードを表示します。

- Paper Trading 検証レポート生成
  - 使い方:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定:
      python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - データベース指定:
      python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニューススコア / レジーム判定）
  - ニューススコアリング（ai_scores 書込）:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

運用に関する注意点
------------------
- run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視データを記録します（監視は本番 DB を前提）。
- paper_trading では本番 DB と完全分離された PAPER_TRADING_SQLITE_PATH を使用する設計です。
- kill.flag（Settings.kill_flag_path）を監視システムが生成すると、ExecutionEngine は停止シグナルを受け取って安全に停止できます。Execution 起動時にフラグの自動クリアを有効にするオプション（KILL_FLAG_CLEAR_ON_START）があります。
- OpenAI 呼び出しは外部 API を利用するため、API エラーやレート制限を考慮したリトライ・フォールバック実装がありますが、API キー管理とコスト管理は運用者責任です。
- Process priority / CPU affinity はプラットフォーム依存（psutil を利用）ですが、権限不足時はワーニングを出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
プロジェクトの主要ファイル・モジュール構成は以下のとおりです（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env 読み込みと Settings
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — レジーム判定（ETF MA + マクロニュース）
  - monitoring/
    - __init__.py
    - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
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
    - （他の broker / engine / order_repository 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定出力格納場所、デフォルト)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

開発者向けメモ
--------------
- .env の自動ロードはプロジェクトルート（.git / pyproject.toml を検出）に依存します。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）は研究機能で参照されます。これらのデータソースは運用側で用意してください。
- MonitoringDB のテーブル作成・マイグレーションは init_monitoring_db() が担当します。既存 DB に対するカラム追加（例: latency_ms, peak_value）の処理も含まれています。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py 内の __version__ を参照してください（現状 0.1.0）。

サポート / 連絡
---------------
実運用・拡張・データ投入・OpenAI API の取り扱い等に関する質問があれば、プロジェクト運営チームと相談してください。

以上がこのリポジトリの README 相当の概要です。必要であればインストール用の requirements.txt、.env.example、起動スクリプト（systemd / supervisord）サンプルなどのテンプレートを追記します。どれを追加しますか？