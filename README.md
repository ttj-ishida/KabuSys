README
======

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリは注文実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュースセンチメント評価などのコンポーネントを持ち、DuckDB / SQLite をデータ基盤として利用します。

主な設計方針
- 本番 / ペーパートレードの分離（KABUSYS_ENV による切替）
- .env ベースの設定（config_setup による対話式作成）
- ロギングは統一された setup_logging（コンソール + 日次ローテーション）
- フェイルセーフ重視（外部 API 失敗時はフォールバック・ログ出力）
- 可能な限りルックアヘッドバイアスを排除（date.today() 等の無自覚参照を回避）

機能一覧
--------
- ExecutionEngine（発注・リスク管理・注文管理）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い data/paper_trading.db に記録
  - PID ファイル管理、停止フラグ検出（data/stop_requested.flag）
- Monitoring（システム状態・注文・リスク監視）
  - system_status / trade_logs / positions / risk_logs / dashboard を SQLite に永続化
  - KillSwitch: ドローダウンやポジション上限で停止フラグ（data/kill.flag）を作成
  - AlertManager（アラート送信の統一ポイント）
- ポートフォリオ構築（銘柄選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ機能（ファクター計算、forward returns、IC 計算、統計サマリー）
- AI モジュール
  - ニュース NLP（OpenAI を用いた銘柄センチメント評価）
  - 市場レジーム判定（ETF MA + マクロニュースの LLM 評価の合成）
- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
1. Python 環境を作成（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - psutil
     - openai  （AI 機能を使う場合）
     - pyyaml （validate_config の YAML 検証を使う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がないリポジトリのため、必要に応じて上記を個別インストールしてください。）

3. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくはルートに .env を手動作成（例は下記参照）。

4. 設定の検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

5. データディレクトリ準備
   - デフォルトの SQLite / DuckDB パスは data/ 以下なので、実行前にディレクトリを作成しておくと良い:
     - mkdir -p data logs

主要環境変数（代表）
-------------------
以下は主要な環境変数とデフォルト値・説明の抜粋です。完全な一覧は kabusys.config.Settings を参照してください。

- KABUSYS_ENV: execution 環境 (development / paper_trading / live)（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（Monitoring 用、監視は環境にかかわらず本番 sqlite_path を使用）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 SQLite）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の約定振る舞い）
- LOG_LEVEL: DEBUG/INFO/…（デフォルト: INFO）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト: 60） — run_monitoring で参照
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

.sample .env（config_setup が出力する内容の例）
------------------------------------------------
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

使い方
------
起動スクリプト（モジュール実行）:
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 動作:
    - Settings に基づき DB 接続を確立（paper_trading の場合は専用 DB を使用）
    - BrokerClient を生成（本番/Mock を自動切替）
    - ExecutionEngine.run_session を別スレッドで実行
    - data/stop_requested.flag を検出したら停止
    - PID ファイル: data/execution.pid（デフォルト。Settings.pid_file_path で変更可能）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 動作:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）
    - monitoring は環境にかかわらず本番 sqlite_path を使用して監視ログを記録
    - data/stop_requested.flag を検出したらループ停止

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill Switch
- 実行プロセスを外部から素早く停止させたい場合:
  - KillSwitch は data/kill.flag を書き込みます。ExecutionEngine はこの kill.flag を検出して安全停止します。
  - 手動で停止フラグを立てる: echo "reason" > data/kill.flag
  - 監視プロセスを停止するための一時的な停止要求（run_* スクリプトの終了）には data/stop_requested.flag を作成します（プロジェクトではこれを run_* が監視しているフラグとして使用）。

ロギング
-------
- ログは setup_logging を通じて stdout と logs/<app_name>.log 日次ローテートに出力されます。
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL（.env）か引数で制御可能（setup_logging の level 引数）。

データベースとマイグレーション
----------------------------
- Monitoring の初期化は init_monitoring_db により冪等にテーブルを作成します（system_status, trade_logs, positions, risk_logs, dashboard）。
- 実行時に必要なカラムがない場合は簡単な ALTER を行う（例: latency_ms / peak_value の追加）。
- DuckDB は分析・リサーチ用途、SQLite は監視・注文ログ用途に使われます。

主要なコード構成（ディレクトリ構成）
------------------------------------
以下は主要ファイル/ディレクトリの概観（src/kabusys 以下）。実際のプロジェクトルートでは src/ をパッケージルートとして配置しています。

- kabusys/
  - __init__.py  (バージョン等)
  - config.py  (Settings クラス: 環境変数の読み取り・自動ロード)
  - config_setup.py  (対話式 .env ウィザード)
  - validate_config.py  (設定検証 CLI)
  - run_execution.py  (ExecutionEngine 起動スクリプト)
  - run_monitoring.py  (Monitoring 起動スクリプト)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/
    - (データ / DB / マスタなど置き場。実行時に data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb 等が生成されます)
  - tools/
    - paper_verification_report.py

注意事項 / 運用上のヒント
-----------------------
- .env は絶対に Git にコミットしないこと（config_setup のヘッダにも明記）。
- KABUSYS_ENV=live の場合は本番設定の確認を厳重に行ってください（validate_config の live 向け追加チェックあり）。
- Monitoring は監視用 DB を使用するため、monitoring の起動は監視対象の ExecutionEngine が参照するデータパスと一致していることを確認してください（特に paper_trading モードの DB 分離）。
- OpenAI を使う機能は API コストとレイテンシが発生します。環境変数 OPENAI_API_KEY を設定し、必要に応じて API 呼び出し頻度を調整してください。
- プロセス優先度設定（set_process_priority）および CPU affinity は psutil を利用して OS に合わせて設定しますが、権限不足で失敗することがあります（警告を出してスキップ）。

トラブルシューティング
---------------------
- validate_config でエラーが出たら、env の必須項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等）を確認してください。
- DuckDB / SQLite に接続できない場合はパスとパーミッションを確認してください。
- OpenAI API 呼び出しで RateLimit 等が発生した場合、内部で指数バックオフが実装されていますが、連続失敗時はログを確認してください。

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ にて管理（現状 0.1.0）。
- ライセンス情報はリポジトリのトップレベル LICENSE ファイルを参照してください（存在する場合）。

問い合わせ
----------
- 実装の詳細や拡張、運用に関する質問はリポジトリ管理者へお問い合わせください。README に書かれていない内部仕様はコード内の docstring を参照してください（各モジュールに詳細な説明があります）。

以上。README に不足があれば、追加で特定セクション（例: ExecutionEngine の CLI オプション、AlertManager の設定方法、具体的な SQL スキーマ解説など）を追記します。