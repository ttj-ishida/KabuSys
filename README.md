KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株自動売買のための内部ライブラリ／実行コンポーネント群です。  
主に以下を提供します。

- 発注・注文管理・リコンシリエーションを行う ExecutionEngine
- システム稼働状況・注文状況・リスクを監視する Monitoring コンポーネント群（監視 DB + Streamlit ダッシュボード）
- ポートフォリオ構築（候補選定・配分・株数決定・セクター制限等）の純粋関数群
- 研究用ファクター計算／特徴量探索モジュール（DuckDB を利用）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール（ニュース NLP、レジーム判定）
- 便利ユーティリティ（環境変数読み込み、プロセス優先度設定など）

このリポジトリはライブラリとしても、個別の実行スクリプトとしても利用できます。

主な機能
--------
- Execution
  - ブローカークライアントの抽象化（本番／paper_trading 切替）
  - OrderManager による状態管理・重複防止・発注
  - Reconciler による起動時の自動復旧（Order / Positions の突合）
  - RiskManager によるリスク制約（設定に基づく却下等）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・実行プロセス・データ鮮度監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション数上限監視とログ化
  - KillSwitch: 条件に応じて ExecutionEngine 停止のための flag ファイルを書き込む
  - AlertManager: LINE Messaging API を使った一方向通知
  - Streamlit ベースの監視ダッシュボード

- Portfolio（純粋関数）
  - 候補選定（スコア降順 / 上位N）
  - 等金額／スコア加重配分
  - セクター集中制限の適用
  - position sizing（risk_based / equal / score）、単元株丸め、aggregate cap

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由で prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - news_nlp: raw_news を集約して OpenAI API で銘柄別センチメントを算出し ai_scores に書き込む
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定

要件
----
- Python 3.10+
- 必要な外部パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
これらは pip でインストールしてください。例:
  pip install duckdb psutil requests openai streamlit

セットアップ手順
--------------
1. リポジトリをクローン／取得しプロジェクトルートへ移動します。構成は src/ 配下にパッケージが置かれています。

2. Python 環境を作成・有効化し、必要パッケージをインストールします（上記参照）。

3. 環境変数設定
   - プロジェクトルートに .env を置けば自動で読み込まれます（.env.local は .env を上書き）。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   代表的な環境変数（.env に記載例）
   - KABUSYS_ENV=development|paper_trading|live
   - OPENAI_API_KEY=xxxxxxxx
   - JQUANTS_REFRESH_TOKEN=xxxxxxxx
   - KABU_API_PASSWORD=xxxxxxxx
   - PAPER_FILL_MODE=instant|partial|never|reject (paper_trading 用)
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - LOG_LEVEL=INFO
   - MONITOR_POLL_INTERVAL=60  （run_monitoring のポーリング間隔上書き）

4. data ディレクトリを作成（任意ですが実行時に自動作成されることもあります）:
   mkdir -p data

使い方（実行例）
----------------

実行スクリプトの起動方法（プロジェクトルートから実行する想定）:

- Monitoring を起動（監視ループ）
  - 直接スクリプト実行:
    python src/kabusys/run_monitoring.py
  - 環境変数でポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python src/kabusys/run_monitoring.py

  備考:
  - Monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）に接続します。init_monitoring_db() により必要テーブルを作成します。
  - 停止させたい場合はプロジェクトルートの data/stop_requested.flag を作成するとループは検知して終了します。

- ExecutionEngine を起動（実取引 or paper_trading）
  - 本番（デフォルト KABUSYS_ENV を指定しないか live に設定）
    python src/kabusys/run_execution.py
  - Paper Trading モード（DB を paper_trading.db に分離、MockBroker を使用）
    KABUSYS_ENV=paper_trading python src/kabusys/run_execution.py

  備考:
  - Execution は Settings を参照して paper_trading 時は paper_sqlite_path を使用します。
  - 停止シグナルは data/stop_requested.flag の有無で検出します。kill.flag は Execution 停止トリガーとして monitoring 側から書き込まれます。

