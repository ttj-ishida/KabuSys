KabuSys — 日本株自動売買フレームワーク
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なソフトウェア基盤です。  
主に以下の用途を想定しています:

- ポートフォリオ構築（候補選定 / 重み計算 / ポジションサイズ算出）
- ファクター計算・特徴量探索（DuckDB を用いたオフラインリサーチ）
- ニュースの LLM（OpenAI）によるセンチメント評価・市場レジーム判定
- 注文管理・ブローカー API 抽象化・リコンシリエーション
- 運用時の監視・アラート（LINE Push、SQLite ベースの監視 DB）
- 実行エンジン（Signal → Order の処理ループ、WebSocket push ドレイン）

設計方針の要点
- 多くのモジュールは純粋関数（副作用を持たない）または DB/ブローカー接続を注入する設計。
- ルックアヘッドバイアスに配慮（日付参照は外部から与える設計）。
- OpenAI 呼び出しのフェイルセーフ化（失敗時にスコアをフォールバック）。
- .env ファイル自動ロード機能（プロジェクトルート判定により .env/.env.local をロード）。

主な機能
--------
- 環境設定管理（kabusys.config.Settings）
  - .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
  - 必須/任意設定の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）
- ポートフォリオ構築（kabusys.portfolio）
  - シグナル選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数（risk_adjustment）
  - ポジションサイズ計算（risk_based / equal / score）
- リサーチ（kabusys.research）
  - Momentum / Volatility / Value ファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news を集約して OpenAI（gpt-4o-mini）へ送信し銘柄毎にセンチメントを ai_scores に書き込み
  - バッチ化・トークン/文字数制限・リトライ・レスポンスバリデーション実装
- レジーム検出（kabusys.ai.regime_detector）
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して daily regime を判定
- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
  - System/Trade/Risk Monitor、KillSwitch、AlertManager（LINE Push）
  - Streamlit ダッシュボードの簡易 UI
- 実行（kabusys.execution）
  - Broker API 抽象（Protocol）・OrderRequest/Response モデル
  - OrderManager（状態遷移・DB 永続化）、ExecutionEngine（Signal→Order ループ）
  - Reconciler（起動時の自動復旧・ポジション照合）

要件
----
- Python 3.10+
- 主要依存ライブラリ（例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
- SQLite（標準ライブラリ）
- 実際のブローカー統合には別途ブローカークライアントの実装が必要

インストール（例）
-----------------
1. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS) / .venv\Scripts\activate (Windows)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai requests psutil streamlit

   ※ プロジェクト提供の requirements.txt がある場合はそれを使用してください。

環境変数 / .env
---------------
プロジェクトルート（.git または pyproject.toml がある階層）にある .env/.env.local を自動で読み込みます（OS 環境変数が優先）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（代表）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用トークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): デフォルト "http://localhost:18080/kabusapi"
- OPENAI_API_KEY (必要時): OpenAI API キー（news_nlp / regime_detector が使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager の通知先
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH: Paper Trading 関連
- KABUSYS_ENV: development | paper_trading | live
- LOG_LEVEL: DEBUG|INFO|...

サンプル .env（最小例）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...

使い方（代表例）
----------------

1) DuckDB を使ったファクター計算（Python から）
- DuckDB 接続を渡して関数を呼ぶだけです。

例:
- from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

2) ニュース NLP スコア付け（OpenAI 必須）
- DuckDB 接続と target_date を渡して score_news を呼びます。

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026,3,20), api_key="sk-...")

3) レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,3,20), api_key="sk-...")

4) 監視 DB 初期化（最初に一度）
  import sqlite3
  from kabusys.monitoring import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)

5) Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

6) ExecutionEngine を使った運用（本番）
- 実際に発注を行うには BrokerAPIProtocol を実装したクライアントと OrderRepository 等のセットアップが必要です。ExecutionEngine は以下のようなコンポーネントを受け取ります:
  - broker (BrokerAPIProtocol 実装)
  - repo (OrderRepository)
  - risk_manager (RiskManager)
  - order_manager (OrderManager)
  - duckdb_conn (DuckDB 接続)
  - config (EngineConfig)
  - reconciler (任意)
- 実行前に kill.flag / PID に関する設定や MonitoringDB の初期化を行ってください。

運用上の重要点
--------------
- kill.flag: settings.kill_flag_path（デフォルト data/kill.flag）への書き込みで ExecutionEngine を安全に停止できます。起動時に存在する場合は設定に応じて拒否または自動クリアされます。
- PID ファイル: 起動時に settings.pid_file_path（デフォルト data/execution.pid）へ PID を書き込みます。古い PID の検出・クリーンアップ機能あり。
- OpenAI 呼び出し: 429 / ネットワークエラー / 5xx に対するリトライロジックを含みます。API キーの管理に注意してください。
- DuckDB / SQLite のバックアップ・ロック等は運用で考慮してください（特に並列更新時）。

ディレクトリ構成（src/kabusys の主要ファイル）
--------------------------------------------
- kabusys/__init__.py
- kabusys/config.py
  - 環境変数・.env 管理、Settings クラス
- kabusys/portfolio/
  - portfolio_builder.py (select_candidates, calc_equal_weights, calc_score_weights)
  - position_sizing.py (calc_position_sizes)
  - risk_adjustment.py (apply_sector_cap, calc_regime_multiplier)
- kabusys/research/
  - factor_research.py (calc_momentum, calc_volatility, calc_value)
  - feature_exploration.py (calc_forward_returns, calc_ic, factor_summary, rank)
- kabusys/ai/
  - news_nlp.py (score_news)
  - regime_detector.py (score_regime)
- kabusys/monitoring/
  - monitoring_db.py (init_monitoring_db, MonitoringDB)
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - alert_manager.py (LINE Push)
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- kabusys/execution/
  - broker_api.py (データモデル・Protocol・例外)
  - order_manager.py (OrderManager)
  - order_repository.py (DB 層 — 注: 実装ファイルはプロジェクトにより存在)
  - reconciler.py
  - execution_engine.py
- kabusys/ai/__init__.py, kabusys/research/__init__.py, kabusys/monitoring/__init__.py, kabusys/portfolio/__init__.py などエクスポート用

テスト・開発
------------
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップでき、テストで環境を分離できます。
- OpenAI 呼び出しはモジュール内で呼び出し箇所を分離しているため、unit test では _call_openai_api を patch してスタブ化できます（news_nlp, regime_detector 共にその設計）。

貢献・拡張ポイント
-----------------
- ブローカー固有の BrokerAPIProtocol 実装を追加することで実運用が可能になります（kabuステーション等）。
- stocks マスタに単元株情報を持たせ、position_sizing の lot_size を銘柄毎に対応させる拡張がコメントに示されています。
- ファクターの追加 / 正規化ユーティリティ（zscore_normalize）は kabusys.data.stats に用意して利用してください。

ライセンス
---------
（このリポジトリにライセンス情報がある場合はここに記載してください）

補足
----
この README はソースコードのドキュメントを基に作成しています。実際の利用にあたっては各モジュールの docstring（関数 / クラスの説明）と環境変数の設定を必ず確認してください。必要であれば、具体的な起動スクリプトやサンプル設定ファイル (.env.example) をプロジェクトルートに用意することを推奨します。