KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買 / リサーチ / 監視を行うための Python ベースのコンポーネント群です。本リポジトリには以下の主要機能を持つモジュールが含まれます。

- 実行エンジン（ExecutionEngine）と発注管理
- 監視（MonitoringEngine）とアラート送信（LINE）
- ポートフォリオ構築（候補選定・配分・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量解析）
- AI ベースのニュースセンチメント（OpenAI を利用）
- 各種ユーティリティ（環境設定読み込み・プロセス優先度設定 等）
- CLI/ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

主な特徴
--------
- 環境変数 / .env ファイルで柔軟に設定可能（自動ロード機能あり）
- paper_trading 環境では発注をモックし、実データベースと分離
- DuckDB を用いたファクター計算・リサーチ処理（ローカルDB中心）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント・レジーム判定（オプション）
- SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
- Streamlit でリアルタイム監視ダッシュボードを提供
- kill.flag による ExecutionEngine の安全停止シグナル機能

動作前提 / 主な依存
-------------------
- Python 3.10+
- パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- SQLite（Python 標準ライブラリで利用）
- ネットワーク（LINE, OpenAI API を使う場合）
- （任意）.env ファイルによる設定

推奨インストール（例）
- 仮想環境を作成して依存をインストールしてください。
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

設定（環境変数）
----------------
設定は環境変数またはプロジェクトルートの .env / .env.local に記述して読み込みます（自動ロード）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（代表例）
- KABUSYS_ENV: 起動環境（development / paper_trading / live）。既定: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（既定: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news/regime の利用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）のパス（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（既定: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading の約定モード（instant | partial | never | reject）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（既定: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグファイル（既定: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループの間隔（秒、既定: 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

PAPER_FILL_MODE の有効値
- instant / partial / never / reject（Settings.paper_fill_mode で検証）

セットアップ手順
----------------
1. リポジトリを取得し仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

3. 環境変数を設定
   - プロジェクトルートに .env ファイルを置くか、環境変数をエクスポート
   - 例（.env）:
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

4. データディレクトリ作成
   - mkdir -p data

5. 初期 DB 作成
   - run_monitoring.py や run_execution.py は起動時に SQLite の監視テーブルを作成（init_monitoring_db）するため、通常は手動初期化は不要です。

基本的な使い方
---------------
- ExecutionEngine を起動（本番/紙取引切り替え）
  - 本番（KABUSYS_ENV=live）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 紙取引（モックブローカー、DB を data/paper_trading.db に分離）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  run_execution は起動時に process priority を high にし、SQLite / DuckDB に接続して ExecutionEngine を起動します。paper_trading 環境時は paper_sqlite_path（既定: data/paper_trading.db）を使用します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視プロセスは常に Settings.sqlite_path（本番用監視 DB）を使用します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードから positions / trade_logs / system_status / dashboard を閲覧できます（read-only）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で SQLite ファイルを指定可能（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）。

- AI 処理（ニュースセンチメント / レジーム判定）
  - 関数を直接呼び出すか、別スクリプトから利用可能。
  - 例（Python から）:
    - from datetime import date
    - import duckdb
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY で指定してください。
  - API 呼び出しはリトライやバリデーションを行い、失敗時は安全にフォールバックします（多くのエラーはスキップして継続する設計です）。

実運用上の注意
---------------
- run_monitoring は監視ログとして既定の sqlite_path（Settings.sqlite_path）を使います。紙取引用 DB とは分離されます。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path に書き込みます（data/paper_trading.db 既定）。
- KillSwitch（data/kill.flag）による停止シグナルを評価し、条件に合致するとフラグファイルを書きます。ExecutionEngine 起動時にフラグのクリア設定（Settings.kill_flag_clear_on_start）を確認してください。
- OpenAI 利用は API コストが発生します。news_nlp と regime_detector はバッチ/チャンクで呼び出し、結果の検証・クリップ・部分書き込みを行うことで安全に設計されています。
- プロセス優先度設定（set_process_priority）は psutil を使用します。権限不足により設定失敗する場合はログに警告が出ます。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py
  - 環境変数ロード・Settings クラス（主要設定プロパティ）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 切替あり）

サブパッケージ:
- ai/
  - news_nlp.py           # ニュースを LLM でスコアリング
  - regime_detector.py    # マクロ + MA200 で市場レジーム判定
- monitoring/
  - monitoring_db.py      # SQLite スキーマ定義・読み書きラッパー
  - system_monitor.py     # システム状態・データ鮮度チェック
  - trade_monitor.py      # 注文滞留・約定異常チェック
  - risk_monitor.py       # ドローダウン・ポジション上限監視
  - kill_switch.py        # kill.flag の管理
  - alert_manager.py      # LINE 通知（クールダウン機能付き）
  - monitoring_engine.py  # 各 monitor を束ねるエンジン
  - streamlit_dashboard.py# Streamlit ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - …（ブローカーファクトリ・エンジン 等、発注関連）
- portfolio/
  - portfolio_builder.py  # 候補選定・重み計算
  - position_sizing.py    # 株数計算・ロット丸め・集約制限
  - risk_adjustment.py    # セクターキャップ・レジーム乗数
- research/
  - factor_research.py    # Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py# 将来リターン / IC / 統計集計
- tools/
  - paper_verification_report.py  # Paper Trading の検証レポート出力
- utils/
  - process_priority.py   # プロセス優先度 / CPU affinity ユーティリティ

テーブル（monitoring DB）
-------------------------
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok, ...)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 固定行で集計値を保持)

補足（設計上のポイント）
----------------------
- .env の自動ロードはプロジェクトルート（.git 或いは pyproject.toml）を基準に行われます。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- monitoring の DB 初期化は init_monitoring_db で冪等に行われます。スキーマ追加時は簡易マイグレーション処理（列追加）を含みます。
- AI 関連機能は外部 API（OpenAI）に依存します。API 呼び出し時のエラーはリトライやフォールバックで安全に処理される設計ですが、実運用では API キーやコスト管理に十分ご注意ください。

ライセンス / 貢献
-----------------
（この README の配布先に合わせてライセンス情報や貢献方法を追記してください）

以上がこのコードベースの概要と使い方です。動作確認や導入方法について具体的な補助（例: requirements.txt の作成、systemd ユニットや Docker 化の提案等）が必要であればお知らせください。