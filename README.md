KabuSys — 日本株自動売買ライブラリ
=================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視用に設計された Python ライブラリ群です。  
ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）、ファクター計算、ニュースの NLP スコアリング（OpenAI 利用）、市場レジーム判定、実行エンジン（発注・リコンシリエーション）、監視ダッシュボード等の機能をモジュール化して提供します。  
設計方針として「DB（DuckDB / SQLite）を参照してロジックを実行」「本番用 API 呼び出しはブローカークライアント層に集約」「ルックアヘッドバイアス回避」「自動 .env ロード」などに配慮しています。

主な機能
--------
- 環境変数 / .env 管理（src/kabusys/config.py）
  - プロジェクトルートの .env / .env.local を自動ロード（優先度: OS 環境 > .env.local > .env）
  - export 形式、クォート、インラインコメント等に対応
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
- ポートフォリオ構築（src/kabusys/portfolio）
  - 候補選定（select_candidates）
  - 等金額・スコア加重の重み計算（calc_equal_weights, calc_score_weights）
  - セクター上限適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes） — リスクベース / 等配分 等
- リサーチ（src/kabusys/research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（src/kabusys/ai）
  - ニュースを OpenAI（gpt-4o-mini）で評価して ai_scores に書き込む（score_news）
  - 市場レジーム判定（ETF ma200 とマクロニュースの LLM センチメントを合成）→ market_regime テーブルへ書込む（score_regime）
  - API 失敗時のフォールバック、リトライロジックあり
- 監視（src/kabusys/monitoring）
  - MonitoringDB（SQLite）による永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - System / Trade / Risk モニタ、KillSwitch、アラート（LINE Push）など
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- 実行（src/kabusys/execution）
  - ExecutionEngine（シグナル読み込み → 発注 → WebSocket push ドレイン）
  - OrderManager（ステートマシン）、Reconciler（再起動時リコンシリエーション）
  - Broker API 抽象（Protocol）によりブローカー実装を差し替え可能

セットアップ（開発環境）
---------------------
前提:
- Python 3.10 以上（|型や match などの近年の記法を使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (監視UI を使う場合)
  - (標準ライブラリ: sqlite3, logging 等)

例（pipenv / venv / pip）:
1. 仮想環境作成・有効化
   - python -m venv .venv && source .venv/bin/activate
2. 依存インストール
   - pip install "duckdb" "openai" "requests" "psutil" "streamlit"

環境変数 / .env
----------------
プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に .env/.env.local を置くと自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みはスキップされます）。

主要な環境変数（使用される設定）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須な箇所あり）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH — Paper Trading 関連設定
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, LOG_LEVEL, KABUSYS_ENV 等

.env のパースは export KEY=val 形式やクォート、コメントに対応しています。

使い方（主なユースケース）
------------------------

1) DuckDB を用いたファクター計算（例: モメンタム）
- DuckDB 接続を用意して calc_momentum を呼び出します。
  - 例:
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect(database="data/kabusys.duckdb")
    res = calc_momentum(conn, date(2026, 3, 20))

2) ニュース NLP スコアリング
- ai.score_news(conn, target_date, api_key=None) を呼ぶと raw_news / news_symbols を読み、OpenAI に問い合わせて ai_scores に書き込みます。
  - api_key を指定しない場合は OPENAI_API_KEY 環境変数を参照します。

3) 市場レジーム判定
- ai.regime_detector.score_regime(conn, target_date, api_key=None) を呼ぶと ma200 とマクロニュースを LLM で評価して market_regime に書き込みます。

4) 監視 DB 初期化
- MonitoringDB を初期化するには:
    import sqlite3
    from kabusys.monitoring.monitoring_db import init_monitoring_db
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)

5) Streamlit ダッシュボード起動
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

