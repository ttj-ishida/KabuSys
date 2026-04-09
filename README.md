# KabuSys

バージョン: 0.1.0

日本株自動売買システムのライブラリ群（研究・ポートフォリオ構築・発注エンジン・監視・AI 補助）。  
このリポジトリは、Signal → Portfolio → Execution の流れ、および監視/アラートやニュース NLP を含む補助機能を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群です。

- DuckDB 上の時系列価格・財務データからファクターを計算し、銘柄選定を行う（research）。
- 等金額・スコア加重・リスクベースなどの配分ロジックでポートフォリオ候補の重み・発注数量を算出する（portfolio）。
- ブローカー API 抽象（BrokerAPIProtocol）を通じて注文作成・送信・同期を行う実行エンジン（execution）。
- システム/注文/リスク監視・LINE 通知・ダッシュボードを提供する監視モジュール（monitoring）。
- ニュース記事から LLM を用いた銘柄単位のセンチメントスコア算出（AI 関連）。

設計方針の特徴:
- 多くの関数は純粋関数（DB の読み取りのみ）でユニットテストしやすく実装。
- ルックアヘッドバイアス防止のため、日付の扱いに注意した実装。
- OpenAI 呼び出し等は失敗時に安全にフォールバックする挙動。

---

## 主な機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily/raw_financials を用いたファクター計算
  - calc_forward_returns / calc_ic / factor_summary：将来リターン・IC 計算・統計サマリー
- portfolio
  - select_candidates：シグナルから候補抽出
  - calc_equal_weights / calc_score_weights：配分重み算出
  - calc_position_sizes：発注株数算出（risk_based, equal, score）
  - apply_sector_cap / calc_regime_multiplier：セクター制限・レジーム乗数
- execution
  - ExecutionEngine：Signal Queue Pull 型発注エンジン（リコンシリエーション・WebSocket ドレイン等）
  - OrderManager / Reconciler：注文の状態遷移・再同期ロジック
  - BrokerAPIProtocol：ブローカー実装用のプロトコル定義（抽象）
- ai
  - news_nlp.score_news：ニューステキストを LLM で評価して ai_scores テーブルへ保存
  - regime_detector.score_regime：ETF とマクロニュースを組合せて market_regime を判定
- monitoring
  - MonitoringDB / init_monitoring_db：SQLite 監視 DB の初期化・操作
  - SystemMonitor / TradeMonitor / RiskMonitor：定期チェック・アラート記録
  - AlertManager：LINE Push 通知（クールダウン管理）
  - streamlit_dashboard：Streamlit ベースの監視ダッシュボード

---

## セットアップ手順

1. Python バージョン
   - Python 3.9+ 推奨（コード内 typing 構文に依存）

2. リポジトリをクローン
   - git clone <リポジトリ URL>
   - cd <repo>

3. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存関係をインストール
   - pip install -U pip
   - 必要な主要パッケージ例：
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit
   - 例:
     - pip install duckdb openai requests psutil streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を実行）

5. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
   - .env の読み込み順と振る舞い:
     - OS 環境変数 > .env.local（上書き） > .env（未設定キーのみセット）
     - `.env.local` は `.env` を上書き（override=True）しますが、OS の環境変数は保護されます。

6. 初期 DB（監視用）作成（例）
   - Python REPL やスクリプトから:
     - import sqlite3
     - from kabusys.monitoring.monitoring_db import init_monitoring_db
     - conn = sqlite3.connect("data/monitoring.db")
     - init_monitoring_db(conn)

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須な機能がある場合）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（default: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（AlertManager）
- LINE_USER_ID: LINE Push 送信先ユーザ ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH: Paper Trading 関連
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視・停止フラグ関連
- KABUSYS_ENV: "development" | "paper_trading" | "live"
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

（コードの settings クラスが詳細なデフォルト値とバリデーションを提供）

---

## 使い方（代表的な例）

- Streamlit 監視ダッシュボード
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開く（例中）

- 監視 DB 初期化
  - Python:
    - import sqlite3
    - from kabusys.monitoring.monitoring_db import init_monitoring_db
    - conn = sqlite3.connect("data/monitoring.db")
    - init_monitoring_db(conn)

- ニュース NLP バッチ実行（ai_scores への書き込み）
  - Python から呼び出す例:
    - import duckdb, datetime
    - from kabusys.ai.news_nlp import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - date = datetime.date(2026, 3, 20)
    - score_news(conn, date, api_key="sk-...")

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="sk-...")

- ファクター / 研究機能
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = calc_momentum(conn, date(2026,3,20))

- ExecutionEngine（本番用フロー）
  - ExecutionEngine は BrokerAPIProtocol を具象実装した broker、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを受け取って動作します。簡易フロー:
    - broker = YourBrokerImplementation(...)
    - repo = OrderRepository(sqlite_conn)
    - order_manager = OrderManager(broker, repo)
    - risk_manager = RiskManager(...)
    - engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=...))
    - engine.run_session()
  - 注意: 実際のブローカー実装（送受信 API）や orders DB のセットアップが必要です。

- MonitoringEngine（ポーリング）
  - from kabusys.monitoring import MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager
  - engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(Path("data/kill.flag")), alert_manager=AlertManager(...))
  - engine.run()  # Ctrl-C で停止

---

## 注意点 / 実運用上のヒント

- OpenAI 呼び出しや外部 API はエラー時にフォールバックする実装ですが、API キー未設定時は明確に例外を出す箇所があります（score_news / score_regime）。
- kill.flag / PID ファイルによりプロセスの停止や残留検知を行います。デプロイ時は適切なファイルパスと権限を確認してください。
- .env のパースロジックはシェル風の export KEY=val、引用符やインラインコメントにも対応しています。ただし極端なケースは考慮外の可能性があるため .env の書式はシンプルに保つことを推奨します。
- Paper Trading 用設定や fill_mode（instant|partial|never|reject）によりブローカーの挙動を模擬できます。開発・検証時に利用してください。
- DuckDB / SQLite のスキーマはコード（SELECT/INSERT 参照箇所）に依存します。既存 DB を用いる場合はスキーマ互換性を確認してください。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py  (version)
  - config.py  (環境変数設定読み込み & Settings)
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
    - broker_api.py
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - (その他 order_repository, order_record, risk_manager 等の実装ファイル が想定)
  - (その他: data pipeline / stats などのモジュールが存在)

---

## 貢献 / テスト

- 新機能や修正は PR を通じてお願いします。ユニットテストの追加を歓迎します。
- LLM など外部 API を叩く機能はモック化してテストすることを推奨します（コード中にテスト用の patch ポイントが明示されています）。

---

何か追加したいセクション（例: API ドキュメント、サンプル .env.example、CI 設定など）があれば指示してください。README を拡張して具体的なコマンド例やサンプル設定ファイルを追加できます。