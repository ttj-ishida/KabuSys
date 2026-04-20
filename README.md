KabuSys — 日本株自動売買システム（簡易 README）
=================================

概要
----
KabuSys は日本株の自動売買を目的としたモジュール群を含むパッケージです。  
主に次の機能を提供します：

- ExecutionEngine（発注実行）と Monitoring（監視）を分離して実行可能
- ポートフォリオ構築・ポジションサイジング（純粋関数群）
- ファクター計算・リサーチユーティリティ（DuckDB を用いた分析）
- AI を用いたニュースセンチメント評価・市場レジーム判定（OpenAI を利用）
- 監視用 DB（SQLite）と監視エンジン（ログ・Kill Switch・アラート連携）
- ペーパートレード検証レポート出力ユーティリティ

特徴
----
主な機能一覧（抜粋）:

- 実行（run_execution.py）
  - 本番/ペーパー（KABUSYS_ENV）に応じた挙動（paper_trading時は MockBroker を使用し DB を分離）
  - リスク管理（RiskManager）、注文管理（OrderManager）、整合性チェック（Reconciler）を統合
- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期的に実行する監視ループ
  - kill.flag による安全停止（Kill Switch）
  - monitoring DB（SQLite）へログ永続化
- ポートフォリオ（portfolio パッケージ）
  - 候補選定、等重・スコア重み、リスク調整（セクター上限・レジーム乗数）、ポジションサイズ計算
- リサーチ（research パッケージ）
  - ファクター計算（モメンタム/バリュー/ボラティリティ等）、将来リターン、IC 計算、統計サマリー
- AI（ai パッケージ）
  - ニュース NLP（OpenAI）による銘柄別センチメント scoring（news_nlp）
  - 市場レジーム判定（regime_detector）
- ツール
  - 環境設定ウィザード（config_setup.py）— .env の作成/更新を対話式で支援
  - 設定検証 CLI（validate_config.py）— 起動前に .env / config/*.yaml を検証
  - Paper Trading 検証レポート（tools/paper_verification_report.py）

セットアップ手順
----------------
1. Python 環境
   - 推奨: Python 3.10+（実行環境に合わせてください）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai
   - 任意/推奨: pip install pyyaml  （validate_config が YAML のパース検証を行う場合）
   - 開発時に必要なパッケージを追記してください（例: pytest 等）

4. 環境変数の初期設定
   - 対話式ウィザードで .env を作成するのが推奨です:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（.env.example 等を参照）

5. データディレクトリとログディレクトリ
   - デフォルトで data/ と logs/ を使用します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を設定してください。

使い方（よく使うコマンド）
------------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱いになります

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV 環境変数で制御（development / paper_trading / live）
  - paper_trading の場合、paper_sqlite_path（デフォルト: data/paper_trading.db）にデータを記録

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は production の sqlite_path を使用する設計（環境に依らず本番監視 DB を使用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも可）

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数または引数で指定

重要な環境変数（主なもの）
--------------------------
（Settings によりデフォルト値が設定されているものもあります）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

- DB / ファイルパス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
  - PID_FILE_PATH（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（デフォルト: data/kill.flag）

- ログ:
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）

- AI:
  - OPENAI_API_KEY（news_nlp / regime_detector で使用）

- その他:
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒）
  - PAPER_FILL_MODE（paper_trading の fill 動作: instant | partial | never | reject）

安全停止（Kill / Stop）
-----------------------
- 監視・実行スクリプトは data/stop_requested.flag や data/kill.flag を利用して外部から停止を指示できます。
  - run_monitoring.py / run_execution.py は stop flag を検知して順次停止します。
  - KillSwitch はリスク閾値超過時に data/kill.flag を書き込み、Execution 側が検出して停止する設計です。

ログとローテーション
--------------------
- ログは kabusys.utils.logging_setup.setup_logging を経由して設定され、
  - コンソール出力（stdout）
  - ファイル出力: logs/<app_name>.log を日次ローテーション（30日保持）
- LOG_DIR 環境変数でログ格納先を変更できます。

ライブラリ API（抜粋）
---------------------
- ポートフォリオ:
  - kabusys.portfolio.select_candidates(...)
  - kabusys.portfolio.calc_equal_weights(...)
  - kabusys.portfolio.calc_score_weights(...)
  - kabusys.portfolio.calc_position_sizes(...)

- リサーチ:
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)

- AI:
  - kabusys.ai.score_news(conn, date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, date, api_key=None)

- 監視 DB:
  - kabusys.monitoring.monitoring_db.init_monitoring_db(sqlite_conn)
  - MonitoringDB（log_system_status, log_trade_event, upsert_dashboard, log_risk_event, get_dashboard 等）

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要ファイルと役割の概略です（抜粋）:

- src/kabusys/
  - __init__.py            — パッケージ定義
  - __version__ = "0.1.0"

- 起動スクリプト
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py     — Monitoring 起動スクリプト

- 設定関連
  - config.py             — Settings クラス（環境変数読み込み・デフォルト）
  - config_setup.py       — .env 対話式ウィザード
  - validate_config.py    — 設定検証 CLI

- 監視（monitoring）
  - monitoring_db.py      — SQLite スキーマ初期化 / DB 操作ラッパ
  - system_monitor.py     — システム状態・データ鮮度監視
  - trade_monitor.py      — （参照: 取引ログ監視ロジック）
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - kill_switch.py        — kill.flag 書き込みユーティリティ
  - monitoring_engine.py  — 複数モニタを束ねる実行ループ
  - alert_manager.py      — （参照: 通知管理）

- 実行関連（execution）
  - execution_engine.py   — ExecutionEngine（発注セッション制御）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py     — BrokerClientFactory（paper_trading時は MockBroker）

- ポートフォリオ（portfolio）
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- リサーチ（research）
  - factor_research.py
  - feature_exploration.py

- AI（ai）
  - news_nlp.py
  - regime_detector.py

- utils
  - logging_setup.py
  - process_priority.py

- tools
  - paper_verification_report.py

注意事項 / 運用上のヒント
-------------------------
- .env は絶対に Git にコミットしないでください（API キーやパスワードを含みます）。
- KABUSYS_ENV=live のときは設定ミス（LINE 未設定や kill flag 自動クリア等）に注意してください。validate_config の live ガードを参照してください。
- ファイル・DB パスの親ディレクトリが無ければ起動時に自動作成される場合がありますが、パーミッションやディスク容量は事前に確認してください。
- run_execution / run_monitoring はプロセス優先度変更を試みます（psutil が必要）。権限がない場合は警告が出ますが継続します。

お問い合わせ / 拡張
-------------------
コード内のドキュメント文字列（docstring）に設計方針や注意点が多く書かれています。機能追加や修正を行う際は該当モジュールの docstring を参照してください。

以上。開発・運用に必要な追加情報があれば、目的に応じて README を更新します。