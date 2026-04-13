README
======

概要
----
KabuSys は日本株の自動売買向けライブラリおよびバッチ実行基盤のミニマム実装です。本リポジトリは以下の主要機能を提供します。

- 注文発行・状態管理を行う ExecutionEngine（本番 / ペーパーの切替対応）
- システム稼働状況・注文状況・リスク監視のための Monitoring コンポーネント
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ算出、セクター制限 等）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量解析
- ニュース NLP を使った銘柄センチメント評価（OpenAI 経由）
- ペーパー取引の検証レポート生成ツール、Streamlit ダッシュボード など

設計方針の概略：
- DB（DuckDB / SQLite）を用いてデータ永続化・集計を行う
- 本番とペーパーは DB を分離（ペーパー時は data/paper_trading.db を使う）
- LLM 呼び出しはフェイルセーフ（失敗時はスコア 0 やスキップして継続）
- ルックアヘッドを防ぐため日付参照に注意（関数は date 引数を受ける）

機能一覧
--------
主な機能（モジュール単位）：

- execution/
  - 注文管理、OrderManager、ExecutionEngine、Reconciler（再起動時の同期）
  - BrokerClientFactory により KABUSYS_ENV=paper_trading 時は MockBroker を使用
- monitoring/
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常チェック
  - RiskMonitor: ドローダウン・ポジション数上限監視（kill.flag 発行）
  - MonitoringDB: SQLite を用いた監視ログ永続化（テーブル作成・マイグレーション含む）
  - AlertManager: LINE Push によるアラート通知（クールダウン管理）
  - streamlit_dashboard: 監視データの簡易ダッシュボード
- portfolio/
  - 候補選定、重み付け（等配分・スコア配分）、ポジションサイズ算出、セクター制限、レジーム乗数
- research/
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価・IC 計算等
- ai/
  - news_nlp.score_news: raw_news を OpenAI で解析し ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA乖離＋マクロニュースで市場レジーム判定
- tools/
  - paper_verification_report.py: Paper Trading DB から検証レポートを生成
- utils/
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- config.Settings: 環境変数の読み込み / デフォルト / バリデーション

必要条件（例）
--------------
Python 3.10+ を想定。主な依存パッケージ：

- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- （標準ライブラリ: sqlite3, logging, datetime など）

インストール例（仮）
- 仮想環境作成後：
  pip install -r requirements.txt
（requirements.txt はプロジェクトに合わせて用意してください。サンプル依存は上記参照）

セットアップ手順
--------------
1. リポジトリをクローン・チェックアウト
2. 仮想環境を作る（venv / pipenv / poetry 等）
3. 依存をインストール（duckdb / psutil / requests / openai / streamlit 等）
4. data ディレクトリを作成:
   mkdir -p data
5. 環境変数を設定
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（但し KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主なキー（.env.example を参照して作成してください）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH（ペーパー時の SQLite DB。デフォルト data/paper_trading.db）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（monitoring 用の SQLite。デフォルト data/monitoring.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート通知用）
     - PID_FILE_PATH（デフォルト data/execution.pid）
     - KILL_FLAG_PATH（デフォルト data/kill.flag）
     - その他しきい値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
6. DB 初期化
   - 実行スクリプトが起動時に monitoring DB のテーブル作成（init_monitoring_db）を行います。
   - DuckDB のテーブル（prices_daily, raw_financials 等）は別プロセスで用意する想定です。

環境変数の自動読み込み
- プロジェクトルート（.git か pyproject.toml があるディレクトリ）から .env/.env.local を自動で読み込みます。
- OS 環境変数の優先度が高く、.env.local は .env を上書きします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読込を無効化できます（テスト用）。

使い方 / 実行例
----------------

1) 監視プロセス起動（Monitoring）
- デフォルトではポーリング間隔 60 秒。環境変数で変更可: MONITOR_POLL_INTERVAL
- スクリプト（パッケージモード）:
  python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL の例:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は設定された sqlite_path（settings.sqlite_path）を使用します（Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計）。

