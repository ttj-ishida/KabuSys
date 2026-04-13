KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群と起動スクリプト、監視・検証ツール群を含みます。  
README はコードベース（src/kabusys 以下）の構成や主要機能、セットアップ・起動方法を日本語でまとめたものです。

概要
----
KabuSys は以下の主要機能を持つ自動売買プラットフォームのコンポーネント群です。

- 注文作成・送信・状態同期（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager 等）と発注制御
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート（LINE push）
- 監視ダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 研究用ファクター計算（Momentum / Volatility / Value 等）と特徴量解析
- ニュース NLP を用いたセンチメントスコアリング（OpenAI）
- 市場レジーム判定（MA と LLM の組合せ）
- Paper Trading 用の分離された DB と検証レポート生成ツール

主な特徴
-------
- 明確なレイヤ分離：データ（DuckDB）、監視（SQLite）、注文管理（SQLite）など用途ごとに分離
- Paper Trading モード：KABUSYS_ENV=paper_trading でモックブローカーを使用し DB を分離
- フェイルセーフな設計：リトライ、データ欠落時のフォールバック、冪等な DB 書き込み等
- OpenAI を用いたニュース解析・レジーム判定（API キー必須）
- Streamlit による簡易監視ダッシュボード
- 各モジュールはテストしやすい純粋関数・副作用の少ない実装を志向

必要要件（依存パッケージ）
------------------------
主要なインポートから推測されるランタイム依存例：

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (監視ダッシュボード実行時)
- SQLite（標準ライブラリで利用可能）

pip での一例インストール:
pip install duckdb psutil requests openai streamlit

（実際の requirements.txt / lockfile がある場合はそちらを参照してください）

設定（環境変数）
----------------
設定は環境変数（.env ファイル経由でも可）で行います。config.py に自動読み込みロジックがあり、プロジェクトルートに .env / .env.local があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主要な環境変数（キーと意味・デフォルト）:

- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live") — デフォルト "development"
- LOG_LEVEL: ログレベル ("DEBUG"|"INFO"|...) — デフォルト "INFO"
- DUCKDB_PATH: DuckDB ファイルパス — デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite（monitoring） — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite — デフォルト data/paper_trading.db
- PAPER_FILL_MODE: Paper Trading の約定挙動 ("instant"|"partial"|"never"|"reject") — デフォルト "instant"
- PID_FILE_PATH: ExecutionEngine が書き込む PID ファイル — デフォルト data/execution.pid
- KILL_FLAG_PATH: Kill Switch が書き込む flag ファイル — デフォルト data/kill.flag
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag をクリアするか ("1" でクリア)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（%）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定（空だと通知はスキップ）

重要なランタイムオーバーライド:
- MONITOR_POLL_INTERVAL: run_monitoring で使用するポーリング間隔（秒）。デフォルト 60。0 以下や不正値は 60 にフォールバック。

セットアップ手順
----------------
1. Git リポジトリをクローンし、プロジェクトルートへ移動
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   pip install duckdb psutil requests openai streamlit
4. 環境変数を設定（.env を作るかシェルで export）
   - .env.example があれば参考に作成してください（config._require の例外メッセージ参照）
5. データディレクトリを作成（必要に応じて）
   mkdir -p data

注: .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に行われます。

起動・使い方
------------

ExecutionEngine（実際の売買セッション開始）
- 本番 / 開発 / Paper Trading の自動切替は KABUSYS_ENV による
- Paper Trading の場合は MockBrokerClient を使用し、data/paper_trading.db を使用して本番 DB と完全分離します

起動コマンド例:
- 本番・開発（設定済の DB/ブローカー）:
  python -m kabusys.run_execution

- Paper Trading:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

run_execution は起動時にプロセス優先度を high に設定し、DB 接続、ブローカー生成、各コンポーネントを組み立てて ExecutionEngine を起動します。ExecutionEngine は PID ファイルを書きます（Settings.pid_file_path）。

Monitoring（監視ループ）
- システム状態・注文滞留・リスクを定期チェックして monitoring DB（SQLite）へ記録し、必要なら kill.flag 書き込みや LINE 通知を行います。

起動コマンド:
- python -m kabusys.run_monitoring

