KabuSys
======

KabuSys は日本株向けの自動売買・調査・監視ツール群です。本リポジトリは発注実行、監視、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM）連携などの機能を含むモジュール群で構成されています。

この README ではプロジェクト概要、主な機能、セットアップ方法、使い方（起動コマンドや主要オプション）、およびディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は以下を目的としたモジュール群の集合です。

- 発注実行エンジン（ExecutionEngine） — ブローカー API とやり取りして注文を生成・管理する。
- 監視（Monitoring） — システム稼働状況、注文状況、リスク監視、Kill Switch による停止制御、LINE 通知等。
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ計算、セクター制限などの純粋関数実装。
- リサーチ（Research） — DuckDB 上の価格・財務データからファクター計算や特徴量解析を行う。
- AI（LLM）連携 — ニュースを LLM（OpenAI）でスコアリングし、レジーム判定などを行う。
- ツール類 — Paper Trading 検証レポート生成や Streamlit ダッシュボードなど。

主な機能一覧
--------------
- Execution
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - ブローカーファクトリで本番 or ペーパー取引（KABUSYS_ENV=paper_trading）を切り替え
  - リスク管理（RiskManager）設定、注文管理（OrderManager）、再整合（Reconciler）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID・データ鮮度監視
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション数監視とログ記録
  - KillSwitch: 条件達成時にフラグファイルを書いて ExecutionEngine 停止
  - AlertManager: LINE Messaging API による通知（クールダウン制御）
  - Streamlit ダッシュボード（read-only で monitoring DB を可視化）
- Portfolio
  - 候補選定（スコア降順）、等配分/スコア加重、リスクベースの株数決定
  - セクターキャップ、レジーム乗数
- Research
  - momentum / volatility / value ファクター計算（DuckDB を利用）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- AI
  - news_nlp.score_news: raw_news を LLM に送り銘柄別センチメントを ai_scores テーブルに書き込み
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュース LLM を合成して market_regime に保存
- Tools
  - paper_verification_report: Paper Trading DB に対する検証レポート出力（稼働率・成功率・レイテンシ等）

セットアップ手順
-----------------
前提
- Python 3.9+（ソースは typing / modern 標準ライブラリ機能を使用）
- system に応じて psutil が動作すること
- OpenAI API を使う機能は OPENAI_API_KEY が必要

必要な Python パッケージ（例）
- duckdb
- psutil
- requests
- openai
- streamlit

例: 仮想環境作成とインストール
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install duckdb psutil requests openai streamlit

（プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

.env（環境変数）設定
- プロジェクトルートに .env / .env.local を置くことで自動読み込みされます（Settings モジュール参照）。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 主な環境変数（例）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用
  - KABU_API_PASSWORD — kabuステーション API パスワード
  - OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
  - KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
  - PAPER_FILL_MODE — paper_trading のモック約定モード (instant | partial | never | reject)
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite DB（デフォルト: data/paper_trading.db）
  - SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH / KILL_FLAG_PATH — PID / kill.flag ファイルパス
  - LOG_LEVEL — ログレベル（DEBUG | INFO | ...）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知設定

データベース初期化
- 監視用 SQLite は init_monitoring_db() により必要テーブルを作成します（冪等）。
- DuckDB 側には prices_daily / raw_financials / raw_news 等のテーブルが必要です（外部手段で用意）。

使い方（主要コマンド）
---------------------

ExecutionEngine を起動
- 本番または開発モードで起動:
  python -m kabusys.run_execution
- ペーパー取引モード（MockBroker を使用し paper_trading DB に記録）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 特記事項:
  - 起動時にプロセス優先度を "high" に設定しようとします（psutil によるため権限が必要な場合あり）。
  - paper_trading は本番 DB と分離して PAPER_TRADING_SQLITE_PATH に書き込みます。

Monitoring（polling）を起動
- 監視ループ起動:
  python -m kabusys.run_monitoring
