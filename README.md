KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買／バックテスト／モニタリングを想定したシステムの一部実装です。
主な機能は以下のとおりです。

- 注文作成・発注・状態管理を行う ExecutionEngine（実取引・模擬取引対応）
- システム稼働状況・注文状態・リスク指標を記録・監視する Monitoring
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限など）
- リサーチ用ファクター計算・特徴量解析ユーティリティ（DuckDB ベース）
- ニュース NLP を用いた銘柄センチメント評価（OpenAI 利用）
- 市場レジーム判定モジュール（MA＋マクロセンチメント合成）
- 各種ユーティリティ（プロセス優先度設定等）および運用ツール（検証レポート、Streamlit ダッシュボード）

特徴
----
- 環境切替（development / paper_trading / live）を環境変数 KABUSYS_ENV で切替可能
  - paper_trading では MockBrokerClient を使用し、本番 DB と分離（デフォルト: data/paper_trading.db）
- 監視コンポーネントは sqlite（監視ログ） + DuckDB（時系列データ解析）を使用
- AI（OpenAI）呼び出しは堅牢に実装（バッチ、リトライ、レスポンス検証、スコアクリッピング）
- Streamlit による監視ダッシュボードを提供
- .env 自動読み込み機能を搭載（プロジェクトルートの .env / .env.local）

必須依存（代表）
- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit
（環境に合わせて pip install してください。requirements.txt があればそちらをご利用ください）

セットアップ手順
----------------
1. リポジトリをクローン / ソースを配置
   - 例: git clone <repo> && cd <repo>

2. Python 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合）
   - pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルートに .env を作り、必要なキーを設定します。
   - 自動ロード順序: OS 環境 > .env.local > .env
   - 主要な環境変数（例）
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...          （AI 機能を使う場合）
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db （必要に応じて）
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=...（通知を LINE に送る場合）
     - LINE_USER_ID=...

   - .env.example を参考に作成してください（未提供の場合は README のサンプルを参照）。

5. データディレクトリの準備（推奨）
   - mkdir -p data

使い方（主要コマンド）
--------------------

実行エンジン（ExecutionEngine）起動
- 開発 / 本番 / ペーパー取引を KABUSYS_ENV で指定して起動します。
- パッケージとして実行する（ソースツリーを PYTHONPATH に含める）
  - PYTHONPATH=src python -m kabusys.run_execution
- または直接スクリプトを実行（プロジェクトルートから）
  - python src/kabusys/run_execution.py
- 注意:
  - KABUSYS_ENV=paper_trading の場合、MockBroker を用いて data/paper_trading.db に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在する場合は起動を行いません。
  - 実行中は data/execution.pid に PID を書き込み、停止は data/stop_requested.flag を作成して要求します（Kill Switch は data/kill.flag を使用）。

監視ループ起動（Monitoring）
- ポーリングで各種モニタを定期実行します。
- デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書きできます（秒、1 以上）。
- 実行例:
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - python src/kabusys/run_monitoring.py
- 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存しません）。

Streamlit ダッシュボード
- 監視データの可視化用 UI。
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- 保存された paper_trading の SQLite DB から検証レポートを出力します。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または DB パス指定:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

AI / レジーム判定・ニューススコア
- プログラムから呼び出す場合:
  - from kabusys.ai.news_nlp import score_news
  - from kabusys.ai.regime_detector import score_regime
- どちらも OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）。

停止 / Kill
- 監視・実行ループを外部から停止する仕組み:
  - data/stop_requested.flag を作成すると run_* のループが終了します（run_execution, run_monitoring 共通）。
  - KillSwitch（条件を満たした場合）は data/kill.flag を書き込み、ExecutionEngine に停止要求を出します。
  - ExecutionEngine は起動時に kill.flag をクリアするオプション（Settings.kill_flag_clear_on_start）で挙動を制御できます。

設定（Settings）
- 環境変数は kabusys.config.Settings 経由で取得されます。主要プロパティ:
  - env （development | paper_trading | live）
  - sqlite_path, paper_sqlite_path, duckdb_path
  - pid_file_path, kill_flag_path
  - paper_fill_mode（instant | partial | never | reject）
  - CPU/MEM/DISK の閾値など（監視関連）
  - LOG_LEVEL（INFO 等）
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ディレクトリ構成（主なファイルと説明）
-----------------------------------
- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / Settings 管理、.env 自動ロード
  - run_execution.py           — ExecutionEngine 起動ラッパー
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
  - portfolio/
    - portfolio_builder.py     — 候補選定・等重 / スコア重み付け
    - position_sizing.py       — 株数（発注数量）計算、上限・丸め処理
    - risk_adjustment.py       — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py       — Momentum / Volatility / Value ファクター計算（DuckDB）
    - feature_exploration.py   — 将来リターン、IC、統計サマリ等
  - ai/
    - news_nlp.py              — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py         — SQLite テーブル作成 & 永続化 API（MonitoringDB）
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — 注文滞留・約定異常監視
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — kill.flag 操作
    - alert_manager.py         — LINE 通知ラッパー
    - monitoring_engine.py     — 各 Monitor をまとめ定期実行する Engine
    - streamlit_dashboard.py   — Streamlit ダッシュボード起動スクリプト
  - execution/
    - order_manager.py         — 発注 API（OrderManager）
    - reconciler.py            — 起動時リコンシリエーション
    - order_repository.py      — 注文 DB 操作（OrdersDB 側）
    - ...                      — ブローカーインターフェース等（別ファイル群）
  - utils/
    - process_priority.py      — プロセス優先度・CPU affinity ユーティリティ
  - data/                      — 実行時に使用するフラグ・DB を配置するディレクトリ（例: data/monitoring.db, data/paper_trading.db, data/stop_requested.flag）

運用上の注意
------------
- 監視 DB（monitoring.db）は init_monitoring_db で必要テーブルを自動作成／マイグレーションします。
- paper_trading モードでは本番 DB を上書きしないよう専用 DB（PAPER_TRADING_SQLITE_PATH）を使用してください。
- OpenAI を使う処理は API 呼び出し料金が発生します。テスト時はモック化してください（モジュール内で _call_openai_api を patch 可能）。
- process priority / cpu affinity 設定は OS 権限によって失敗する場合があります（ログに警告が出ます）。

サンプルコマンドまとめ
--------------------
- ExecutionEngine 起動（paper_trading 例）
  - KABUSYS_ENV=paper_trading PYTHONPATH=src python -m kabusys.run_execution
- Monitoring 起動（デフォルト 60s）
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

その他
-----
- この README はソースコードの docstring と実装に基づく概要です。実運用前に必ずテスト環境での動作確認、環境変数・権限の確認を行ってください。
- ご不明点や追加で README に載せてほしいサンプルや設定項目があれば教えてください。