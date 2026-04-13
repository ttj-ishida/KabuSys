README
=====

概要
----
KabuSys は日本株の自動売買システムのコンポーネント群です。本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ／ファクター計算、AI（ニュースセンチメント／レジーム判定）などを含むモジュール群を提供します。設計方針として、可能な限り純粋関数化・DB分離・ルックアヘッドバイアス回避が考慮されています。

主な特徴
---------
- Execution Engine 起動・再起動時のリコンシリエーション（Reconciler）
- Paper Trading（KABUSYS_ENV=paper_trading）用の分離された SQLite DB
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- 監視ログ用 SQLite（init_monitoring_db による自動初期化）
- Streamlit ベースの監視ダッシュボード
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算（Momentum / Volatility / Value）および特徴量解析（IC, summary）
- ニュースの LLM ベースセンチメント評価（OpenAI API を用いるバッチ処理）
- 市場レジーム判定（ETF + マクロニュース + LLM）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）

前提・依存
----------
- Python 3.10+
- 外部ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリに同梱）
- ネットワーク（OpenAI や LINE API を利用する場合）

インストール（例）
-----------------
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

3. ソース配置
   - 本リポジトリのルートに `src/` が存在している想定です。
   - 必要に応じて pyproject.toml / setup を整備してください。

設定（環境変数）
----------------
本プロジェクトは .env / .env.local からの自動読み込みを行います（プロジェクトルートに .git または pyproject.toml がある場合）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須な機能がある場合）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading 時の fill 動作（instant | partial | never | reject。デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視（monitoring）用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアする場合は "1"
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）

セットアップ手順（初回）
----------------------
1. data ディレクトリなど必要ディレクトリを作成
   - mkdir -p data

2. DuckDB / SQLite ファイルの初期化は各起動スクリプトが自動で行います。
   - 監視 DB の初期化: run_monitoring / run_execution が内部で init_monitoring_db を呼びます。
   - DuckDB のテーブルは外部 ETL / pipeline により用意する想定（prices_daily, raw_financials, raw_news 等）。

実行方法
--------
- 監視ループの起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

  特記事項:
  - 監視は Settings に基づき本番 sqlite_path を使用（環境値に関係なく監視DBは本番パスを参照）。
  - 起動時にプロセス優先度を "high" に設定します（psutil を使用）。

- 実行エンジンの起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH にデータを記録します（本番 DB と完全分離）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易的に uptime, fill_rate, send_rate, latency(P95) などをレポートします。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で表示。監視エンジンを起動していないと DB が無くエラーになります。

- AI / レジーム機能（プログラム呼び出し例）
  - Python API 経由で利用:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

  - OpenAI API キーが必須（api_key 引数か OPENAI_API_KEY 環境変数）。

主要モジュールと責務（簡易）
--------------------------
- kabusys.config
  - 環境変数読み込み・検証。Settings クラスを通じて各種設定を提供。
- kabusys.monitoring
  - monitoring_db: 監視用 SQLite スキーマ・永続化 API
  - system_monitor / trade_monitor / risk_monitor: 各種チェック
  - monitoring_engine: 複数モニタの統合ループ
  - kill_switch: 条件により ExecutionEngine 停止フラグを書き込む
  - alert_manager: LINE Push 通知
  - streamlit_dashboard: 簡易 Web ダッシュボード
- kabusys.execution
  - order_manager / order_repository / reconciler / execution_engine（起動スクリプトから利用）
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment（候補選定・重み付け・株数計算・セクター制限）
- kabusys.research
  - factor_research: momentum / volatility / value 等のファクター計算（DuckDB 前提）
  - feature_exploration: 将来リターン計算、IC、統計サマリー
- kabusys.ai
  - news_nlp: ニュースセンチメント集約および OpenAI 呼び出しロジック
  - regime_detector: マクロ記事 + ETF ma200 を統合したレジーム判定

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- monitoring_engine.py
- kill_switch.py
- alert_manager.py
- streamlit_dashboard.py
- __init__.py

src/kabusys/execution/
- order_manager.py
- reconciler.py
- (その他: broker_factory 等)

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py

src/kabusys/utils/
- process_priority.py

運用上の注意 / ベストプラクティス
---------------------------------
- Paper Trading は本番 DB と厳密に分離されています。KABUSYS_ENV=paper_trading を利用してください。
- OpenAI API 呼び出しはレート制限や一時エラーを想定しており、リトライやフェイルセーフ（スコア=0にフォールバック等）が組み込まれていますが、実運用では API キー・コスト管理に注意してください。
- kill.flag による停止は冪等で、既に存在する場合は書き換えません。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を使ってクリアする運用も可能です。
- monitoring の初回実行で DB スキーマが自動作成・マイグレーションされます（列追加処理あり）。
- 並列プロセス環境では PID ファイルと kill.flag の扱いに注意してください（stale PID 検出ロジックあり）。

開発・テスト
-----------
- Settings の自動 .env ロードを無効化してユニットテストを行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- OpenAI 呼び出しや外部 API 呼び出しはモック化（unittest.mock）可能な設計になっています（_call_openai_api 等を patch）。

付記
----
本 README はコードベースの主要箇所を要約したものです。詳細な設計（PortfolioConstruction.md / StrategyModel.md 等）は別ドキュメントを参照してください（コード中のコメントで参照箇所が記載されています）。問題や補足が必要であれば告知してください。