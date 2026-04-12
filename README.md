KabuSys — 日本株自動売買システム（README）
=================================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python コードベースです。本リポジトリには以下の主要機能群が含まれます。

- 注文実行エンジン（ExecutionEngine）と起動スクリプト
- 監視コンポーネント（System / Trade / Risk）とポーリングエンジン
- Paper Trading 用の切り替えと検証レポート生成ツール
- ポートフォリオ構築、ポジションサイズ計算、セクター制約などの純粋関数群
- DuckDB を用いたリサーチ / ファクター計算モジュール
- ニュース NLP（OpenAI）を用いた銘柄別センチメントスコアリングとレジーム判定
- Streamlit ベースの監視ダッシュボード

主な特徴
--------
- 本番 / PaperTrading / 開発環境を環境変数 KABUSYS_ENV で切り替え（development / paper_trading / live）
- Paper Trading は本番 DB と分離（data/paper_trading.db を使用、PAPER_TRADING_SQLITE_PATH で上書き可）
- 監視は SQLite に永続化（system_status, trade_logs, positions, risk_logs, dashboard テーブル）
- OpenAI を使ったニュースセンチメント（gpt-4o-mini 想定）と市場レジーム判定
- duckdb を用いた高速なファクター計算・研究ワークフロー
- LINE Push を使ったアラート送信（AlertManager）
- 実行プロセス優先度の設定ユーティリティ（psutil ベース）

必要条件
--------
- Python 3.10+（型ヒントに | None 等を使用）
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 標準ライブラリ: sqlite3, logging, argparse, datetime 等

セットアップ手順
----------------
1. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. 環境変数の設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（既存の OS 環境変数は保護されます）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb  (デフォルト)
     - SQLITE_PATH=data/monitoring.db   (監視用、デフォルト)
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant | partial | never | reject  (paper_trading 用)
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  (監視ポーリング間隔 秒、run_monitoring で使用)

   - .env のフォーマットは shell 形式（export も可）で、クォートやコメントに対応しています。

4. データディレクトリの作成
   - mkdir -p data

    init_monitoring_db() は起動時に自動で DB スキーマを作成／マイグレーションするため、事前に手動でテーブルを作る必要はありません。

使い方
------
実行スクリプト（モジュールとして実行可能）:

- 監視ループを起動（SystemMonitor をポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（SQLITE_PATH）を常に使用します（KABUSYS_ENV に関わらず）

- 注文実行（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録して本番 DB とは完全分離します。
  - 起動時にプロセス優先度を "high" に設定します（set_process_priority）

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を上書き）
  - 主要な検証指標: 稼働率、注文成功率、送信率、P95 レイテンシ など
  - しきい値はソース内で定義（例: 稼働率 >= 99% 等）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは read-only 接続（DB が存在しない場合はエラーメッセージ）

- AI 関連:
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime をプログラムから呼び出して、OpenAI を用いたスコアリング／レジーム判定を実行できます（OPENAI_API_KEY 必須）。
  - news_nlp.score_news は target_date（date オブジェクト）を引数にとり、その日のニュースウィンドウを集約してスコアを書き込みます。

監視／停止機構
--------------
- PID ファイル: Settings.pid_file_path（デフォルト data/execution.pid）を用いてプロセス生存を監視します。stale PID を検出した場合は警告ログとログイベントが出ます。
- Kill Switch: data/kill.flag の存在により ExecutionEngine 停止を要求できます（KillSwitch によりファイル作成）。KillSwitch は drawdown やポジション上限超過をトリガとして flag を書き込みます。既存の flag は上書きされません（冪等）。
- AlertManager: LINE Push API を通じて一方向通知を送信。channel token と user id が未設定の場合はログのみ。

重要な動作・設計上の注意
------------------------
- .env の自動読み込み: プロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動読み込みします。テスト時などで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading と本番 DB は分離されます（run_execution は is_paper 判定で paper_sqlite_path を使用）。
- 監視側（run_monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path を使用して監視ログを記録します（常に「本番」監視DBを想定）。
- OpenAI 呼び出しはリトライ・バックオフ実装あり。不安定時はフェイルセーフ（ゼロやスキップ）で継続するよう設計されています。
- DuckDB を使うリサーチ機能は prices_daily / raw_financials 等テーブルを前提としています（データ投入は別途必要）。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数・設定読み込みロジック（.env 自動読み込み、Settings クラス）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（PaperTrading 切替対応）
- tools/
  - __init__.py
  - paper_verification_report.py
    - Paper Trading DB を解析して検証レポートを出力する CLI
- ai/
  - news_nlp.py
    - ニュースを LLM で評価し ai_scores に保存する処理
  - regime_detector.py
    - マクロ記事＋ETF MA を組み合わせて市場レジームを判定
- monitoring/
  - __init__.py
  - monitoring_db.py
    - SQLite テーブル作成・ORM 的ユーティリティ（MonitoringDB）
  - system_monitor.py
    - CPU/メモリ/ディスク/データ鮮度/プロセス生存をチェック
  - trade_monitor.py
    - 注文滞留・約定異常を検出
  - risk_monitor.py
    - ドローダウンおよびポジション上限を監視
  - monitoring_engine.py
    - 各 Monitor を束ねるポーリング実行ロジック
  - alert_manager.py
    - LINE Push による通知実装
  - kill_switch.py
    - data/kill.flag の作成・検査ユーティリティ
  - streamlit_dashboard.py
    - Streamlit ベースの監視ダッシュボード
- execution/
  - (OrderManager, Reconciler, OrderRepository 等。実行ロジックやブローカ抽象化)
  - reconciler.py
  - order_manager.py
  - （その他実装ファイルはコードベースに依存）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - ポートフォリオ構築に関する純粋関数群
- research/
  - factor_research.py
  - feature_exploration.py
  - ファクター計算・IC や統計サマリ等
- utils/
  - process_priority.py
    - psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ
  - その他ユーティリティ

補足（運用メモ）
----------------
- 監視 DB のスキーマは init_monitoring_db() により起動時に自動作成とマイグレーションが行われます（安全に何度でも呼べる冪等性）。
- Paper Trading の fill 動作（MockBrokerClient の振る舞い）は設定 PAPER_FILL_MODE に従います（instant / partial / never / reject）。
- OpenAI 利用時は API キー（OPENAI_API_KEY）と適切なレート管理が必要です。呼び出しはバッチ化・リトライ制御されていますが、コストとレート上限には注意してください。

ライセンス / コントリビュート
-----------------------------
（ここにライセンスやコントリビュート方法を記載してください。プロジェクト固有のポリシーがあれば追記を推奨します。）

以上。必要であれば、実際の起動スクリプト例、.env.example のサンプル、依存関係の requirements.txt を含めた README 版を追加で作成します。どの情報を優先して追記しますか？