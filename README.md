KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株を対象とした自動売買システムのコードベースです。本リポジトリは以下の主要機能を含み、実運用（live）、ペーパートレード（paper_trading）、開発（development）いずれの実行モードにも対応します。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理・リコンサイル等
- 監視（Monitoring）: システム稼働状況、注文状況、リスク監視、Kill Switch
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクター制限
- リサーチ: ファクター計算（Momentum / Value / Volatility 等）、特徴量解析
- AI モジュール: ニュースの NLP スコアリング（OpenAI）、市場レジーム判定
- ツール: ペーパートレード検証レポート生成、設定ウィザード、設定検証 CLI
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込み等

主な機能一覧
-------------
- run_execution.py: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパー用 DB に記録。
- run_monitoring.py: SystemMonitor のポーリングループを起動。監視データを SQLite に書き込む。
- monitoring: SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine 等の監視周り実装。
- portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター適用、レジーム乗数等の純粋関数群。
- research: DuckDB を利用したファクター計算（mom/vol/value）、将来リターン、IC 計算など。
- ai: news_nlp（OpenAI を使ったニュースセンチメントのバッチスコアリング）、regime_detector（マクロ記事 + ETF MA からレジーム判定）。
- tools: paper_verification_report（ペーパートレード履歴からの PASS/FAIL レポート出力）。
- 設定関連: config_setup（.env 対話式ウィザード）、validate_config（起動前設定検証）、config（自動 .env 読み込み・Settings）。

前提条件 / 推奨環境
------------------
- Python 3.9+（型アノテーションにより 3.9 以上を想定）
- 必要な外部ライブラリ（例）: duckdb, psutil, openai, PyYAML（YAML 検証は任意）
  - 実行前に requirements.txt がある場合はそちらを使用してください（本コード例ではファイル未提示のため下記参照）。

セットアップ手順（ローカル）
-------------------------
1. リポジトリをクローン:
   git clone <repo-url>
2. 仮想環境作成・有効化:
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール:
   pip install duckdb psutil openai PyYAML
   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）
4. .env の作成:
   - 対話式で作成: python -m kabusys.config_setup
   - 手動作成: リポジトリルートに .env を置く（.env.example を参照）
   自動ロード:
     - config.py はプロジェクトルートの .env を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
5. 設定検証（起動前チェック）:
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱いになります。

主要な環境変数（代表）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な任意 / 設定:
- KABUSYS_ENV: execution 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
  - paper_trading の場合は MockBrokerClient を利用し、PAPER_TRADING_SQLITE_PATH に DB を記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時のフィル動作 ("instant" | "partial" | "never" | "reject")（デフォルト: "instant"）
- LOG_LEVEL: ログレベル（"DEBUG","INFO",...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で利用）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60 秒）

使い方（起動例）
----------------
- 環境作成・確認:
  python -m kabusys.config_setup
  python -m kabusys.validate_config

- 実行エンジン起動（実際に発注する環境では注意）:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading とすると MockBrokerClient を使用し、data/paper_trading.db に記録されます。
  - エンジンは data/stop_requested.flag を監視。フラグが存在すると起動・実行を停止します。

- 監視プロセス起動:
  python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を環境に関係なく使用します（monitoring 用は本番 DB を想定）。

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  --db オプションで SQLite パスを指定可能。デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

- AI スコアリング（プログラム呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
    DuckDB 接続を渡してニュース NLP を実行し ai_scores テーブルへ書き込む。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
    レジーム判定と market_regime への書き込みを行う。

ログ / ローテーション
--------------------
- ログはルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次）を設定します。
- デフォルトログディレクトリ: logs/
- 各アプリケーション実行時に app_name 引数でログファイル名が決まります（例: execution → logs/execution.log）。
- ログレベルは以下の順で解決されます: 関数引数 > LOG_LEVEL 環境変数 > "INFO"

