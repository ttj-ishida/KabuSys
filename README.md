KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。注文発行・リスク管理・監視・レポート・リサーチ・ニュースNLP等、実運用に必要なコンポーネント群を含みます。本リポジトリはモジュール化されたライブラリ兼実行用スクリプト群で、実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替えて利用できます。

主な機能
--------
- ExecutionEngine: ブローカーとの発注・注文状態管理・リコンシリエーション（再起動復旧）
- Risk Manager / Reconciler / OrderManager: 発注フローとリスク制御
- Monitoring: システム状態・注文滞留・約定異常・ドローダウン監視、LINE 通知、kill flag による停止
- Monitoring DB: SQLite に監視ログを永続化（system_status / trade_logs / positions / risk_logs / dashboard）
- Dashboard: Streamlit による監視ダッシュボード（読み取り専用）
- Paper Trading ツール: ペーパートレード用 DB 分離、検証レポート生成ツール
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約、レジーム補正
- Research: DuckDB を用いたファクター計算・将来リターン・IC・統計サマリー
- AI モジュール: OpenAI を用いたニュースセンチメント（news_nlp）および市場レジーム判定（regime_detector）
- ユーティリティ: プロセス優先度 / CPU affinity 設定など

前提（Requirements）
-------------------
- Python 3.9+
- SQLite（標準ライブラリで利用）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- ネットワークアクセス（ブローカー API / LINE / OpenAI を使用する場合）

インストール
------------
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt がある場合はそれを利用してください）

設定（環境変数）
----------------
KabuSys は環境変数または .env / .env.local を用いて設定します。プロジェクトルートに .env を置くと自動的に読み込まれます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（任意）
- LINE_USER_ID: LINE Push の送信先ユーザーID（任意）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
  - paper_trading のときは MockBroker を使用し DB を data/paper_trading.db に分離
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant | partial | never | reject）。デフォルト: instant
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite パス（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチ用フラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアする場合は 1
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）

運用用フラグ:
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）。0 以下や不正値は無視されデフォルトにフォールバック。
- data/stop_requested.flag: run_execution / run_monitoring の停止検出用フラグファイル
- data/kill.flag: KillSwitch による ExecutionEngine 停止フラグ（kill_switch モジュールが書き込む）

初期 DB
--------
- 監視テーブルは起動スクリプト内で init_monitoring_db() により自動作成（冪等）されます。
- paper_trading 環境では paper_trading 用の SQLite を使用し、本番 DB と分離されます。

使い方（実行例）
----------------

1. Execution Engine を起動
   - 通常（デフォルト環境: development）
     - python -m kabusys.run_execution
   - ペーパートレードで起動
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - 実運用（live）
     - export KABUSYS_ENV=live
     - python -m kabusys.run_execution

   実行時、PID ファイル（デフォルト data/execution.pid）や stop flag（data/stop_requested.flag）を参照します。stop を要求する場合は stop_requested.flag を作成してください。

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（秒単位、例: export MONITOR_POLL_INTERVAL=30）

3. Streamlit ダッシュボード（監視）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは監視 DB を読み取り専用で開きます（起動していない場合はエラー表示）

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB を指定する場合:
     - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI / レジーム関連（ライブラリ関数として利用）
   - kabusys.ai.score_news(conn, target_date, api_key=None)  — raw_news から銘柄別センチメントを ai_scores テーブルへ書込
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — レジーム判定を market_regime テーブルへ書込
   - どちらも OPENAI_API_KEY の設定が必要（引数で渡すことも可能）

停止・強制停止
---------------
- 正常停止（監視ループ等）:
  - run_monitoring および run_execution は data/stop_requested.flag の存在を検知して安全に終了します。
- KillSwitch:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き、ExecutionEngine に停止要求を出します（設定で clear on start を有効化可能）。

ディレクトリ構成（概要）
----------------------
src/kabusys/
- __init__.py
- config.py                         — 環境変数ロード / Settings
- run_execution.py                  — ExecutionEngine 起動スクリプト
- run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト

modules / サブパッケージ:
- execution/
  - order_manager.py
  - reconciler.py
  - (ブローカー関連・order_repository 等)
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
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
- tools/
  - paper_verification_report.py
- utils/
  - process_priority.py

（上記は主要ファイルの抜粋です。実際のファイル構成はリポジトリを参照してください）

開発メモ / 注意点
-----------------
- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を検出して .env / .env.local を自動読み込みします。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading: KABUSYS_ENV=paper_trading のときは実口座と完全に分離された DB（デフォルト data/paper_trading.db）を使用します。
- DuckDB: リサーチ・AI は DuckDB を多用します。DuckDB のスキーマ（prices_daily / raw_news / raw_financials 等）を事前に用意してください。
- OpenAI 呼び出し: レート制限・一時エラーは指数バックオフでリトライしますが、API キーやコストに注意してください。
- ログ: スクリプトは基本 INFO レベルでログ出力します。LOG_LEVEL で変更可能です。

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献に関するガイドラインを記載してください）

付録: よく使うコマンド例
-----------------------
- ペーパートレード起動（Bash）
  - export KABUSYS_ENV=paper_trading
  - export OPENAI_API_KEY=sk-...
  - python -m kabusys.run_execution

- 監視起動（30秒間隔）
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

最後に
------
この README はコードベースから抽出した主な機能・使い方の概要です。実運用前に各モジュールのドキュメント（モジュール内 docstring）や設定を十分に確認してから実行してください。必要であれば .env.example を作成し、環境変数のテンプレートを用意することを推奨します。