# KabuSys

日本株向け自動売買システムのコアライブラリ（リサーチ・ポートフォリオ構築・発注・監視・AIユーティリティを含む）。

概要
- DuckDB を使ったリサーチ／ファクター計算
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング）
- 発注エンジン（OrderManager / ExecutionEngine / Broker API 抽象）
- 再起動時のリコンシリエーション（Reconciler）
- ニュースセンチメント（OpenAI を用いた LLM 評価）および市場レジーム判定
- 監視機能（SQLite ベースの監視DB、各種 Monitor、LINE 通知、Streamlit ダッシュボード）
- 環境変数の自動ロード・設定管理

主な機能一覧
- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（無効化フラグあり）
  - Settings クラスから typed な設定取得
- ポートフォリオ構築
  - select_candidates: スコア順で候補選定
  - calc_equal_weights / calc_score_weights: 配分重み計算
  - apply_sector_cap: セクター集中制限適用
  - calc_regime_multiplier: レジームに応じた乗数
  - calc_position_sizes: 単元丸め・リスクベース/重みベースの株数計算、資金スケール調整
- リサーチ / ファクター計算
  - calc_momentum / calc_volatility / calc_value: DuckDB の prices_daily / raw_financials を用いてファクターを算出
  - calc_forward_returns / calc_ic / factor_summary: 特徴量の評価・IC 計算・統計サマリ
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事を銘柄ごとに集約し LLM でセンチメントを算出して ai_scores テーブルへ書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロ記事センチメントを合成して market_regime に保存
- 発注（Execution）
  - BrokerAPI 抽象（Protocol） + データモデル（OrderRequest/OrderStatus 等）
  - OrderManager: 注文状態遷移・送信・同期・キャンセル
  - ExecutionEngine: シグナルループ、push ドレイン、Gate チェック、kill switch 連携
  - Reconciler: 起動時の注文 / ポジション突合せ
- 監視
  - MonitoringDB.init_monitoring_db: SQLite スキーマ初期化
  - MonitoringDB / MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor
  - AlertManager: LINE push 通知（クールダウン管理）
  - kill_switch: フラグファイル経由での緊急停止
  - streamlit_dashboard: Streamlit で監視ダッシュボード表示

セットアップ手順（開発/実行環境の最低案内）
1. 前提
   - Python 3.10+
   - システムに以下の Python パッケージをインストールしてください（プロジェクトの requirements.txt があればそれを使用）。
     - duckdb, openai, requests, psutil, streamlit
   - 例:
     - pip install duckdb openai requests psutil streamlit

2. リポジトリ配置
   - ソースは `src/kabusys/` 配下にあります。プロジェクトルートには `.git` または `pyproject.toml` がある想定です。
   - パッケージインストール（ローカル開発向け）:
     - pip install -e .

3. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（自動読み込みを抑制するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 主要な環境変数の例（.env）:
     ```
     # .env.example
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=your_line_token
     LINE_USER_ID=your_line_user_id
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_FILL_MODE=instant
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     KILL_FLAG_CLEAR_ON_START=0
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. 監視DB 初期化（Monitoring）
   - Python スクリプトで SQLite 接続を作成しスキーマを作成:
     ```python
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db

     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

5. DuckDB（リサーチ用テーブル）準備
   - リサーチ関数は `prices_daily`, `raw_financials`, `raw_news`, `news_symbols`, `ai_scores`, `market_regime` 等のテーブルを参照します。これらの投入は別途データパイプラインで行ってください（kabusys.data.pipeline の利用を想定）。

使い方（主な例）
- 設定値の取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- ファクター計算（DuckDB 接続例）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

- ニュースセンチメント算出（OpenAI API キー必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026,3,20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {written}")
  ```

- レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,3,20), api_key="sk-...")
  ```

- 監視エンジン（単発実行 / ループ）
  ```python
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine
  # 必要なオブジェクト（duckdb_conn, order_repo 等）を生成して MonitoringEngine に渡す
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
  engine.run_once()  # テスト用に一回だけ実行
  engine.run()       # 実運用: KeyboardInterrupt までポーリング
  ```

- Streamlit ダッシュボード起動
  - コマンド:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定、等配分・スコア配分
    - position_sizing.py     — 株数・資金割当計算
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value の計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite スキーマ + MonitoringDB 操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py          — Broker API データモデル・Protocol・例外
    - order_manager.py
    - order_repository.py    — (存在を前提とした DB 層)
    - execution_engine.py
    - reconciler.py
    - reconciler.py
  - その他（data パイプライン、stats ユーティリティ等が別モジュールとして想定）

補足 / 注意事項
- OpenAI API を利用する機能（news_nlp, regime_detector）を使う場合は API キーが必須です。エラーが発生した場合、システムはフェイルセーフ（スコア 0.0 など）で継続する設計です。
- .env の自動読み込みはプロジェクトルートの検出に .git または pyproject.toml を利用します。配布後も動くよう __file__ に基づいてルートを探します。
- ExecutionEngine は実環境での発注に使うため、BrokerAPI の実装（kabu station クライアント等）を渡して運用してください。リスク管理（Gate1/2/3）・kill switch との連携が組み込まれています。
- DuckDB / SQLite のスキーマやテーブルはデータ提供パイプライン側で整備してください。research 関数は prices_daily / raw_financials / raw_news 等のテーブルを前提とします。

以上がこのリポジトリの概要・導入・主な使い方です。必要であれば、セットアップスクリプト・requirements.txt のテンプレートや具体的なサンプルデータ投入手順、より詳細な実行例（ExecutionEngine の実装サンプル）を追記します。どの部分を詳細化しますか？