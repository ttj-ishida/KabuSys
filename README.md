# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視機能を提供する軽量なライブラリ／フレームワークです。DuckDB / SQLite をデータ層に使い、kabuステーション等のブローカー API や OpenAI を組み合わせて、ファクター計算・ポートフォリオ構築・発注エンジン・監視ダッシュボード・ニュース NLP（LLM）によるセンチメント集計等の機能を提供します。

本 README はこのリポジトリのコードベース（src/kabusys 以下）についての概要、機能、セットアップ、使い方、ディレクトリ構成をまとめたものです。

前提
- Python 3.10 以上（PEP 604 の型注記（A | B）などを使用しているため）
- 基本的に標準ライブラリ中心だが、外部パッケージ（下記）を利用します

主要外部依存（代表例）
- duckdb
- openai
- requests
- psutil
- streamlit
（必要に応じて `pip install` で導入してください。プロジェクトに requirements.txt があればそれを利用します）

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要ユースケース）
- 環境変数（.env）
- ディレクトリ構成

---

プロジェクト概要
- DuckDB / SQLite を用いたデータ集計・永続化と、ブローカー API を通じた発注制御、監視・アラート機能を備えた自動売買システムのコンポーネント群です。
- モジュールは疎結合に設計されており、リサーチ（ファクター計算）、ポートフォリオ構築、ポジションサイジング、発注マネージャ、リコンシリエーション、監視・アラート（LINE）、ダッシュボード（Streamlit）、LLM を使ったニュースセンチメント評価などを個別に利用できます。
- 設定は環境変数または .env から読み込み。自動読み込みロジックはプロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を読みます。

---

機能一覧
- 設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み、必須変数チェック、各種設定 accessor（paths / API トークン / 環境）
- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定（スコア順）、等金額／スコア加重配分、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算（単元丸め・aggregate cap）
- リサーチ（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、要約統計量
- AI（kabusys.ai）
  - ニュース記事を集約して OpenAI（gpt-4o-mini 等）でセンチメント評価 → ai_scores テーブルに書き込み
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントを合成）
  - API 呼び出しは冪等・リトライ・バリデーションを組み込み
- 実行（kabusys.execution）
  - OrderManager / ExecutionEngine：注文ライフサイクル管理、ブローカー送信、同期（sync）・キャンセル・再送制御
  - Reconciler：起動時の自動復旧（OrderSent の突合・ポジション差分検出）
- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）スキーマ／CRUD
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager
  - Streamlit ダッシュボード（read-only で monitoring.db を表示）
- 実運用向けの安全策
  - kill.flag による外部停止、PID ファイル、レート制限・サーキットブレーカ、フェイルセーフ（API 失敗時にデフォルト挙動で継続）など

---

セットアップ手順（ローカル開発用の例）

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate   (Unix/macOS)
   .venv\Scripts\activate      (Windows)

3. 必須パッケージをインストール
   pip install --upgrade pip
   pip install duckdb openai requests psutil streamlit

   （実際のプロジェクトでは requirements.txt を用意している場合があるので、あれば `pip install -r requirements.txt` を推奨します）

4. 環境変数設定
   - リポジトリルートに .env を置くことで自動読み込みされます（.env.local は .env を上書き）。
   - 自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
   - 必須項目や推奨項目は後述の「環境変数」参照。

5. データベース初期化（監視用の SQLite）
   Python REPL またはスクリプトから:
   from sqlite3 import connect
   from kabusys.monitoring.monitoring_db import init_monitoring_db
   conn = connect("data/monitoring.db")
   init_monitoring_db(conn)

6. DuckDB の準備
   DuckDB データベースへ価格データ・raw_financials・raw_news 等のテーブルをロードしておく必要があります（プロジェクト固有の ETL を想定）。DuckDB パスは環境変数 DUCKDB_PATH で指定可能（デフォルト data/kabusys.duckdb）。

---

使い方（主要な例）

- 設定の参照
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

- リサーチ（モメンタム計算）の呼び出し（DuckDB コネクションが必要）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  results = calc_momentum(conn, date(2026, 3, 20))
  # results は [{ "date": ..., "code": ..., "mom_1m": ..., ... }, ...]

