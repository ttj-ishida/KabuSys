KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買システム向けライブラリ／実行フレームワークです。  
主に以下の機能群を備え、戦略の研究・ポートフォリオ構築・注文実行・監視・AI を用いたニュース解析までをカバーします。

主な特徴
--------
- Execution（発注）エンジン
  - ブローカー抽象化（本番／Paper Trading 切替可能）
  - OrderManager / OrderRepository / Reconciler による状態管理と再同期処理
- Monitoring（監視）
  - システム稼働状況、注文滞留、約定異常、ドローダウン監視
  - kill.flag による安全停止シグナル
  - SQLite ベースの監視 DB（冪等でスキーマ作成／マイグレーション）
  - Streamlit ダッシュボード（監視用）
- Portfolio construction（銘柄選定・配分・建玉サイズ）
  - 候補選定、等金額／スコア加重、リスク調整、ポジションサイズ計算
- Research（ファクター計算・特徴量探索）
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、要約統計
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメントの銘柄別スコア化
  - ETF とマクロニュースの組合せによる市場レジーム判定
  - API 呼び出しはリトライ・フェイルセーフ設計
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
  - コマンドラインツール: paper_trading 検証レポート生成スクリプトなど

セットアップ
-----------
※ 以下はリポジトリに requirements.txt/pyproject.toml があることを前提とした一般的な手順です。実際の依存は環境に合わせて調整してください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt / pyproject がある場合はそちらを使ってください。）

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数（.env の準備）
   - プロジェクトルートに .env（または .env.local）を作成して必要な設定を入れてください。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live  (default: development)
       - paper_trading の場合、MockBrokerClient を使用しデータは data/paper_trading.db に保存されます。
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン
     - KABU_API_PASSWORD: kabuステーション API パスワード（本番接続）
     - SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject (Paper Trading の約定モード)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, ...（監視関連）

   - 自動 .env 読込: config モジュールは .env/.env.local を自動でロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

使い方（よく使うコマンド）
------------------------

- 実行エンジンの起動（本番 or paper_trading に応じて挙動が変わる）
  - python -m kabusys.run_execution
  - 特徴: 起動時にプロセス優先度を High に設定し、SQLite/DuckDB に接続して ExecutionEngine を実行します。
  - paper_trading 環境では MockBroker を使用し、PAPER_TRADING_SQLITE_PATH にデータを書き込みます。

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能。
  - 監視は常に本番用 sqlite_path（設定で指定した SQLITE_PATH）を使用します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview/Positions/Orders/System タブを表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11
  - 指定期間の稼働率、注文成功率、送信率、レイテンシ等を算出し PASS/FAIL 判定を行います。

- AI 関連（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

重要な実装・挙動メモ
-------------------
- 監視 DB 初期化
  - init_monitoring_db() は冪等にテーブルとインデックスを作成し、必要に応じて簡単なマイグレーション（カラム追加）を行います。run_execution / run_monitoring 起動時に自動的に呼ばれます。

- Process 優先度
  - run_* スクリプトは起動直後に set_process_priority("high") を呼び出します（psutil ベース、Windows/Linux の差分吸収）。権限不足や未対応 OS の場合は警告を出して無視します。

- Paper Trading
  - KABUSYS_ENV=paper_trading のときは BrokerClientFactory が MockBrokerClient を生成し、データは PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に保存され、本番 DB とは完全に分離されます。
  - PAPER_FILL_MODE により約定の挙動（instant/partial/never/reject）を制御できます。

- AI（OpenAI）
  - news_nlp / regime_detector は gpt-4o-mini を前提に設計。429/タイムアウト/5xx はエクスポネンシャルバックオフでリトライします。API 失敗時は安全側のフォールバック（例: macro_sentiment=0.0）を行い、例外でアプリ全体を停止させない設計です。
  - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用します。未設定時は ValueError が発生します。

- Kill Switch
  - RiskMonitor の判定などで kill.flag に書き込みを行い、ExecutionEngine に対して停止シグナルを送ります。KillSwitch は冪等で既存ファイルがあれば再書き込みしません。ExecutionEngine 起動時の KILL_FLAG_CLEAR_ON_START=1 によるクリア挙動に対応しています。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理（.env ロード）
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py
  - execution/
    - order_manager.py
    - order_repository.py
    - order_record.py
    - execution_engine.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                     # 実行時生成されるデータファイル（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）

付録: よく使う環境変数（抜粋）
--------------------------------
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SQLITE_PATH (data/monitoring.db)
- DUCKDB_PATH (data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject)
- PID_FILE_PATH (data/execution.pid)
- KILL_FLAG_PATH (data/kill.flag)
- MONITOR_POLL_INTERVAL (秒、デフォルト 60)
- LOG_LEVEL (DEBUG/INFO/...)

ライセンス・テスト
------------------
- 本リポジトリ内に LICENSE / tests ディレクトリがある場合はそちらを参照してください（この README はコードベースから生成したドキュメントです）。

問い合わせ・貢献
----------------
- バグ報告・機能提案は Pull Request / Issue にて受け付けてください。README に書かれていない運用上の注意点や追加の環境変数がある場合は .env.example を参照してください。

以上。必要であれば .env.example のサンプル、起動スクリプトの systemd ユニット例、Dockerfile / docker-compose 例なども追加で作成します。どれが必要か教えてください。