README
====

プロジェクト概要
----
KabuSys は日本株向けの自動売買／バックテスト／監視を想定した Python コードベースです。  
主要な機能群は以下の通りです:

- 注文発行・状態管理（ExecutionEngine、OrderManager、OrderRepository）
- リコンシリエーション（再起動時の同期）
- リスク管理（RiskManager、RiskMonitor）
- 監視（SystemMonitor、TradeMonitor、MonitoringEngine）
- ダッシュボード（Streamlitベースの監視 UI）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- 研究 / ファクター計算（DuckDB を用いたファクター・特徴量計算）
- AI 支援（OpenAI を用いたニュースセンチメント、レジーム判定）
- Paper Trading 検証レポート生成ツール

設計上のポイント:
- DuckDB は時系列・ファクターデータの分析用、SQLite は監視ログや Paper Trading のトランザクション保存に利用。
- .env / 環境変数から設定をロード（自動ロードを無効化可能）。
- paper_trading 環境ではブローカーは Mock 実装を使用し、本番 DB と分離された SQLite を利用。

主な機能一覧
----
- 実行系
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper/live/development を切替）
  - Reconciler: 再起動後の注文・ポジション同期
  - OrderManager: 注文の作成・同期・キャンセル等の高レベル API
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔指定）
  - MonitoringEngine: System/Trade/Risk 各 Monitor を束ねる
  - AlertManager: LINE Push による通知（設定がある場合）
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
  - monitoring_db.py / MonitoringDB: 監視ログの永続化（SQLite）
- ポートフォリオ構築
  - portfolio/ 以下に等配分・スコア加重・リスク調整・ポジションサイズ算出の純粋関数群
- 研究・解析
  - research/ 以下にファクター計算（momentum/value/volatility）、前方リターン計算、IC 等
- AI
  - ai/news_nlp.py: OpenAI を用いたニュースのセンチメントスコア化（ai_scores へ書込）
  - ai/regime_detector.py: MA200 とマクロセンチメントを用いた日次レジーム判定（market_regime へ書込）
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポートを生成（CLI）

セットアップ手順
----
前提:
- Python 3.9+（型アノテーション等を使用）
- 必要なパッケージ（例: duckdb, psutil, requests, openai, streamlit）

例: 仮想環境 + pip
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを使用）
   - pip install duckdb psutil requests openai streamlit

3. 環境変数を用意
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（デフォルト動作）。  
     自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: 必須（J-Quants 用）
     - KABU_API_PASSWORD: 必須（kabuステーション API）
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject  (デフォルト: instant)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（任意）
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト: 60）

4. データディレクトリ
   - デフォルトでは data/ 以下を使用します。起動時に存在しない場合は作成してください。
   - 重要なフラグファイル:
     - data/stop_requested.flag: run_monitoring/run_execution が検知する停止フラグ
     - data/kill.flag: KillSwitch が作成する ExecutionEngine 停止フラグ
     - data/execution.pid: ExecutionEngine の PID を書くファイル

使い方
----
実行系を動かす（本番/テストに合わせて設定）:

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

- Monitoring 起動（ポーリング）
  - MONITOR_POLL_INTERVAL を指定して上書き可能（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）にログを書きます。
  - 監視ではプロセス優先度を "high" に設定しようとします（プラットフォーム依存で失敗しても継続）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite ファイルを開きます（接続失敗時はエラー表示）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB の指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 機能
  - ニューススコアリング: kabusys.ai.score_news を直接呼ぶ（DuckDB 接続と target_date を渡す）。OPENAI_API_KEY を環境変数または引数で設定してください。
  - レジーム判定: kabusys.ai.regime_detector.score_regime を呼び出し、market_regime テーブルへ書き込みます。こちらも OPENAI_API_KEY が必要。

設定の自動ロードについて
- config.Settings は起動時にプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env → .env.local の順で環境変数を読み込みます。
- OS 環境変数が優先され、.env.local は .env を上書きします。
- 自動ロードを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

監視・KillSwitch の挙動
- RiskMonitor / TradeMonitor / SystemMonitor は定期的にデータを評価し、MonitoringDB（SQLite）に記録します。
- KillSwitch は drawdown やポジション上限などの条件を満たすと data/kill.flag を作成し、ExecutionEngine 側が検知して停止します。
- AlertManager は LINE の push API を使い通知します（トークン未設定時はログのみ）。

ディレクトリ構成
----
以下は src/kabusys 以下の主要ファイル・ディレクトリ（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定読込
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — SystemMonitor ポーリング起動
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP（OpenAI）
    - regime_detector.py         — レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py          — SQLite スキーマ / MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ... (ブローカ API / engine / repository 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/  (実行時に使用するファイル・フラグ)
    - monitoring.db (default: SQLITE_PATH)
    - kabusys.duckdb (default: DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - stop_requested.flag / kill.flag / execution.pid

注意事項・運用メモ
----
- 環境（KABUSYS_ENV）が paper_trading の場合、実際のブローカーへ発注しない設定になります。Paper モードは本番 DB と分離しており、PAPER_TRADING_SQLITE_PATH に記録されます。
- monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）に書き込みます（運用監視は一貫した DB を使うため）。
- OpenAI を使う機能はレート制限や一時エラーに対してエクスポネンシャルバックオフでリトライしますが、API キー未設定時は ValueError を送出します。
- process_priority の設定は OS により成功しないことがあります（その場合はログに警告が出てスキップされます）。
- DuckDB / SQLite ファイルは適切なバックアップとアクセス権設定を行ってください（Streamlit は read-only URI モードで接続可能）。

貢献・拡張
----
- 新しいブローカー実装は execution/broker_* に追加し、BrokerClientFactory で選択できるようにする。
- ポートフォリオロジックやファクターは research / portfolio 以下の純粋関数を拡張することで容易に追加可能。
- AI モジュールは OpenAI のモデル切替やプロンプト改善で性能を向上できます。API 呼び出し部はテスト時にモックしやすい設計にしています。

お問い合わせ
----
- ソースコード内の docstring および関数コメントを参照してください。実用時は .env.example を元に必要な環境変数を設定してください。

以上。