- ニュース NLP スコアリング（OpenAI API キーが必要）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # env に OPENAI_API_KEY を設定するか、引数に api_key を渡す
  written = score_news(conn, date(2026, 3, 20), api_key=None)
  print(f"written scores: {written}")

- Streamlit ダッシュボード起動（監視DB が準備済みのこと）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringEngine をテストで一回だけ動かす
  from kabusys.monitoring import MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager
  # 各 Monitor に必要な依存（DB 接続や OrderRepository 等）を準備して渡す
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(Path("data/kill.flag")), alert_manager=AlertManager(...))
  engine.run_once()

- ExecutionEngine（本番的なセッション実行）
  実際に ExecutionEngine を稼働させるには BrokerAPI 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続など多数のコンポーネントを組み合わせる必要があります。ライブラリは各コンポーネントを受け取る形で実行するため、テスト用のモックやローカル実装を作ると良いです。

注意点
- OpenAI 等外部 API 呼び出しをする処理は、APIキーがなければ ValueError を投げます（あるいはフェイルセーフで 0.0 を返す実装箇所あり）。API キーの扱いに注意してください。
- kill.flag / PID ファイル / DB 書き込みの振る舞いにより、複数プロセスからの同時起動などに対する安全性をある程度担保していますが、運用前にテスト環境で十分に検証してください。

---

環境変数（.env）例

最小限の例（.env.example としてリポジトリに含めてください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0

補足:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env/.env.local を読み込む処理を無効化できます（テスト用）。
- PAPER_FILL_MODE は paper trading の挙動を制御します（instant/partial/never/reject）

---

ディレクトリ構成（抜粋: src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                    # 環境変数・設定管理
  - portfolio/
    - __init__.py
    - portfolio_builder.py       # 候補選定・配分計算
    - position_sizing.py         # 株数計算・aggregate cap
    - risk_adjustment.py         # セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py         # Momentum / Volatility / Value の計算
    - feature_exploration.py     # 将来リターン・IC・統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py                # ニュース集約・LLM スコアリング
    - regime_detector.py         # MA200 + マクロセンチメントでレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py           # SQLite スキーマ & MonitoringDB クラス
    - system_monitor.py          # システム監視（CPU/メモリ/データ鮮度）
    - trade_monitor.py           # 注文滞留・約定異常監視
    - risk_monitor.py            # ドローダウン/ポジション上限監視
    - kill_switch.py             # kill.flag 制御
    - alert_manager.py           # LINE へのプッシュ通知
    - monitoring_engine.py       # 各モニタを束ねるエンジン
    - streamlit_dashboard.py     # Streamlit による可視化ダッシュボード
  - execution/
    - broker_api.py              # ブローカー API のデータモデル / Protocol / 例外
    - order_manager.py           # 発注マネージャ（状態遷移・送信）
    - execution_engine.py        # セッション実行エンジン（signal/drain loop）
    - reconciler.py              # 起動時リコンシリエーション
    - (他、order_repository / order_record / risk_manager 等は別ファイルを想定)
  - (data パッケージは参照されるが本 README のコード抜粋外)

---

開発・運用上の注意
- DuckDB のテーブルスキーマ（prices_daily, raw_financials, raw_news, ai_scores, market_regime, signals, portfolio_targets 等）は、リサーチ/AI/実行コンポーネントに依存します。ETL 側で適切にデータをロードしてください。
- 本コードは本番発注に使える設計思想を持ちますが、実際の運用ではブローカー API 実装、手数料/スリッページ等のパラメータ微調整、冗長化・監視体制を整備してください。
- LLM 呼び出しはコスト発生と遅延があるため、バッチサイズやリトライ設定は運用に合わせて調整してください。

---

貢献・問い合わせ
- バグ報告や機能提案は Issue を立ててください。プルリク歓迎です。
- 大きな変更を加える場合は設計方針（特に DB スキーマや注文状態遷移）に影響が出ないよう注意してください。

以上。必要であれば README にサンプル .env.example の完全なテンプレートや、requirements.txt の自動生成例、より具体的なコード例（ExecutionEngine の組み立て例など）を追加します。どの部分を詳しく載せましょうか？