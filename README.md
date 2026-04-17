KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム「KabuSys」のコアライブラリ群です。
コンポーネントには実行エンジン（ExecutionEngine）、監視（Monitoring）、
ポートフォリオ構築、リサーチ（ファクター計算）やニュースNLP / レジーム判定などが含まれます。

主な目的は
- 日次の銘柄選定・配分・株数決定のロジック（純粋関数として実装）
- 実売買の発注管理と再同期（Reconciler）
- システム稼働・注文状態の監視とアラート（LINE）
- Paper Trading 用の完全分離 DB と検証ツール
- ニュースを LLM（OpenAI）で評価して銘柄センチメントやレジーム判定に活用

機能一覧
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番／Paper Trading を区別して専用 DB を使用
  - Broker クライアントの抽象化（モック含む）、OrderManager、RiskManager、Reconciler 組み立て
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk・プロセス生存・データ鮮度を監視し SQLite に永続化
  - TradeMonitor: 滞留注文・約定異常価格を検出してログ/リスクイベント記録
  - RiskMonitor: ドローダウン監視・ポジション上限監視
  - KillSwitch / AlertManager: 閾値で flag ファイルを書き ExecutionEngine 停止や LINE 送信
  - MonitoringEngine / run_monitoring.py: ポーリングループ起動用
  - Streamlit ダッシュボード（streamlit_dashboard.py）
- Portfolio construction
  - 候補選定、等配分・スコア加重、セクターキャップ、レジーム乗数、株数算出（単元丸め、リスク制約）
- Research
  - DuckDB ベースのファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI を利用）
  - ニュース NLU による銘柄センチメント（ai.news_nlp.score_news）
  - マクロニュース + ETF MA による市場レジーム判定（ai.regime_detector.score_regime）
- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ（psutil を利用）
  - .env 自動読み込みと Settings ラッパ（環境変数管理）

前提・必須ソフトウェア
---------------------
- Python 3.10+（型注釈で一部 union など使用）
- pip install 可能な以下パッケージ（後述の requirements を参照）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリ sqlite3 を使用）
- ネットワーク（OpenAI / LINE API を使う場合）

推奨 requirements.txt（例）
- duckdb
- psutil
- openai
- requests
- streamlit

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は上のパッケージ群を個別に pip install）

4. データディレクトリを作る
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートの .env / .env.local を用意できます（自動読み込みあり）
   - 主要な環境変数（.env の例）:
     - KABUSYS_ENV=development|paper_trading|live          （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN=your_jquants_token            （必須: 一部機能で使用）
     - KABU_API_PASSWORD=your_kabu_password                （必須: 本番でのブローカ接続）
     - OPENAI_API_KEY=sk-...                               （AI 機能を使う場合）
     - DUCKDB_PATH=data/kabusys.duckdb                     （デフォルト）
     - SQLITE_PATH=data/monitoring.db                      （監視用 DB）
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db     （paper_trading 用 DB）
     - LINE_CHANNEL_ACCESS_TOKEN=...                       （LINE アラート用）
     - LINE_USER_ID=...                                    （LINE アラート用）
     - LOG_LEVEL=INFO

   - 注意:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます
     - Settings クラスでは KABUSYS_ENV の値は "development","paper_trading","live" に制約されています

主要コマンド・使い方
-------------------

1) 監視ループを起動（Monitoring）
- デフォルトは data/monitoring.db を使用し、本番 sqlite_path を参照します（監視は環境に依らず production DB を監視）。
- 環境変数でポーリング間隔を上書きできます:
  - MONITOR_POLL_INTERVAL (秒, デフォルト 60)
- 実行:
  - python -m kabusys.run_monitoring
- 停止:
  - data/stop_requested.flag を作成するとループは検知して終了します（スクリプト側に stop フラグパスがハードコーディングされています）。

2) 実行エンジンを起動（ExecutionEngine）
- Paper Trading の場合は KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し
  data/paper_trading.db を使います（本番 DB と分離）。
- 実行:
  - python -m kabusys.run_execution
- 停止:
  - data/stop_requested.flag を作成すると実行中のエンジンを停止させます。
- PID / フラグ:
  - execution.pid（デフォルト data/execution.pid）でプロセスの生存監視を行います
  - data/kill.flag は KillSwitch による停止要求に利用します（実行エンジンは起動時に kill.flag を検出すると起動をスキップします）

