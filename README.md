README
======

概要
----
KabuSys は日本株向けの自動売買および検証・監視ツール群をまとめた小規模なシステムです。本コードベースは以下の機能を含みます。

- 実際の発注エンジン（ExecutionEngine）と発注管理（OrderManager / Reconciler）
- 監視（System / Trade / Risk）とアラート（LINE Push）機能
- Paper Trading 実行・検証（paper DB に完全分離）
- ファクター計算・リサーチユーティリティ（DuckDB を用いたファクター計算等）
- ニュース NLP を使ったセンチメント計算（OpenAI API を利用）
- Streamlit ベースの監視ダッシュボード
- 各種ユーティリティ（プロセス優先度設定、.env ロード等）

主な特徴
--------
- 環境分離:
  - 本番（live）、Paper Trading（paper_trading）、開発（development）を KABUSYS_ENV で切替可能。
  - Paper Trading 実行時は専用 SQLite DB (data/paper_trading.db) を使用し、本番 DB と分離。
- 監視と自動停止:
  - System / Trade / Risk モニタリングを行い、KillSwitch により停止フラグ（data/kill.flag）を書き出せる。
  - ポーリング監視は run_monitoring.py で常駐実行可能。MONITOR_POLL_INTERVAL で間隔を変更可能。
- Research / AI:
  - DuckDB の prices_daily / raw_financials などを参照してファクター計算や将来リターン、IC 等を算出。
  - ニュース記事を集約し OpenAI（gpt-4o-mini 等）で銘柄・マクロセンチメントを算出して ai_scores に格納。
- 運用支援ツール:
  - paper_verification_report: Paper Trading DB から稼働率・注文成功率・レイテンシ等の検証レポートを生成。
  - Streamlit ダッシュボードで監視データを可視化。

セットアップ手順
--------------
1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 明示的な requirements.txt がない場合、主要依存をインストールしてください:
     pip install duckdb psutil requests openai streamlit

   - 実環境や CI では追加の依存（テストツールなど）が必要な場合があります。

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data
   - 監視や実行時に data/*.db, data/*.pid, data/kill.flag, data/stop_requested.flag を使用します。

4. 環境変数の準備
   - .env または .env.local をプロジェクトルートに置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development|paper_trading|live
     - JQUANTS_REFRESH_TOKEN=（必須）
     - KABU_API_PASSWORD=（必須）
     - OPENAI_API_KEY=（ニュース NLP / regime 判定で使用）
     - LINE_CHANNEL_ACCESS_TOKEN=（任意、AlertManager 用）
     - LINE_USER_ID=（任意、AlertManager 用）
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject （paper_trading の約定挙動）
     - MONITOR_POLL_INTERVAL=（秒、例: 60） — run_monitoring のポーリング間隔上書き

   - 例 (.env):
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

注意: Settings クラスで必須の環境変数が未設定だと起動時に ValueError が発生します。

使い方
------
基本的な実行方法は以下です。プロジェクトルート（src/ のひとつ上）で実行することを想定しています。

1. 監視ループを起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は常に本番 sqlite_path を使用します（実行環境にかかわらず monitoring の DB は本番パスを参照）。

   停止:
   - data/stop_requested.flag を作成するとループが終了します。

2. ExecutionEngine（発注エンジン）を起動
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
   - 起動時、data/stop_requested.flag が存在すると起動せず終了します。
   - 実行中に data/stop_requested.flag を作成するとエンジン停止処理が行われます。

3. Paper Trading 検証レポート（コマンドライン）
   - python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     --db PATH で PAPER_TRADING_SQLITE_PATH を指定できます（引数 > 環境変数 > デフォルト の優先順）。

4. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - ダッシュボードは read-only モードで SQLite を開いて表示します。監視データが無い場合は案内が表示されます。

5. AI / Research API の利用（コード呼び出し）
   - kabusys.ai.score_news(conn, target_date, api_key=None) — raw_news → ai_scores にスコア書込み
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — market_regime を更新
   - kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic などは DuckDB 接続を受けて純粋に計算を行います。

運用時のフラグ / ファイル
-------------------------
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルを確認して終了/停止します。任意の内容のファイルで OK。

- data/kill.flag
  - KillSwitch がトリガー条件を満たした際に書き込まれる停止フラグ（ExecutionEngine 停止のシグナルとして使用）。KillSwitch により冪等に作成されます。

- PID ファイル
  - ExecutionEngine は data/execution.pid（または Settings.pid_file_path の値）を用いてプロセス存在チェックを行います。古い PID ファイルが残っていてプロセスが存在しない場合は stale PID と判定し削除します。

設定（Settings クラス）
---------------------
主要設定は kabusys.config.Settings で管理されており、環境変数から読み込まれます。重要項目の抜粋:

- env: KABUSYS_ENV (development | paper_trading | live)
- jquants_refresh_token: JQUANTS_REFRESH_TOKEN（必須）
- kabu_api_password: KABU_API_PASSWORD（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp, regime_detector）
- PAPER_FILL_MODE: instant | partial | never | reject
- SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / DUCKDB_PATH
- PID_FILE_PATH / KILL_FLAG_PATH
- CPU / MEMORY / DISK の閾値（監視用）

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                      — 環境変数 / Settings
    utils/
      process_priority.py          — プロセス優先度 / CPU affinity
    execution/                     — 発注エンジン関連（OrderManager / Reconciler / Engine 等）
      order_manager.py
      reconciler.py
      ...（他の execution モジュール）
    monitoring/                     — 監視関連
      monitoring_db.py             — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    ai/                             — ニュース NLP / レジーム検出
      news_nlp.py
      regime_detector.py
    research/                       — ファクター計算・特徴探索
      factor_research.py
      feature_exploration.py
    portfolio/                      — ポートフォリオ構築（候補選定・重み・サイズ計算等）
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    data/                           — （データ処理パイプラインなどが入る想定）
    tools/
      paper_verification_report.py  — Paper Trading 検証レポート
    run_monitoring.py               — SystemMonitor ポーリングループの起動スクリプト
    run_execution.py                — ExecutionEngine 起動スクリプト

data/
  (ランタイムで生成するファイル群)
  - monitoring.db        — 監視用 SQLite（デフォルト）
  - paper_trading.db     — Paper Trading 用 SQLite（paper_trading 時）
  - kabusys.duckdb       — DuckDB データ（prices_daily, raw_financials 等）
  - execution.pid
  - stop_requested.flag
  - kill.flag
  - ...

設計上の注意点 / 運用メモ
------------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が見つかれば自動で .env / .env.local を読み込みます。
  - テスト等で自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- Paper Trading:
  - KABUSYS_ENV=paper_trading のとき、実際のブローカーではなく MockBrokerClient（BrokerClientFactory に実装）を使用し、paper DB に記録されます。実運用の DB と完全分離です。

- OpenAI 使用:
  - news_nlp.py / regime_detector.py は OpenAI API を利用します。API 呼び出しはエラー（RateLimit / 接続断 / 5xx 等）に対してリトライやフェイルセーフを実装していますが、API キーは必須の呼び出しがあります（関数引数または環境変数 OPENAI_API_KEY）。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成・必要なカラムの追加（簡易マイグレーション）を行います。

- 権限:
  - process_priority の設定や CPU affinity は OS により動作が異なり、権限不足で失敗する場合は警告ログを出してスキップします。

ライセンス・貢献
----------------
（ここにライセンスや貢献方法を追記してください）

問い合わせ
----------
不明点や拡張要望があれば開発者にご相談ください。

以上。