オプション:
- 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（例: export MONITOR_POLL_INTERVAL=30）。

Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示するダッシュボード
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- paper_verification_report スクリプトは paper trading DB のログを解析し PASS/FAIL 判定のレポートを出力します

実行例:
- python -m kabusys.tools.paper_verification_report
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- または DB パス指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db

AI モジュール（ニューススコア / レジーム判定）
- OpenAI API キー (OPENAI_API_KEY) が必要
- プログラム的に呼ぶ場合:
  from kabusys.ai import score_news
  # score_news(conn, target_date, api_key="...")

- レジーム判定:
  from kabusys.ai.regime_detector import score_regime
  # score_regime(duckdb_conn, target_date, api_key="...")

監視・停止シグナル（kill.flag / pid）
- ExecutionEngine は起動時に PID を pid_file に書きます（デフォルト data/execution.pid）。
- Monitoring の KillSwitch が危険検知（ドローダウン、ポジション上限超過など）すると KILL_FLAG_PATH（data/kill.flag）へ理由を書き込みます。存在すると ExecutionEngine 停止シグナルとして扱います。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると既存の kill.flag を消去します（クリーンスタート用）。

データベース初期化
- run_execution / run_monitoring 起動時に必要な監視テーブルは init_monitoring_db により冪等に作成されます（monitoring_db.py）。

ディレクトリ構成（主要ファイルの説明）
-------------------------------------
以下は src/kabusys の主要なファイル・パッケージと簡単な説明です。

- src/kabusys/__init__.py
  - パッケージ定義・バージョン

- src/kabusys/config.py
  - 環境変数の読み込み・Settings クラス。.env 自動読み込みのロジックを含む。

- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じたブローカ生成、paper_trading 分離）。

- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 可変。

- src/kabusys/execution/
  - 注文周りの実装（order_manager.py、reconciler.py、order_repository.py 等）
  - reconciler: 再起動時の注文・ポジション突合

- src/kabusys/monitoring/
  - 監視コンポーネント群：system_monitor.py, trade_monitor.py, risk_monitor.py
  - monitoring_db.py : SQLite テーブル定義と MonitoringDB ラッパ
  - monitoring_engine.py: 複数の Monitor を束ねる実行ループ
  - alert_manager.py: LINE Push 通知
  - kill_switch.py: kill.flag 管理
  - streamlit_dashboard.py: streamlit ダッシュボード

- src/kabusys/portfolio/
  - ポートフォリオ構築：portfolio_builder.py, position_sizing.py, risk_adjustment.py

- src/kabusys/research/
  - ファクター計算・特徴量解析（factor_research.py, feature_exploration.py）

- src/kabusys/ai/
  - ニュース NLP（news_nlp.py）: OpenAI でセンチメントを算出し ai_scores に書込
  - レジーム判定（regime_detector.py）: MA とマクロニュースの LLM 結果を合成して market_regime を書込

- src/kabusys/tools/
  - paper_verification_report.py: Paper Trading ログから検証レポート出力

- src/kabusys/utils/
  - process_priority.py: プロセス優先度 / CPU affinity のヘルパ

注記・運用上のポイント
--------------------
- Paper Trading モードでは実際のブローカーへの発注は行わず、データベースは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に分離されます。運用で本番 DB を上書きしないよう注意してください。
- OpenAI を用いる処理は API 呼び出しの失敗をフォールバック（スコア 0.0 等）で扱う設計ですが、API キーの漏洩やコスト管理には注意してください。
- Monitoring は KABUSYS_ENV に依らずデフォルトで本番の SQLITE_PATH を使います（run_monitoring の仕様）。必要なら環境変数で監視 DB を指定してください。
- process priority / CPU affinity 設定はプラットフォーム依存で失敗する可能性があります（アクセス権限等）。その場合は警告ログを出してスキップします。

開発・テスト
-------------
- 各モジュールは副作用を抑えた実装が意図されており、ユニットテストやモック差替えが容易です（例: OpenAI 呼び出しをパッチする等）。
- DB 関連は一時ファイルまたはメモリ内 SQLite を用いてテスト可能です。

最後に
------
この README はコードベースの主要な使い方と構成をまとめたものです。細かな挙動（パラメータや内部のアルゴリズムの詳細）は該当するモジュールの docstring / コメントを参照してください。必要であれば README に追記する項目（例: 具体的な設定例、運用手順、テスト手順等）を教えてください。