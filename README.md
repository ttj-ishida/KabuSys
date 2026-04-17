KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買システムです。戦略のポートフォリオ構築、発注エンジン、監視・アラート、リサーチ／ファクター計算、AI によるニュースセンチメント評価などを備えたモジュール構成になっています。  
パッケージは src/kabusys 配下に実装されており、モジュール化されているため研究用途（DuckDB を用いたファクター計算）や Paper Trading（本番 DB と分離）にも対応しています。

主な機能
---------
- Execution
  - ExecutionEngine を中心とした発注フロー（OrderManager、OrderRepository、RiskManager、Reconciler）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、本番 DB と分離して data/paper_trading.db に記録
  - 再起動時の自動リコンシリエーション（Reconciler）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期チェック
  - kill.flag による安全な停止（KillSwitch）
  - 監視ログの永続化（SQLite）と集計（DuckDB）
  - LINE 通知によるアラート（AlertManager）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Portfolio construction
  - 候補選定、重み付け（等金額／スコア）、セクター制限、レジーム乗数、株数決定（単元丸め／利用可能資金に基づくスケーリング）
- Research
  - DuckDB を使ったファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、特徴量サマリ
- AI
  - ニュースを OpenAI に送りセンチメントスコアを算出して ai_scores に格納（kabusys.ai.news_nlp）
  - マクロセンチメントと ma200 を組み合わせた市場レジーム判定（kabusys.ai.regime_detector）
- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
  - 環境変数読み込みと設定管理（kabusys.config.Settings）

セットアップ
----------
必要条件
- Python 3.10 以上（型注釈に | を使用しているため）
- システムに sqlite3（標準ライブラリ）、その他以下の Python パッケージが必要:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- ネットワーク接続（OpenAI API を利用する場合）

インストール（例）
1. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
2. 依存パッケージをインストール:
   - pip install duckdb psutil requests openai streamlit
   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用）

環境変数
- .env / .env.local に設定を置くことで起動時に自動的に読み込まれます（プロジェクトルートを .git または pyproject.toml で検出）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- 主な環境変数（Settings で参照されるもの）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

簡単な .env 例
（実際にはシークレットは安全に管理してください）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant
- LINE_CHANNEL_ACCESS_TOKEN= (LINE 通知を使う場合)
- LINE_USER_ID= (LINE 通知先)

使い方
------
監視ループを起動（本番・開発共通）
- 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒単位で上書き可能（デフォルトは 60 秒）。
- 実行:
  - python -m kabusys.run_monitoring
  - 起動時にプロセスの優先度を "high" に設定します（可能な場合）。
  - 監視は Settings に設定された sqlite_path を使います（監視は環境にかかわらず本番 sqlite_path を使用）。

ExecutionEngine を起動（発注系）
- KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）に記録されます。本番モード（live）では実ブローカークライアントを使います。
- 実行:
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid が作成され、停止命令は data/stop_requested.flag により伝達されます。停止フラグが存在する場合は起動しません。

Streamlit ダッシュボード
- 監視用 SQLite を read-only で開いてダッシュボードを表示します。
- 実行例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Paper Trading 検証レポート
- data/paper_trading.db を対象にレポートを標準出力へ出力します。
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パス上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

AI 機能
- OpenAI を使う機能（ニュースセンチメント、レジーム判定）は OPENAI_API_KEY が必要です。関数呼び出し時に api_key 引数で明示的に渡すことも可能です。
- エラーや API 側の一時障害時にはフェイルセーフ（0.0 フォールバック、部分失敗の保護）を備えています。

停止・キルスイッチ
- KillSwitch は RiskMonitor の結果などから判断して data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- その他、data/stop_requested.flag（run_monitoring / run_execution でチェック）により即時停止を行います。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                    — 環境変数読み込み / Settings クラス
- run_monitoring.py            — SystemMonitor ポーリングループ起動
- run_execution.py             — ExecutionEngine 起動スクリプト
- utils/
  - process_priority.py        — プロセス優先度・CPU affinity ユーティリティ
- monitoring/
  - __init__.py
  - monitoring_db.py           — SQLite ベースの永続化層（init / CRUD）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py       (実装ファイルはここに含まれる想定)
  - broker_factory.py
  - broker_api.py
  - order_record.py
  - order_*                   (その他発注関連モジュール)
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
- data/                       — 実行時に使用するファイル群（DB, pid, flags 等）
- tools/
  - paper_verification_report.py

注意点 / 運用メモ
-----------------
- Settings は .env/.env.local を自動読み込みします（OS 環境変数が優先）。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うと自動読み込みを抑制できます。
- PAPER_TRADING モードでは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に完全分離して記録されます。本番 DB の保護のためデフォルトで分けられています。
- OpenAI 等外部 API の利用はネットワーク・API 制限に左右されます。news_nlp や regime_detector はリトライやフォールバックを備えていますが、API キー管理と利用制限には注意してください。
- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db が起動時に冪等に実行します（既存 DB にないカラムを追加する処理あり）。
- プロセス優先度の変更や CPU affinity の設定はプラットフォーム依存で、権限不足時は警告を出してスキップします。

貢献 / 開発
-----------
- コードベースはモジュール単位で単体テストやモックがしやすい設計になっています（外部依存は注入可能）。
- 変更を加える場合はテストを追加し、特に発注・リスク・監視に関わるロジックはステージング（paper_trading）で十分に検証してください。

ライセンス
---------
（この README にライセンス情報は含まれていません。プロジェクトルートに LICENSE ファイルがあれば参照してください。）

補足
----
README に記載のコマンドやパスはソース内のデフォルト値に基づいています。実環境では .env や運用スクリプトでパスや環境変数を明示的に設定して運用してください。