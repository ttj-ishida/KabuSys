KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買システムのコア部品群です。本リポジトリには以下の主要機能が含まれます。

- 注文実行エンジン（ExecutionEngine）およびブローカークライアント抽象化（本番 / ペーパートレード切替）
- 監視用ポーリング（System / Trade / Risk モニタ）と Kill Switch（フラグファイルによる外部停止）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイジング、セクター制限）
- リサーチ用ファクター計算・特徴量解析（DuckDB を用いた分析関数）
- ニュース NLP / レジーム検出（OpenAI を用いたマクロ・銘柄別センチメント）
- Paper Trading 検証レポート生成ツール

特徴
----
- 環境別挙動:
  - KABUSYS_ENV=paper_trading: MockBroker を使用し paper_trading 用 SQLite に分離して記録
  - 本番（live）と開発（development）モードの切替サポート
- DB:
  - 監視ログは SQLite（data/monitoring.db がデフォルト）
  - 分析用に DuckDB（data/kabusys.duckdb がデフォルト）
- 安全機構:
  - Kill Switch（data/kill.flag）で外部から ExecutionEngine を停止可能
  - リスク監視（ドローダウン、ポジション数超過）でアラートおよび kill をトリガー
- ロギング:
  - 共通の logging 設定ユーティリティ（コンソール + 日次ローテートファイル）
- AI 統合:
  - OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメントおよびレジーム検出（API キー必要）
- ツール:
  - 設定ウィザード (.env 作成支援)
  - 設定検証 CLI
  - Paper Trading の検証レポート生成

セットアップ手順
----------------
前提:
- Python 3.9+（ソースは typing|Path 等を利用）
- システム依存のネイティブライブラリは不要だが、以下パッケージが必要です。

推奨インストール（例）:
- pip install duckdb psutil openai
- optional: PyYAML（config/*.yaml の検証をする場合）

.env の用意:
1. 対話式ウィザードで初期 .env を作る:
   - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）

2. 自動ロード:
   - デフォルトでプロジェクトルートの .env と .env.local を自動的に読み込みます。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主な設定項目（例・デフォルト）:
- KABUSYS_ENV: development | paper_trading | live  (default: development)
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定挙動）

使い方
------

設定検証:
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いで exit(1)

環境設定ウィザード:
- python -m kabusys.config_setup

ExecutionEngine（発注エンジン）起動:
- python -m kabusys.run_execution
- 動作:
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、MockBrokerClient を使います。
  - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。
  - 停止は data/stop_requested.flag の作成で指示できます（monitoring 側からもトリガー可）。

Monitoring（監視ループ）起動:
- python -m kabusys.run_monitoring
- 説明:
  - SystemMonitor / TradeMonitor / RiskMonitor を定期的に走らせ、KillSwitch や AlertManager を用いて通知やフラグ操作を行います。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path を参照（環境に関わらず monitoring 用 DB は settings.sqlite_path を使用）。

Paper Trading 検証レポート:
- python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH を優先）

AI 関連:
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を与えて ai_scores を書き込む。API キーは引数か OPENAI_API_KEY 環境変数で指定。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - レジームを計算して market_regime テーブルへ書き込む。OpenAI API を使用。

ログ:
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一。
- デフォルトのログディレクトリ: logs/
- 環境変数 LOG_DIR で変更可能。

仕組み・安全運用メモ:
- Kill Switch:
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る（起動時に設定で自動クリア可能）。
  - Settings.kill_flag_clear_on_start=1 を本番で有効にするのは危険（デフォルト 0 を推奨）。
- 停止フラグ:
  - data/stop_requested.flag を監視してループを終了する（run_execution/run_monitoring で利用）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び、可能であれば優先度を上げます（psutil に依存）。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要モジュール構成の抜粋です。実際のリポジトリは pyproject.toml / README / scripts 等を含む可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定読み込みロジック
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/                    — 発注関連（Engine, OrderManager など）※詳細は該当ディレクトリ参照
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py           — （存在する想定）取引滞留・約定異常検出
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py           — （存在する想定）通知送信ロジック
  - portfolio/
    - portfolio_builder.py       — 候補選定・重み付け
    - position_sizing.py         — 株数決定・資金配分ロジック
    - risk_adjustment.py         — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py         — momentum / volatility / value の計算（DuckDB）
    - feature_exploration.py     — forward returns / IC / summary
  - ai/
    - news_nlp.py                — ニュースの LLM スコアリング（ai_scores への書き込み）
    - regime_detector.py         — マクロ + ETF MA を用いた市場レジーム判定
  - data/                        — 実行時に使用する data/*.db、flag、pid など（プロジェクトルートの data/）
  - utils/
    - logging_setup.py
    - process_priority.py
    - その他ユーティリティ

依存関係（主要）
----------------
- duckdb
- psutil
- openai
- (optional) PyYAML — validate_config の YAML 検証に使用

開発者向け補足
--------------
- DuckDB / SQLite スキーマはコード内に明記。分析クエリは prices_daily / raw_financials / raw_news 等のテーブルを前提とします。
- LLM 呼び出しは外部 API の失敗を想定してフェイルセーフになっています（リトライ、失敗時はデフォルト値で継続）。
- 自動で .env をロードする仕組みは config._find_project_root() を使うため、パッケージ配布後も CWD に依存せず動作する設計になっています。
- MONITOR_POLL_INTERVAL を小さくすると監視頻度が上がりますが、過度に短くすると負荷が増えるので注意してください（デフォルト 60 秒）。

ライセンス・注意
----------------
- .env ファイルや API トークンは決して Git にコミットしないでください。
- 本システムは実際の発注を行う仕組みを含みます。本番運用前に十分な検証・監査を行ってください（validate_config を活用してください）。

-----

必要であれば、README に含める「よくある運用コマンド一覧」「.env のサンプル」「DB スキーマ概要（テーブル定義）」などを追加で作成します。どれを優先して追加しますか？