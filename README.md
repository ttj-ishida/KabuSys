README
======

概要
----
KabuSys は日本株向け自動売買システムのコアライブラリ群です。本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）と注文管理（OrderManager / Reconciler）
- 監視（Monitoring）: システム状態・注文滞留・リスク監視、アラート送信、ダッシュボード
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 支援モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- ツール（Paper Trading 検証レポート、Streamlit ダッシュボード起動等）
- 設定管理（環境変数 / .env の読み込みヘルパ）

この README は、コードベースの使い方・セットアップ・構成をまとめたものです。

主な機能
--------
- Execution
  - 実行エンジン起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化と Mock 対応（paper_trading 環境）
  - リコンシリエーション（再起動時の状態同期）
  - 注文状態管理とリスク制御（Rate limit / ポジション上限等のチェック）

- Monitoring
  - SystemMonitor: CPU / memory / disk / プロセス生存 / データ鮮度監視
  - TradeMonitor: 注文滞留（stale）・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限チェック、ダッシュボード更新
  - KillSwitch: しきい値越えで data/kill.flag を書き込み ExecutionEngine を停止
  - AlertManager: LINE Messaging API による通知（クールダウン管理）
  - Streamlit ダッシュボード起動スクリプト

- Portfolio
  - 候補選定（スコア順ソート）
  - 等金額・スコア加重配分
  - セクター集中制限の適用
  - ポジションサイズ計算（リスクベース、単元株丸め、aggregate cap のスケーリング）

- Research / AI
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（情報係数）や統計サマリ
  - ニュース NLP（OpenAI）による銘柄別センチメント集計と ai_scores への書込み
  - レジーム検出（MA200 とマクロセンチメントの合成）

セットアップ手順
----------------

前提
- Python 3.10+（型アノテーション等に依存）
- システムに応じたパッケージのインストール（以下参照）

1. リポジトリのクローン
   - git clone <repo-url>
   - パッケージルートは src/ 配下に配置されていることを想定

2. 仮想環境の作成と有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux / macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 実運用では requirements.txt を用意して pip install -r requirements.txt を使ってください

4. データディレクトリ作成
   - mkdir -p data
   - デフォルトで使用される DB パス:
     - DuckDB: data/kabusys.duckdb (環境変数 DUCKDB_PATH で上書き可)
     - Monitoring SQLite: data/monitoring.db (SQLITE_PATH)
     - Paper Trading SQLite: data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)

5. 環境変数設定
   - プロジェクトルートの .env / .env.local を使えます（config.py が自動ロード）
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須の箇所あり）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
     - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - LOG_LEVEL: DEBUG/INFO/…（Settings.log_level で検証）

   例 .env（簡易）
   - KABUSYS_ENV=paper_trading
   - OPENAI_API_KEY=sk-...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...

使い方
------

起動・停止

- 監視プロセス（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
  - run_monitoring は常に本番用の sqlite_path（Settings.sqlite_path）を参照します（KABUSYS_ENV に依らず）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
  - 実行中は data/execution.pid に PID を書きます（PID ファイルの stale 判定あり）
  - 停止フラグ:
    - global stop flag: data/stop_requested.flag — 存在すると run_monitoring / run_execution は安全に終了します
    - kill switch: data/kill.flag — KillSwitch が書き込み、ExecutionEngine に対して停止を促す（再起動時にクリアするオプションがある）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: 稼働率、注文成功率、レイテンシ等のサマリと PASS/FAIL 判定

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring.db を読み取り専用で開きます（監視プロセスが先に初期化しておくこと）

AI 関連
- kabusys.ai.news_nlp.score_news(target_date) / kabusys.ai.regime_detector.score_regime(target_date)
  - OpenAI API キーが必要（OPENAI_API_KEY または引数で指定）
  - rate limit / 5xx 等に対しリトライ・フェイルセーフ処理あり（失敗時はスコアをスキップまたは 0.0 で継続）

