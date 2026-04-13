# KabuSys

KabuSys は日本株自動売買システムのモジュール群です。発注・リコンシリエーション、監視（モニタリング）、ポートフォリオ構築、リサーチ（ファクター計算）、ニュース NLP による AI スコアリングなどの機能を備えたモジュール設計になっています。

本 README はコードベース（src/kabusys 以下）の主要コンポーネント、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（実行例）
- 主要環境変数
- ディレクトリ構成

---

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株自動売買システム（発注エンジン、監視、リスク管理、ポートフォリオ構築、リサーチ、ニュース NLP など）
- 設計方針（コード内コメントより）
  - 本番データ（DuckDB / SQLite）と Paper Trading を分離
  - ルックアヘッドバイアスを避ける（date.today()/datetime.now() の無制限利用を避ける実装）
  - フェイルセーフ（外部 API 失敗時のフォールバック）
  - テスト容易性（依存注入・純粋関数化された計算部分）

---

機能一覧
- 実行エンジン
  - run_execution.py: ExecutionEngine を起動し、ブローカーとやり取りして発注処理を行う
  - Paper Trading モードでは MockBrokerClient を使用し、DB を分離
- 監視（Monitoring）
  - run_monitoring.py: SystemMonitor のポーリングループを起動
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor をまとめて定期実行、アラート送信、Kill Switch 評価
  - SystemMonitor: プロセス生存・リソース使用率・データ鮮度を監視
  - TradeMonitor: 注文滞留や約定異常を検出
  - RiskMonitor: ドローダウン・ポジション数上限を監視
  - AlertManager: LINE Messaging API を使ったプッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード: 監視データを可視化（streamlit run）
- ポートフォリオ構築
  - 候補選定、重み計算（等配分・スコア加重）
  - セクター制約の適用、レジーム乗数
  - 株数決定（risk_based / equal / score）、単元株丸め、aggregate cap のスケーリング
- リサーチ
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 特徴量探索（将来リターン、IC、統計サマリー）
  - DuckDB 上の prices_daily / raw_financials を参照して計算
- AI（ニュース NLP / レジーム判定）
  - news_nlp.score_news: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとにセンチメントを算出し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA 乖離とマクロニュースセンチメントを合成して market_regime テーブルへ保存
  - OpenAI API の呼び出しはリトライ・バックオフ等を実装、失敗時は安全にフォールバック
- ツール
  - tools.paper_verification_report: Paper Trading DB を集計して検証レポートを標準出力に出す
- ユーティリティ
  - config.Settings: 環境変数/.env 読み込みとアプリ設定
  - process_priority: プロセス優先度や CPU affinity 設定ユーティリティ
  - monitoring_db: SQLite ベースの監視 DB 操作ラッパ（テーブル生成／マイグレーション含む）

---

セットアップ手順（ローカル開発向け）
前提
- Python 3.10 以上（型ヒントに | を使用）
- git が使える環境

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成と有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合は下記をインストールしてください（コードで使用されている主要ライブラリ）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

4. .env ファイル（任意）
   - プロジェクトルートに .env または .env.local を置くと Settings が自動読み込みします（既存の OS 環境変数は上書きされません）。
   - 重要な環境変数例（.env.example を参考に作成してください）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LINE_CHANNEL_ACCESS_TOKEN=... (LINE 通知を使う場合)
     - LINE_USER_ID=...
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60  (run_monitoring のポーリング間隔を秒で上書き)

5. データベース
   - monitoring 用 SQLite は run_monitoring.py/run_execution.py 起動時に init_monitoring_db() により必要テーブルが自動作成されます（monitoring DB 用）。
   - DuckDB（prices_daily / raw_financials / raw_news 等）はリサーチや AI 機能で参照されます。これらのテーブルは事前に作成・投入しておく必要があります（外部データパイプラインで準備）。

---

使い方（実行例）
- 実行エンジン（発注）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により動作モードを切替:
    - paper_trading: MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - live: 実ブローカーを使用（環境変数でブローカー設定が必要）
- 監視ループ
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定する例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 引数 --db に監視用 SQLite のパスを渡す（read-only URI が使用されます）
- AI 機能（プログラムから利用）
  - ニューススコア算出:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

注意点 / 運用上のポイント
- Paper Trading と本番 DB は分離されています（PAPER_TRADING_SQLITE_PATH を参照）。
- Kill Switch: risk モジュールで判定されると Settings.kill_flag_path（デフォルト data/kill.flag）にフラグを書き込み、ExecutionEngine 側で停止させる仕組みです。
- PID ファイル: ExecutionEngine は pid_file（デフォルト data/execution.pid）を使ってプロセス監視・stale PID の検出を行います。
- OpenAI API を使う機能は OPENAI_API_KEY が必要です。失敗時は安全にフォールバックする実装ですが、API キーがない場合は呼び出し前に ValueError が発生します。
- streamlit を使う場合はユーザー環境で streamlit をインストールしておく必要があります。

主要環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper trading の fill 動作（instant|partial|never|reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視閾値）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信用）

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - process_priority.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager, Reconciler, OrderRepository 等の実装ファイルが存在)
    - order_manager.py
    - reconciler.py
    - ...（ブローカー関連やエンジン構成ファイル）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/ (外部データ/DB はここに配置する想定)
    - (data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db 等)

（上記はコードベースから抜粋した主要モジュール一覧です）

---

よくある質問（FAQ）
- Q: Paper Trading と本番はどのように分離されていますか？
  - A: KABUSYS_ENV=paper_trading の場合、Execution 起動時に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使います。MockBrokerClient が用いられ、実ブローカーにアクセスしません。

- Q: 監視（Monitoring）の初期テーブルは自動作成されますか？
  - A: はい。run_monitoring / run_execution 起動時に init_monitoring_db() が呼ばれ、必要テーブルと簡単なマイグレーションを行います。

- Q: DuckDB のテーブル（prices_daily など）はどう用意すればよいですか？
  - A: リサーチ・AI 機能は DuckDB 上の特定テーブルを参照します。これらのデータは外部のデータパイプラインや別スクリプトで準備してください（本 README ではデータ注入の手順は含みません）。

---

開発・運用上の注意
- 本リポジトリのコードは実運用を想定した設計になっています。実運用で使う際はブローカー API キーや資金管理、リスク制御、テストの徹底を行ってください。
- OpenAI など外部 API を呼ぶ箇所はレート制限・コストの観点で注意が必要です。設定やログを確認して運用してください。

---

貢献
- バグ報告や改善提案は Issue を立ててください。プルリクエストは歓迎します。

---

以上。必要であれば README に含める具体的なコマンド集（systemd サービス定義例、docker-compose 例、requirements.txt の雛形など）を追加作成します。どの情報を補完しますか？