- Streamlit ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - モジュール実行（引数で期間指定可）
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または直接スクリプト:
    python src/kabusys/tools/paper_verification_report.py --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定、環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能（デフォルト data/paper_trading.db）。

停止・フラグ操作
----------------
- Execution 停止リクエスト（外部から強制停止）:
  - KillSwitch により data/kill.flag が書き込まれると実行エンジンは停止されます（Monitoring の評価により作成）。
  - 手動で kill.flag を作成すると Execution は停止する可能性があります（設定による）。
- 停止フラグ（監視・実行の共通停止）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution は検知して終了します。
- KillSwitch の管理:
  - KillSwitch クラスには clear() があり、Execution 起動時に呼ばれて古い kill.flag を削除する挙動が設定されていることに注意してください。

ライブラリとしての利用
--------------------
- AI スコアリング（例）
  from kabusys.ai.news_nlp import score_news
  score_news(duckdb_conn, target_date, api_key="...")

- レジーム判定（例）
  from kabusys.ai.regime_detector import score_regime
  score_regime(duckdb_conn, target_date, api_key="...")

- Research / Factor（例）
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  calc_momentum(duckdb_conn, date(2026, 4, 1))

- Portfolio（例）
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

- Monitoring API（テスト用）
  - MonitoringEngine をインスタンス化して run_once() を呼ぶことで単発評価が可能（単体テスト向け）。

設定（Settings）についてのポイント
--------------------------------
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を検出）から .env を自動ロードします。
  - .env.local は .env をオーバーライドします。
  - OS 環境変数は保護され、.env.local による上書きも制御されます。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- 主要な Settings プロパティ（実装参照）
  - env: KABUSYS_ENV（development / paper_trading / live）
  - sqlite_path, paper_sqlite_path, duckdb_path
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - PAPER_FILL_MODE（paper_trading の挙動）
  - CPU/MEM/DISK のしきい値（監視用）

ディレクトリ構成（主なファイル）
----------------------------
src/
  kabusys/
    __init__.py                — パッケージ定義
    config.py                  — Settings / .env ローダ
    run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    run_execution.py           — ExecutionEngine 起動スクリプト
    ai/
      news_nlp.py              — ニュース NLP（OpenAI）によるスコアリング
      regime_detector.py      — 市場レジーム判定
    monitoring/
      monitoring_db.py         — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
    execution/
      order_manager.py
      reconciler.py
      ... （broker API / order_repository 等の実装）
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    tools/
      paper_verification_report.py
    utils/
      process_priority.py
    data/                      — 実行時生成される想定のディレクトリ（DB / PID / flags）

注意事項 / 運用上のポイント
--------------------------
- Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。Paper Trading の発注ログは paper_trading.db に分離されています。
- OpenAI 等外部 API を使う機能は API キーの漏洩を避けるため環境変数で安全に管理してください。
- process priority / CPU affinity の設定はプラットフォーム（Windows / POSIX）に依存し、権限不足や未対応 OS ではスキップされます。
- DuckDB に対する executemany の挙動（空リスト不可など）に配慮した実装上の注意点があります。直接 SQL を操作する際は既存実装を踏襲してください。
- Python の型注釈や一部構文（Union 型 |）は Python 3.10 以上を想定しています。

開発 / 貢献
-------------
- コードはモジュール単位で分かれており、純粋関数（portfolio、research）や副作用のあるコンポーネント（monitoring_db、execution）に分離されています。ユニットテストは純粋関数から実装するとテストしやすいです。
- 外部 API 呼び出し部分（OpenAI クライアント呼び出しなど）はテスト時にモック可能なように設計されています（テスト時は _call_openai_api を patch する等）。

以上。README を参照の上、実行・拡張してください。必要であれば .env.example の雛形や docker-compose / systemd ユニットのサンプルも作成しますので指示してください。