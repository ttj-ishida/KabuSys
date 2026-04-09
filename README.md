# KabuSys

日本株向けの自動売買 / 研究 / 監視ツールキット。  
DuckDB / SQLite をデータ基盤に、kabuステーション等のブローカーAPIや OpenAI を利用した補助機能を組み合わせて、シグナルの実行・ポートフォリオ構築・モニタリングを行うためのライブラリ群です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を提供します。

- 日次のファクター計算・特徴量探索（research）
- ポートフォリオ構築（銘柄選定・配分・株数決定）
- 実行エンジン（ExecutionEngine）によるシグナル受取→発注の自動化（ブローカー抽象化）
- 起動時リコンシリエーション（注文・ポジションの突合）
- ニュースを用いた LLM（OpenAI）ベースのセンチメント評価 & 市場レジーム判定（AI）
- 監視・アラート（LINE push）とダッシュボード（Streamlit）
- 監視ログ永続化（SQLite、MonitoringDB）

設計方針の特徴：
- 各種演算は可能な限り「純粋関数」か「DB読取＋計算」に分離し、実行ロジックとIOを分離。
- ルックアヘッドバイアス防止（target_date を明示して履歴のみを参照する実装）。
- 自動環境変数ローディング、冪等性を意識した DB 書き込みと失敗耐性。

---

## 主な機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上の prices_daily / raw_financials からファクター算出
  - calc_forward_returns / calc_ic / factor_summary：特徴量探索・IC 計算等
- portfolio
  - select_candidates / calc_equal_weights / calc_score_weights：候補選定・重み付け
  - calc_position_sizes：リスクベース・重みベースの株数計算（単元丸め・上限・aggregate cap）
  - apply_sector_cap / calc_regime_multiplier：セクター集中制限・レジーム乗数
- execution
  - ExecutionEngine：シグナル処理（Gate1〜3）と WebSocket ドレインループ
  - OrderManager / Reconciler：注文状態遷移管理、起動時リコンシリエーション
  - broker_api：ブローカー用データモデル・Protocol と例外定義
- ai
  - news_nlp.score_news：ニュースを集約して OpenAI に送り、銘柄別センチメントを ai_scores に書き込み
  - regime_detector.score_regime：ETF MA とマクロニュース LLM を合成して market_regime を決定
- monitoring
  - MonitoringDB + MonitoringEngine：監視ログ永続化とポーリングエンジン
  - SystemMonitor / TradeMonitor / RiskMonitor：システム・注文・リスク監視
  - AlertManager：LINE Push による通知
  - streamlit_dashboard.py：監視ダッシュボード（Streamlit）

---

## セットアップ手順

前提：Python 3.10 以上（型記法に | を利用しているため）。プロジェクトルートには通常 `.git` または `pyproject.toml` があり、自動的に .env を読み込みます。

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb openai requests psutil streamlit

   ※ 実行に使うブローカークライアント等は別途必要（本リポジトリ外）。requirements.txt がある場合はそちらを利用してください。

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local があれば優先して上書き）。自動ロードはプロジェクトルートが見つからない場合スキップされます。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

   例 `.env`（必要なものだけ抜粋）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   KILL_FLAG_CLEAR_ON_START=0
   ```

   重要:
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須で未設定だと Settings で例外が出ます。
   - OPENAI_API_KEY は ai.score_news / score_regime を使う際に必要です（引数で上書き可能）。

5. Monitoring DB 初期化（SQLite）
   - Python REPL などで MonitoringDB.init_monitoring_db を呼ぶか、MonitoringEngine の利用前に init を実行してください。
   - 例:
     ```py
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

---

## 使い方（代表的な実行例）

- DuckDB を使ったファクター計算（research）
  ```py
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  print(len(res), res[:3])
  ```

- ニュースセンチメントの計算と ai_scores への書き込み
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を渡すか環境変数 OPENAI_API_KEY を設定する
  n_written = score_news(conn, date(2026, 3, 20), api_key=None)
  print("書き込み銘柄数:", n_written)
  ```

- レジーム判定（market_regime への書き込み）
  ```py
  from kabusys.ai.regime_detector import score_regime
  # score_regime(conn, target_date, api_key=None)
  ```

- 監視ダッシュボード（Streamlit）
  実行コマンド（ソース内に説明あり）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- MonitoringEngine（ポーリング）
  - MonitoringEngine を組み立てて run() を呼びます（例では AlertManager, SystemMonitor, TradeMonitor, RiskMonitor を注入）。
  - run() は KeyboardInterrupt までポーリングします。テスト用に run_once() が利用可能。

- ExecutionEngine（実取引セッション）
  - ExecutionEngine.run_session() がセッション全体のエントリ。
  - 実行には BrokerAPI 実装、OrderRepository、OrderManager、RiskManager、DuckDB 接続などを注入する必要があります。
  - kill.flag を利用した外部停止、PID ファイルの管理、起動時のリコンシリエーションに対応。

---

## 設定と環境変数（主なもの）

- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を探索）で `.env` と `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- Settings から参照される主要環境変数
  - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
  - KABU_API_PASSWORD — kabuステーション API（必須）
  - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
  - OPENAI_API_KEY — OpenAI（ai モジュールで使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager（LINE通知）
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_FILL_MODE — paper trading のモード（instant|partial|never|reject）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite パス
  - PID_FILE_PATH / KILL_FLAG_PATH — デフォルトのファイルパス
  - KILL_FLAG_CLEAR_ON_START — 1 にすると起動時に kill.flag を自動でクリア
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
  - KABUSYS_ENV — development | paper_trading | live
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys 配下のファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理（.env 自動ロード）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・スケーリング
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value ファクター
    - feature_exploration.py       — 将来リターン・IC・統計
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース→LLMセンチメント→ai_scores 書込
    - regime_detector.py           — MA + マクロLLM によるレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite スキーマ + MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                — Broker Protocol / データモデル / 例外
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - ... (order_repository, order_record 等が別ファイルとして存在する前提)

その他: data/（DB ファイル等。デフォルトパスは Settings に定義）

---

## 運用上の注意

- OpenAI 呼び出しはネットワーク/課金要因があるため、API キーの管理とレート制御に注意してください。AI モジュールは 429 / タイムアウト / 5xx を再試行する実装がありますが、失敗時はフォールバックして安全に継続する設計です。
- 実取引モード（live）での稼働前に paper_trading モードで十分なテストを行ってください。PAPER_FILL_MODE 等で挙動を調整できます。
- kill.flag / PID ファイルによる外部制御を取り入れており、起動時に既存 kill.flag があると起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 の場合はクリアして起動可能）。
- MonitoringDB のスキーマ変更時のマイグレーション処理が一部実装されていますが、重要な DB 操作ではバックアップを推奨します。

---

## 開発・拡張

- 各モジュールは依存を最小化して設計されているため、カスタム BrokerAPIProtocol 実装を差し替えれば複数ブローカーに対応できます。
- ポートフォリオ設計（PortfolioConstruction.md 相当）に合わせて position_sizing のパラメータや lot_size、cost_buffer を調整してください。
- research モジュールは DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）に依存します。ETL パイプラインでこれらのテーブルを正しく作成してください。

---

必要であれば、README に以下の追記を作成します：
- より詳細な実行例（ExecutionEngine の組み立て例）
- 必要なテーブルスキーマ（DuckDB 側）
- CI / テストの実行方法
- 開発フロー・コード規約

ご希望があれば追加で記載します。