2) ExecutionEngine 起動（発注エンジン）
- 実行:
  python -m kabusys.run_execution
- KABUSYS_ENV=paper_trading の場合:
  - BrokerClientFactory が MockBrokerClient を選択し、ペーパー用 SQLite（デフォルト data/paper_trading.db）を使用します。
  - 本番 DB とは完全に分離されます。
- 起動時にプロセス優先度を "high" に設定（set_process_priority を呼ぶ）。

3) Paper Trading 検証レポート
- コマンドライン:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4) Streamlit ダッシュボード
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で SQLite DB に接続し、Overview / Positions / Orders / System タブを表示します。

主要ファイル・振る舞いの補足
--------------------------
- run_monitoring.py
  - MONITOR_POLL_INTERVAL 環境変数で監視間隔を指定（デフォルト 60 秒）。不正な値はログを出してデフォルトにフォールバック。
  - PID ファイルの検出や kill.flag の処理は別モジュール（SystemMonitor / KillSwitch）が担当。

- config.Settings
  - 環境変数をラップして型変換・バリデーションを提供。
  - KABUSYS_ENV は "development","paper_trading","live" のいずれか。
  - PAPER_FILL_MODE の検証ロジックあり。

- ai/news_nlp.py, ai/regime_detector.py
  - OpenAI（gpt-4o-mini）を使った NLP スコアリングを実施。API キーは OPENAI_API_KEY 環境変数（または関数引数）で指定。
  - API 呼び出しはリトライ・バックオフ実装あり。失敗時はフェイルセーフによりスコア 0 またはスキップ。

- monitoring/monitoring_db.py
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルを作成。
  - マイグレーション（列追加）の処理あり（冪等）。

- monitoring/kill_switch.py
  - リスク条件（ドローダウン・ポジション上限）が満たされた場合に kill.flag を書き込み、ExecutionEngine に停止シグナルを送る。既存ファイルがあれば再書き込みしない（冪等）。

- utils/process_priority.py
  - Windows / POSIX (Linux/Mac/FreeBSD) 対応でプロセス優先度を設定（失敗時は警告ログ）。

運用上の注意
------------
- 本番運用時は KABUSYS_ENV を "live" に設定してください。
- Paper Trading は完全に別 DB を使いますが、DuckDB（市場データ等）パスは共有する想定のため適切に管理してください。
- OpenAI API の利用はコストが発生します。AI 機能は必須ではなく、APIキーが未設定の場合は該当処理は例外またはスキップで扱われます（各関数の挙動に従う）。
- kill.flag の自動クリアは Settings.kill_flag_clear_on_start による制御が可能。Execution 起動フローでクリーンアップを行う設計になっています。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py
- run_monitoring.py
- run_execution.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- monitoring_engine.py
- kill_switch.py
- alert_manager.py
- streamlit_dashboard.py
- __init__.py

src/kabusys/execution/
- order_manager.py
- reconciler.py
- (その他: broker_factory, execution_engine, order_repository 等が存在)

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py
- __init__.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py
- __init__.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py
- __init__.py

src/kabusys/tools/
- paper_verification_report.py
- __init__.py

src/kabusys/utils/
- process_priority.py
- __init__.py

ライセンス・貢献
---------------
本 README には記載がありません。利用・改変時はリポジトリの LICENSE を参照してください。バグや改善提案は Issue / Pull Request を送ってください。

補足（トラブルシュート）
-----------------------
- SQLite / DuckDB ファイルが見つからない場合、該当コマンドはエラーまたは早期終了します。パスを確認し、必要なテーブル（prices_daily / raw_financials 等）を準備してください。
- psutil によるプロセス優先度設定が失敗することがあります（権限不足など）。その場合は警告ログが出力されますが、処理自体は続行します。
- OpenAI 呼び出しで RateLimit 等が発生した場合は指数バックオフでリトライしますが、上限超過や致命的エラーは該当チャンクをスキップします。

以上。必要に応じて、特定のモジュールや機能の詳細な README を追加しますか？