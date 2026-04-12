KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買／研究／監視を支援する Python コードベースです。戦略のファクター計算、ポートフォリオ構築、発注管理、監視・アラート、Paper Trading 検証ツール、LLM を用いたニュースセンチメント評価などのコンポーネントで構成されています。

主な設計方針
- DuckDB / SQLite を使ったデータレイヤ（価格データは DuckDB、監視ログは SQLite）。
- 本番・Paper Trading を環境変数 KABUSYS_ENV で切替（development / paper_trading / live）。
- 自動化ジョブ（ExecutionEngine / MonitoringEngine）はプロセス優先度や PID / kill フラグを用いて管理。
- OpenAI（gpt-4o-mini）を用いたニュース NLP / レジーム判定（API キー必須）。API 呼び出しはフォールバック・リトライ等の安全策あり。
- .env / .env.local の自動読み込み機能（プロジェクトルート検出）／無効化オプションあり。

機能一覧
--------
- execution（発注関連）
  - OrderManager、Reconciler による発注・再同期ロジック
  - BrokerClientFactory による本番 / モックブローカー切替（paper_trading 時は mock）
- portfolio（ポートフォリオ構築）
  - 候補選定（スコア順）、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research（研究用ファクター計算）
  - momentum / volatility / value ファクター計算、将来リターン・IC・統計サマリ等
- ai（LLM を用いた機能）
  - ニュースセンチメント（news_nlp.score_news）
  - レジーム判定（regime_detector.score_regime）
- monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite ベースの監視 DB とストリーミングダッシュボード（Streamlit）
  - LINE プッシュ通知（AlertManager）
  - KillSwitch（指定条件で ExecutionEngine 停止フラグ作成）
- tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.9+（ソースは typing 機能を利用）
- DuckDB, psutil, openai, requests, streamlit 等の依存ライブラリ

推奨インストール手順（例）
1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数の設定:
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（代表例）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の資格情報（必要に応じて設定）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のパス（デフォルトは data 以下）

使い方
------
起動スクリプト
- ExecutionEngine（発注エンジン）起動:
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。

- Monitoring（監視）起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - Monitoring は常に本番 sqlite_path を使って監視ログを保存します（環境に依らず）。

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代替）
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データベースは読み取り専用で開かれます。MonitoringEngine を先に起動してデータを作成してください。

AI 関連
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要（関数に api_key を渡すことも可）
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 同じく OPENAI_API_KEY が必要

設定・動作の注意点
- .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml がある場所）を探索して .env / .env.local を読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きできます。
- Process Priority:
  - 起動スクリプトは最初に set_process_priority("high") を試みます（psutil による実装）。権限がないと警告になりますが実行自体は継続します。
- PID / Kill Flag:
  - ExecutionEngine は PID ファイルを書き、Monitoring 側はそれをチェックします。KillSwitch は data/kill.flag を書いて ExecutionEngine 停止を指示します。
- DB マイグレーション:
  - init_monitoring_db(conn) は冪等でテーブル作成および簡単なカラム追加（マイグレーション）を行います。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / 設定管理（.env 自動読み込み）
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト

パッケージ（主要）
- ai/
  - news_nlp.py                 — ニュースセンチメント取得（OpenAI）
  - regime_detector.py         — 市場レジーム判定（MA + LLM 合成）
- execution/
  - order_manager.py           — 発注状態遷移を扱う外向き API
  - reconciler.py              — 起動時の受注再同期・ポジション照合
  - （その他 broker_factory 等）
- monitoring/
  - monitoring_db.py           — SQLite 監視ログ層（init / CRUD）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py
- tools/
  - paper_verification_report.py

重要なファイル / 設定の一覧
- data/kabusys.duckdb          — DuckDB（デフォルトパス）
- data/monitoring.db           — 監視用 SQLite（デフォルト）
- data/paper_trading.db        — Paper Trading 用 SQLite（paper_trading 環境時）
- data/execution.pid           — ExecutionEngine の PID（デフォルト）
- data/kill.flag               — KillSwitch による停止フラグ

開発者向けメモ
----------------
- DuckDB クエリは関数内で直接実行しており、テスト時はモック接続を渡すことで副作用を防げます。
- AI 呼び出し（OpenAI）は retry / backoff ロジックを含みますが、テストでは _call_openai_api をモックすることが想定されています。
- .env のパースはシェル形式の一部をサポート（export プレフィックス、クォート、インラインコメントなど）。

ライセンス・貢献
----------------
（このリポジトリのライセンス／貢献方法についてはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。無い場合はリポジトリ所有者に問い合わせてください。）

問い合わせ / サポート
--------------------
- 実行時のログは標準の logging を用いて INFO レベルで出力されます。問題発生時はログと使用している環境変数を添えて報告してください。
- OpenAI を利用する機能は API キーや通信の安定性に依存するため、キー設定・ネットワーク状況・レート制限に注意してください。

以上。必要であれば README に含めるコマンド例や .env.example のテンプレートを生成します。どの情報を追加しますか？