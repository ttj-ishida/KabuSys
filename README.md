KabuSys — 日本株自動売買フレームワーク
===================================

概要
----
KabuSys は、個別株の自動売買に必要な主要コンポーネント（ポートフォリオ構築、ポジションサイジング、リスク制御、ファクター研究、ニュース NLP によるセンチメント、監視・アラート、発注エンジン／ブローカーインターフェース等）をモジュール化して提供する Python コードベースです。DuckDB / SQLite をローカル DB として用い、OpenAI（gpt-4o-mini）をニュース・マクロ判定に利用する実験的な AI 機能を含みます。

主な特徴
--------
- ポートフォリオ構築
  - シグナルの上位選定（スコア順）
  - 等配分・スコア重み付けの重み算出
- ポジションサイズ決定
  - リスクベース / 等配分 / スコア配分
  - 単元株（lot）丸め、1 銘柄上限、投下資金上限、コストバッファ等を考慮
- リスク調整
  - セクター集中の除外（セクター上限）
  - 市場レジームに応じた投下資金乗数（bull/neutral/bear）
- リサーチ（研究）モジュール
  - Momentum / Volatility / Value 等ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI 機能
  - ニュース記事から銘柄ごとのセンチメントスコアを算出して ai_scores に保存（OpenAI API）
  - マクロニュース + ETF MA200 乖離から市場レジーム判定（market_regime テーブルへ書込）
- 監視（Monitoring）
  - SQLite ベースの監視 DB（system_status / trade_logs / positions / risk_logs / dashboard）
  - システム監視（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - 注文滞留・約定異常検出
  - リスクモニタ（ドローダウン / ポジション数上限）と Kill Switch（flag ファイル）
  - LINE Push によるアラート送信
  - Streamlit ダッシュボードによる可視化
- 発注・実行
  - ExecutionEngine: シグナル取得 → Gate チェック → 発注（OrderManager） → WebSocket ドレイン（push）
  - Reconciler: 再起動時の注文・ポジション整合化
  - Broker API 層は Protocol で抽象化（テスト容易）

セットアップ手順
---------------
以下は基本的なセットアップ例です（プロジェクトに requirements.txt がある想定）。実行環境に合わせて適宜調整してください。

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai requests psutil streamlit
   - （プロジェクトが requirements.txt を持つ場合）pip install -r requirements.txt

   主な依存（参考）
   - duckdb
   - openai
   - requests
   - psutil
   - streamlit

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）に .env / .env.local を置くと、自動で読み込まれます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必要な環境変数（一部、デフォルト値はコード参照）：

     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - OPENAI_API_KEY (OpenAI を使用する場合)
     - LINE_CHANNEL_ACCESS_TOKEN (任意、LINE 通知)
     - LINE_USER_ID (任意、LINE 通知)
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (例: data/monitoring.db)
     - PAPER_FILL_MODE (instant/partial/never/reject, default: instant)
     - PAPER_TRADING_SQLITE_PATH (例: data/paper_trading.db)
     - PID_FILE_PATH (default: data/execution.pid)
     - KILL_FLAG_PATH (default: data/kill.flag)
     - KILL_FLAG_CLEAR_ON_START (0/1, default: 0)
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）
     - KABUSYS_ENV (development/paper_trading/live, default: development)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, default: INFO)

   - 例 .env（最低限の例）
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. Monitoring DB の初期化（SQLite）
   - Python REPL やスクリプトから:
     ```
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db

     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

使い方（主要な操作例）
--------------------

- 設定値の参照
  ```
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- DuckDB を使ったファクター計算（例：momentum）
  ```
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュースセンチメントの計算と書き込み
  ```
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  print(f"wrote scores for {count} codes")
  ```

- 市場レジーム判定
  ```
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- MonitoringEngine の一回実行（テスト用 run_once）
  - SystemMonitor / TradeMonitor / RiskMonitor 等を組み合わせて MonitoringEngine を作成し、run_once() を呼びます（詳細は実装参照）。
  - 例（概念）:
    ```
    from kabusys.monitoring import MonitoringEngine, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager
    # 各モニタのインスタンス化には sqlite3/duckdb コネクションや OrderRepository 等が必要
    engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
    engine.run_once()
    ```

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（本番発注ループ／セッション実行）
  - ExecutionEngine の使用には BrokerAPI 実装（BrokerAPIProtocol に準拠）、OrderRepository（SQLite）、RiskManager、OrderManager、DuckDB 接続等が必要です。環境上のブローカークライアントを用意して組み立ててください。
  - サンプルは実装内 docstring と ExecutionEngine.run_session() を参照してください。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理（.env 自動読み込みロジック含む）
  - portfolio/
    - __init__.py
    - portfolio_builder.py  — シグナル選定・重み付け
    - position_sizing.py    — 株数決定・スケーリング
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py— 将来リターン, IC, 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP による銘柄センチメント集計・書込み
    - regime_detector.py    — ETF MA200 + マクロセンチメントで市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py      — SQLite テーブル定義 / MonitoringDB クラス
    - system_monitor.py     — CPU/メモリ/データ鮮度監視
    - trade_monitor.py      — 注文滞留 / 価格異常監視
    - risk_monitor.py       — ドローダウン / ポジション上限監視
    - kill_switch.py        — flag ファイルによる停止シグナル
    - alert_manager.py      — LINE Push 通知
    - monitoring_engine.py  — 各 Monitor を束ねたポーリングエンジン
    - streamlit_dashboard.py— Streamlit ダッシュボード
  - execution/
    - broker_api.py         — Broker API のデータモデル / Protocol / 例外
    - order_manager.py      — Order State Machine の外向き API
    - order_repository.py   — (別ファイル想定) SQLite 注文リポジトリ
    - reconciler.py         — 起動時のリコンシリエーション
    - execution_engine.py   — Signal Queue Pull 型発注エンジン
    - ...                   — （その他、order_record, risk_manager 等が別ファイルとして想定）
  - monitoring/ (上記)
  - その他: data, docs, tests 等（プロジェクトルートに配置される想定）

実運用での注意点
----------------
- .env の取り扱い: API キーやパスワードなどの機密値は適切に管理してください。デプロイ先では .env.local を用いてローカル上書きを行う運用が想定されます。
- OpenAI 利用: API 呼び出しにはコストとレート制限があります。news_nlp / regime_detector はリトライや失敗時のフォールバックを実装していますが、API キーの漏洩に注意してください。
- ブローカーとの接続: broker_api は Protocol により抽象化されています。実際のブローカー実装は安全性（order id の永続化、再試行戦略）に注意して実装してください。
- Kill Switch / PID ファイル: 起動時の kill.flag の扱いや PID ファイル管理は設定に依存します（settings.kill_flag_clear_on_start 等）。

貢献 / 開発
------------
- テスト: 各モジュールは純粋関数や依存注入を重視しているためモックを使った単体テストが書きやすい設計です（OpenAI 呼び出し関数はテストでパッチ可能）。
- ドキュメント: PortfolioConstruction.md, StrategyModel.md 等の設計ドキュメントに沿って実装されています。新機能は設計ドキュメントを更新してください。

---

この README はコードベース（src/kabusys/*.py）を参照して作成しています。各モジュールの詳細な利用方法やパラメータはソース内 docstring を参照してください（例: kabusys/research/*.py, kabusys/ai/*.py, kabusys/monitoring/*.py）。追加のサンプルやデプロイ手順が必要であれば教えてください。