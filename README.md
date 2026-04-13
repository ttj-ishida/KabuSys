README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリには以下を含みます。
- 発注エンジン（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- 監視基盤（System / Trade / Risk Monitoring）、監視ログの永続化（SQLite）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等）
- AI を使ったニュースセンチメント（OpenAI）と市場レジーム判定
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

設計方針の要点
- 本番/ペーパートレードは分離（ペーパートレード時は専用 SQLite を使用）
- DuckDB を用いた時系列・ファクター計算（prices_daily / raw_financials 等）
- OpenAI API は任意。失敗時はフェイルセーフ（スコア 0 など）で継続
- 環境変数 / .env ファイルを用いた構成。自動ロードはプロジェクトルートを探索して行う

主な機能一覧
- Execution
  - 起動スクリプト: run_execution.py（KABUSYS_ENV により paper_trading モード切替）
  - BrokerClientFactory による実ブローカー / モック切替
  - OrderManager: 注文作成・送信・同期
  - Reconciler: 再起動時の注文・ポジション照合（自動復旧）
  - RiskManager: 発注時のリスクチェック（レート制限、ドローダウン等）
- Monitoring
  - run_monitoring.py によるポーリング監視ループ（System / Trade / Risk）
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - AlertManager: LINE へのプッシュ通知（任意）
  - KillSwitch: フラグファイルで ExecutionEngine 停止を通知
  - Streamlit ダッシュボード（監視 DB の可視化）
- Portfolio construction
  - 候補抽出（select_candidates）、等重・スコア加重（calc_equal_weights / calc_score_weights）
  - セクターキャップ適用（apply_sector_cap）
  - ポジションサイズ決定（calc_position_sizes）
- Research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC 計算・統計サマリー（feature_exploration）
- AI
  - ニュースセンチメント（kabusys.ai.news_nlp.score_news）: OpenAI を用いて銘柄毎にスコア化して ai_scores に書き込み
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）: MA200 とマクロニュースの LLM 評価を合成
- ツール
  - Paper Trading 検証レポート: kabusys.tools.paper_verification_report
  - Streamlit ダッシュボード: monitoring/streamlit_dashboard.py

セットアップ手順
----------------
前提
- Python 3.10+（typing にある | 型や match を想定）
- SQLite（標準ライブラリ）
- DuckDB（ローカル DB 用）
- OpenAI API を利用する場合は API キー

推奨手順（Unix/macOS）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （運用環境では requirements.txt を用意している場合はそれでインストールしてください）

3. .env の準備
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（CWD 依存せず .git / pyproject.toml を基準に探索）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

主な環境変数（一部）
- KABUSYS_ENV: development | paper_trading | live（既定: development）
- SQLITE_PATH: 監視 DB（monitoring）ファイルパス（既定: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（既定: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（既定: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（既定: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（既定: data/kill.flag）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の必須トークン
- OPENAI_API_KEY: OpenAI を使用する場合は必須（ai モジュール）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- PAPER_FILL_MODE: paper_trading 時のフィルモード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、既定 60）

使い方
-------

1) 監視ループを起動する（監視ログの記録）
- デフォルトで本番 sqlite_path を使用（監視は環境にかかわらず本番 DB を参照）
- 実行:
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

2) ExecutionEngine（発注エンジン）を起動する
- ペーパートレードで起動する例（本番 DB と分離して data/paper_trading.db を使用）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 本番起動例:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 起動時にプロセス優先度を high に設定し、PID ファイルを出力します。kill.flag により外部から停止シグナルを送れます。

3) Paper Trading 検証レポートを生成する
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- デフォルト DB: data/paper_trading.db。別パスを使う場合は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を設定

4) Streamlit 監視ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only URI で SQLite を開くため、MonitoringEngine が DB を生成している必要があります

5) AI 関連（プログラム的に呼び出す例）
- ニュースセンチメントを実行（Python REPL やスクリプトで）
  - from kabusys.ai.news_nlp import score_news
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, datetime.date(2026,4,10), api_key="sk-...")

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, datetime.date(2026,4,10), api_key="sk-...")

注意: OPENAI_API_KEY を環境変数に設定していれば api_key を省略できます。

設定ファイル（.env）例
----------------------
例:
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=sk-...
KABUSYS_ENV=paper_trading
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py                 - パッケージ定義・バージョン
    config.py                   - 環境変数/設定管理
    run_monitoring.py           - SystemMonitor ポーリング起動スクリプト
    run_execution.py            - ExecutionEngine 起動スクリプト

    execution/                  - 発注・ブローカー関連
      order_manager.py
      reconciler.py
      order_repository.py
      order_record.py
      execution_engine.py
      broker_factory.py
      broker_api.py
      ...

    monitoring/                 - 監視（DB / モニタ / アラート / ダッシュボード）
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py

    portfolio/                  - ポートフォリオ構築（純粋関数）
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/                   - ファクター計算・特徴量探索
      factor_research.py
      feature_exploration.py
      __init__.py

    ai/                         - OpenAI を使った NLP / レジーム判定
      news_nlp.py
      regime_detector.py
      __init__.py

    data/                       - データパイプライン（DuckDB 参照用コード等）
      pipeline.py
      stats.py
      ...

    tools/
      paper_verification_report.py
      __init__.py

    utils/
      process_priority.py
      __init__.py

運用上の注意
--------------
- ペーパートレード時は paper_sqlite_path（data/paper_trading.db）に発注ログ等が書き込まれ、本番 DB と完全分離されます。
- run_monitoring はデフォルトで本番 sqlite_path を参照します（監視は本番 DB を見る想定）。
- OpenAI の呼び出しはネットワーク障害やレート制限を想定してリトライ・フェイルセーフ実装になっていますが、API キーの管理・使用量には注意してください。
- PID ファイル・kill.flag による制御があります。ExecutionEngine は起動時に PID ファイルを書き、kill.flag による停止要求を監視 / 判定します。
- monitor / engine はプロセス優先度設定を試みますが、権限不足やプラットフォーム差で設定できない場合は警告を出して継続します。

開発・テスト
-------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ユニットテストでは OpenAI 呼び出しや外部 API をモックしてテストすることを推奨します（コード内で _call_openai_api 等を patch する設計になっています）。

ライセンス・貢献
----------------
- 本 README に記載の以外のポリシー（ライセンスや CONTRIBUTING）についてはリポジトリのトップレベルにあるファイルを参照してください。

以上。運用・導入で不明点があれば使い方や .env 設定例、特定コンポーネントの起動手順を詳述しますので教えてください。