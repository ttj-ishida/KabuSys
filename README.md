# KabuSys

KabuSys は日本株向けの自動売買・研究・監視基盤のミニマル実装です。  
本リポジトリは発注エンジン、監視・アラート基盤、ポートフォリオ構築ロジック、ファクター計算、LLM を用いたニュース NLP などを含みます。

以下はコードベース（src/kabusys）に基づく README です。

概要
- 自動売買エンジン（ExecutionEngine）とその補助コンポーネント（OrderManager、RiskManager、Reconciler 等）
- 監視サブシステム（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- 監視データ永続化（SQLite ベースの MonitoringDB）
- Paper Trading モード（本番 DB と完全分離）
- DuckDB を用いた時系列データ / ファクター計算・研究モジュール
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定
- Streamlit ベースの簡易ダッシュボード
- 検証レポート生成ツール（Paper Trading 用）

主な機能
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 SQLite（data/paper_trading.db）に記録
  - 実行中の PID 管理、停止フラグ監視、ExecutionEngine のセッション管理
- 監視プロセス起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system_status 等を保存
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を参照（環境に依存せず）
- 監視データ層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを作成・マイグレーション
  - MonitoringDB クラスによるログ／アップサート API を提供
- リスク監視（risk_monitor.py）・注文監視（trade_monitor.py）・システム監視（system_monitor.py）
  - ドローダウン・ポジション上限・滞留注文・約定異常価格などを検知し risk_logs に記録
  - KillSwitch により重大リスク発生時に data/kill.flag を書き込み、ExecutionEngine 停止シグナルを送出
- アラート（alert_manager.py）
  - LINE Messaging API へプッシュ通知（トークン・ユーザ未設定時は送信せずログのみ）
  - (level, category) 単位でメモリ内クールダウン機能あり
- Streamlit ダッシュボード（streamlit_dashboard.py）
  - monitoring.db を読み取り専用で表示（ポートフォリオ概要、ポジション、注文履歴、最新システム状態、リスクログ）
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - paper_trading DB から稼働率・注文成功率・送信率・レイテンシ等の指標を抽出して PASS/FAIL 判定
- ポートフォリオ構築（portfolio/*）
  - 候補選定、等配分・スコア加重配分、セクター上限適用、ポジションサイズ決定（lot 単位丸め・集計キャップ）
- 研究モジュール（research/*）
  - DuckDB を使ったファクター（Momentum / Volatility / Value）計算、将来リターン、IC 計算、統計サマリ
- AI モジュール（ai/*）
  - news_nlp.score_news: raw_news を集約して OpenAI に送信、ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを合成して日次レジーム判定

動作要件（目安）
- Python 3.10+
- 依存パッケージ（主なもの）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボードを使う場合)
- SQLite、ファイル書き込み権限（data ディレクトリ）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし、作業ディレクトリを開く
2. 仮想環境を作成して有効化（例: python -m venv .venv; source .venv/bin/activate）
3. 必要パッケージをインストール
   - 例:
     pip install duckdb psutil openai requests streamlit
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を推奨
4. 環境変数を設定（下記参照）。ローカルではプロジェクトルートに .env / .env.local を置くと自動読み込みされる（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

主要な環境変数
- 必須（実行する機能に応じて）
  - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（research 等で使用）
  - KABU_API_PASSWORD — kabu ステーション API パスワード（発注用）
- 実行環境設定
  - KABUSYS_ENV — 補助モード: development（デフォルト） / paper_trading / live
  - LOG_LEVEL — ログレベル（DEBUG, INFO...）
- DB/ファイルパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - PID_FILE_PATH — 実行エンジン PID ファイル（デフォルト data/execution.pid）
  - KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- Paper Trading 振る舞い
  - PAPER_FILL_MODE — instant | partial | never | reject（デフォルト: instant）
- 監視 / 実行設定
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動ロードを無効化
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / regime_detector で使用）
- LINE
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager の送信に使用

実行例
- 監視プロセスを起動
  - MONITOR_POLL_INTERVAL を任意で指定可能:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 既定では data/monitoring.db を作成し、定期的に system_status 等を記録します

- 実行エンジンを起動
  - 本番モード（デフォルト development / live 切替は KABUSYS_ENV にて）
    python -m kabusys.run_execution
  - Paper Trading（本番 DB と分離）
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在すると起動を中止します（停止フラグ）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で指定可。

ライブラリの利用例（Python REPL から）
- AI スコア付与（DuckDB 接続が必要）:
  from datetime import date
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')
  from kabusys.ai.news_nlp import score_news
  score_news(conn, date(2026,4,1), api_key='sk-...')

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,4,1), api_key='sk-...')

- 研究用関数:
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  calc_momentum(conn, date(2026,4,01))

停止 / フラグ管理
- 実行停止を外部から指示する仕組み:
  - data/stop_requested.flag — run_execution / run_monitoring のループがこのファイルの存在を検知して停止
  - data/kill.flag — KillSwitch が書き込むことで更に強制停止・アラートを発生させる（ExecutionEngine は起動時にこのファイルの存在を確認）

実装上の注意
- Paper Trading は本番 DB と分離される設計（settings.is_paper による分岐）
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込みする（CWD 非依存）
- set_process_priority（psutil）によりプロセス優先度を設定するが、権限不足やプラットフォーム差分で失敗する場合は警告ログが出て継続
- DuckDB に対する executemany の空リストバインドに注意（実装内で保護あり）

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングスクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント評価 / ai_scores 書き込み
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite テーブル初期化 / MonitoringDB API
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス状態監視
    - trade_monitor.py — 滞留注文・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - (OrderManager, OrderRepository, EngineConfig, ExecutionEngine, Reconciler, RiskManager 等の実装)
    - reconciler.py
    - order_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定・丸め・キャップ処理
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value ファクター
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - utils/
    - __init__.py
    - process_priority.py — psutil を用いた優先度 / CPU affinity 設定ユーティリティ
  - data/ (実行時に作られる想定)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード)
    - kabusys.duckdb (DuckDB)
    - execution.pid, stop_requested.flag, kill.flag, ...

最後に / 注意事項
- 実際のブローカー接続や資金を扱う場合は十分なテスト・レビュー・安全対策（リスク制約・検証・取引量制御）を行ってください。
- OpenAI API を用いる機能は API コストやレスポンスの安定性に依存します。API キー管理とエラーハンドリングに注意してください。
- 本 README はコードスニペットに基づく概要であり、実稼働前に各設定値・閾値の見直しを推奨します。

必要であれば、README を Markdown ファイル（README.md）として整形して出力します。追加で含めたいコマンドや設定例があれば教えてください。