# KabuSys — README

※この README はコードベース（src/kabusys 以下）を元に作成した開発者向けのドキュメントです。

概要
---
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリには以下の主要機能を備えるモジュール群が含まれます。

- 注文管理・執行（ExecutionEngine、OrderManager、Reconciler 等）
- リスク管理・監視（RiskMonitor、SystemMonitor、TradeMonitor、MonitoringEngine）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ（ファクター計算、特徴量解析）
- AI（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な特徴
---
- duckdb / sqlite を使った履歴・分析ストレージ
- Production / Paper Trading を環境変数で切替可能（KABUSYS_ENV）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント・市場レジーム判定
- 監視エンジンと LINE 通知によるアラート（AlertManager）
- 起動時の自動リコンシリエーション機能（再起動後の注文同期）
- Streamlit ベースの監視ダッシュボード

セットアップ
---
前提
- Python 3.10 以上（PEP 604 の型記法を使用しているため）
- sqlite3（標準モジュール）
- システムに応じた開発ツール（ビルド不要なパッケージ中心）

推奨パッケージ（例）
- duckdb
- psutil
- openai
- requests
- streamlit

例: pip によるインストール
- 仮想環境推奨（venv / poetry 等）
- pip install duckdb psutil openai requests streamlit

環境変数 / .env
- 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。
- 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

主な環境変数（代表）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading 時は専用の Paper DB を使い、MockBrokerClient を利用する設計です
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の可能性あり）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須の可能性あり）
- OPENAI_API_KEY: OpenAI API 呼び出しに利用
- PAPER_FILL_MODE: paper_trading 時の挙動（instant/partial/never/reject、デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH: paper DB のパス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: ExecutionEngine 停止フラグ（デフォルト: data/kill.flag）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用、デフォルト 60）。1 未満または不正値は無視されデフォルトにフォールバック。

使い方（起動例）
---

1) 監視ループ（SystemMonitor）
- 目的: システム状態・データ鮮度・各種監視を定期実行し SQLite に永続化
- 実行スクリプト: src/kabusys/run_monitoring.py
- 起動例:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL は秒数（1秒以上）で上書き可
- 特記事項:
  - 実行開始時にプロセス優先度を "high" に設定しようとします（psutil に依存）
  - monitoring は KABUSYS_ENV にかかわらず production (= Settings.sqlite_path) の DB を使用する点に注意

2) 実行エンジン（ExecutionEngine）
- 目的: ブローカーへ注文を送るエンジン（本番 / ペーパー切替）
- 実行スクリプト: src/kabusys/run_execution.py
- 起動例:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 特記事項:
  - paper_trading 環境時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離
  - 起動時に set_process_priority("high") を呼び出します
  - ExecutionEngine は BrokerClientFactory を通じて Broker を生成します（環境に応じて Mock など）

3) Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で別 DB 指定可能。または環境変数 PAPER_TRADING_SQLITE_PATH を使用
- 出力: 稼働率、注文成功率、送信率、レイテンシ統計 (P95 など)、PASS/FAIL 判定

4) Streamlit ダッシュボード
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能: ダッシュボード（Overview / Positions / Orders / System）をブラウザで閲覧

5) AI 機能（ニュースセンチメント / レジーム判定）
- ニューススコア: kabusys.ai.news_nlp.score_news
  - DuckDB から raw_news / news_symbols を読み取り、OpenAI API で銘柄別スコアを ai_scores テーブルへ書き込み
  - バッチ処理、リトライ、レスポンスバリデーション等を実装
- レジーム判定: kabusys.ai.regime_detector.score_regime
  - ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルに記録
- どちらも OPENAI_API_KEY が必要（引数で渡すことも可能）。API 失敗時は安全にフォールバックする設計。

ディレクトリ構成（主要ファイル）
---
以下は src/kabusys ディレクトリの主要ファイルおよびモジュールです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env のロードと Settings クラス
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite を使った監視ログ層（テーブル初期化・CRUD）
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag を書き込むロジック
    - alert_manager.py             — LINE Push を使ったアラート送信
    - monitoring_engine.py         — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py       — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - (Broker 関連、order_repository 等: 実装ファイル群)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py                   — ニュースを OpenAI でスコアリング
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity 設定ユーティリティ
    - __init__.py
  - data/ (期待されるデータフォルダ、デフォルト DB 等)
    - kabusys.duckdb (default: data/kabusys.duckdb)
    - monitoring.db (default: data/monitoring.db)
    - paper_trading.db (default: data/paper_trading.db)

注意事項・実装上のポイント
---
- Settings と .env
  - config.Settings は .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動ロードします。OS 環境変数が優先され、.env.local は上書きします。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードは無効化されます（テスト用）。
- DB 初期化
  - monitoring_db.init_monitoring_db(conn) は冪等的にテーブルを作成し、必要なカラム追加（マイグレーション）を行います。スクリプト起動時に呼ばれます。
- プロセス優先度 / CPU affinity
  - set_process_priority で Windows/Linux の差を吸収して優先度を設定します（psutil に依存）。権限不足時は警告を出してスキップします。
- Kill Switch
  - RiskMonitor 等の結果によって KillSwitch が data/kill.flag を書き込み、ExecutionEngine 停止の合図を送ります。flag は冪等に書き込まれます。
- Paper Trading
  - paper_trading 環境は本番 DB と完全分離する設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出し
  - AI モジュールは OpenAI のレスポンスを厳密に検証し、429/タイムアウト/5xx に対して指数バックオフでリトライします。API キー未設定時は ValueError を投げる箇所があります。

よく使うコマンドまとめ
---
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

最後に
---
この README は現状のコードベース（提供されたファイル群）をもとにした概要・使い方ガイドです。実行時に足りない依存や追加の設定がある場合があります（Broker 実装、外部 API の認証等）。ローカルで実行する前に .env.example を参照し必要な環境変数をセットしてください。必要であれば README を拡張してセットアップスクリプトや Docker Compose の説明を追加できます。