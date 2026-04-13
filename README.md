# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。本リポジトリは取引実行、ポートフォリオ構築、監視、研究（ファクター計算）、
ニュース NLP によるセンチメント評価などを含むモジュール群を提供します。

以下はコードベースの概要・セットアップ・使い方・ディレクトリ構成のまとめです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（実行例）
- 主要環境変数（Settings）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたモジュール群です。
- 主な責務:
  - 実行エンジン（ExecutionEngine）と発注制御（OrderManager / Reconciler）
  - ポートフォリオ構築（銘柄選定・重み計算・ポジションサイズ計算）
  - 監視（System / Trade / Risk モニタ、アラート、kill switch、Streamlit ダッシュボード）
  - 研究用ファクター計算（DuckDB 経由での prices_daily / raw_financials 利用）
  - ニュースの NLP を使ったセンチメント評価（OpenAI）
  - Paper Trading 用モード（本番 DB と分離して検証可能）

機能一覧
- 実行・復旧
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading モードをサポート）
  - Reconciler による起動時の注文/ポジション突合
- 監視
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch
  - Streamlit で監視ダッシュボードを起動可能
- データ / 研究
  - research モジュール: ファクター計算 (momentum/volatility/value)、forward returns、IC 計算等
  - DuckDB を想定した価格・財務データ参照で研究を実行
- AI（ニュース）
  - ai.news_nlp: OpenAI を使ったニュースの銘柄別センチメントスコア付与（ai_scores テーブルに書き込み）
  - ai.regime_detector: マクロ + 1321 の MA200 乖離の合成で日次レジーム判定（market_regime テーブルへ書込み）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）
- DB 永続化
  - monitoring_db: SQLite に監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）を作成・管理

セットアップ手順（基本）
1. Python 環境を用意
   - 推奨: 仮想環境 (venv/virtualenv/conda) を使用
   - 例:
     python -m venv .venv
     source .venv/bin/activate

2. 依存パッケージをインストール
   - 本コードで利用されている主要パッケージ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit（ダッシュボード使用時）
   - requirements.txt は付属していない想定のため手動でインストール:
     pip install duckdb psutil requests openai streamlit

