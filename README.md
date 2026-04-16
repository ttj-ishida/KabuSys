README
=====

概要
----
KabuSys は日本株向けの自動売買／研究／監視プラットフォームの軽量実装です。本プロジェクトは以下の主要機能を持ち、実運用（本番）と Paper Trading を分離して扱えるよう設計されています。

- 注文生成・発注管理（Execution）
- 発注リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- システム監視（SystemMonitor / MonitoringEngine）
- 監視ログ永続化（SQLite）
- ファクター計算・リサーチ（DuckDB ベース）
- ニュース NLP（OpenAI を用いたセンチメント評価）
- Paper Trading 検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

特徴
----
- 本番と Paper Trading の DB を分離（Paper Trading は data/paper_trading.db を利用）
- DuckDB を用いた時系列／ファクタ計算（prices_daily / raw_financials 等を前提）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント、レジーム判定（堅牢なリトライ／バリデーションロジック）
- 監視エンジンが滞留注文・約定異常・ドローダウン・プロセス死去などを検知してログ・アラート（LINE）・Kill Switch を操作
- プロセス優先度（High/Normal/Low）と CPU affinity を設定するユーティリティ

要件
----
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリ）
- インターネット接続（OpenAI / LINE を利用する場合）

環境変数（主要）
----------------
自動で .env / .env.local をプロジェクトルートからロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
必須・よく使うものを抜粋します。

必須（利用機能により）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API 用
- OPENAI_API_KEY — OpenAI 呼び出しに必要（news_nlp / regime_detector）

任意 / デフォルトあり:
- KABUSYS_ENV — 環境: development | paper_trading | live （デフォルト: development）
- PAPER_FILL_MODE — paper_trading におけるモック約定挙動: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 sqlite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH — 各種ファイルパス
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用

セットアップ手順
--------------
1. リポジトリを取得し仮想環境を作成:
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）:
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を利用）

3. データディレクトリを作成:
   - mkdir -p data

4. 環境変数を設定:
   - プロジェクトルートに .env を作成するか、環境変数をエクスポートしてください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     KABUSYS_ENV=development
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

5. （オプション）監視 DB 初期化は各プロセス起動時に自動的に実行されます（init_monitoring_db）。

使い方
------

1) 監視ループ（Monitoring）
- 目的: system_status / trade_logs / risk_logs / dashboard を定期的に記録・評価し、Kill Switch / LINE 通知を管理します。
- 実行:
  - python -m kabusys.run_monitoring
- 設定:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 監視は KABUSYS_ENV に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
- 停止:
  - プロジェクトルートの data/stop_requested.flag を作成するとループが終了します（run_monitoring/run_execution と共通）。

2) Execution（注文エンジン）
- 目的: ブローカークライアント経由で発注・状態管理、リスク制御を行います。paper_trading 環境ではモックブローカーを利用し DB を分離します。
- 実行:
  - python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合は mock broker を使用し、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
  - 実行時、data/execution.pid を出力することで外部から存在確認できます。
- 停止:
  - data/stop_requested.flag を作成するか、KillSwitch が data/kill.flag を書き込むと停止シグナルを受け取ります。

3) Paper Trading 検証レポート
- 目的: Paper Trading DB のログから稼働率・注文成功率・レイテンシ等の検証レポートを出力。
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db パラメータで Paper Trading DB を指定（デフォルト: env/PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

4) 監視ダッシュボード（Streamlit）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - ダッシュボードは監視用 SQLite を読み取り専用で開きます。MonitoringEngine が DB を作成 / 更新している必要があります。

5) AI / リサーチ機能（プログラムから使用）
- ニュース NLP（センチメント）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=...)
- レジームスコア:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=...)
- ファクター計算・リサーチ:
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

重要なファイル・挙動（実行時の注意）
----------------------------------
- stop/kill フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution のメインループを安全に終了させるために利用されるファイル
  - data/kill.flag — KillSwitch が書き込むことで ExecutionEngine に対して停止指示を送る
- PID ファイル:
  - data/execution.pid（デフォルト） — ExecutionEngine の PID を記録
- Paper Trading:
  - PAPER_TRADING_SQLITE_PATH により本番 DB と完全分離されます
- OpenAI 呼び出し:
  - リトライ（429 / 接続エラー / 5xx 等）やレスポンス JSON のバリデーションを組み込んでいますが、APIキー・コスト・レート制限には注意してください
- process priority:
  - 起動時に set_process_priority("high") を呼び出しています（psutil の権限不足で失敗することがありますが警告ログに留まります）

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — Settings クラス（.env 自動読み込み・設定取得）
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- ai/
  - news_nlp.py — ニュースセンチメントスコア取得ロジック（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 / CRUD（system_status / trade_logs / risk_logs / positions / dashboard）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE 通知送信
  - monitoring_engine.py — 複数モニタを束ねるエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文作成 / 管理
  - reconciler.py — 再起動時のリコンシリエーション
  - …（Broker API / OrderRepository 等のモジュール）
- research/
  - factor_research.py — momentum/volatility/value 等のファクター計算（DuckDB）
  - feature_exploration.py — forward returns, IC, 統計サマリ
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・cap チェック
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
- data/ (実行時に使用)
  - monitoring.db, paper_trading.db, kabusys.duckdb, *.flag, *.pid など

各モジュールの役割（簡単）
------------------------
- monitoring_db.py: 監視関連の DB スキーマ初期化と読み書き API（MonitoringDB）
- system_monitor.py: CPU/memory/disk、Execution プロセス生存、データ鮮度を監視
- trade_monitor.py: 滞留注文（stale）や約定価格異常を検知して risk_logs に記録
- risk_monitor.py: ダッシュボードからドローダウンやポジション数を評価しアラート登録
- alert_manager.py: LINE API に対してクールダウン付きのプッシュ通知
- ai/news_nlp.py, ai/regime_detector.py: OpenAI を利用した NLP 処理（バッチ化・リトライ・結果検証）

注意事項
--------
- 本リポジトリは実運用を想定した要素（注文 API、実資金、外部 API キー）を含みます。テスト・評価時は必ず KABUSYS_ENV=paper_trading を使用し、Paper Trading 用 DB を利用してください。
- OpenAI キー・LINE トークン等は秘密情報です。*.env を管理する際は適切に取り扱ってください。
- process priority（高優先度）設定は権限不足で失敗する場合があります。ログを確認してください。
- DuckDB / SQLite ファイルは大きくなる可能性があるため、バックアップ・保守を検討してください。

ライセンス・貢献
----------------
（ここにライセンス情報や貢献方法を追加してください。）

以上。README に不足する具体的な実行例や追加の環境設定が必要であれば、利用シナリオに合わせて追記します。