- ポーリング間隔を変更:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  デフォルトは 60 秒。0 以下や不正な値はデフォルトにフォールバックします。
- 監視は Settings によらず本番 sqlite_path（SQLITE_PATH）を使います。

Streamlit ダッシュボード（監視）
- 起動例（read-only モードで監視 DB を開く）:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Dash は monitoring DB を読み取り専用で表示します。監視プロセスを先に起動しておくとデータが見えます。

Paper Trading 検証レポート
- コマンドライン:
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --from YYYY-MM-DD
    --to   YYYY-MM-DD
    --db PATH （PAPER_TRADING_SQLITE_PATH を上書き可能）
- 出力: 稼働率、注文成功率、送信率、レイテンシ（P95）等のサマリと PASS/FAIL 判定

AI（ニューススコア / レジーム判定）の呼び出し（プログラム的に）
- news_nlp.score_news(conn, target_date, api_key=None)
  - conn: DuckDB 接続
  - target_date: date オブジェクト
  - api_key: None の場合は環境変数 OPENAI_API_KEY を参照
- regime_detector.score_regime(conn, target_date, api_key=None)
- どちらも API キーが未設定だと ValueError が発生します。API 呼び出しはリトライ・フェイルセーフの仕組みが組み込まれています（失敗時はスコア0などでフォールバックするロジックあり）。

構成・設計上の注意
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロードします（CWD に依存しない）。
- KABUSYS_ENV の値:
  - development: 開発用
  - paper_trading: ペーパー取引（MockBroker + 別 SQLite）
  - live: 本番
- paper_trading の場合、発注は MockBrokerClient を使用し data/paper_trading.db に記録されるように設計されています。
- Monitoring の kill switch は data/kill.flag を書き、ExecutionEngine 側で存在確認して停止トリガーとします。
- プロセス優先度設定はプラットフォーム依存（Windows/Linux/macOS）で psutil を利用します。権限不足で失敗しても警告ログを出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 配下のおもなファイルとディレクトリ（コードベースから抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                         # 環境変数・Settings
  - run_execution.py                  # ExecutionEngine 起動スクリプト
  - run_monitoring.py                 # SystemMonitor ポーリング起動
  - tools/
    - __init__.py
    - paper_verification_report.py    # ペーパー取引検証レポート
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - ... (注文関連の実装)
  - monitoring/
    - __init__.py
    - monitoring_db.py                # SQLite テーブル作成 / MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/
    - pipeline.py (参照: get_last_price_date)  # DuckDB 操作ユーティリティ
    - stats.py (zscore_normalize 等)
  - utils/
    - process_priority.py             # プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py
  - その他: models / 仮実装ブローカー等

よくあるトラブルシューティング
-----------------------------
- OpenAI API キーがない / 空:
  - AI 機能を呼ぶと ValueError になります。OPENAI_API_KEY を設定してください。
- psutil によるプロセス優先度変更で AccessDenied:
  - 管理者権限が必要な場合があります。失敗時は警告ログのみで処理は継続します。
- monitoring DB がない / 読み込みエラー:
  - monitoring.run_monitoring で init_monitoring_db() が自動作成しますが、Streamlit ダッシュボードは read-only で開くため DB ファイルが存在しないとエラーになります。先に監視プロセスを起動してください。
- .env 自動読み込みを無効化したい:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト時などに有用）。

ライセンス / 貢献
-----------------
（ここにはライセンスやコントリビューションに関する情報を追記してください）

最後に
------
この README はコードベースから取得できる情報をベースに作成しました。実運用前に各モジュールの設定値（特にブローカー認証情報、DB パス、OpenAI API キー、PAPER_FILL_MODE、リスク閾値）を適切に構成してください。必要であれば README にサンプル .env のテンプレートや requirements.txt、起動用 systemd ユニット例などを追加できます。必要があれば追って作成します。