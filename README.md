# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリです。ポートフォリオ構築、ポジションサイジング、リスク管理、監視、LLM を使ったニュースセンチメント評価などのコンポーネントを提供します。

主な設計方針:
- 各モジュールは可能な限り純粋関数（副作用を持たない）またはデータ永続化層とビジネスロジックを分離
- DuckDB / SQLite をローカル DB に使う（本番の発注 API とは分離）
- OpenAI（gpt-4o-mini）を用いた自然言語処理機能を組み込めるが、API 失敗時はフェイルセーフで継続する設計
- 自動環境変数読み込み（.env / .env.local）をサポート

## 機能一覧
- ポートフォリオ構築
  - シグナル候補選定（score / rank ベース）
  - 等配分・スコア加重配分の重み計算
  - セクター集中制限適用
  - レジーム乗数（bull / neutral / bear）計算
- ポジションサイジング
  - リスクベース / 比率ベースの株数決定
  - 単元株（lot）丸め、利用可能現金に応じたスケーリング
- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily, raw_financials テーブル参照）
  - 将来リターン、IC（Spearman）計算、統計サマリー
- AI（LLM）連携
  - ニュース記事をまとめて OpenAI へ送信し、銘柄別センチメントを ai_scores テーブルへ書き込み（score_news）
  - マクロニュース + ETF MA200 乖離を使った市場レジーム判定（score_regime）
  - API 呼び出しはリトライ・バックオフとレスポンスバリデーションを実装
- 実行エンジン / 注文管理
  - OrderManager / OrderRepository / Reconciler によるクラッシュ耐性のある発注フロー
  - ExecutionEngine による信号プル & WebSocket push ドレイン（kill flag / Gate チェック等）
- 監視
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE push）
  - Streamlit ダッシュボード（read-only）

## 必要条件（想定）
- Python 3.10+
- ライブラリ（例）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit
- SQLite（標準ライブラリで利用可能）
- ネットワークアクセス（OpenAI 利用時）

requirements.txt が無い場合は上記をインストールしてください:
pip install duckdb openai requests psutil streamlit

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell)
3. 依存パッケージをインストール
   pip install duckdb openai requests psutil streamlit
4. 環境変数／.env を用意
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
5. monitoring DB 初期化（SQLite 接続を渡す）
   Python で:
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   import sqlite3
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)

## 環境変数（.env）例
プロジェクトは .env / .env.local / OS 環境変数から設定を読み込みます。主要なキー例:

.env.example:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant     # instant|partial|never|reject
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0  # 1 にすると起動時に既存 kill.flag をクリア
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0
KABUSYS_ENV=development     # development|paper_trading|live
LOG_LEVEL=INFO
LINE_CHANNEL_ACCESS_TOKEN=   # LINE 通知が必要なら設定
LINE_USER_ID=

注意:
- Settings クラス経由で各値を取得できます（kabusys.config.settings）
- 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定だと ValueError が出ます

## 使い方（主要エントリ / サンプル）

- DuckDB 上でファクター計算（calc_momentum 等）
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  # records: list of dict with keys like "code", "mom_1m", ...

- ニュースセンチメントスコアの生成（OpenAI API が必要）
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  # ai_scores テーブルへ書き込まれる（書き込み件数を返す）

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026,3,20), api_key="sk-...")

- 監視ダッシュボード（Streamlit）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringEngine（ポーリング監視）
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager
  import sqlite3, duckdb
  monitoring_conn = sqlite3.connect("data/monitoring.db")
  duck_conn = duckdb.connect("data/kabusys.duckdb")
  system = SystemMonitor(monitoring_conn, duck_conn)
  # TradeMonitor は OrderRepository が必要（テスト時はモック）
  # RiskMonitor は MonitoringDB を使って起動
  engine = MonitoringEngine(system, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(Path("data/kill.flag")), alert_manager=AlertManager(token, user_id))
  engine.run()  # 例: 永続実行（KeyboardInterrupt で停止）

- ExecutionEngine（発注セッションの実行）
  ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続等が必要です。テスト環境で動かす場合はモックを渡して run_session() を呼びます。

  主要メソッド:
  - ExecutionEngine.run_session() — 本番セッション実行（PID ファイル / kill.flag 管理含む）
  - ExecutionEngine._process_signals()／_drain_push_queue() — テスト時に個別呼び出し可能

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / .env 自動ロード、Settings（アプリ設定）
- portfolio/
  - portfolio_builder.py — 候補選定、等重/スコア重み計算
  - position_sizing.py — 株数計算、aggregate cap
  - risk_adjustment.py — セクター上限、レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value 計算
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py — ニュース記事をまとめて OpenAI へ投げる、ai_scores への書込み
  - regime_detector.py — マクロニュース + ETF MA200 による regime 判定
- monitoring/
  - monitoring_db.py — SQLite スキーマ作成・MonitoringDB ラッパ
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - alert_manager.py — LINE push 通知
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 監視ポーリングエンジン
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - broker_api.py — Broker API プロトコル定義、データモデル、例外
  - order_manager.py — Order State Machine の外向け API（create/send/sync/cancel）
  - reconciler.py — 起動時リコンシリエーション（OrderSent などの回復）
  - execution_engine.py — Signal Queue Pull 型発注エンジン
  - ...（その他 OrderRepository 等は同階層に存在する想定）
- monitoring, portfolio, research, ai それぞれ __init__.py を備え、外部から利用しやすい API を提供

## 開発メモ / 注意点
- .env パーサはシェル形式の export KEY=val、コメント、クォート、エスケープに対応しています。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml の存在）を基にしてファイルを探索します。プロジェクトルートが見つからない場合は自動ロードをスキップします。
- Settings クラスは値のバリデーション（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）を行います。
- OpenAI を使う機能は API レート制限や一時エラーを考慮したリトライ実装が入っていますが、API キーの管理はユーザ側で行ってください。
- 実際のブローカー連携を行うには BrokerAPIProtocol の実装が必要です。テストやCIではモック実装を使用してください。
- DuckDB / SQLite テーブルスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）は別途準備する必要があります（この README ではスキーマ定義を記載していませんが、research や ai モジュールの SQL を参照してください）。

---

問題点や改善案、使い方の追加サンプルが必要であれば教えてください。README の英語版や具体的な DB スキーマ／サンプルデータ作成手順も作成できます。