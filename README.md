# KabuSys — README (日本語)

概要
-----
KabuSys は日本株の自動売買に向けて設計された小規模なフレームワークです。  
主な役割は以下のとおりです。

- 量的リサーチ（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定・重み付け・リスク調整・サイズ算出）
- 発注・状態管理（OrderManager / ExecutionEngine）
- 監視・アラート（監視 DB、LINE 通知、ダッシュボード）
- AI 支援（ニュース NLP によるセンチメント評価、マクロレジーム判定）

設計方針としては「純粋関数」「DB 分離」「ルックアヘッドバイアス防止」「フェイルセーフ」を重視しており、本番ブローカー/API 呼び出し部分は明確に分離されています。

主な機能
---------
- 環境変数管理（.env / .env.local の自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- ファクター計算（モメンタム、ボラティリティ、バリュー等） — duckdb を使って prices_daily / raw_financials を参照
- ポートフォリオ構築
  - 候補選定（スコア順）
  - 重み計算（等分、スコア加重）
  - セクター上限適用、レジームに応じた資金乗数
  - ポジションサイズ計算（リスクベース・等分・スコアベース、単元丸め、aggregate cap）
- AI モジュール
  - ニュースセンチメント（OpenAI を利用して raw_news → ai_scores へ書込）
  - レジーム判定（ETF の MA200 とマクロニュースを合成）
- 発注/実行系
  - Broker API 抽象（Protocol）・データモデル・例外
  - OrderManager（状態遷移、安全な永続化フロー）
  - ExecutionEngine（シグナルループ + push ドレイン、kill flag、reconciliation）
  - Reconciler（起動時の自動復旧）
- 監視系
  - MonitoringDB（SQLite ベースの永続層、テーブル定義・マイグレーション含む）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE 送信）
  - streamlit ダッシュボード（読み取り専用）

セットアップ手順
--------------
前提
- Python 3.10 以上（型注釈の | 型を使用しているため）
- Git

手順（例）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - requirements.txt があれば: pip install -r requirements.txt
   - 主要依存例（プロジェクト内で使用されているライブラリ）:
     - duckdb
     - openai
     - psutil
     - requests
     - streamlit
   例: pip install duckdb openai psutil requests streamlit
4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動で読み込まれます（.env.local は .env を上書き）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 代表的な環境変数の例（後述の .env.sample を参照）
5. DB 初期化（監視用 SQLite）
   - Python REPL またはスクリプトで init_monitoring_db を呼び出してテーブルを作成します。
     例:
       import sqlite3
       from kabusys.monitoring.monitoring_db import init_monitoring_db
       conn = sqlite3.connect("data/monitoring.db")
       init_monitoring_db(conn)
6. DuckDB / データ配置
   - データ用 duckdb ファイル（デフォルト: data/kabusys.duckdb）。prices_daily / raw_financials / raw_news 等のテーブルはリサーチ・AI モジュールで参照されます。必要に応じて ETL を用意してください。

環境変数（.env）サンプル
-------------------------
以下は主要なキー例です。プロジェクトに合わせて .env.example を参照して整備してください。

例 (.env):
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
KABU_API_BASE_URL=http://localhost:18080/kabusapi
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_FILL_MODE=instant
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（主要な呼び出し例）
-------------------------

注意: ここでは代表的な使い方と関数を紹介します。実稼働では broker 実装や DB スキーマ、ETL の整備が必要です。

1) 設定読み出し
- settings オブジェクトから環境設定を取得できます。
  例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
    duckdb_path = settings.duckdb_path

2) ファクター計算（リサーチ）
- DuckDB 接続を与えてファクターを計算します。
  例:
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    conn = duckdb.connect("data/kabusys.duckdb")
    date0 = date(2026, 3, 20)
    momentum = calc_momentum(conn, date0)
    vol = calc_volatility(conn, date0)
    value = calc_value(conn, date0)

3) ニュース NLP スコアリング（AI）
- OpenAI API キーを OPENAI_API_KEY に設定するか、引数で渡します。
  例:
    from kabusys.ai import score_news
    from datetime import date
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, date(2026,3,20))  # OPENAI_API_KEY が環境変数にある前提

4) レジーム判定
  例:
    from kabusys.ai import score_regime  # 実装は ai.regime_detector.score_regime
    score_regime(conn, date(2026,3,20))

5) ポートフォリオ構築
- 候補選定・重み計算・サイズ計算の連携例
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
    candidates = select_candidates(buy_signals, max_positions=10)
    weights = calc_score_weights(candidates)
    sizes = calc_position_sizes(weights, candidates, portfolio_value=1_000_000, available_cash=700_000, current_positions={}, open_prices=price_map)

6) 監視系実行（1回だけ）
  例:
    import sqlite3, duckdb
    from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
    mon_conn = sqlite3.connect("data/monitoring.db")
    duck_conn = duckdb.connect("data/kabusys.duckdb")
    sys_mon = SystemMonitor(mon_conn, duck_conn)
    # TradeMonitor は OrderRepository のインスタンスが必要
    risk_mon = RiskMonitor(mon_conn)
    ks = KillSwitch(Path("data/kill.flag"))
    alert = AlertManager(settings.line_channel_access_token, settings.line_user_id)
    engine = MonitoringEngine(sys_mon, trade_monitor, risk_mon, interval_sec=60, kill_switch=ks, alert_manager=alert)
    engine.run_once()

7) Streamlit ダッシュボード
- 監視 DB を読み取り専用で表示します。
  実行例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

8) ExecutionEngine（発注セッション）
- 実稼働では BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、Reconciler 等を組み合わせて使います。テストではモックを渡して run_session() や run_once 系メソッドを実行して検証します。

ディレクトリ構成（抜粋）
--------------------
リポジトリの主要ファイル構成（src 以下のみ、抜粋）:

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - __init__.py
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
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
  - (その他: order_repository, order_record, risk_manager 等が存在する想定)
- research/ (上記)
- その他（data, strategy, etc. — パッケージ化のため __all__ に含まれます）

注意事項 / 運用上のポイント
---------------------------
- .env 読み込みはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行われます。テストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI モジュールは OpenAI API を使用します。トークンの管理とコストに注意してください。API 失敗時はフェイルセーフ（スコア 0.0 フォールバック等）を備えていますが、設定やリトライ方針を把握して運用してください。
- ExecutionEngine や OrderManager はブローカー側の実装（BrokerAPIProtocol）に強く依存します。実稼働前にサンドボックス／シミュレーション（Paper Trading）で十分に検証してください。
- 監視系は適切な権限で PID ファイルや kill.flag を管理します。kill.flag による起動拒否や自動クリアは settings.kill_flag_clear_on_start に依存します。

開発・テスト
------------
- 単体関数群（portfolio, research, monitoring_db 等）は副作用を抑えており、ユニットテストが書きやすい設計です。OpenAI 呼び出し部は _call_openai_api を patch することで外部呼び出しをモックできます。
- DuckDB / SQLite を組み合わせた統合テストではテスト用 DB を用意して差し替えてください。

ライセンス / 貢献
-----------------
（この README 生成対象コードのライセンス情報が提供されていないため、ここでは省略します。実プロジェクトでは LICENSE を明示してください。）

以上が KabuSys の概要・セットアップ・使い方のまとめです。必要であれば README をより具体的なコマンド例や requirements.txt のテンプレート、.env.example の完全版などで拡張します。どの部分を詳しく出力しますか？