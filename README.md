KabuSys — README
=================

概要
----
KabuSys は日本株自動売買システムのコードベース（ライブラリ + 起動スクリプト群）です。
主な目的は次の通りです。

- 売買シグナルに基づく発注・リスク管理・実行（Execution）
- システム稼働監視・注文異常検知・キルスイッチ（Monitoring）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ用ファクター計算・特徴量解析
- ニュースを使った LLM ベースのセンチメント解析（AI）
- Paper Trading 検証ツール・ダッシュボード（Streamlit）

この README はソースから読み取れる主要機能、セットアップ、実行方法、ディレクトリ構成を日本語でまとめたものです。

主な機能
--------
- Execution
  - OrderManager / ExecutionEngine ベースの発注フロー、ブローカー抽象化（実ブローカー / MockBroker の切替）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）の設定とチェック
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度の監視
  - TradeMonitor: 滞留注文・約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション数の監視と alert / kill flag 発行
  - MonitoringEngine: 上記モニタを纏めたポーリングループ
  - MonitoringDB: SQLite に監視ログ / trade_logs / risk_logs / dashboard を永続化
  - Streamlit ダッシュボード（監視データ閲覧）
- Portfolio
  - 候補選定、等配分・スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイジング（単元丸め・利用可能現金に対するスケール）
- Research
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ
- AI
  - ニュース記事をまとめて OpenAI（gpt-4o-mini 等）へ送り、銘柄ごとのセンチメントを ai_scores に書き込む（retry・バッチ処理・レスポンスバリデーション実装）
  - 市場レジーム判定（ETF の MA200 とマクロニュースセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成（期間指定可）
  - 各種補助ユーティリティ（プロセス優先度設定等）

セットアップ
------------
1. 推奨 Python バージョン
   - Python 3.10 以上を推奨（typing の近代機能や新しい依存に合わせて）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 他にプロジェクトで使用するパッケージがあれば追加してください。

   ※ 実行環境により OS 固有の依存（psutil の一部機能など）に注意してください。

4. 環境変数 / .env
   - プロジェクトはルート（.git または pyproject.toml を探索）にある .env / .env.local を自動で読み込みます。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主な環境変数（代表例）
   - KABUSYS_ENV: execution モード。development | paper_trading | live（デフォルト: development）
     - paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db を利用（本番 DB と分離）
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な箇所あり）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須な箇所あり）
   - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）で使う
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視・キルフラグ関連）
   - PAPER_FILL_MODE: paper_trading の MockBroker の fill 動作（instant|partial|never|reject）

5. データディレクトリ
   - data/ 配下に DB を格納する運用が想定されています（例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）
   - 起動スクリプトが必要に応じて init_monitoring_db を呼び DB スキーマを作成します。

使い方（起動コマンド例）
---------------------

- Monitoring を起動（常駐ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60 秒）
  - python -m kabusys.run_monitoring
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  挙動のポイント:
  - 実行開始時にプロセス優先度を "high" にセットしようとします（psutil による）
  - 監視は Settings から sqlite_path を参照し、監視ログ（production 側 DB）を使用します（KABUSYS_ENV に依らず本番 sqlite_path を使用する実装）

- Execution を起動（注文実行エンジン）
  - python -m kabusys.run_execution
  - 環境により KABUSYS_ENV を設定:
    - KABUSYS_ENV=paper_trading : MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と完全分離）
    - KABUSYS_ENV=live : 実ブローカーを使用（各種 API キー等を設定すること）
  - 実行開始時にプロセス優先度を "high" に設定します。

- Streamlit ダッシュボード（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB を読み取り専用で開き、positions / recent orders / system status / recent risk logs を表示します。
  - 起動に失敗した場合は MonitoringEngine を先に起動してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定する場合:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは data/paper_trading.db。--db オプションか PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能。

- AI 関連（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY）
  - コード上の関数を呼び出すことで単体処理可能:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 実行は DuckDB 接続（prices_daily / raw_news 等が必要）を準備して行います。
  - LLM 呼び出しではリトライやレスポンス検証が施されており、失敗時はフェイルセーフ動作（スコア 0 など）になります。

設定と注意点
--------------
- 環境自動ロード
  - ルートで .env / .env.local が見つかると自動で読み込まれます（既存 OS 環境変数は保護されます）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- Paper Trading と本番 DB の分離
  - KABUSYS_ENV=paper_trading 時は paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番監視 DB と分離されます。
- MONITOR_POLL_INTERVAL
  - run_monitoring のポーリング間隔を秒で上書きできます（デフォルト 60 秒）。1 未満／不正値はデフォルトにフォールバックします。
- Kill Flag（data/kill.flag）
  - KillSwitch は条件に合致した場合に kill.flag を書き込み、ExecutionEngine 側がこれを検出して安全停止する仕組みです。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START を参照してフラグをクリアする設定があります。
- OpenAI の利用
  - API 呼び出しにはネットワークや API 制限の影響を受けます。score_news / score_regime は 429・タイムアウト・5xx などを対象に指数バックオフでリトライする実装を持ちます。
- process priority / CPU affinity
  - utils/process_priority.py により Windows / POSIX の差分を吸収してプロセス優先度を設定しますが、権限不足などで設定が失敗する場合は警告ログを出してスキップします。

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主要ファイル・モジュール（提供ソースからの抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / Settings 管理
  - run_monitoring.py              - SystemMonitor ポーリング起動スクリプト
  - run_execution.py               - ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  - Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py             - SQLite スキーマ / DB 操作ラッパー
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
    - (その他: broker_api, execution_engine, order_repository など想定)
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
  - data/ (想定ディレクトリ、実行時に DB 等を配置)
  - utils/
    - process_priority.py
    - __init__.py

補足（開発者向け）
------------------
- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等（存在チェック）でテーブルを作成し、既存 DB にカラムが欠けている場合は ALTER TABLE による追加（軽微なマイグレーション）を行います。
- ロギング
  - 起動スクリプトは logging.basicConfig(level=logging.INFO) を呼び出します。詳細ログを見たい場合は環境変数 LOG_LEVEL を設定してください（有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL）。
- テスト容易性
  - OpenAI など外部呼び出し部分は内部で分割され、ユニットテスト時は該当関数を patch して差し替えられるように設計されています。

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報やコントリビューション規約はプロジェクトルート（LICENSE, CONTRIBUTING.md 等）を参照してください（本 README のサンプルには含まれていません）。

以上。必要であれば README に入れる具体的な .env.example のテンプレートや、systemd / supervisor 用の起動ユニット例、運用手順（バックアップ・ログローテーション・監視設定）を追加で作成します。どの情報を追加したいか教えてください。