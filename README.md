KabuSys — 日本株自動売買システム
=================================

この README は提供されたコードベースに基づく簡易ドキュメントです。プロジェクト全体の概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめています。

プロジェクト概要
--------------
KabuSys は日本株自動売買のためのモジュール群です。主な機能は以下のとおりです。

- 注文管理・発注（ExecutionEngine / OrderManager / BrokerClientFactory）
- リコンシリエーション（再起動後の注文同期）
- リスク管理（Drawdown 監視、ポジション上限等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- 監視ダッシュボード（Streamlit）
- Paper Trading 用の分離データベースサポート
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチ用ファクター計算（DuckDB を用いたファクター計算）
- ニュース NLP（OpenAI を用いたニュースセンチメント計算）
- 市場レジーム判定（MA + マクロセンチメントの合成）
- ユーティリティ（環境設定読み込み、プロセス優先度設定 等）

主な機能一覧（抜粋）
------------------
- 実行系
  - run_execution.py：ExecutionEngine の起動スクリプト（paper_trading モード時は MockBrokerClient を使用）
  - Reconciler：起動時の注文・ポジション照合
  - OrderManager / OrderRepository：注文の状態管理と永続化（SQLite）
- 監視系
  - run_monitoring.py：SystemMonitor のポーリングループ起動スクリプト
  - MonitoringEngine：System / Trade / Risk 各 Monitor を束ねる
  - MonitoringDB：監視ログ用 SQLite テーブル初期化と CRUD（system_status / trade_logs / positions / risk_logs / dashboard）
  - streamlit_dashboard.py：Streamlit での可視化
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment：候補選定、重み計算、数量決定、セクター制限 等
- リサーチ / AI
  - research.factor_research, feature_exploration：DuckDB を用いたファクター計算・IC 等
  - ai.news_nlp：OpenAI でニュースをセンチメントスコア化し ai_scores に書き込み
  - ai.regime_detector：MA200 とマクロセンチメントから日次レジーム判定
- ツール
  - tools.paper_verification_report：Paper Trading DB を解析して検証レポートを出力

セットアップ手順
----------------

1. Python 環境
   - Python 3.10+ を推奨。
   - 必要なパッケージ（例）
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit（監視ダッシュボード利用時）
   - 例（pipenv / virtualenv / poetry 等で仮想環境を作成してから）:
     - pip install duckdb psutil requests openai streamlit

2. 環境変数 / .env
   - プロジェクトルートに .env / .env.local を置くと自動的に読み込まれます（OS 環境変数が優先）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須環境変数（少なくとも運用時に必要）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルト値があるものを含む）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト、監視用 DB）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
     - PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定挙動、デフォルト: instant）
     - PID_FILE_PATH: data/execution.pid（ExecutionEngine の PID ファイル）
     - KILL_FLAG_PATH: data/kill.flag
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
     - OPENAI_API_KEY（ai モジュール利用時に必要）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、デフォルト 60 秒）

   - 簡単な .env 例:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - KABU_API_PASSWORD=xxxxx
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=paper_trading

3. データディレクトリ
   - デフォルトでは data/ 以下に DB ファイルや pid/flag ファイルが置かれます。必要に応じてパスを environment で変更してください。

使い方（主要コマンド）
--------------------

- Monitoring の起動（長期ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に「本番」用の sqlite_path を使用します（KABUSYS_ENV に依らず）。

- Execution の起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に取引ログ等を記録し、本番 DB と分離します。
  - 起動時にプロセス優先度を high に設定し、pid ファイルに PID を書きます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（SQLite DB パス。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます）
  - 出力: 稼働率、注文成功率、送信率、レイテンシ統計、Pass/Fail 判定

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only で開き、positions / trade_logs / system_status / dashboard を表示します。

- AI / リサーチ関数（Python から呼び出して利用）
  - ai:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key が None の場合は OPENAI_API_KEY を参照
  - regime:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)
  - research:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
    - 各関数に duckdb.Connection / target_date を渡して利用

監視 DB（MonitoringDB）について
-----------------------------
init_monitoring_db は以下のテーブルとインデックスを作成します（冪等）:

- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code PRIMARY KEY, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id = 1 の単一行を保持: updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

MonitoringDB は上記テーブルの読み書きをラップしたユーティリティ（ログ挿入、upsert、dedup 付きリスクログ等）を提供します。

プロジェクトのディレクトリ構成
----------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py               — パッケージ定義（バージョン等）
  - config.py                 — 環境変数読み込み、Settings クラス
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - risk_adjustment.py       — セクター制限・レジーム乗数
    - position_sizing.py       — 株数決定・スケーリング・丸め
    - __init__.py
  - research/
    - factor_research.py       — Momentum/Volatility/Value 計算
    - feature_exploration.py   — 将来リターン・IC・統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py              — ニュースセンチメントスコア生成（OpenAI）
    - regime_detector.py       — 市場レジーム判定（MA200 + マクロ）
    - __init__.py
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化・ラッパー
    - system_monitor.py        — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py         — 滞留注文 / 約定異常検出
    - risk_monitor.py          — ドローダウン監視・ポジション上限監視
    - monitoring_engine.py     — 各 Monitor を束ねる
    - alert_manager.py         — LINE push 通知
    - kill_switch.py           — kill.flag 書込で Execution 停止シグナル
    - streamlit_dashboard.py   — Streamlit ダッシュボード
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - order_repository.py (他ファイルが存在すると想定)
    - broker_factory.py (他ファイルが存在すると想定)
    - execution_engine.py (他ファイルが存在すると想定)
    - __init__.py (想定)
  - utils/
    - process_priority.py      — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

注意事項 / 運用上のポイント
------------------------
- 環境（KABUSYS_ENV）が paper_trading の場合は paper_sqlite_path が使用され、本番 DB と分離されます。paper_trading モードは MockBrokerClient を用いてテスト用に振る舞います。
- run_monitoring は Monitoring 用 DB（settings.sqlite_path）を用います。KABUSYS_ENV に関係なく本番 sqlite_path を参照する点に注意してください。
- OpenAI を使う機能（ai.news_nlp, ai.regime_detector）は OPENAI_API_KEY が必要です。キー未設定時のハンドリングはモジュール毎に異なり、例外を投げるケースがあります。
- .env のパースは多少柔軟に実装されています（export 付き、クォート対処、コメント処理など）。ただし自動読み込みを望まない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- モニタリングの kill.flag によって ExecutionEngine を停止させる仕組みがあり、KillSwitch は冪等に flag を書きます。Execution 側は起動時に kill.flag をクリアするオプションが設定可能です（Settings.kill_flag_clear_on_start）。

トラブルシューティング
---------------------
- DB が見つからず Streamlit が開けない場合は MonitoringEngine を起動して監視 DB を初期化してください（init_monitoring_db は実行時に DB を作成します）。
- OpenAI API の呼び出しでレート制限や一時的な失敗が起きた場合は、各モジュールにリトライやフェイルセーフ処理が組み込まれていますが、ログを参照して再試行してください。
- process priority / cpu affinity の設定はプラットフォーム依存であり、権限不足により失敗することがあります（警告ログのみ）。

最後に
------
この README はコードベースから抽出した動作・設定の要点をまとめたものです。追加で README に明記したい運用手順や実行例（systemd ユニット、Dockerfile、CI 設定など）があれば教えてください。必要に応じて実運用向けのドキュメント（起動スクリプト、環境変数テンプレート、例外時のオペレーション手順）も作成します。