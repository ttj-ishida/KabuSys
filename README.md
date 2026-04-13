README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を行うソフトウェア群です。本リポジトリは以下の主要機能を提供します。

- 注文生成・送信・状態管理を行う実行エンジン（ExecutionEngine）
- 監視サブシステム（System / Trade / Risk モニタ）とアラート送信
- ポートフォリオ構築・銘柄選定・ポジションサイズ計算の純粋関数群
- 研究用ファクター計算・特徴量解析ユーティリティ（DuckDB を利用）
- ニュース NLP による銘柄センチメント評価（OpenAI API 経由）
- 市場レジーム判定（MA とマクロセンチメントの合成）
- Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード

特に、監視部分は SQLite ベースの永続層を持ち、実行プロセスの生存確認・データ鮮度・滞留注文・ドローダウンなどの監視と、LINE へのアラート送信を備えています。

主な機能一覧
--------------
- 実行 / リコンシリエーション
  - 起動時の OrderSent 状態の突合（Reconciler）
  - OrderManager による作成→送信→同期の安全な状態遷移
- 監視
  - SystemMonitor：CPU/MEM/DISK、実行プロセス PID、データ鮮度
  - TradeMonitor：滞留注文、約定価格の異常検出
  - RiskMonitor：ドローダウン、ポジション上限の監視（KillSwitch 連携）
  - AlertManager：LINE Push による通知（クールダウンあり）
  - MonitoringEngine：上記を束ねてポーリング
  - streamlit_dashboard：監視 DB を可視化する UI
- ポートフォリオ構築（純粋関数）
  - 候補選定（score / rank）、等配分・スコア重み・リスクベースの株数算出
  - セクターキャップ適用、レジーム乘数計算
- 研究（DuckDB）
  - momentum / volatility / value ファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（OpenAI）
  - ニュース記事を銘柄別にまとめて LLM でスコアリングし ai_scores に格納
  - マクロ記事を用いた市場レジーム判定（market_regime テーブルへ書き込み）
- ツール
  - paper_verification_report：Paper Trading 用の検証レポート生成（CLI）
  - 各種 DB マイグレーション・初期化ロジック（monitoring_db.init_monitoring_db）

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（型注釈や構文に依存）
- ネットワーク接続（OpenAI / LINE / ブローカー API を使用する場合）

1. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil openai requests streamlit
   - 実運用では追加でブローカークライアントの依存等が必要です（個別に導入してください）

3. データディレクトリの準備
   - デフォルトでは data/ 以下に DB 等を作成します。必要に応じて手動で作成してください。
     - mkdir -p data

4. 環境変数の設定
   - .env ファイル（プロジェクトルート）に必要な変数を設定できます。本ライブラリは独自の .env パーサを持ち、
     OS 環境変数 > .env.local > .env の順で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数（最低限運用で必要なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知を使う場合
     - KABUSYS_ENV — 実行環境（development | paper_trading | live）。デフォルトは development
     - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH — PID/kill flag のパス（デフォルト data/…）
     - LOG_LEVEL — ログレベル（DEBUG|INFO|…）

5. DB 初期化は各起動スクリプトが自動で行います（monitoring_db.init_monitoring_db を呼びます）。

使い方
------
主要スクリプトの実行例です。プロジェクトルートで実行してください。

- 監視ループの起動（常時稼働プロセス）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き可能（デフォルト 60秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 実行開始時にプロセス優先度を "high" に設定し、監視用 SQLite（settings.sqlite_path）と DuckDB に接続します。
  - 注意: Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用）を用いる仕様です。

- 実行エンジンの起動（当日の取引処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）。
  - 起動時にリコンシリエーション等を実行し、ExecutionEngine.run_session() を呼びます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも可）
  - 出力に基づき稼働率・注文成功率・レイテンシ等を PASS/FAIL 判定します。

- AI / 研究用関数（ライブラリとして利用）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
    - DuckDB 接続を渡してニューススコアを ai_scores テーブルへ書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
    - 市場レジーム（bull/neutral/bear）を算出して market_regime テーブルへ書き込みます。
  - 研究モジュール（kabusys.research）には calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等が含まれます。

運用上の注意
--------------
- PID ファイルと kill.flag
  - ExecutionEngine は起動時に PID ファイル（settings.pid_file_path）を作成し、SystemMonitor はこれを参照して実行プロセスの生死を判定します。
  - KillSwitch は条件を満たした場合に kill.flag（settings.kill_flag_path）を書き込み、ExecutionEngine 側がこれを検知して安全に停止する仕組みです。
- 権限
  - set_process_priority() などの操作は環境によって権限が必要です。権限不足の場合は警告が出てスキップされます。
- Paper Trading
  - paper_trading 環境では本番 DB と完全に分離されることを意図しています（PAPER_TRADING_SQLITE_PATH を使用）。
- DuckDB / SQLite
  - 研究・履歴データは DuckDB（高速な分析向け）に格納され、実行ログ等は SQLite（軽量永続）に格納されます。
- OpenAI 呼び出し
  - API 呼び出しはリトライやバックオフ、レスポンス検証を実装していますが、API キーが未設定の場合は ValueError を発生させます。失敗時はフェイルセーフ（0.0 などにフォールバック）で継続する処理もあります。

ディレクトリ構成
----------------
（主要ファイル／モジュールのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージ初期化（__version__ 等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替あり）

  - ai/
    - news_nlp.py — ニュースの LLM スコアリング処理（ai_scores への書込）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py — SQLite 永続層（テーブル作成 / CRUD ユーティリティ）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 書き込みユーティリティ
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各 Monitor をまとめるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/  (実行ロジック、OrderManager, OrderRepository, BrokerFactory 等)
    - reconciler.py — 起動時の自動復旧ロジック
    - order_manager.py — Order の状態遷移管理と broker 呼び出しのラップ
    - ...（ブローカ API インターフェース・リポジトリ等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数算出ロジック（単元丸め、aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成（CLI）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ

サンプル .env（最小例）
----------------------
以下は運用に必要になりがちな変数の例です（実際の値は適宜設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxx
LINE_USER_ID=Uxxxxxxxxxxxx
MONITOR_POLL_INTERVAL=60

付記 / 開発メモ
----------------
- .env のパースは独自実装で、export KEY=val / quoted values / inline コメント等に対応しています。
- DuckDB の一部 SQL は分析向けに最適化されており、prices_daily / raw_financials / raw_news 等のテーブル設計に依存します。
- AI 呼び出し部分は OpenAI の SDK 変更に対して defensive な実装（status_code の安全取得等）を行っています。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 env ロードを無効化できます。

問い合わせ / 貢献
-----------------
バグ報告や機能改善の提案は issue を立ててください。プルリクエスト歓迎です。

---  
以上。運用や導入で不明点があれば実行したいユースケース（監視のみ / 本番実行 / Paper Trading など）を教えてください。具体的なコマンドや env の例を補足します。