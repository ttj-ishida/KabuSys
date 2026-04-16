KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向けの自動売買システムのコアライブラリ群です。戦略の研究／ファクター計算、ポートフォリオ構築、発注エンジン、監視（モニタリング）、AI を用いたニュースセンチメント評価などが含まれます。本 README ではプロジェクト概要、主な機能、セットアップ・実行手順、簡単な使い方、ディレクトリ構成を日本語でまとめます。

前提
----
- Python 3.10+
- 主な依存ライブラリ（プロジェクトで使用）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード用)
  - sqlite3（標準ライブラリ）
- 環境変数は .env / .env.local / OS 環境変数から読み込みます（Settings モジュール参照）。
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

プロジェクト概要
--------------
KabuSys は以下の主要コンポーネントで構成されています。

- research: DuckDB 上の価格・財務データからファクター（モメンタム、バリュー、ボラティリティ等）を計算するモジュール
- portfolio: 候補選定、重み付け、リスク調整、株数決定などのポートフォリオ構築ロジック
- execution: 発注エンジン、OrderManager、Reconciler（起動時復旧）などの実装
- monitoring: システム監視（CPU/メモリ/ディスク/データ鮮度）、注文監視、リスク監視、アラート送信、kill switch
- ai: OpenAI を用いたニュースセンチメント（news_nlp）やレジーム判定（regime_detector）
- tools: 運用補助スクリプト（例: Paper Trading の検証レポート生成）
- utils: プロセス優先度設定やユーティリティ

主な機能一覧
-------------
- DuckDB を使ったファクター計算（calc_momentum / calc_volatility / calc_value）
- 研究用ユーティリティ（将来リターン、IC 計算、統計サマリ）
- ポートフォリオ構築（候補選定、等配分／スコア配分、リスク調整、ポジションサイズ計算）
- 発注管理（OrderManager、OrderRepository、Reconciler）
- 実行エンジンと Paper Trading 対応（本番 DB と paper_trading DB の分離）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）、監視ログの永続化（SQLite）
- LINE によるアラート送信（AlertManager）
- OpenAI を用いたニュースセンチメント / レジーム判定（api キー必須）
- Streamlit ベースの監視ダッシュボード（読み取り専用で monitoring DB を表示）
- 運用レポート出力ツール（Paper Trading 検証レポート）

セットアップ手順
----------------
1. リポジトリをクローン・チェックアウト
   - 例: git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要なパッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. 環境変数 / .env の設定
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（既存 OS 環境変数は保護されます）。
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
     - JQUANTS_REFRESH_TOKEN: 必須（settings.jquants_refresh_token が要求）
     - KABU_API_PASSWORD: 必須（kabu API 用）
     - OPENAI_API_KEY: OpenAI を使う場合に必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を有効にする場合
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視ログ SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject (Paper Trading の約定モード)
     - LOG_LEVEL: DEBUG/INFO/...（設定値検証あり）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

5. データディレクトリ
   - data/ 以下に DB 等を置く想定（必要なディレクトリは自動作成される箇所があります）。
   - モニタリングの停止フラグ: data/stop_requested.flag
   - kill switch: data/kill.flag
   - execution PID: data/execution.pid

使い方（主な実行コマンド）
------------------------

- 監視ループを起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - 補足:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用してログを記録します。
    - 停止方法: data/stop_requested.flag を作成するか Ctrl+C。

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません。
    - 実行中に stop flag を作成するとエンジンを停止します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH (PAPER_TRADING_SQLITE_PATH を上書き)
  - 例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードでは positions / trade_logs / system_status / risk_logs / dashboard の最新情報を表示します（読み取り専用）。

- OpenAI 関連（プログラム呼び出し）
  - ai モジュールの関数はプログラムから呼び出します。例:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

  - regime_detector の score_regime も同様に呼び出します（OpenAI API キーが必要）。

運用上のポイント
----------------
- .env の優先順位: OS 環境変数 > .env.local > .env（Settings モジュール内の自動ロードロジック）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）。0 以下や不正値はデフォルト 60 秒にフォールバックします。
- stop/kill フラグ:
  - data/stop_requested.flag を作成すると long-running プロセス（run_monitoring / run_execution など）が停止手順を開始します。
  - KillSwitch（監視コンポーネント）は条件を満たすと data/kill.flag を作成して ExecutionEngine に停止を促します。
- Paper Trading：
  - KABUSYS_ENV=paper_trading にすると、paper 用 DB を使い、MockBrokerClient（外部 API に発注しない）で動作します。運用と検証を明確に分離できます。
- プロセス優先度:
  - run_* スクリプト実行時に set_process_priority("high") を呼び出しています。環境によってはアクセス権限で失敗することがあります（警告ログのみ）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要なモジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env ロード含む）
  - run_monitoring.py              — SystemMonitor のポーリング起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（OpenAI）
    - regime_detector.py           — 市場レジーム判定（OpenAI + MA）
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 broker_factory / execution_engine / order_repository 等)
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ + MonitoringDB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py             — LINE 通知
    - kill_switch.py
    - streamlit_dashboard.py
  - utils/
    - __init__.py
    - process_priority.py          — プロセス優先度 / CPU affinity

補足ドキュメント参照
-------------------
- コード中の docstring / コメントに設計や設計上の注意点が多く含まれています（例: PortfolioConstruction.md / StrategyModel.md 等の参照を示すコメント）。実装の詳細やアルゴリズムの意図は各モジュールの docstring を参照してください。

ライセンス / 貢献
----------------
- 本リポジトリのライセンス情報（LICENSE）がある場合はそれに従ってください。貢献は通常の GitHub フロー（issue / pull request）で受け付けます。

お問い合わせ
-----------
- 実行・セットアップ中の質問やバグ報告は issue を立ててください。README に記載が必要な補足や手順の改善提案も歓迎します。

以上。必要であれば各モジュール（例: ExecutionEngine の起動フロー、OrderManager API、AI モジュールの具体的な呼び出し例など）について別途詳細なドキュメントを作成します。どの部分を優先して欲しいか教えてください。