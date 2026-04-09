# KabuSys

日本株向け自動売買フレームワーク（ライブラリ群）。  
研究（ファクター計算）→ ポートフォリオ構築 → 発注エンジン → 監視・アラート の各レイヤを分離して提供します。OpenAI を用いたニュース NLP / レジーム判定や、DuckDB / SQLite を用いたローカルデータ処理・永続化を前提とした設計です。

---

## 概要

このコードベースは以下の主要機能を持ちます：

- ファクター計算（モメンタム、ボラティリティ、バリュー等） — kabusys.research
- ポートフォリオ構築（候補選定、重み付け、セクター制約、レジーム乗数、株数計算） — kabusys.portfolio
- 発注エンジン（OrderManager / ExecutionEngine）とブローカー API 抽象 — kabusys.execution
- 起動時のリコンシリエーション（Reconciler）による自動復旧
- 監視層（system/trade/risk の監視、kill switch、LINE 通知、Streamlit ダッシュボード） — kabusys.monitoring
- AI 関連（ニュースのセンチメント付与、マクロニュースによる市場レジーム判定） — kabusys.ai
- 環境設定の自動読み込み / 管理 — kabusys.config

設計方針として多くの関数は副作用を持たない「純粋関数」になっており、DuckDB / SQLite 接続などは呼び出し側で注入する形を取っています。これによりロジックのテスト容易性と安全性を高めています。

---

## 主な機能一覧

- research
  - calc_momentum, calc_volatility, calc_value：DuckDB の prices_daily / raw_financials を用いたファクター計算
  - calc_forward_returns, calc_ic, factor_summary：特徴量評価・IC 計算・統計サマリ
- portfolio
  - select_candidates, calc_equal_weights, calc_score_weights：候補選定・重み生成
  - apply_sector_cap, calc_regime_multiplier：セクター制約・レジーム乗数
  - calc_position_sizes：株数（単元）計算、aggregate / per-stock cap、コストバッファ対応
- execution
  - OrderManager：DB とブローカー API を組み合わせた注文状態管理
  - ExecutionEngine：シグナル処理ループ + WebSocket プッシュ処理（セッション実行）
  - Reconciler：起動時の注文 / ポジション照合
  - broker_api：OrderRequest / OrderStatus / Position 等のデータモデル、Protocol、例外
- ai
  - score_news：OpenAI（gpt-4o-mini 等）を用いたニュースセンチメントの集約と ai_scores テーブル書込
  - score_regime：ETF（1321）MA + マクロニュースセンチメントを合成した日次レジーム判定
- monitoring
  - MonitoringDB：SQLite ベースの永続化スキーマ（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor：各種チェック
  - KillSwitch / AlertManager：kill.flag による停止、LINE push による通知
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）と Settings クラス

---

## 動作要件（概略）

- Python >= 3.10
- 必要パッケージ（例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
- SQLite は標準ライブラリで利用可

例（最低限のインストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

※ 実運用では依存バージョン固定（requirements.txt/poetry）を推奨します。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール（上記参照）

3. 環境変数設定
   - プロジェクトルートに `.env` として必要な変数を配置できます。
   - 自動ロードの優先順は OS 環境変数 > .env.local > .env です。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用）。
   - 主要な環境変数（使用されるものの一例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI 機能利用時)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (監視アラート用)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE（instant/partial/never/reject）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
   - `.env` のサンプル行:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=...
     LINE_USER_ID=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. 監視用 SQLite スキーマ初期化（MonitoringDB）
   - 例:
     ```python
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db

     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```
   - Streamlit ダッシュボードは読み取り専用で開けるように URI を指定して起動できます（下記参照）。

---

## 使い方（代表例）

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_paper)
  ```

- DuckDB に接続してファクター計算（研究用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect('data/kabusys.duckdb')
  res = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP によるスコア付与（ai）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  # api_key を None にすると環境変数 OPENAI_API_KEY を参照
  written = score_news(conn, date(2026, 3, 20), api_key=None)
  print(f"書き込んだ銘柄数: {written}")
  ```

