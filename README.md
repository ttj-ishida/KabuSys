README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の軽量実装です。  
主な目的は戦略の研究・ポートフォリオ構築・注文エンジンの実行・運用監視を統合することです。  
このリポジトリにはデータ処理（DuckDB）、執行エンジン（kabuステーション連携またはモック）、監視・アラート、リサーチ／ファクター計算や AI を用いたニューススコアリング等のコンポーネントが含まれます。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 本番（kabuステーション）・ペーパートレード（MockBroker）を切り替え可能（KABUSYS_ENV）。
  - リスク管理（RiskManager）、OrderManager、Reconciler 等を備える。
  - 起動時に PID ファイルを書き、停止はフラグファイル監視で行う。
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine。
  - SQLite ベースの監視 DB（monitoring.db）へログ保存。
  - Kill Switch（リスク基準により Execution を強制停止）をサポート。
- ポートフォリオ構築ユーティリティ
  - 候補選定、重み計算、ポジションサイズ決定、セクター制約など純粋関数群。
- リサーチ
  - DuckDB を利用したファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ツール。
- AI モジュール
  - OpenAI を用いたニュース NLP（銘柄別センチメント）と市場レジーム判定。
  - 失敗時のフォールバックやリトライ・バッチ処理ロジックを実装。
- 運用ユーティリティ
  - .env 対話型ウィザード（config_setup）、設定検証 CLI（validate_config）、Paper Trading 検証レポート生成ツール等。
- ロギング
  - 統一的なログ設定（コンソール stdout + 日次ローテートファイル、既定 logs/）。

セットアップ手順
--------------
※ プロジェクトルートは .git または pyproject.toml のあるディレクトリを自動検出します。

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt  
   - 必須ライブラリ（最低限）:
     - duckdb
     - psutil
     - openai （AI機能を使う場合）
   - 任意:
     - PyYAML（config/*.yaml の構文検証に使用）

3. 環境変数設定（.env）
   - 対話ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で .env を用意する場合は .env.example を参照して作成してください。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

主要な環境変数（抜粋とデフォルト）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — default: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API ベース URL — default: http://localhost:18080/kabusapi
- LOG_LEVEL: ログレベル — default: INFO
- DUCKDB_PATH: DuckDB ファイルパス — default: data/kabusys.duckdb
- SQLITE_PATH: 監視 SQLite パス — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite — default: data/paper_trading.db
- PAPER_FILL_MODE: ペーパートレードの約定挙動 — default: instant（instant|partial|never|reject）
- OPENAI_API_KEY: OpenAI を使う場合は必須（AI機能）

運用上のファイル・フラグ（デフォルト位置）
- data/execution.pid: ExecutionEngine の PID（Execution 起動時に書き込まれる）
- data/stop_requested.flag: run_execution / run_monitoring が監視する停止フラグ（存在すると実行を停止）
- data/kill.flag: KillSwitch によって書き込まれる停止フラグ（Execution を停止するために使用）
- logs/: ログファイル（例: logs/execution.log, logs/monitoring.log）

使い方（起動・コマンド）
---------------------

1) 環境設定ウィザード
   - python -m kabusys.config_setup
   - 対話的に .env を作成 / 更新します。

2) 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いで終了コード 1 を返します。

3) ExecutionEngine を起動（メインの発注エンジン）
   - python -m kabusys.run_execution
   - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録します。
   - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。
   - 停止させるには data/stop_requested.flag を配置する、または kill.flag により停止判定されます。

4) Monitoring を起動（監視プロセス）
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
   - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使います（環境に依らず）。

5) Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   - PAPER_TRADING_SQLITE_PATH 環境変数を参照します（指定がない場合 default: data/paper_trading.db）。

6) AI / リサーチ関数の利用（ライブラリとして）
   - ニューススコアリング:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key=...)
   - 市場レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key=...)
   - ファクター計算:
     - from kabusys.research import calc_momentum, calc_volatility, calc_value
     - calc_momentum(duckdb_conn, target_date) など

停止・Kill の違い
- stop_requested.flag (data/stop_requested.flag)
  - run_execution / run_monitoring がループで確認する「手動停止リクエスト」。存在すると起動を停止または実行中に終了します。
- kill.flag (Settings.kill_flag_path, default: data/kill.flag)
  - KillSwitch（監視により自動生成）で書き込まれる。リスク条件（例：ドローダウン過大）を満たしたときに ExecutionEngine を停止させるために使用されます。

ロギング
--------
- setup_logging により stdout とファイル出力を統一して設定します。デフォルトログディレクトリは logs/。
- ファイルハンドラは日次ローテーションで 30 日分保持します。
- LOG_DIR 環境変数や setup_logging の引数で変更可能です。

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 & Settings 管理（自動 .env 読み込み）
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 起動前の設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py      — 共通ロギング設定
    - process_priority.py   — プロセス優先度 / CPU affinity 設定
  - execution/               — ExecutionEngine と関連モジュール（エンジン / order_manager 等）
    - (※詳細実装は該当ディレクトリに存在)
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ & DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI 経由）
    - regime_detector.py    — レジーム判定（MA + マクロセンチメント）
  - tools/
    - paper_verification_report.py
  - data/                   — 実行時に生成される既定の DB / フラグ / pid（例: data/*.db, data/*.flag）

注意事項・運用上のヒント
---------------------
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。
- 本番環境（KABUSYS_ENV=live）の場合は LINE の通知設定や Kill Switch の設定等を慎重に確認してください（validate_config が補助します）。
- OpenAI を使う機能は API コストが発生します。rate limit / エラーに対するリトライ実装はありますが、利用状況とコストを把握してから有効化してください。
- DuckDB / SQLite のパスは環境変数で変更可能です。監視 DB（monitoring）は本番でも同一パスを使う設計に注意してください。
- process_priority.set_process_priority() は OS 権限によって失敗する場合があります（その場合は警告ログが出ます）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env 読み込みを無効化できます。

ライセンス / 貢献
-----------------
- この README はコードベースの概要説明です。実運用する場合は各モジュールの実装・テスト・セキュリティ・例外処理を十分に確認のうえご利用ください。貢献や改善提案は Pull Request/Issue を通じて行ってください。

以上。必要であれば、README に「起動例」「サンプル .env」「コマンド一覧」を追加できます。どの形式（簡易 or 詳細サンプル）を望むか教えてください。