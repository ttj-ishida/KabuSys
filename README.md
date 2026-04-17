# KabuSys

日本株向けの自動売買システム（モジュール群）のリポジトリ。  
本リポジトリは発注エンジン、監視（モニタリング）、ポートフォリオ構築、リサーチ、AI（ニュース/NLP・レジーム判定）などの主要機能をモジュール化して提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 監視ループ起動
  - ExecutionEngine 起動
  - Paper Trading 検証レポート
  - Streamlit ダッシュボード
  - AI スコア / レジーム判定（ライブラリ呼び出し）
- 環境変数（主なもの）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株自動売買のためのライブラリ／実行バイナリ群です。  
- 発注ロジック・注文管理・再突合（reconcile）・リスク管理・監視・アラート（LINE）・ポートフォリオ構築・ファクター計算・ニュースNLP 等の機能を含みます。  
- DB 永続化として SQLite（監視・注文ログ等）と DuckDB（時系列・ファクタ計算等）を利用します。  
- モジュール設計で、テストや paper_trading（モックブローカー）運用を容易にしています。

---

機能一覧
- 実行系（execution）
  - ExecutionEngine（発注セッションの起動／管理）
  - OrderManager、OrderRepository、Reconciler（注文同期と再突合）
  - RiskManager（発注前リスク制約）
- 監視（monitoring）
  - SystemMonitor（プロセス・CPU/メモリ/DISK・データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件達成で停止フラグを書き込み ExecutionEngine を止める）
  - AlertManager（LINE push によるアラート送信）
  - MonitoringEngine（上記を束ねたポーリングエンジン）
  - monitoring 用 DB 初期化ユーティリティ
  - Streamlit ダッシュボード表示スクリプト
- ポートフォリオ（portfolio）
  - 候補選定、等配分／スコア配分、セクターキャップ、ポジションサイズ算出（単元丸め含む）
- リサーチ（research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（ai）
  - news_nlp: raw_news を LLM（OpenAI）へ送り銘柄別センチメント ai_scores を作成
  - regime_detector: ma200 乖離とマクロニュースセンチメントを合成して market_regime を判定
- ツール（tools）
  - paper_verification_report: Paper Trading の検証レポート生成（期間指定可）
- ユーティリティ
  - Settings（.env 自動ロード、環境変数ラップ）
  - process_priority（プロセス優先度・CPU affinity 設定）

---

セットアップ手順（推奨）
1. Python 環境の準備
   - Python 3.10+ を推奨（typing の Union | 等を使用）  
   - 仮想環境を作る: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージのインストール
   - 必要パッケージ（主なもの）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合はそれを使ってください）

3. プロジェクトルートに data ディレクトリを作成
   - mkdir -p data
   - デフォルトの DB ファイルは次の通り（必要に応じて環境変数で変更可）
     - data/monitoring.db (SQLite)
     - data/paper_trading.db (Paper Trading 用 SQLite)
     - data/kabusys.duckdb (DuckDB)

4. 環境変数設定
   - プロジェクトルートに .env ファイルを置けば自動ロードされます（.env.local は上書き可）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI や LINE 等は利用機能に応じて設定（下記「環境変数」参照）

---

使い方（主要スクリプト・例）

1) 監視ループを起動（SystemMonitor 単体実行）
- 実行:
  - python -m kabusys.run_monitoring
- 説明:
  - Settings を読み、monitoring 用の SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）に接続して SystemMonitor を初期化しポーリングを開始します。
  - デフォルトポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で秒数を上書きできます。
  - 停止方法: Ctrl+C、またはプロジェクトルート data/stop_requested.flag を作成すると次のポーリング前に終了します。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に依らない実装）。

2) ExecutionEngine を起動（発注エンジン）
- 実行:
  - python -m kabusys.run_execution
- 説明:
  - Settings.env によって paper_trading（モックブローカー）／live の動作を切替えます。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、DB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使って本番 DB と完全分離します。
  - 起動時に data/stop_requested.flag があれば起動せず終了します。実行中に同フラグが作成されると安全に停止されます。
  - 実行中の PID は data/execution.pid（デフォルト）に書かれます。SystemMonitor はこの PID の存否を見てプロセス停止を検出します。

3) Paper Trading 検証レポート生成
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH も使用可能）
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標と PASS/FAIL 判定を標準出力へ表示します。

4) Streamlit ダッシュボード（監視 UI）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視用 SQLite を読み取り専用で開いてダッシュボードを表示します。MonitoringEngine によるデータがあることが前提です。

5) AI 機能（ライブラリ呼び出しとして）
- ニュース NLP（ai.score_news）
  - 引数: DuckDB 接続、target_date、api_key(optional)
  - OpenAI API キーを api_key 引数または環境変数 OPENAI_API_KEY で渡します。
  - 対象ウィンドウは target_date の前日 15:00 JST ～ target_date 当日 08:30 JST（内部的に UTC へ変換）
- レジーム判定（ai.regime_detector.score_regime）
  - DuckDB 接続、target_date、api_key(optional)
  - ma200 とマクロニュースセンチメントを合成して market_regime テーブルへ冪等的に書き込みます。

---

環境変数（主なもの）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject、デフォルト instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか ("1" で有効)
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値（％）

※ .env ファイル読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して行われます。既存の OS 環境変数は保護されます。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

注意点 / 運用メモ
- process_priority: 起動時にプロセス優先度を high にしようとしますが、権限が足りない場合は警告ログを出してスキップします（psutil を使用）。
- stop フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution の手動停止に使用
  - data/kill.flag: KillSwitch が作成する停止フラグ（ExecutionEngine 停止用）
- DB マイグレーション: monitoring_db.init_monitoring_db() は必要なテーブルを冪等に作成し、既存スキーマにカラムがなければ ALTER TABLE で追加する処理を行います。
- LLM 呼び出しは外部 API（OpenAI）を使用するため、API キーとネットワーク環境の整備が必要です。API 失敗時は多くの箇所でフォールバック（0.0 スコア等）して例外を上位へ伝播しない設計になっていますが、運用方針は注意してください。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他発注関連モジュール: broker_factory, execution_engine, order_repository, ...)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - data/ (実行時に使用されることが多いディレクトリ、DB・フラグファイル等を保存)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper trading 用)
    - kabusys.duckdb (DuckDB)

（上記は主なファイルの抜粋です。実際のリポジトリには他の補助モジュールや実装ファイルがあります）

---

サンプル .env（プロジェクトルート）
例:
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
MONITOR_POLL_INTERVAL=60

---

開発・拡張のヒント
- DuckDB 接続を渡す設計のため、研究モジュールは副作用が少なくテストしやすいです（SQL + Python の組合せで計算）。
- AI モジュールは外部 API 呼び出しをラップしており、テストでは _call_openai_api を patch してモック可能です。
- ポートフォリオ構築やポジション算出は純粋関数群として実装されているため、単体テストのカバレッジが非常に高めやすい構造です。

---

不明点や追加してほしい内容があれば教えてください。設定例やデプロイ手順（systemd／Docker／コンテナ化）などのドキュメント化も対応します。