監視と停止（Kill Switch）
-----------------------
- KillSwitch は RiskMonitor の結果（ドローダウン・ポジション上限）に基づき data/kill.flag を書き込み、ExecutionEngine に停止を促します。
- run_execution は data/stop_requested.flag や data/execution.pid を使用して実行制御を行います。
- run_monitoring はプロジェクト data/stop_requested.flag を検知するとループを終了します。

DB スキーマ（監視用 / monitoring_db）
-----------------------------------
monitoring_db.init_monitoring_db() により以下テーブルが作成されます（冪等）:
- system_status: cpu/memory/disk/process_ok 等の時系列
- trade_logs: 発注イベントログ（event_type: Created/Sent/Filled 等、latency_ms を含む）
- positions: 保有一覧（code, qty, avg_price, current_price, updated_at）
- risk_logs: リスク関連イベント（DRAWDOWN_ALERT 等）
- dashboard: 集計（id=1 の単一行で portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

ライブラリ / モジュールの簡単説明
--------------------------------
- kabusys.config: .env ファイルの自動読み込み、Settings クラスによる環境変数アクセス
- kabusys.config_setup: 対話式 .env 作成ウィザード
- kabusys.validate_config: 起動前に必須 env や config/*.yaml を検証
- kabusys.utils.logging_setup: 統一的なロギング設定ユーティリティ
- kabusys.utils.process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
- kabusys.portfolio: 候補選定・重み付け・ポジションサイズ・リスク調整（純粋関数）
- kabusys.research: DuckDB を使ったファクター計算・IC/RF 計算
- kabusys.ai: news_nlp（OpenAI ベースのニューススコアリング）、regime_detector
- kabusys.monitoring: 監視エンジンと各種モニタ（System/Trade/Risk）、KillSwitch、AlertManager（実装あり）
- scripts/entry modules: run_execution.py / run_monitoring.py / tools/paper_verification_report.py

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
  __init__.py
  config.py
  config_setup.py
  validate_config.py
  run_execution.py
  run_monitoring.py
  tools/
    __init__.py
    paper_verification_report.py
  utils/
    __init__.py
    logging_setup.py
    process_priority.py
  portfolio/
    __init__.py
    portfolio_builder.py
    position_sizing.py
    risk_adjustment.py
  research/
    __init__.py
    factor_research.py
    feature_exploration.py
  ai/
    __init__.py
    news_nlp.py
    regime_detector.py
  monitoring/
    monitoring_db.py
    system_monitor.py
    trade_monitor.py
    risk_monitor.py
    monitoring_engine.py
    kill_switch.py
  execution/                # 実行エンジン関連（BrokerFactory等はここ）
    ...
  data/                     # 実行時に作られる/参照するデータファイル（DB, pid, flags 等）
  logs/                     # ログ出力先（デフォルト）

開発者向けヒント
-----------------
- .env は絶対にリポジトリにコミットしないでください（config_setup.py の注意書きを参照）。
- validate_config は起動前チェックに便利です。--strict を検討してください。
- AI 関連は OpenAI API を利用するため、テストでは _call_openai_api をモックする設計になっています。
- DuckDB をローカルに用意し、prices_daily / raw_financials / raw_news 等のテーブルを作ることで research / ai 機能をローカルで検証できます。

トラブルシューティング
-----------------------
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみになります（警告出力）。
- MONITOR_POLL_INTERVAL に 0 以下を設定すると無効値として 60 秒が使われます（警告ログ）。
- OpenAI API キー未設定で ai.score_news / score_regime を呼ぶと ValueError が発生します。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ で管理されています（例: 0.1.0）。
- ライセンス情報は本リポジトリに付随する LICENSE ファイルを参照してください（本コード断片では記載ありません）。

最後に
------
この README はコードベースから抜粋した主要な使い方・設計意図をまとめたものです。各モジュールの詳細（関数引数、返り値、動作仕様）はソースコード内の docstring を参照してください。必要であれば、各モジュールの API リファレンス用 README も作成できます。どの項目を優先してドキュメント化するか教えてください。