KabuSys — 日本株自動売買ライブラリ
=================================

このリポジトリは、日本株自動売買システム「KabuSys」の一部実装を抜粋した Python パッケージです。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュースセンチメント評価などのコンポーネントを含みます。

この README はリポジトリ内のコード（src/kabusys/ 以下）を基に、日本語での概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

プロジェクト概要
----------------
- 目的: 日本株の自動売買を安全に運用するためのコンポーネント群（リサーチ、ポートフォリオ構築、発注、監視、アラート、AI によるニュース解析）を提供する。
- 設計方針:
  - DuckDB / SQLite を利用した履歴データ処理と監視ログ保存
  - 発注は BrokerClient（本番／モック切替）経由
  - 監視（MonitoringEngine）は別プロセスでポーリングして監視ログ・アラート・KillSwitch を管理
  - OpenAI（gpt-4o-mini 等）を用いたニュース NLP / レジーム検知を実装（API キー必須）
  - 環境変数/.env による設定管理。自動的に .env /.env.local をロード（無効化可能）

主な機能一覧
-------------
- research:
  - ファクター計算 (momentum, volatility, value)
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- portfolio:
  - 候補選定 (select_candidates)
  - 重み計算（等分配・スコア加重）
  - 危険調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- execution:
  - ExecutionEngine（起動・セッション管理）
  - OrderManager（Order State Machine 外向き API）
  - Reconciler（再起動時の注文／ポジション同期）
  - BrokerClientFactory により本番/ペーパートレード切替
- monitoring:
  - SystemMonitor（CPU/メモリ/Disk、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文、約定異常価格）
  - RiskMonitor（ドローダウン監視、ポジション上限監視）
  - KillSwitch（重大アラートで data/kill.flag を書き込む）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - MonitoringEngine（各 Monitor を束ねたポーリングループ）
  - streamlit ベースの監視ダッシュボード（読み取り専用）
- tools:
  - paper_verification_report：ペーパートレード DB を解析して検証レポートを出力
- ai:
  - news_nlp.score_news：raw_news を LLM でセンチメント評価して ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロニュースから市場レジーム（bull/neutral/bear）判定

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型ヒントで modern syntax を利用）
- DuckDB、psutil、openai、requests、streamlit 等のライブラリが必要

簡易セットアップ例:
1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt があればそれを使用してください）

3. ソースを PYTHONPATH に通す（ローカル開発用）
   - export PYTHONPATH=$PWD/src  （Windows PowerShell: $env:PYTHONPATH = "$PWD/src"）

4. 環境変数 / .env
   - プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数例（.env に記述）:
     - KABUSYS_ENV=development|paper_trading|live
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant|partial|never|reject
     - LOG_LEVEL=INFO

5. data ディレクトリ作成（PID / flag / DB の親）
   - mkdir -p data

使い方（主要なエントリポイント）
-------------------------------

実行の前提: PYTHONPATH を src に通すか、パッケージをインストールしてください。開発時は以下のように実行します:

1) 監視プロセス（Monitoring）
- 起動:
  - PYTHONPATH=src python -m kabusys.run_monitoring
- 補足:
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlit e_path（デフォルト data/monitoring.db）を使用します。run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を参照します。
  - 停止を要求するにはプロジェクトルートの data/stop_requested.flag を作成（または削除）する仕組みになっています（run_monitoring はこのフラグを検出してループを抜けます）。

2) 発注エンジン（Execution）
- 起動:
  - PYTHONPATH=src python -m kabusys.run_execution
- 補足:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録して本番 DB と分離します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中の停止リクエストは data/stop_requested.flag を作成することで行えます。実行中は _EXECUTION_PID（data/execution.pid）ファイルも生成されます。

3) Streamlit ダッシュボード（監視用）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 補足:
  - ダッシュボードは監視 DB を読み取り専用で開き、ポートフォリオ、注文ログ、システム状態、リスクイベントなどを表示します。

4) Paper Trading 検証レポート
- 実行:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH が優先されますが、--db で上書き可能）