プロセス優先度・CPU 設定
- run_monitoring / run_execution は起動時に set_process_priority("high") を呼び出します（psutil を使用）。
  - 権限がない場合は警告を出してスキップします。

停止・強制停止の仕組み
- stop_requested.flag: 手動で作成すると run_monitoring/run_execution が検知して安全に終了します
- kill.flag: KillSwitch が条件を満たした際に書き込み、ExecutionEngine に停止を促します（Settings.kill_flag_path で場所指定）

ディレクトリ構成
----------------

src/kabusys/
- __init__.py
- config.py
  - 環境変数/.env の読み込みと Settings クラス
- run_monitoring.py
  - SystemMonitor をポーリングで実行するエントリポイント
- run_execution.py
  - ExecutionEngine を起動するエントリポイント（paper_trading モード対応）
- tools/
  - __init__.py
  - paper_verification_report.py
    - Paper Trading DB から検証レポートを生成
- monitoring/
  - __init__.py
  - monitoring_db.py
    - SQLite ベースの永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py
    - システム状態・データ鮮度チェック
  - trade_monitor.py
    - 注文滞留・価格異常チェック
  - risk_monitor.py
    - ドローダウン・ポジション上限チェック
  - kill_switch.py
    - kill.flag の書き込みロジック
  - alert_manager.py
    - LINE push による通知
  - monitoring_engine.py
    - 各モニタを束ねるループ（テスト用 run_once / 本番用 run）
  - streamlit_dashboard.py
    - Streamlit での監視ダッシュボード
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - execution_engine.py
  - broker_factory / broker_api (抽象)
  - order_record.py
  - risk_manager.py
  - （実装の詳細はソースを参照）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
    - ニュース記事を集約して OpenAI に送信、ai_scores テーブルに書き込む
  - regime_detector.py
    - MA200 とマクロセンチメントで市場レジーム判定
  - __init__.py
- utils/
  - process_priority.py
    - psutil を使ってプロセス優先度 / CPU affinity を設定
  - __init__.py
- data/ (実行時に生成される想定)
  - monitoring.db (SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - stop_requested.flag / kill.flag / execution.pid / …


運用上の注意
-------------
- 環境変数の自動読み込み:
  - config.py はプロジェクトルート（.git か pyproject.toml がある場所）を探し、.env / .env.local を読み込みます
  - OS 環境変数が優先され、.env.local は .env を上書きします
  - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は idempotent（冪等）でテーブルと一部のカラム追加を行います

- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、発注は MockBroker によって行われ、paper_trading 用 SQLite に記録されます（本番 DB と分離）
  - PAPER_FILL_MODE で約定挙動（instant/partial/never/reject）を設定可能

- OpenAI API:
  - 大量リクエストや高頻度呼び出しに対してレート制限やエラーが発生する可能性があります。news_nlp / regime_detector はリトライロジックを備えていますが、API キーの利用制限に注意してください。

補足（トラブルシュート）
-----------------------
- PID ファイルの stale 判定:
  - PID ファイルが残りプロセスが存在しない場合、SystemMonitor は stale と見なしファイルを削除しリスクイベントに記録します

- SQLite を read-only で開く:
  - Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。DB が存在しない・ロックされている場合は起動エラーを表示します

- ロギング:
  - run_monitoring / run_execution は basicConfig(level=INFO) で起動します。LOG_LEVEL 環境変数で Settings.log_level を変更できます（値は DEBUG/INFO/... のみ許容）

ライセンス / 貢献
-----------------
- 本 README にライセンス情報は含めていません。リポジトリ内の LICENSE を参照してください。
- バグ修正・機能追加はプルリクエスト歓迎です。大きな変更は事前に issue で相談してください。

以上がこのコードベースの概要と基本的な使い方です。必要であれば、実際の起動例（環境変数の雛形 / systemd ユニットの例 / docker-compose 設定例）なども追記できます。どの情報が必要か教えてください。