- レジーム判定（ai/regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect('data/kabusys.duckdb')
  score_regime(conn, date(2026, 3, 20))
  ```

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 起動時に監視 DB が読めない場合はエラー表示されます。MonitoringEngine を先に動かしてデータを生成してください。

- MonitoringEngine の簡易実行（単発実行）
  - 監視コンポーネントを組み合わせてテスト的に 1 回だけ実行する例:
    ```python
    import sqlite3, duckdb
    from kabusys.monitoring import (
        MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
    )
    # 実際には OrderRepository や broker 等を用意する必要があります（ここは省略）
    mon_conn = sqlite3.connect("data/monitoring.db")
    duck_conn = duckdb.connect("data/kabusys.duckdb")
    system = SystemMonitor(mon_conn, duck_conn)
    trade = TradeMonitor(mon_conn, order_repo)  # order_repo は実装を用意
    risk = RiskMonitor(mon_conn)
    ks = KillSwitch(Path("data/kill.flag"))
    alert = AlertManager(settings.line_channel_access_token, settings.line_user_id)
    engine = MonitoringEngine(system, trade, risk, interval_sec=60, kill_switch=ks, alert_manager=alert)
    engine.run_once()
    ```

- ExecutionEngine（発注セッション）の利用
  - 実稼働には BrokerAPIProtocol を満たすブローカークライアント、OrderRepository、RiskManager、OrderManager、DuckDB 接続、EngineConfig などが必要です。インスタンスを組み合わせて `ExecutionEngine.run_session()` を呼びます。
  - 起動時には kill.flag の存在や PID ファイルの操作、Reconciler による自動復旧などの処理が行われます。実運用前にロジックを十分理解して下さい。

---

## 環境変数自動読み込みの挙動（重要）

- 実装はプロジェクトルート（.git または pyproject.toml を起点）を探し、ルート直下の `.env` と `.env.local` を自動で読み込みます（`src/kabusys/config.py`）。
- 読み込みの優先順:
  1. OS 環境変数（常に保護）
  2. `.env.local`（既存変数を上書きする）
  3. `.env`（未設定のキーのみ設定）
- テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 主要ディレクトリ構成（src/kabusys）

- config.py
  - Settings クラス・.env 自動読み込みロジック
- __init__.py
  - パッケージメタ情報（__version__ 等）
- portfolio/
  - portfolio_builder.py：候補選定・等重/スコア重み計算
  - position_sizing.py：株数（単元）計算、aggregate スケールダウンロジック
  - risk_adjustment.py：セクター上限、レジーム乗数
- research/
  - factor_research.py：momentum/value/volatility ファクター計算（DuckDB）
  - feature_exploration.py：将来リターン・IC・統計サマリ等
- ai/
  - news_nlp.py：ニュースを集約して OpenAI に送信、ai_scores テーブルへ書込
  - regime_detector.py：MA200 とマクロセンチメントを合成して市場レジーム判定
- monitoring/
  - monitoring_db.py：SQLite スキーマ / MonitoringDB ラッパ
  - system_monitor.py, trade_monitor.py, risk_monitor.py：各種チェック
  - kill_switch.py：kill.flag 制御
  - alert_manager.py：LINE Push
  - monitoring_engine.py：各 Monitor を束ねたループ
  - streamlit_dashboard.py：監視ダッシュボード
- execution/
  - broker_api.py：API データモデル / 例外 / Protocol
  - order_manager.py：注文状態マシンの外向き API
  - execution_engine.py：発注セッションのコントローラ
  - reconciler.py：起動時の自動復旧
  - （その他：order_repository, order_record, risk_manager 等は本リポジトリに含まれる想定）
- monitoring と ai / research は DuckDB / SQLite DB に依存します（read/write）。

---

## 注意事項・運用上のポイント

- AI 呼び出し（OpenAI）を行う処理は API 失敗時にフェイルセーフとしてスコア 0.0 を採る等の設計がされていますが、API キーは必須です。負荷やレート制限に注意してください。
- ExecutionEngine は実際のブローカー API を呼ぶ設計です。実稼働前に paper_trading 環境で徹底的にテストしてください。
- kill.flag / PID ファイルは安全性の高い停止・残留検出に使われます。運用ルールを整備してください。
- duckdb / sqlite のファイルパスは Settings から取得します。バックアップ・排他制御を考慮してください。
- unit テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD` を利用したり、OpenAI 呼び出し部分をモックするなどの手法を推奨します（コード内にもモック用に差し替え可能な関数が用意されています）。

---

この README はコードベースの概要と利用開始に必要なポイントをまとめたものです。各モジュールの詳細な使用法や API（OrderRepository 等）については該当ファイルの docstring / コメントを参照してください。必要であれば使用例や CLI スクリプト、requirements.txt/poetry 設定の追記ドキュメントも作成できます。