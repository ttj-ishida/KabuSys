KabuSys — README (日本語)
========================

概要
----
KabuSys は日本株を対象とした自動売買／リサーチ／監視を行う小規模なシステム群です。  
主な機能は以下のとおりです（発注/ブローカー統合・リスク管理・監視・ファクター計算・ニュースNLPなど）。  
このリポジトリはライブラリ／CLI スクリプト群と、監視ダッシュボード（Streamlit）、検証レポート生成ツールを含みます。

機能一覧
--------
- Execution（発注エンジン）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントのファクトリ（paper_trading モードで MockBroker を使用）
  - OrderManager / OrderRepository / Reconciler による注文ライフサイクル管理と再同期
  - リスク管理（ポジション上限・利用率など）
- Monitoring（運用監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - kill.flag による ExecutionEngine 停止シグナル
  - Streamlit を用いた監視ダッシュボード（read-only）
- Research（リサーチ）
  - DuckDB ベースのファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算・IC（情報係数）・ファクター統計
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重の重み計算、リスク調整（セクター上限、レジーム乗数）
  - 株数計算（単元丸め、リスクベース配分、集約キャップ）
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントスコアリング（ai.news_nlp.score_news）
  - マクロニュース + ETF MA を用いた市場レジーム判定（ai.regime_detector.score_regime）
- Tools
  - paper_trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提 / 依存
------------
- Python 3.9+（ソースの型注釈は 3.10+ を想定する箇所あり）
- 必要な主なパッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（組み込み）
- ネットワーク接続（ブローカーAPI / OpenAI を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repo-url>
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限の例）:
   - pip install duckdb psutil requests openai
   - （監視ダッシュボードを使う場合）pip install streamlit
4. 環境変数設定:
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。
   - 必須例（.env.example を参考に作成してください）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
   - 任意 / デフォルト（必要に応じて上書き）:
     - KABUSYS_ENV=development | paper_trading | live  (デフォルト: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=... (AI 機能を使う場合)
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60  (監視ループ間隔: 秒)
     - PAPER_FILL_MODE=instant|partial|never|reject  (paper_trading の約定モード)
5. データディレクトリ作成:
   - mkdir -p data

使い方
------
- 実運用の監視ループ（SystemMonitor 単体を回す）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更できます（デフォルト 60）。
  - Monitoring は常に本番用 sqlite_path を使用します（KABUSYS_ENV に依存せず）。

- ExecutionEngine 起動（発注エンジン）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil によるため権限によっては警告が出ます）。

- 監視ダッシュボード（Streamlit）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザでダッシュボードを開き、監視データを確認できます（読み取り専用推奨）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）
  - 期間を指定するとその期間の稼働率・注文成功率・レイテンシ等をレポートします。

- AI / リサーチ関数をプログラムから呼ぶ（例: ニューススコアリング）:
  - Python から直接関数を呼べます（DuckDB 接続を用意する必要あり）。
  - 例（概略）:
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - OpenAI API キーが未設定だと例外になります。

- 設定の自動読み込み:
  - config モジュールはプロジェクトルート（.git または pyproject.toml）を探し、.env / .env.local を自動ロードします。
  - OS 環境変数は上書きされません（.env.local は override=True ですが OS 環境変数は protected）。

注意点 / 運用上のポイント
-------------------------
- run_monitoring は常に本番用 sqlite_path を使います。paper_trading を分離したい場合は run_execution 側の PAPER_TRADING_SQLITE_PATH を利用してください。
- kill.flag 機構により監視側から ExecutionEngine 停止を指示できます。flag ファイルは Settings.kill_flag_path（デフォルト data/kill.flag）。
- paper_trading モードでは PAPER_FILL_MODE によって MockBroker の約定挙動が変化します（instant/partial/never/reject）。
- OpenAI 呼び出しはネットワーク依存かつレート制限があり、リトライ戦略を組み込んでいますが API キーの管理に注意してください。
- プロセス優先度や CPU affinity の設定は psutil に依存し、権限不足で警告が出ることがあります。
- DuckDB の SQL クエリはファクター計算やニュース集計で主要に使用します。prices_daily / raw_financials / raw_news 等のテーブルスキーマに依存します。

ディレクトリ構成（抜粋）
--------------------
- src/kabusys/
  - __init__.py
  - config.py                         （環境変数・設定管理）
  - run_monitoring.py                 （SystemMonitor ポーリング起動）
  - run_execution.py                  （ExecutionEngine 起動）
  - utils/
    - process_priority.py             （プロセス優先度 / affinity ユーティリティ）
  - monitoring/
    - __init__.py
    - monitoring_db.py                （SQLite 永続化層）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (OrderRepository / broker_api など)
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
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/ (想定データディレクトリ)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - monitoring.db  (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)

開発時のヒント
---------------
- .env のパースは config._load_env_file で独自実装されています。export KEY=val 形式やクォート・インラインコメントの扱いに対応しています。
- DuckDB を使ったリサーチ関数は副作用を持たず、純粋な SQL / Python 演算でファクターを返す設計です。テストしやすく、外部 API に依存しません（AI 部分を除く）。
- monitoring_db.init_monitoring_db は冪等でマイグレーション（列追加）を行います。既存 DB に互換性のための処理があります。

ライセンス / 貢献
----------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（存在しない場合は要確認）。
- バグ報告・機能要望は Issue を立ててください。プルリクエスト歓迎です。

以上。導入や実運用で不明点があれば、どの機能を使いたいかを教えてください。具体的な起動コマンドや .env のサンプルを併せて案内します。