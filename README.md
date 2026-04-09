# KabuSys

日本株自動売買プラットフォームのコアライブラリ（研究・ポートフォリオ構築・発注・監視・AI 補助）。  
このリポジトリは、DuckDB / SQLite を用いたデータ処理、kabu ステーション等のブローカー抽象、LLM を使ったニュース評価・レジーム判定、発注エンジンと監視基盤を含みます。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群を提供します。

- ファクター計算（モメンタム / ボラティリティ / バリュー等）と研究用ユーティリティ
- 銘柄選定・重み付け・ポジションサイズ計算（等分配・スコア加重・リスクベース）
- セクター集中制限や市場レジームに基づくリスク調整
- OpenAI を用いたニュースのセンチメントスコアリング（銘柄単位）
- ETF とマクロニュースを合成した市場レジーム判定（bull/neutral/bear）
- 発注エンジン（ExecutionEngine）・OrderManager・Reconciler 等の実運用ロジック
- ブローカー API 抽象（Protocol）に基づくクライアント層
- 監視のための SQLite 永続化層（MonitoringDB）と各種モニタ、LINE 通知用 AlertManager
- Streamlit ベースの監視ダッシュボード

設計方針として、外部 API 呼び出しや永続化を明確に分離し、テスト容易性とフェイルセーフを重視しています。

---

## 主な機能一覧

- kabusys.research
  - calc_momentum / calc_volatility / calc_value（DuckDB に対する純粋関数）
  - calc_forward_returns / calc_ic / factor_summary（特徴量評価・統計）
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes（リスクベース／等分配の株数算出）
  - apply_sector_cap, calc_regime_multiplier（セクター制約・レジーム乗数）
- kabusys.ai
  - news_nlp.score_news（OpenAI を使った銘柄別ニューススコア算出）
  - regime_detector.score_regime（ETF MA + マクロニュースでレジーム推定）
- kabusys.execution
  - ExecutionEngine（シグナル読み込み→発注→WebSocket ドレインループ）
  - OrderManager / Reconciler / RiskManager（発注状態管理、再同期）
  - broker_api：OrderRequest / OrderStatus / Position 等のデータモデルと例外
- kabusys.monitoring
  - MonitoringDB（SQLite テーブル作成・CRUD）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - streamlit_dashboard（監視用 UI）

---

## セットアップ手順

前提
- Python 3.10 以上（`X | Y` 型ヒントを使用しているため）
- DuckDB, OpenAI SDK, requests, psutil, streamlit 等の依存

1. リポジトリをクローンして作業ディレクトリへ移動
   git clone <repo-url>
   cd <repo>

2. 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate

3. 必要パッケージをインストール（例）
   pip install duckdb openai requests psutil streamlit

   ※プロジェクトが pyproject.toml を持つ場合:
   pip install -e .

4. データディレクトリ作成
   mkdir -p data

5. 監視用 SQLite DB の初期化
   python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); conn.close()"

6. 環境変数（.env）を用意
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が自動で探索され、`.env` → `.env.local` の順で読み込まれます（OS 環境変数が優先され、`.env.local` は上書きされます）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN : （必須）J-Quants トークン
- KABU_API_PASSWORD : （必須）kabu ステーション API パスワード
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN : LINE 通知用トークン（AlertManager）
- LINE_USER_ID : LINE 通知先ユーザー ID
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE : Paper Trading の fill_mode（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH : ExecutionEngine が書き込む PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH : Kill フラグファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START : 起動時に kill.flag を自動クリアするなら "1"
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視閾値
- KABUSYS_ENV : 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL : ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

.env の例（簡易）
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な例）

- DuckDB 接続・リサーチ関数の実行（例: モメンタム計算）
  python - <<'PY'
  import duckdb, datetime
  from kabusys.research import calc_momentum
  conn = duckdb.connect('data/kabusys.duckdb')
  res = calc_momentum(conn, datetime.date(2026, 3, 20))
  print(len(res))
  PY

- ニューススコア算出（OpenAI API キーが必要）
  python - <<'PY'
  import duckdb, datetime, os
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect('data/kabusys.duckdb')
  os.environ['OPENAI_API_KEY'] = 'sk-...'
  n = score_news(conn, datetime.date(2026, 3, 20))
  print('scored', n, 'codes')
  PY

- レジームスコア算出
  python - <<'PY'
  import duckdb, datetime, os
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect('data/kabusys.duckdb')
  os.environ['OPENAI_API_KEY'] = 'sk-...'
  score_regime(conn, datetime.date(2026,3,20))
  PY

- Streamlit 監視ダッシュボードの起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- 監視 DB の初回作成（再掲）
  python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; init_monitoring_db(sqlite3.connect('data/monitoring.db'))"

- ExecutionEngine（本番想定）  
  実運用では Broker API 実装（BrokerAPIProtocol 準拠）、OrderRepository、RiskManager、Reconciler などを組み合わせて実行します。テスト時はモック実装を使って `ExecutionEngine.run_session()` を呼び出すことでセッション処理を確認できます。

注意点
- OpenAI 呼び出し周りはリトライ / フェイルセーフが組み込まれていますが、API キーの管理やレート制限に注意してください。
- self-contained なテストを行う場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境の自動読み込みを抑制できます。
- news_nlp._call_openai_api / regime_detector._call_openai_api はテスト時にパッチで差し替え可能です。

---

## ディレクトリ構成（主要ファイル）

src/
  kabusys/
    __init__.py
    config.py
    # ポートフォリオ関連
    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    # 研究・特徴量
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    # AI 関連（OpenAI 呼び出し）
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    # 実行・発注関連
    execution/
      broker_api.py
      execution_engine.py
      order_manager.py
      reconciler.py
      # （その他: order_repository, order_record, risk_manager などが想定される）
    # 監視関連
    monitoring/
      __init__.py
      monitoring_db.py
      monitor*.py (system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py)
      alert_manager.py
      kill_switch.py
      streamlit_dashboard.py
    # （data パッケージや strategy, execution など他もプロジェクト内に存在する想定）

---

## 開発・テストメモ

- 設定読み込みは project root（.git または pyproject.toml）を基準に `.env` / `.env.local` を自動読込します。パス解決は config._find_project_root() により行われ、CWD に依存しません。
- テストでは OpenAI 実体呼び出しをモックし、news_nlp._call_openai_api / regime_detector._call_openai_api を patch してください。
- Paper Trading モードは設定 `KABUSYS_ENV=paper_trading` を使い、PAPER_FILL_MODE 等で挙動を制御できます。
- 重要な挙動（kill.flag の扱い、PID 書き込み、再起動時のリコンシリエーション）は設定や flag により制御できます。運用時の安全弁として KillSwitch / Reconciler の挙動を理解してください。

---

README はここまでです。必要であれば「実行例のスクリプト雛形」「.env.example の完全版」「運用フロー図」などを追加で作成します。どれが欲しいか教えてください。