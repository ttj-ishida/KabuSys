KabuSys — 日本株自動売買システム（README）
=======================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なシステム群です。
主要機能は注文発行・リコンシリエーション・ポートフォリオ構築、ファクター計算、ニュース NLU によるセンチメント評価、監視・アラート機能などを含みます。DuckDB を用いたリサーチ用データ処理、SQLite による軽量な永続化、OpenAI（gpt-4o-mini）を用いたニュース評価を想定しています。

主な特徴（機能一覧）
------------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / paper_trading モードの切替（環境変数 KABUSYS_ENV）
  - Broker クライアント抽象化（実ブローカー / MockBroker の切替）
  - リスク管理（RiskManager）・OrderManager・Reconciler による再起動リカバリ
- Monitoring（監視）コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常の検出
  - RiskMonitor: ドローダウン／ポジション数監視と kill.flag の発行
  - AlertManager: LINE Push による通知
  - MonitoringEngine: 複数モニターのポーリング統合
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio 構築モジュール
  - 候補選定、等配分 / スコア配分、ポジションサイズ計算、セクターキャップ、レジーム係数
- Research（ファクター計算・特徴量解析）
  - momentum / volatility / value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算・IC 計算・統計サマリー
- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news(): raw_news を LLM に投げ銘柄ごとにスコア化して ai_scores に書込
  - regime_detector.score_regime(): ETF MA とマクロニュースの LLM 評価を組み合わせて market_regime を算出
- ユーティリティ
  - process_priority（プロセス優先度 / CPU affinity）
  - 設定管理（.env 自動読み込み・Settings）

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（型注釈や機能を利用）
- system に次のライブラリをインストールします（例）:

  pip install duckdb psutil openai requests streamlit

（プロジェクトに requirements.txt がある場合はそれを使用してください）

仮想環境（例）
- python -m venv .venv
- source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip install --upgrade pip
- pip install duckdb psutil openai requests streamlit

環境変数 / .env
- プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 主要な環境変数（主なものを抜粋）:
  - KABUSYS_ENV: development | paper_trading | live（default: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、default: instant）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
  - SQLITE_PATH: monitoring DB（default: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
  - PID_FILE_PATH / KILL_FLAG_PATH: 各種パス（default: data/execution.pid, data/kill.flag）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default: 60）

使い方（実行例）
----------------

1) ExecutionEngine を起動（本番／ペーパートレード）
- 本番環境（デフォルト）:
  KABUSYS_ENV=live python src/kabusys/run_execution.py
- Paper trading 環境（MockBroker を使用、DB を分離）:
  KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py

run_execution は Settings を読み取り、paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

2) Monitoring を起動（ポーリング）
- 環境変数でポーリング間隔を上書き:
  MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py
- 動作: PID ファイルの存在や Execution プロセス生存、システム資源・データ鮮度を定期ログ（SQLite）に記録します。
- 注意: Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログを統一するため）。

3) Streamlit ダッシュボード
- 起動例:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ブラウザで監視 DB の状態を確認できます（読み取り専用URIで接続）。

4) Paper Trading 検証レポート
- コマンドラインから生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- 引数 --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）。

5) AI モジュールの利用（ニューススコア / レジーム判定）
- Python スクリプトまたは REPL から呼び出します。例（概念）:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")

  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を参照します。
  - API 呼び出しはリトライ・フォールバックロジックを備えています（失敗時は安全側の値で継続）。

設定管理の挙動
----------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml がある場所）を起点に .env/.env.local を読み込みます。
  - OS 環境変数は保護され、.env は既存値を上書きしません（.env.local は override=True だが OS 環境は保護される）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- Settings クラス（src/kabusys/config.py）にプロジェクトで使用する環境変数とデフォルト値、バリデーションが定義されています。必須項目が未設定の場合は ValueError を投げます。

データベース（デフォルトパス）
----------------------------
- monitoring DB (SQLite): data/monitoring.db
- paper trading DB (SQLite): data/paper_trading.db
- DuckDB: data/kabusys.duckdb

- run_execution は paper_trading モードであれば紙トレ用 DB に接続して本番 DB と明確に分離します。monitoring 側は常に sqlite_path（本番）を参照します。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py: パッケージ定義
- config.py: 環境変数 / Settings 管理（.env 自動読み込み）
- run_execution.py: ExecutionEngine 起動スクリプト
- run_monitoring.py: SystemMonitor 用ポーリング起動スクリプト

パッケージ（機能別）
- kabusys/execution/
  - order_manager.py, reconciler.py, ... （発注ロジック / ブローカー抽象）
- kabusys/monitoring/
  - monitoring_db.py: SQLite テーブル定義と CRUD
  - system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_engine.py, kill_switch.py, alert_manager.py
  - streamlit_dashboard.py
- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- kabusys/research/
  - factor_research.py, feature_exploration.py
- kabusys/ai/
  - news_nlp.py, regime_detector.py
- kabusys/utils/
  - process_priority.py
- kabusys/tools/
  - paper_verification_report.py

開発メモ / 注意点
-----------------
- process_priority.set_process_priority() はプラットフォーム差を吸収しつつアクセス権限エラーをログに落として処理を継続します。
- MonitoringDB.init_monitoring_db は冪等でマイグレーション（カラム追加）を簡易的に行います。
- DuckDB 周りは読み取り専用クエリや分析処理が中心で、CSV 等のデータ投入は想定外のため手順が別に必要です（プロジェクト内参照）。
- OpenAI 呼び出しは外部 API に依存するため、テスト時は各モジュール内の _call_openai_api をモックする設計になっています。
- セキュリティ: API キーやパスワード等は .env / 環境変数で管理し、リポジトリに含めないでください。

ライセンス・貢献
----------------
- 本コードベースのライセンスや貢献ルールはリポジトリのルートに記載してください（ここでは省略）。

問題の報告や問い合わせ
---------------------
- バグ報告 / 要望はリポジトリの issue に記載してください。README に記載の手順で再現手順と環境変数のダンプ（機密情報はマスク）を添えてください。

以上。必要があれば各コマンドの具体例（systemd サービス化、Dockerfile、CI 設定など）や詳細な環境変数一覧・.env.example を追加で作成します。どの情報が欲しいか教えてください。