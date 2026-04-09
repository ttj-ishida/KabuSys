KabuSys — README（日本語）
=======================

概要
----
KabuSys は日本株の自動売買 / リサーチ / 監視を目的とした軽量なコードベースです。  
主に以下の機能群を提供します。

- ポートフォリオ構築（候補選定・重み付け・株数算出・セクター制約）
- ファクター計算・特徴量探索（DuckDB を使用したオンチェーン計算）
- ニュースの LLM（OpenAI）によるセンチメントスコアリングおよび市場レジーム判定
- 実行エンジン（シグナルから発注、WebSocket プッシュ処理、リコンシリエーション）
- 監視（システム / 注文 / リスク監視）、LINE によるアラート送信、Streamlit ダッシュボード
- 環境変数 / .env 管理ユーティリティ

設計上のポイント
- DB（DuckDB / SQLite）経由での計算を優先し、本番ブローカー・発注 API や外部へは必要に応じて疎結合に実装しています。
- 自動ロードされる .env ロジック（プロジェクトルートの .env / .env.local）によりローカル設定を簡易化。
- LLM 呼び出し部分は堅牢化（バリデーション・リトライ・フェイルセーフ）しています。

主な機能一覧
----------------
- 設定管理: kabusys.config.Settings（.env / 環境変数自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- ポートフォリオ:
  - 候補選定: select_candidates
  - 重み計算: calc_equal_weights / calc_score_weights
  - リスク調整: apply_sector_cap / calc_regime_multiplier
  - ポジションサイジング: calc_position_sizes
- リサーチ:
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 将来リターン・IC・統計: calc_forward_returns, calc_ic, factor_summary, rank
- AI:
  - ニュース NLP: score_news（OpenAI API を使用して ai_scores に書き込み）
  - レジーム判定: score_regime（ETF 1321 の MA200 とマクロニュースを統合）
- 実行 / 発注:
  - Broker API 抽象（broker_api.Protocol）
  - Order 管理: OrderManager（create/send/sync/cancel）
  - ExecutionEngine（シグナル処理 / push ドレイン / kill switch / リコンシ）
  - Reconciler（起動時の状態復旧 / ポジション差分検知）
- 監視:
  - MonitoringDB（SQLite 永続化層）、MonitoringEngine（ポーリング集約）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

セットアップ手順
----------------
推奨 Python バージョン: 3.10 以上（型注釈に | を使用）

1. リポジトリをクローン
   - git clone ...（適宜置き換え）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Linux/macOS）
   - .venv\Scripts\activate（Windows）

3. 依存パッケージのインストール（requirements.txt がない場合の例）
   - pip install duckdb openai requests psutil streamlit

   例: requirements.txt の例
   - duckdb
   - openai
   - requests
   - psutil
   - streamlit

4. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml を基準）に .env, .env.local を作成できます。
   - 自動ロードの順序: OS 環境変数 > .env.local (override=True) > .env (override=False)
   - 自動ロードを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env.example（サンプル）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- OPENAI_API_KEY=...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0

使い方（主要な例）
------------------

設定の使用
- Python から設定を読む:
  from kabusys.config import settings
  token = settings.jquants_refresh_token

DuckDB / リサーチ系
- DuckDB コネクションを開き、ファクター計算を呼ぶ例:
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect('data/kabusys.duckdb')
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)

ニューススコアリング（AI）
- ai.news_nlp.score_news を呼んで ai_scores テーブルへ書き込む:
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")

レジーム判定
- ai.regime_detector.score_regime:
  from kabusys.ai.regime_detector import score_regime
  n = score_regime(conn, date(2026,3,20), api_key="sk-...")

監視 DB 初期化
- MonitoringDB スキーマ作成:
  import sqlite3
  from kabusys.monitoring import init_monitoring_db

  conn = sqlite3.connect('data/monitoring.db')
  init_monitoring_db(conn)

Streamlit ダッシュボード起動
- コマンド:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ExecutionEngine（本番的な起動）
- ExecutionEngine は BrokerAPI の実装、OrderRepository（SQLite）、RiskManager 等が必要です。  
  テスト時はモック実装を渡して run_session / run_once を使用してください。

