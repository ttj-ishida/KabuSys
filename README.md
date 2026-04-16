README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群を集めた Python コードベースです。本リポジトリは以下の主要領域を含みます:

- 注文実行エンジン（ExecutionEngine）と発注管理（OrderManager / Reconciler）
- 監視・アラート（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- リサーチ（ファクター計算 / 特徴量探索）
- AI 支援（ニュース NLP によるセンチメント／レジーム判定）
- 運用支援ツール（監視ダッシュボード、paper trading 検証レポート 等）

設計上のポイント:
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（data/paper_trading.db）。
- 監視（monitoring）は環境にかかわらず本番 sqlite_path を使用し、運用監視を分離。
- OpenAI を用いた処理は API キー未設定時に例外やフェイルセーフ処理を行う設計。

主な機能
--------
- ExecutionEngine の起動スクリプト（src/kabusys/run_execution.py）
  - 本番/ペーパー切替、MockBrokerClient による分離実行、PID ファイル管理、停止フラグ対応
- Monitoring（src/kabusys/run_monitoring.py / monitoring モジュール）
  - CPU/メモリ/ディスク/プロセス生存監視、データ鮮度チェック、注文滞留・価格異常検出
  - Kill Switch（条件を満たすと data/kill.flag に理由を書き込む）
  - LINE によるアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
  - 稼働率、注文成功率、レイテンシ、リスク却下数の集約と PASS/FAIL 判定
- AI コンポーネント（src/kabusys/ai）
  - news_nlp.score_news: raw_news を LLM に投げて銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM 判定を合成して market_regime に書き込む
- ポートフォリオ構築ユーティリティ（src/kabusys/portfolio）
  - 候補選定、重み計算、セクター制限、ポジションサイズ計算（単元丸め / aggregate cap）

セットアップ手順
---------------
1. Python 環境準備
   - 推奨: Python 3.9+（利用ライブラリにより要件が変わる可能性があります）
   - 仮想環境作成例:
     python -m venv .venv
     source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージのインストール
   - requirements.txt がある場合:
     pip install -r requirements.txt
   - 主要な依存（参考）:
     pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 重要な環境変数（主なものとデフォルト）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants API）
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒, run_monitoring 用, デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT / LOG_LEVEL
   - .env.example があれば参照して .env を作成してください。

4. データディレクトリ
   - data/ 以下に DB やフラグファイルを置きます（必要に応じて作成）。
   - 例:
     data/monitoring.db
     data/paper_trading.db
     data/kabusys.duckdb
     data/execution.pid
     data/kill.flag
     data/stop_requested.flag

使い方
-----
- 監視プロセスを起動
  - デフォルトポーリング間隔 60 秒、停止は data/stop_requested.flag の作成で可能:
    python -m kabusys.run_monitoring
  - 環境変数で間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ExecutionEngine）を起動
  - Paper Trading（KABUSYS_ENV=paper_trading）は専用 DB に書き込み、MockBroker を使います:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番実行:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると thread のループ検知で安全に停止します。
    - Kill Switch が条件を満たすと data/kill.flag を作成して ExecutionEngine に停止シグナルを送る設計です。

- Streamlit ダッシュボード (監視)
  - Start:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - コマンドラインから期間指定で実行:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュールの利用（プログラムから）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

運用に関する注意
----------------
- Paper Trading は本番データベースと明示的に分離されています（PAPER_TRADING_SQLITE_PATH）。
- 監視プロセスは monitoring DB（SQLITE_PATH）に監視ログ・リスクログ等を永続化します。init_monitoring_db が存在しないテーブルを自動作成します。
- ExecutionEngine と MonitoringProcess は PID ファイル / フラグファイル（data/execution.pid / data/stop_requested.flag / data/kill.flag）で連携します。フラグは冪等的に扱われます。
- OpenAI API 呼び出しはリトライ・バックオフ・レスポンス検証（JSON 解析・型チェック）を行い、失敗時はフェイルセーフでスコアをスキップまたは 0.0 にフォールバックします。
- プロセス優先度や CPU affinity の設定は utils/process_priority.py にまとめられており、OS により挙動が異なります（権限不足時は警告を出してスキップ）。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py                            — 環境変数 / Settings 管理（.env 自動ロードあり）
  - run_monitoring.py                    — SystemMonitor ポーリング起点スクリプト
  - run_execution.py                     — ExecutionEngine 起動スクリプト
  - data/ (想定)                         — DB / フラグ配置ディレクトリ（プロジェクトルート直下）
  - ai/
    - news_nlp.py                        — ニュース NLP（OpenAI 経由のスコアリング）
    - regime_detector.py                 — レジーム判定（ETF MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py                   — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository, order_record など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py

補足（トラブルシューティング）
------------------------------
- .env の自動読み込みを無効化したい場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- monitoring / execution 起動時に既存の kill.flag をクリアしたい場合:
  Settings.kill_flag_clear_on_start を環境変数 KILL_FLAG_CLEAR_ON_START=1 で有効にする（設定読み取りは Settings に依存）。
- OpenAI の呼び出しでレスポンスが不正（JSON 解析失敗等）の場合、該当チャンクはスキップされ、ログが記録されます。
- DuckDB / SQLite のファイルパスは Settings.duckdb_path / Settings.sqlite_path / Settings.paper_sqlite_path で管理されています。デフォルトは data/*.db。

ライセンス・貢献
----------------
- 本ドキュメントではライセンスファイルが示されていません。リポジトリの LICENSE を確認してください。
- バグ修正や機能改善は Pull Request を歓迎します。テストや静的解析の追加も推奨します。

以上。必要であれば各コマンドの実行例や .env.example のテンプレート、起動フロー図などを追記します。どの情報をより詳細に載せたいか教えてください。