KabuSys — 日本株自動売買システム（簡易 README）
=================================

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコードベースです。本リポジトリには以下の主要機能群が含まれます。

- 発注・注文状態管理（ExecutionEngine / OrderManager / Reconciler）
- リスク監視（ドローダウン、ポジション上限など）
- システム監視（CPU/メモリ/ディスク、プロセス生存、データ鮮度）
- モニタリング DB 層（SQLite）
- ポートフォリオ構築ロジック（候補選定・重み算出・ポジションサイズ計算）
- 研究用モジュール（ファクター計算・将来リターン・IC 等）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- 運用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）
- 実行ユーティリティ（プロセス優先度 / CPU affinity 設定）

主要機能一覧
-------------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化・ファクトリ
  - OrderManager（注文作成、キャンセル、同期）
  - Reconciler（再起動時の注文・ポジション突合）
  - RiskManager（オーダーレベルの制約／サーキットブレーカー等）
- Monitoring
  - SystemMonitor（プロセス生存・データ鮮度・リソース監視）
  - TradeMonitor（滞留注文／約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - KillSwitch / AlertManager（自動停止判定・LINE通知）
  - MonitoringEngine（複数モニタを束ねたポーリング）
  - Streamlit ダッシュボード（監視用 GUI）
- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター制限・レジーム乗数
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC、統計サマリー
- AI
  - ニュース NLP（OpenAI を用いた銘柄単位センチメント）
  - レジーム判定（ETF MA とマクロセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - 各種ユーティリティ

セットアップ手順
----------------
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .venv\Scripts\activate
   - Unix/macOS: source .venv/bin/activate

3. 必要パッケージをインストール
   - 必須（代表）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. データディレクトリを用意
   - mkdir -p data

5. 環境変数 / .env
   - 本プロジェクトは .env / .env.local を自動読み込みします（OS の環境変数が優先）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須（運用に応じて）:
     - JQUANTS_REFRESH_TOKEN（J-Quants）
     - KABU_API_PASSWORD（kabu API）
     - OPENAI_API_KEY（AI 機能利用時）
   - その他主要変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL, MONITOR_POLL_INTERVAL 等

6. （任意）パッケージとしてインストール
   - PYTHONPATH を使う代わりに本パッケージをインストールしておくと便利:
     - pip install -e .

使い方（起動 / ツール）
----------------------

共通
- Python モジュールとして起動することを想定しています。開発時はプロジェクトルートから
  PYTHONPATH=src を付けて実行するか、pip install -e . を行ってから実行してください。

Monitoring 起動
- 監視ループを起動（SystemMonitor をポーリングして monitoring DB を更新）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60）
  - 実行例:
    - PYTHONPATH=src python -m kabusys.run_monitoring
  - ログレベル等は Settings を通じて制御

Execution 起動
- 実際の ExecutionEngine を起動（ブローカーと繋いで発注を行う）
  - 本番運用では KABUSYS_ENV=live（既定: development）
  - Paper Trading（完全に分離された DB を使用）:
    - export KABUSYS_ENV=paper_trading
    - PYTHONPATH=src python -m kabusys.run_execution
  - run_execution は stop フラグ（data/stop_requested.flag）を検知すると安全停止します。
  - 実行前に data ディレクトリや PID 周りの権限を確認してください。

Paper Trading 検証レポート
- ローカルの paper_trading DB を対象に実行統計を出力
  - 例:
    - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを明示する場合は --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH

Streamlit ダッシュボード
- 監視 DB の可視化（読み取り専用）
  - 例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB が存在しない / 開けない場合はエラー表示されます（MonitoringEngine で DB 作成・更新されます）。

AI（ニュース NLP / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必須
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（prices_daily / raw_news / news_symbols / ai_scores テーブル）を受け取り、結果を ai_scores テーブルに書き込みます。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）の MA200 とマクロニュースを組み合わせた判定を market_regime テーブルへ書き込みます。

停止・強制停止
- run_execution / run_monitoring はプロジェクトの data/stop_requested.flag を検出すると終了します（stop フラグ）。
- KillSwitch（RiskMonitor 等）が条件を満たすと Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込み、アラート／停止判定に利用されます。
- 手動で停止する場合は data/stop_requested.flag を作成する（空ファイルを touch するなど）。

設定（Settings）について
-----------------------
- 設定は環境変数と .env / .env.local から読み込みます（読み込み順: OS 環境 > .env.local > .env）。
- 自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主要プロパティ（Settings クラス）:
  - jquants_refresh_token, kabu_api_password
  - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - line_channel_access_token, line_user_id
  - duckdb_path, sqlite_path, paper_sqlite_path
  - paper_fill_mode: instant | partial | never | reject（不正値はエラー）
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - KABUSYS_ENV: development | paper_trading | live（不正値はエラー）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要ファイル／モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite ベースの永続化層
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
    - (broker_factory, execution_engine, order_repository 等を含む)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

運用上の注意 / 備考
------------------
- DB 初期化
  - monitoring DB（SQLite）は init_monitoring_db() により必要テーブルを冪等に作成します。run_monitoring や run_execution 起動時に自動で実行されます。
- 権限
  - process priority / cpu affinity の設定は OS 権限に依存します（psutil を使用）。権限が不足すると警告が出ますが処理は継続します。
- AI 呼び出し
  - OpenAI API を利用する処理はリトライ・バックオフ・レスポンス検証の仕組みを備えていますが、API キーは必須です。API 利用時のコストに注意してください。
- Paper Trading
  - paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ログ
  - 各モジュールは標準の logging を使用します。環境変数 LOG_LEVEL でレベルを設定できます。

問い合わせ / 追加情報
--------------------
- コード内に設計方針や技術的注記が多数コメントとして残されています。実運用や拡張時は各モジュール（特に execution/, monitoring/, ai/）を参照してください。
- README の補足や requirements.txt、運用手順書が必要であれば、利用するランタイム環境（OS、Python バージョン、実ブローカーの仕様）に応じて追記できます。

以上。必要であれば起動コマンドの具体例や systemd / supervisor でのサービス化手順、CI 用のテスト手順などの追記を行います。