3. 環境変数（.env）を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` が自動ロードされます（OS 環境変数を保護）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - AI 機能を使う場合:
     - OPENAI_API_KEY（必須）
   - LINE 通知を使う場合:
     - LINE_CHANNEL_ACCESS_TOKEN（オプション）
     - LINE_USER_ID（オプション）
   - 監視関連 / DB パスの主な環境変数（デフォルトあり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - KABUSYS_ENV (development | paper_trading | live) — default: development

4. データディレクトリを作成
   - 例:
     mkdir -p data

5. （必要に応じて）価格データや raw_financials/raw_news テーブルの準備（DuckDB）

使い方（実行例）
- 監視ループを起動（production sqlite を使用）
  - デフォルトで 60 秒間隔でポーリングします。変更するには MONITOR_POLL_INTERVAL を設定。
  - 例:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 説明:
    - run_monitoring は KABUSYS_ENV に依らず settings.sqlite_path（デフォルト data/monitoring.db）を使います。
    - 起動時にプロセス優先度を high に設定しようとします（psutil が必要）。

- 実行エンジンを起動（本番 / Paper Trading）
  - Paper trading モード（ローカル分離 DB を使用）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper 用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
    - PAPER_FILL_MODE 環境変数でモックの約定挙動を制御（instant / partial / never / reject）。
  - 本番モード:
    KABUSYS_ENV=live python -m kabusys.run_execution

- Streamlit ダッシュボード起動（監視 DB を読み取り専用で開く）
  - 例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポートを生成
  - 例:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラムから呼び出す）
  - ニューススコア付け:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")  # api_key省略時は環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

主要な環境変数（Settings で定義されているもの）
- 環境選択:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
    - settings.is_paper / is_live / is_dev で参照
- DB パス:
  - DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- PID / Kill flag:
  - PID_FILE_PATH（default: data/execution.pid）
  - KILL_FLAG_PATH（default: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START (1 to clear on start)
- Paper Trading 設定:
  - PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- 閾値（監視）:
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（デフォルト値は Settings にて指定）
- その他:
  - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY

挙動・注意点
- .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml）を起点に .env → .env.local の順で読み込みます。
  - .env の行パーサは export KEY=val / quoted values / コメントなどに対応しています。
  - OS 環境変数は保護され、.env.local の override によっても上書きされません（必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
- DB 初期化:
  - monitoring_db.init_monitoring_db() は冪等的で、必要なテーブル・インデックスを作成します。初回接続時に自動で呼ばれます（run_monitoring / run_execution が実行時に確保）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil が権限やプラットフォームで利用できない場合は警告を出してスキップします。
- Kill switch:
  - RiskMonitor が閾値超過などを検出した際、KillSwitch が data/kill.flag を書き込むことがあり、ExecutionEngine 側でこれを検知して安全停止する設計です。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは broker factory が MockBrokerClient を使用して、本番 DB と完全に分離して data/paper_trading.db に記録されます。
- OpenAI 呼び出し:
  - ニュース NLP / レジーム判定は OPENAI_API_KEY が必要。API エラーやパースエラー時にはフェイルセーフ化され、完全停止を引き起こさないように設計されています（スコアを 0 にフォールバックなど）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py (パッケージメタ情報)
  - config.py (Settings / .env 自動ロード処理)
  - run_monitoring.py (SystemMonitor ポーリングループ起動)
  - run_execution.py (ExecutionEngine 起動)
  - tools/
    - paper_verification_report.py (Paper Trading 検証レポート)
  - portfolio/
    - portfolio_builder.py (候補選定・重み計算)
    - position_sizing.py (株数計算・キャップ/スケーリング)
    - risk_adjustment.py (セクターキャップ・レジーム乗数)
  - monitoring/
    - monitoring_db.py (SQLite スキーマ & DB ラッパ)
    - system_monitor.py (システム状態・データ鮮度監視)
    - trade_monitor.py (滞留注文・約定異常監視)
    - risk_monitor.py (ドローダウン / ポジション上限監視)
    - kill_switch.py (kill.flag 制御)
    - alert_manager.py (LINE 通知)
    - monitoring_engine.py (各モニタを束ねる)
    - streamlit_dashboard.py (Streamlit ダッシュボード)
  - execution/
    - order_manager.py (Order State Machine の外向け API)
    - reconciler.py (起動時リコンシリエーション)
    - ...（broker_factory / execution_engine / order_repository 等の実装が想定）
  - research/
    - factor_research.py (momentum / volatility / value)
    - feature_exploration.py (forward returns / IC / summary)
  - ai/
    - news_nlp.py (raw_news → OpenAI による銘柄別スコアリング)
    - regime_detector.py (MA200 + マクロセンチメントで日次レジーム判定)
  - utils/
    - process_priority.py (psutil を用いたプロセス優先度 / CPU affinity 設定)
  - data/
    - デフォルト DB ファイルや pid/flag ファイルが置かれる（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/kill.flag）

追加のヒント・運用メモ
- ローカルでの検証には KABUSYS_ENV=paper_trading を使い、本番 DB を汚さないようにしてください。
- monitoring のポーリング間隔は MONITOR_POLL_INTERVAL（秒）で変更可能。値が不正（0以下・非整数）の場合は 60 秒にフォールバックします。
- .env のパースは引用符・バックスラッシュエスケープ・インラインコメントなどをかなり細かくサポートしています。詳細は config.py の実装を参照してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。監視ループを先に動かしてデータが作られていることを確認してください。

---

必要に応じて README に実行例・CI 設定・systemd ユニット例・テストの実行方法などを追記できます。追加したい項目があれば教えてください。