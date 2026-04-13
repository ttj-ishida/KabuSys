KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした Python パッケージ群です。本リポジトリは取引エンジン（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、ファクター計算／研究（Research）、AI ユーティリティ（News NLP / Regime Detector）などを含みます。設計方針として以下を重視しています。

- 本番・ペーパートレードの分離（KABUSYS_ENV による切替）
- DuckDB / SQLite を用いたローカルデータ処理
- OpenAI を用いたニュースセンチメント解析（フェイルセーフ設計）
- 監視・アラート（LINE Push、kill flag、Streamlit ダッシュボード）

主な機能
--------
- Execution
  - Broker クライアント抽象化（本番 / モック切替）
  - OrderManager / ExecutionEngine / Reconciler による注文管理・起動時リコンシリエーション
  - RiskManager による投下資金・上限制御
- Monitoring
  - SystemMonitor: プロセス生存 / CPU/Memory/Disk / データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン監視・ポジション上限監視
  - KillSwitch: フラグファイルによる ExecutionEngine 強制停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（監視状況の可視化）
  - 永続化層（SQLite）: system_status, trade_logs, positions, risk_logs, dashboard
- Portfolio
  - 候補選定（select_candidates）、等重/スコア重み計算、ポジションサイズ計算、セクター上限適用、レジーム乗数
- Research
  - ファクター計算（momentum/value/volatility）、将来リターン・IC 計算、統計サマリ
- AI
  - news_nlp: OpenAI を使ったニュースごとの銘柄センチメントスコア付与（ai_scores への書き込み）
  - regime_detector: ETF とマクロニュースを統合して市場レジーム判定（market_regime 書き込み）
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）

セットアップ
------------
1. Python 仮想環境を作成（推奨: Python 3.10+）
   - unix/mac:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - 本リポジトリには requirements.txt は同梱していませんが、少なくとも次をインストールしてください。
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

3. 環境変数 / .env
   - プロジェクトルートの .env / .env.local を自動ロードします（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 代表的な環境変数（最低限プロダクション実行に必要なもの）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...（AI 機能を使う場合必須）
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用: data/paper_trading.db)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（監視アラートに LINE を使う場合）
   - .env の例:
     - JQUANTS_REFRESH_TOKEN=xxxx
     - KABU_API_PASSWORD=yyyy
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=paper_trading

4. データディレクトリ
   - デフォルトの DB パスは data/ 以下です。必要に応じてディレクトリを作成してください。
     - mkdir -p data

使い方
------
- 監視ループ起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定できます（デフォルト 60）。
  - 例:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 実行開始時にプロセス優先度を "high" に設定します（set_process_priority を使用）。

- Execution 起動（売買エンジン）
  - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を利用して PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します（本番 DB と分離）。
  - 実行:
    - python -m kabusys.run_execution

- Paper Trading 検証レポート
  - data/paper_trading.db を対象に稼働率・成功率・レイテンシ等のサマリを作成します。
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - または指定 DB:
      - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- Streamlit ダッシュボード（監視画面）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用の SQLite DB を read-only で開きます。MonitoringEngine を先に起動してデータを書き込んでおいてください。

- AI 関連（ニューススコア / レジーム判定）
  - OPENAI_API_KEY が必要です。これらは DuckDB 接続を受け取り、ai_scores / market_regime へ書き込みます（フェイルセーフにより API 失敗時は一部をスキップ・中立値で継続します）。
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

設定の挙動（重要）
-----------------
- 設定の自動読み込み
  - .env（プロジェクトルート）と .env.local が自動で読み込まれます。OS 環境変数は保護され、.env.local は上書きモードで読み込まれます。
- KABUSYS_ENV
  - development / paper_trading / live のいずれか。paper_trading は DB を分離してモックブローカーを使う想定。
- MONITORING は環境にかかわらず本番 sqlite_path を使って初期化（run_monitoring の仕様）。
- PID/KILL フラグ
  - pid ファイル（デフォルト data/execution.pid）を監視・管理。kill.flag（デフォルト data/kill.flag）を用いて ExecutionEngine の外部停止をトリガーできます。

監視 DB（SQLite）スキーマ概要
----------------------------
init_monitoring_db により以下のテーブルが作成されます（冪等）。

- system_status
  - id, recorded_at (ISO8601), cpu_percent, memory_percent, disk_percent, process_ok
- trade_logs
  - id, logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms
- positions
  - code (PK), qty, avg_price, current_price, updated_at
- risk_logs
  - id, logged_at, event_type, metric_name, metric_value, threshold, detail
- dashboard
  - id（常に1）, updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

ディレクトリ構成（主要ファイル）
------------------------------
以下は主要モジュールのツリー（src/kabusys を基準）。実際のファイル数はさらにありますが代表を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings（.env 自動ロード含む）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （Broker / Engine 等の実装はこの階層に配置）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (参照されるが別実装のモジュールあり)
    - pipeline / stats 等への参照

開発上の注意・ベストプラクティス
--------------------------------
- .env.example を参考に .env を作成してください（必須キーは Settings が _require() で検証します）。
- OpenAI API を使用する機能は API キーが必須です。実行前に環境変数 OPENAI_API_KEY を設定してください。
- 本番環境での KABUSYS_ENV=live 実行時は DB のバックアップ／排他に注意してください。
- Monitoring のポーリングはデフォルト 60 秒です。短くしすぎると API / DB に負荷がかかるため必要に応じて MONITOR_POLL_INTERVAL を調整してください。
- Process priority / CPU affinity 設定はプラットフォーム依存です（psutil を使用）。権限不足だと警告でスキップされます。

ライセンス・貢献
----------------
- 本 README にライセンス情報が含まれていないため、リポジトリルートの LICENSE を参照してください。
- バグ報告・機能要望は Issue を作成してください。

以上です。必要があれば、README にサンプル .env.example や requirements.txt、起動用 systemd ユニットの例などを追加して作成します。どれを追加しますか？