6) ExecutionEngine（本番/テスト）
- ExecutionEngine を使うには BrokerAPI の実装（BrokerAPIProtocol を満たすクラス）、OrderRepository（SQLite を扱う実装）、RiskManager、OrderManager、DuckDB 接続等を用意してインスタンス化します。実行は engine.run_session()（本番）や engine.run_once()/engine._drain_push_queue()（テスト用）で制御します。
- ExecutionEngine は起動時に PID 書き出し、kill.flag の扱い、リコンシリエーション等を行います。

ディレクトリ構成（主なファイル）
------------------------------
src/
  kabusys/
    __init__.py                # パッケージメタ（version 等）
    config.py                  # 環境変数 / .env ローダー（settings オブジェクト）
    ai/
      __init__.py
      news_nlp.py              # ニュース NLP スコアリング（OpenAI 経由）
      regime_detector.py       # 市場レジーム判定（ma200 + マクロセンチメント）
    portfolio/
      __init__.py
      portfolio_builder.py     # 候補選定、重み計算
      risk_adjustment.py       # セクターキャップ、レジーム乗数
      position_sizing.py       # 株数計算・スケーリング・ロット丸め
    research/
      __init__.py
      factor_research.py       # Momentum/Volatility/Value ファクター計算
      feature_exploration.py   # 将来リターン、IC、統計サマリ
    monitoring/
      __init__.py
      monitoring_db.py         # MonitoringDB 初期化・CRUD
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py         # LINE 送信実装
      monitoring_engine.py
      streamlit_dashboard.py   # Streamlit ダッシュボード起動スクリプト
    execution/
      broker_api.py            # Broker API のデータモデル・Protocol・例外
      execution_engine.py
      order_manager.py
      reconciler.py
      ...                     # （OrderRepository / OrderRecord 等は別ファイルに存在）
    research/                   # 既述
    portfolio/                  # 既述
    monitoring/                 # 既述
    data/                       # （別モジュール群。DuckDB 関連ユーティリティ等が想定）

設計上の注意点 / 備考
--------------------
- ルックアヘッドバイアス回避:
  - AI / リサーチの関数は内部で date.today() 等を参照せず、呼び出し側が target_date を明示して渡します。
  - prices_daily クエリは必要に応じて target_date より前のデータのみを参照します。
- 自動 .env ロード:
  - プロジェクトルートが検出できない場合は自動ロードをスキップします。
  - OS の環境変数を保護する仕組み（.env.local は上書き可能だが OS 環境は保護）があります。
- OpenAI API:
  - API を利用する機能は OPENAI_API_KEY（または関数引数での api_key）を必要とします。
  - RateLimit / ネットワーク障害・5xx は指数バックオフでリトライし、失敗時はフェイルセーフ（スコア=0.0、あるいはスキップ）します。
- DB 書込みの原子性:
  - ai.score_news や regime_detector.score_regime、MonitoringDB などはトランザクション（BEGIN / COMMIT / ROLLBACK）で整合性を保つ設計です。

貢献・拡張案（将来案）
--------------------
- 銘柄ごとの lot_size をマスタで管理し position_sizing に反映
- price のフォールバック（前日終値等）を用いた exposure 推定の改善
- より詳細なテスト・CI、例: OpenAI 呼び出しのモックを使ったユニットテスト
- 帳票・可視化の拡充（Streamlit UI 拡張）

ライセンス / 作者
-----------------
（この README はコードベースから自動生成した概要ドキュメントです。ライセンス表記や作者情報はプロジェクトルートの LICENSE / pyproject.toml を参照してください。）

補足（よくあるコマンド）
---------------------
- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- DB 初期化（監視用）:
  python -c "import sqlite3; from kabusys.monitoring.monitoring_db import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn)"

- DuckDB 接続例（インタラクティブ）:
  >>> import duckdb
  >>> conn = duckdb.connect(database='data/kabusys.duckdb')

必要に応じて README に追記したい箇所（例: Broker 実装方法、OrderRepository スキーマ、API トークン取得手順など）があれば教えてください。追加で具体的な利用例（ExecutionEngine の起動スクリプト雛形等）も作成できます。