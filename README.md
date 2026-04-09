# KabuSys

日本株向けの自動売買 / 研究 / 監視ライブラリ群です。  
シグナルのポートフォリオ構築〜発注（ExecutionEngine）、ファクター計算・リサーチ、ニュースのLLM評価、監視（MonitoringEngine / Streamlit ダッシュボード）などのコンポーネントを提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- 取引システムのコアロジック（注文状態管理、発注フロー、再起動時リコンシリエーション）
- ポートフォリオ構築（候補選定・重み付け・株数計算・リスク調整）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- ニュースの自然言語評価（OpenAI を利用した銘柄別センチメント）
- 市場レジーム判定（ETF とマクロニュースを組み合わせて判定）
- 監視（システム/注文/リスク監視、LINE 通知、Streamlit ダッシュボード）
- 設定管理（.env / 環境変数読み込み）

設計方針として、DB 操作は明確に分離され、関数群は可能な限り純粋関数で構成されています。ルックアヘッドバイアス防止やフェイルセーフ（API 失敗時のフォールバック）に配慮しています。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（オーバーライドルールを含む）
  - 必須環境変数チェック

- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等配分 / スコア加重の重み計算
  - セクター上限適用
  - レジームに応じた投下資金乗数

- ポジションサイズ計算
  - リスクベース（stop-loss を考慮）や等分配・スコア配分
  - 単元株（lot）丸め、集計上限（aggregate cap）へのスケーリング

- リサーチ（DuckDB ベース）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー

- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースを集約し LLM でセンチメントを算出
  - バッチ送信、リトライ、レスポンス検証、DuckDB への反映

- 市場レジーム判定（ETF + マクロニュース + LLM）
  - ma200 乖離とマクロセンチメントを合成して 'bull'/'neutral'/'bear' を決定
  - 結果を market_regime テーブルへ保存

- Execution / Broker インターフェース
  - OrderManager / Reconciler / ExecutionEngine：状態遷移と発注フロー管理
  - BrokerAPIProtocol ベースのクライアント実装を差し替えて利用可能

- 監視
  - MonitoringDB（SQLite）による永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE）
  - Streamlit ダッシュボード（read-only）

---

## セットアップ手順（開発用）

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb openai requests psutil streamlit

   （実装内容に応じて他パッケージが必要になる場合があります）

4. 環境変数 / .env を準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くことで自動的に読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. SQLite 監視DB の初期化（任意）
   - Python で実行:
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

6. DuckDB （価格データ / リサーチ用）の準備
   - デフォルトパス: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
   - 必要なテーブル（prices_daily, raw_financials, raw_news, ...）をロードしておくこと

---

## 主要な環境変数（settings）

設定管理は `kabusys.config.Settings` を通じて行われます。主な変数とデフォルト：

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: "http://localhost:18080/kabusapi")
- LINE_CHANNEL_ACCESS_TOKEN (通知用、空なら通知は送られない)
- LINE_USER_ID (通知用)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_FILL_MODE (default: "instant"; valid: instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視閾値)
- KABUSYS_ENV (development|paper_trading|live) default: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) default: INFO
- OPENAI_API_KEY (OpenAI 呼び出しに使用)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1: 自動 .env 読み込みを無効化)

必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY）は設定がないと例外が発生します。

---

## 使い方（抜粋・例）

以下は、主要な機能を呼び出す際の最小例です。実際には Broker 実装や DB 構成が必要です。

- ニュース NLP（OpenAI を使ってスコアを DuckDB に書き込む）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")
  print(f"written scores: {written}")

- 市場レジーム判定

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="YOUR_OPENAI_KEY")

- Streamlit ダッシュボード（read-only）起動

  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- 監視DB 初期化（SQLite）

  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  conn.close()

- ExecutionEngine の起動（実運用は Broker 実装や OrderRepository 等の依存が必要）

  # 概念的な例（実行には具象 broker/repo/risk_manager 等が必要）
  from datetime import date, time
  import duckdb
  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig

  duck_conn = duckdb.connect("data/kabusys.duckdb")
  config = EngineConfig(target_date=date.today())
  engine = ExecutionEngine(broker=your_broker, repo=your_repo, risk_manager=rm, order_manager=om, duckdb_conn=duck_conn, config=config)
  engine.run_session()

- ポートフォリオ構築 / ポジション決定（関数利用例）

  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [{"code":"7203","signal_rank":1,"score":0.9}, ...]
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=7_000_000, current_positions={}, open_prices={"7203":9000}, allocation_method="score")

---

## 実運用上の注意点・設計メモ

- .env の読み込み順序:
  - OS 環境変数 > .env.local（override=True） > .env（override=False）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化

- LLM 呼び出し（news_nlp / regime_detector）はネットワーク障害や API レート制限を考慮してリトライ・フォールバック処理を行いますが、API キーは必ず渡すか環境変数 OPENAI_API_KEY を設定してください。

- ExecutionEngine の kill switch（data/kill.flag）により安全に全ループを停止できます。起動時に kill.flag が存在すると設定により起動を拒否します（KILL_FLAG_CLEAR_ON_START=1 で自動クリア可）。

- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブル構成に依存します。リサーチ機能を利用する前に必要テーブルを整備してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・.env 読み込み・Settings
  - portfolio/
    - portfolio_builder.py  # 候補選定・重み計算
    - position_sizing.py    # 株数計算・集計 cap
    - risk_adjustment.py    # セクター制限・レジーム乗数
  - research/
    - factor_research.py    # momentum/value/volatility 計算（DuckDB）
    - feature_exploration.py# 将来リターン・IC・統計
  - ai/
    - news_nlp.py           # ニュース→銘柄別 AI スコア (OpenAI)
    - regime_detector.py    # 市場レジーム判定 (ETF + LLM)
  - monitoring/
    - monitoring_db.py      # SQLite テーブル定義 + MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py      # LINE 通知
    - monitoring_engine.py  # 各監視を束ねる
    - streamlit_dashboard.py
  - execution/
    - broker_api.py         # Broker 用データモデル・Protocol・例外
    - order_manager.py      # OrderManager（発注フロー）
    - reconciler.py         # 起動時リコンシリエーション
    - execution_engine.py   # Signal を引いて発注するエンジン
    - ...（OrderRepository など別ファイル）
  - monitoring/、ai/、portfolio/ 等のパッケージ初期導出

（上記は主要ファイルを抜粋しています。実コードにはさらに多くのモジュールが含まれます。）

---

## テスト・開発メモ

- LLM / 外部 API 呼び出し部分はテストでモック化可能（コード中に差し替えポイントあり）。
- DuckDB 接続はメモリ接続やテスト用 DB ファイルで容易に差し替え可能。
- SQLite（監視DB）はファイル実体を用いるが read-only URI を Streamlit で利用できます（dashboard では read-only モードで接続）。

---

必要ならサンプルの .env.example、依存関係の requirements.txt、や ExecutionEngine をローカルで動かすための最小サンプルスクリプトを別途作成します。どれを優先して欲しいか教えてください。