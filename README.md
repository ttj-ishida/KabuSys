KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。本リポジトリにはトレード実行（ExecutionEngine）や監視（MonitoringEngine）、ポートフォリオ構築、リサーチ／ファクター計算、LLM ベースのニュース NLP・レジーム判定などのモジュールが含まれます。設計は以下を重視しています:

- 本番と Paper Trading の分離（DB・ブローカーの切替）
- 監視・アラート機構（LINE Push 連携、kill.flag による安全停止）
- DuckDB を使った時系列データ処理（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・マクロ判定（フェイルセーフ実装）
- テスト容易性と副作用の少ない純粋関数の採用（ポートフォリオ構築等）

主な機能
---------
- Execution 関連
  - OrderManager: 発注ワークフローと重複チェック
  - Reconciler: 再起動時の注文／ポジション突合（自動復旧）
  - ExecutionEngine（起動スクリプトあり）: 実行スレッド管理・PID ファイル等

- Monitoring（監視）関連
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常監視
  - RiskMonitor: ドローダウン・ポジション上限監視
  - MonitoringEngine: これらを束ねるポーリングエンジン
  - AlertManager: LINE push による通知（cooldown 管理）
  - KillSwitch: kill.flag の書き込みによる Execution 停止シグナル
  - SQLite ベースの永続化（monitoring_db）

- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 等配分／スコア加重（calc_equal_weights, calc_score_weights）
  - 単元株丸め・ポジションサイズ計算（calc_position_sizes）
  - セクターキャップ適用・レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- Research（リサーチ）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC 計算・統計サマリ（calc_forward_returns, calc_ic, factor_summary）

- AI（LLM 連携）
  - news_nlp.score_news: ニュースをまとめて OpenAI に投げ、銘柄ごとのスコアを ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF とマクロ記事を用いて日次の市場レジームを判定・永続化

- ツール
  - paper_verification_report: Paper Trading DB を分析して稼働率・注文成功率・レイテンシ等の検証レポートを生成

セットアップ
-----------
前提
- Python 3.9+（タイプヒントに | を多用しているため、3.10 推奨）
- SQLite（標準ライブラリ）
- DuckDB
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）

例: 仮想環境作成とパッケージインストール
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt がある場合はそれに従ってください）

環境変数と .env の自動読み込み
- Settings モジュールはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して .env/.env.local を自動で読み込みします。
- 自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 代表的な環境変数:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 用）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 DB のデフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading の約定モード（instant, partial, never, reject）
  - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

主なファイル・パス（デフォルト）
- データディレクトリ: data/
- 監視 DB (SQLite): data/monitoring.db
- Paper Trading DB (SQLite): data/paper_trading.db
- DuckDB: data/kabusys.duckdb
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（run_* スクリプトの手動停止フラグ）
  - data/kill.flag（KillSwitch が書く停止フラグ）

使い方（起動・ツール）
--------------------

1) 監視ループ（MonitoringEngine）の起動
- 監視ループは常に本番用の sqlite_path を使用します（KABUSYS_ENV に依存しません）。
- 起動:
  python -m kabusys.run_monitoring
- ポーリング間隔を変更:
  export MONITOR_POLL_INTERVAL=30  # 秒（正の整数、デフォルト 60）
- 停止:
  data/stop_requested.flag を作成すると安全にループを抜けます（または Ctrl+C）。

2) 実行エンジン（ExecutionEngine）の起動
- Paper Trading の場合は MockBrokerClient が使われ、data/paper_trading.db を使用して本番 DB と分離されます。
- 起動:
  python -m kabusys.run_execution
- 実行中に data/stop_requested.flag を作成すると Engine を停止します。
- Execution の PID は data/execution.pid に保存されます。

3) Paper Trading 検証レポート
- 使い方:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
- 出力: 稼働率・注文成功率・送信率・レイテンシ（P95）等のサマリと PASS/FAIL 判定

4) 監視ダッシュボード（Streamlit）
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 読み取り専用で DB に接続し、ポートフォリオ値・ポジション・直近注文・システムステータス等を表示

5) AI モジュール実行例
- ニューススコアリング:
  - スコア生成関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 実行には OPENAI_API_KEY が必要。関数は DuckDB 接続を受け取る。
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が必要。DB に market_regime レコードを書き込みます。
- いずれの処理も LLM のエラーや API 障害に対してフェイルセーフ（デフォルト値で継続）に設計されています。

設定上の注意点 / 動作仕様
-----------------------
- .env 読込順:
  OS 環境変数 > .env.local > .env（OS 環境変数は保護され、.env.local でも上書きされない）
- MONITOR_POLL_INTERVAL:
  監視ループの秒間隔。0 以下や非整数は警告が出てデフォルト（60秒）にフォールバックします。
- 監視 DB のマイグレーション:
  init_monitoring_db() は冪等で、必要に応じてテーブル追加・カラム追加を行います（例: trade_logs.latency_ms, dashboard.peak_value）。
- Paper Trading 分離:
  run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を用います。Monitoring は常に sqlite_path（本番監視 DB）を使用する点に注意してください。
- KillSwitch:
  RiskMonitor がドローダウン超過やポジション上限超過を検出すると、KillSwitch が data/kill.flag を作成して Execution 停止を促します。KillSwitch は冪等に書き込みを行います。
- OpenAI API:
  - OPENAI_API_KEY が未設定の場合、score_news / score_regime は ValueError を投げます（呼び出し側で捕捉してください）。
  - レート制限や 5xx エラーに対しては指数バックオフでリトライします。解析失敗時は安全に 0.0 等へフォールバックします。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                      # 環境変数読み込み・Settings
    run_monitoring.py              # SystemMonitor ポーリングループ起動スクリプト
    run_execution.py               # ExecutionEngine 起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py # Paper Trading 検証レポート
    utils/
      __init__.py
      process_priority.py          # プロセス優先度・CPU affinity
    monitoring/
      __init__.py
      monitoring_db.py             # SQLite 永続化層（init + MonitoringDB）
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      # ...（broker_api, execution_engine, order_repository 等が存在）
    portfolio/
      __init__.py
      portfolio_builder.py
      risk_adjustment.py
      position_sizing.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/                          # 実行時に利用される data ファイル群（DB, pid, flag 等）
      (data/kabusys.duckdb, monitoring.db, paper_trading.db, execution.pid, stop_requested.flag, kill.flag)

開発者向けメモ
---------------
- ローカルでの Paper Trading は PAPER_TRADING_SQLITE_PATH を設定して専用 DB を使ってください。
- .env.example を作成して必要な環境変数を一覧化するとセットアップが楽になります（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, LINE_* 等）。
- テスト時に .env の自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部はユニットテストでモック可能な形に分離されています（例えば _call_openai_api を patch）。

ライセンス・バージョン
---------------------
- パッケージバージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

問い合わせ・貢献
----------------
バグ報告、改善提案、プルリクエストは GitHub 上のリポジトリに issue/PR を作成してください。README にない使い方の質問やデプロイに関する相談も歓迎します。

---
この README はソースコードのドキュメント・挙動に基づいて作成しました。追加で記載してほしいコマンドや環境例（.env.example のサンプルなど）があれば教えてください。