5) AI モジュール（ニュース NLP / レジーム検知）
- news_nlp.score_news, regime_detector.score_regime は DuckDB 接続（kabusys.data のテーブル）を受け取り処理します。実行時には OPENAI_API_KEY が必要です。
- 使用例（疑似）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn=duckdb_conn, target_date=date(2026,4,1))
- API キー未設定時は ValueError を送出します。

重要なファイル / フラグ
------------------------
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py がチェックする停止フラグ。存在すると実行を停止または起動を拒否します。
- data/kill.flag
  - KillSwitch によって書き込まれるファイル。ExecutionEngine に停止シグナルを送る目的で使用します（KillSwitch.evaluate が条件を満たすと書き込み）。
- data/execution.pid
  - 実行エンジンが PID を書き込むファイル。SystemMonitor はこの PID ファイルでプロセスの生存を確認します。
- DB
  - monitoring（SQLite）: デフォルト data/monitoring.db
  - duckdb（分析・時系列データ）: デフォルト data/kabusys.duckdb
  - paper_trading（SQLite）: data/paper_trading.db（ペーパートレード専用）

設定（Settings）について
-----------------------
- Settings クラス（kabusys.config.Settings）が環境変数から各種設定を読み出します。
- 自動 .env 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）に .env/.env.local があれば読み込みます。
  - OS 環境変数の上書きを防ぐため .env.local は override=True だが保護リスト（既存 OS 環境）を尊重します。
  - 自動ロードを停止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 重要な環境変数（抜粋）:
  - KABUSYS_ENV: development|paper_trading|live
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで必須）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用
  - KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 用
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）用
  - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（default=60）

ディレクトリ構成（抜粋）
-----------------------
（src/kabusys 以下の主要ファイル／モジュール）
- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
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
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 execution 関連モジュールは一部省略)
  - utils/
    - __init__.py
    - process_priority.py
  - data/   (実行時に生成されるファイル群: *.db, *.pid, *.flag など)

注意事項 / 運用上のポイント
-------------------------
- Monitoring と Execution は別プロセスで運用する想定です。監視は Execution のプロセス生存や注文状況をチェックし、必要に応じて KillSwitch を発動して安全停止させます。
- run_monitoring は KABUSYS_ENV に依らず本番の sqlite_path を使用する点に注意してください（監視データは本番 DB を想定）。
- Paper Trading モード（KABUSYS_ENV=paper_trading）は発注先をモックに切り替え、paper_trading 用 DB を使用して本番 DB と分離します。
- OpenAI API の呼び出しはレート制限やネットワーク失敗に対して指数バックオフでリトライする実装になっていますが、API キー未設定や重大エラー時はフェイルセーフ（0.0 スコアなど）にフォールバックする処理があります。
- process_priority.set_process_priority() を起動時に呼んでおり、OS によっては権限不足で設定に失敗することがあります（警告でスキップされます）。

よく使うコマンド例
-----------------
- 監視起動:
  - PYTHONPATH=src python -m kabusys.run_monitoring
- 実行エンジン起動:
  - PYTHONPATH=src python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート:
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サンプル .env（最小例）
---------------------
# KABUSYS 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# OpenAI
OPENAI_API_KEY=sk-...

# Broker / API
KABU_API_PASSWORD=...

# LINE Notifications (任意)
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

さらに詳しいドキュメント
-----------------------
各モジュールの docstring に設計方針や挙動の詳細が記載されています。コード内コメント（日本語）が比較的充実しているため、実際に触りながら理解を深めることを推奨します。

サポート / 開発
----------------
- 開発時は PYTHONPATH を src に指定してモジュールを直接実行できます。
- 単体テストやモックは各モジュール内で想定されています（API 呼び出し部分は差し替え可能な抽象化あり）。

以上が本コードベースの概要と利用手順です。必要があれば、運用向けの systemd ユニット例や Docker 化、CI 用の検証コマンドなどの追加ドキュメントも作成できます。ご希望があれば教えてください。