3) Streamlit ベースの監視ダッシュボード（読み取り専用）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only モードで SQLite を開きます。MonitoringEngine によって監視 DB が作成され、データが蓄積されます。

4) Paper Trading 検証レポート生成ツール
- 検証レポートを標準出力に生成します（paper_trading DB を読みます）。
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI 機能（ニューススコア・レジーム判定）
- 両機能とも OpenAI API key（OPENAI_API_KEY または引数）が必須です。
- プログラム内呼び出し例（簡易）:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,1), api_key="sk-...")

  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026,4,1), api_key="sk-...")

重要な設計ポイント・挙動
------------------------
- DB の分離:
  - Paper Trading（KABUSYS_ENV=paper_trading）は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB（monitoring.db）と完全分離します。
- 環境変数読み込み:
  - プロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動ロードします（既存 OS 環境変数は上書きされない。`.env.local`は上書き可能）。
- プロセス優先度:
  - run_* スクリプト起動時に set_process_priority("high") を呼びます。権限不足で失敗することがあるため、その場合は警告に留まります。
- フラグファイル:
  - stop_requested.flag / kill.flag を用いてプロセス間シグナリングを行います。これらは data ディレクトリ下に作られます。
- モジュールは「フェイルセーフ」で設計されています:
  - OpenAI API エラー時は一定のフォールバックやスキップ動作をとり、他コンポーネントへの例外伝播を避ける設計が多用されています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                 - パッケージ定義（__version__ 等）
- config.py                   - Settings / .env 自動読み込みロジック
- run_monitoring.py           - Monitoring ポーリングループ起動スクリプト
- run_execution.py            - ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py - Paper Trading 検証レポート CLI
- monitoring/
  - monitoring_db.py          - SQLite 永続化層（テーブル初期化 / MonitoringDB クラス）
  - system_monitor.py         - システム状態・データ鮮度監視
  - trade_monitor.py          - 注文滞留・約定異常監視
  - risk_monitor.py           - ドローダウン・ポジション上限監視
  - monitoring_engine.py      - 各 Monitor を束ねる実行ループ
  - kill_switch.py            - kill.flag 書き込みロジック
  - alert_manager.py          - LINE 通知ユーティリティ
  - streamlit_dashboard.py    - Streamlit ダッシュボード
- execution/
  - order_manager.py          - 発注管理ロジック
  - reconciler.py             - 再起動後の同期（リコンシリエーション）
  - ...                       - Broker 抽象等（省略）
- portfolio/
  - portfolio_builder.py      - 候補選定、等配分・スコア配分
  - risk_adjustment.py        - セクターキャップ、レジーム乗数
  - position_sizing.py        - 株数決定、単元丸め、aggregate cap
- research/
  - factor_research.py        - Momentum/Volatility/Value 計算（DuckDB）
  - feature_exploration.py    - 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py               - ニュースを LLM でスコアリングして ai_scores に書込
  - regime_detector.py        - ETF MA + マクロニュースで市場レジーム判定
- utils/
  - process_priority.py       - プロセス優先度 / CPU affinity ユーティリティ
- data/                       - 実行時に使用する DB / pid / flag を置く想定ディレクトリ（作成推奨）

補足・トラブルシューティング
----------------------------
- 権限問題:
  - プロセス優先度の設定や CPU affinity は管理者権限を必要とする場合があります。失敗しても警告が出て実行は続行します。
- OpenAI 使用時:
  - レート制限や API エラーに対して自動リトライがありますが、キーやクォータに注意してください。
- DuckDB / SQLite:
  - DuckDB はきちんとインストールしておいてください。streamlit での read-only 接続は URI + ?mode=ro を使っています。
- kill.flag / stop_requested.flag:
  - これらを誤って残すと実行が停止または起動をスキップします。起動前に不要なら削除してください（KillSwitch.clear() を使うロジックもあります）。

最後に
------
この README はコードベース内の主要機能と運用上の注意点をまとめたものです。各モジュールの詳細は該当ソースファイル（src/kabusys/...）の docstring / コメントを参照してください。具体的な Broker 実装、ExecutionEngine の残り実装、テスト・デプロイ手順は別途補足ドキュメントを参照または追加してください。