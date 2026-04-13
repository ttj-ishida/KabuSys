KabuSys — README
===============

概要
----
KabuSys は日本株の自動売買システム（リサーチ→ポートフォリオ構築→発注→監視）を想定した Python パッケージです。
主な機能はファクター計算・特徴量解析、ポートフォリオ構築、注文管理・再同期間合（reconciliation）、監視（稼働率・滞留注文・リスク）およびニュース NLP を用いた AI スコアリングです。  
データ永続化には SQLite（監視・注文ログ）と DuckDB（時系列 / ファクター集計）を使用します。

主な特徴
---------
- ファクター計算（Momentum / Volatility / Value） — kabusys.research
- 特徴量探索・IC 計算（Research 向けユーティリティ）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- ExecutionEngine 周り（OrderManager / OrderRepository / Reconciler）
- Paper Trading モード（本番 DB と分離された data/paper_trading.db を使用）
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
  - ログ永続化用の MonitoringDB（system_status, trade_logs, risk_logs, positions, dashboard）
  - LINE へのプッシュ通知（AlertManager）
  - Kill Switch（条件で ExecutionEngine を停止するフラグファイル）
- AI モジュール
  - news_nlp.score_news: OpenAI (gpt-4o-mini) を使った銘柄ごとのニュースセンチメント評価
  - regime_detector.score_regime: ma200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- 監視ダッシュボード（Streamlit）と Paper Trading 検証レポート生成ツール

前提（推奨）
-------------
- Python 3.10+
- 必要ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを利用する場合）
- SQLite（標準で同梱）と任意の OS（Windows / Linux / macOS をサポートする実装あり）

セットアップ手順
----------------
1. リポジトリをクローン／展開し、プロジェクトルートへ移動します。

2. 仮想環境を作成して有効化します（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストールします（pip 例）:
   - pip install duckdb psutil requests openai streamlit

   実際の requirements.txt がある場合はそれを使用してください。

4. 環境変数の設定:
   - プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（デフォルトで OS 環境変数を優先）。
   - 必須（運用に応じて設定）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（使用時）
     - KABU_API_PASSWORD — kabuステーション API（発注に必要）
   - OpenAI を使う場合:
     - OPENAI_API_KEY — news_nlp / regime_detector の呼び出しで必要
   - 主要なオプション（デフォルト値）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - SQLITE_PATH: data/monitoring.db
     - DUCKDB_PATH: data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - LOG_LEVEL: INFO
     - PAPER_FILL_MODE: instant | partial | never | reject （paper_trading 時のモック約定挙動）
   - 監視ポーリング間隔:
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60 秒）。0 以下や不正値は無視され 60 秒にフォールバック。

5. データディレクトリ作成:
   - data/ ディレクトリなど必要な親ディレクトリを作成しておくとよいです。
   - PID / flag ファイルも同ディレクトリに置くのが既定です。

使い方（実行例）
----------------
- 監視ループを起動（プロセス優先度を高に設定します）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（秒）

- ExecutionEngine（注文実行）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。

- Paper Trading 検証レポートを出力:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- Streamlit ダッシュボード（監視）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI モジュール（プログラムから呼ぶ場合）:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="...")  （conn は duckdb connection）

注意点・挙動
-------------
- KABUSYS_ENV
  - development: 標準挙動（本番 DB を使用）
  - paper_trading: 発注はモック、paper_trading 用 DB に記録して本番 DB と分離
  - live: 本番運用モード（実際のブローカー / API を利用）

- Monitoring は KABUSYS_ENV に関係なくデフォルトの sqlite_path（本番監視 DB）を使用します（運用上の観点から本番監視 DB を想定）。

- process priority / CPU affinity の設定は psutil を利用します。権限不足や未対応 OS では警告を出してスキップされます。

- OpenAI API 呼び出しはレート制限や 5xx 等に対してエクスポネンシャルバックオフの再試行ロジックを持ちますが、最終的に失敗した場合は安全にフォールバック（例: macro_sentiment=0.0）します。

データベース・スキーマ（監視）
------------------------------
init_monitoring_db() により以下テーブルを作成（冪等）します:
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 の集計行: updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)

主要モジュールの役割（簡易）
---------------------------
- kabusys.config — 環境変数読み込み・Settings クラス
- kabusys.utils.process_priority — プロセス優先度 / CPU affinity 設定ユーティリティ
- kabusys.monitoring.* — 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch 等）
- kabusys.monitoring.monitoring_db — 監視 DB の初期化と読み書きラッパー（MonitoringDB）
- kabusys.execution.* — 発注・Order 管理・Reconciler（再同期）、ExecutionEngine（起動スクリプトから利用）
- kabusys.portfolio.* — 候補選定・重み付け・ポジションサイズ計算・リスク調整
- kabusys.research.* — ファクター計算（momentum/value/volatility）、特徴量探索・IC 計算
- kabusys.ai.* — news_nlp（ニュース NLP によるスコア付与）、regime_detector（市場レジーム判定）
- kabusys.tools.paper_verification_report — Paper Trading の検証レポート生成
- streamlit_dashboard.py — 監視情報を可視化する Streamlit アプリ

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py
    utils/
      __init__.py
      process_priority.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    monitoring/
      __init__.py
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      monitoring_engine.py
      alert_manager.py
      kill_switch.py
      streamlit_dashboard.py
    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    execution/
      (OrderManager, OrderRepository, Reconciler, ExecutionEngine 等)
    tools/
      __init__.py
      paper_verification_report.py
    run_monitoring.py
    run_execution.py

よくある運用上のヒント
----------------------
- 開発環境で Paper Trading を行う場合は KABUSYS_ENV=paper_trading を指定して本番 DB を汚さないようにしてください。
- OpenAI を用いる処理は API キー（OPENAI_API_KEY）を .env に指定しておくと便利です。
- MONITOR_POLL_INTERVAL は監視の負荷と反応速度のトレードオフです（デフォルト 60 秒）。
- PID ファイルや kill.flag を利用してプロセスの状態検知・停止を行う仕組みがあります。ExecutionEngine 側が kill.flag を監視して停止する設計になっています（詳しくはコード内の KillSwitch / ExecutionEngine 実装を参照）。

ライセンス / 貢献
-----------------
本リポジトリのライセンス情報・貢献ルールがある場合はプロジェクトルートの LICENSE / CONTRIBUTING を参照してください。

補足
----
本 README はコードベースの主要機能と使い方をまとめたもので、細かい設定や内部設計は各モジュールの docstring（ソース内コメント）を参照してください。必要であればさらに詳しい使用例や設定テンプレート（.env.example）を追加できます。