監視エンジン（サンプル）
- MonitoringEngine を使って1回だけ実行（テスト）:
  from kabusys.monitoring import MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, MonitoringDB, AlertManager, KillSwitch
  import sqlite3, duckdb

  mconn = sqlite3.connect('data/monitoring.db')
  duck_conn = duckdb.connect('data/kabusys.duckdb')
  init_monitoring_db(mconn)
  system = SystemMonitor(mconn, duck_conn)
  trade = TradeMonitor(mconn, order_repo)  # order_repo は実装／モック
  risk = RiskMonitor(mconn)
  ks = KillSwitch(Path('data/kill.flag'))
  am = AlertManager(settings.line_channel_access_token, settings.line_user_id)
  engine = MonitoringEngine(system, trade, risk, interval_sec=60, kill_switch=ks, alert_manager=am)
  engine.run_once()  # 単発実行（ユニットテスト向け）

ディレクトリ構成
----------------
主要なファイルと役割（簡易ツリー）:

src/kabusys/
- __init__.py                        — パッケージ定義、バージョン
- config.py                          — 環境変数 / .env 自動ロード、Settings クラス
- portfolio/
  - __init__.py
  - portfolio_builder.py             — 候補選定・等重/スコア重み
  - position_sizing.py               — 株数計算（リスクベース・比率ベース）
  - risk_adjustment.py               — セクターキャップ・レジーム乗数
- research/
  - __init__.py
  - factor_research.py               — Momentum / Volatility / Value 計算
  - feature_exploration.py           — 将来リターン・IC・統計
- ai/
  - __init__.py
  - news_nlp.py                      — ニュース集約 → OpenAI でスコア化 → ai_scores へ書き込み
  - regime_detector.py               — ETF + マクロニュースで市場レジーム判定
- monitoring/
  - __init__.py
  - monitoring_db.py                 — SQLite テーブル定義・CRUD ラッパー
  - system_monitor.py                — システム状態・データ鮮度監視
  - trade_monitor.py                 — 注文滞留・約定異常監視
  - risk_monitor.py                  — ドローダウン・ポジション上限監視
  - kill_switch.py                   — フラグファイルによる停止信号
  - alert_manager.py                 — LINE Push 送信（クールダウン管理）
  - monitoring_engine.py             — 各監視を束ねるポーリングエンジン
  - streamlit_dashboard.py           — Streamlit ベースの監視ダッシュボード
- execution/
  - broker_api.py                    — Broker API のデータモデル・Protocol・例外
  - order_manager.py                 — Order 管理（DB と Broker の仲介）
  - order_repository.py              — （ファイルに見つかる）Order DB 操作（別実装が含まれる想定）
  - order_record.py                  — Order 状態遷移ロジック（別ファイル）
  - reconciler.py                    — 起動時リコンシリエーション
  - execution_engine.py              — シグナル→発注・push ドレインの実行エンジン
  - risk_manager.py                  — 発注前の Gate チェック（外部：未掲載ファイル）
- monitoring/...（上に説明）

注意点 / 運用上のヒント
-----------------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。配布版ではプロジェクトルートが見つからない場合は自動ロードをスキップします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を指定すると自動ロードを無効化できます（テストで便利）。
- OpenAI API を使う機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を必須とし、失敗時はフォールバックやスキップの挙動があります。実運用時はレート制限などに注意してください。
- MonitoringDB（SQLite）と DuckDB のパスは Settings で指定可能（環境変数 DUCKDB_PATH / SQLITE_PATH）。
- ExecutionEngine の run_session は実際の broker 実装（BrokerAPIProtocol）と OrderRepository が必要です。直接起動する前にローカル環境で十分にテストしてください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開きます。MonitoringEngine を稼働させてデータが蓄積されていることを確認してください。

貢献 / 開発
------------
- 各モジュールは単体でテストしやすいように依存注入（Conn / Broker / Repo / Client）を用いています。ユニットテストではモックを差し込み、KABUSYS_DISABLE_AUTO_ENV_LOAD を使用してください。
- ドキュメントや設計メモ（PortfolioConstruction.md 等）に従って実装が分割されています。新機能追加の際は既存の設計指針に従ってください。

ライセンス
---------
- このリポジトリのライセンス情報は付属ファイル（LICENSE 等）を参照してください（本 README には含まれていません）。

問い合わせ
----------
- 実装に関する質問やバグ報告はリポジトリの issue に投稿してください。README の補足やサンプル追加の要望も歓迎します。

以上。必要であれば、README に記載するサンプル .env.example や requirements.txt を具体化して追記します。どの形式（簡潔版 / 詳細版）を望むか教えてください。