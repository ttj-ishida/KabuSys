# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（モジュール群の切り出し実装）。  
このリポジトリには、ポートフォリオ構築・ポジションサイズ計算・ファクター研究・ニュース NLP を使ったセンチメント評価・実行エンジン・監視周りのユーティリティが含まれます。

---

## プロジェクト概要

KabuSys は以下のようなコンポーネントを持つ自動売買システムのコア実装です：

- 環境設定管理（.env 自動読み込み、Settings）
- ポートフォリオ構築（候補選定・重み計算）
- ポジションサイズ計算（リスクベース・等配分・スコア加重）
- リスク調整（セクターキャップ、レジーム乗数）
- ファクター計算・研究（モメンタム、バリュー、ボラティリティ、IC 等）
- ニュース NLP（OpenAI を使った記事センチメント集約 → ai_scores 書き込み）
- 市場レジーム判定（ETF とマクロニュースの合成）
- 実行エンジン（signal queue ベース、発注管理、リコンシリエーション）
- 監視（System / Trade / Risk の監視、LINE 通知、Streamlit ダッシュボード）
- 永続化：DuckDB（時系列データ・研究データ）と SQLite（監視ログ / 注文 DB）

設計方針として「DB/外部 API 呼び出しは呼び出し側から接続を受け取る」「副作用を最小化した純粋関数を分離」などが採られています。

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git / pyproject.toml を基準）
  - 環境変数未設定時の必須チェック（Settings クラス）

- ポートフォリオ
  - select_candidates（スコア降順で上位 N を選択）
  - calc_equal_weights / calc_score_weights（重み計算）
  - calc_position_sizes（リスクベース / 等配分 / スコア配分の株数算出）
  - apply_sector_cap（セクター集中制限）
  - calc_regime_multiplier（市場レジームに応じた投下資金倍率）

- リサーチ / ファクター
  - calc_momentum / calc_value / calc_volatility（DuckDB の prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank

- AI（OpenAI）
  - score_news（ニュース記事群をまとめて OpenAI に送り銘柄ごとのスコアを ai_scores に書込）
  - score_regime（ETF とマクロニュースからレジーム判定を行い market_regime に書込）

- 実行（Execution）
  - ExecutionEngine（シグナル読み込み → Gate チェック → 発注、WebSocket push ドレイン）
  - OrderManager / Reconciler（発注・状態遷移・再同期）
  - Broker API Protocol・データモデル（OrderRequest/OrderStatus/Position 等）

- 監視
  - MonitoringDB（SQLite に監視情報を永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch
  - AlertManager（LINE Push 通知）
  - Streamlit ダッシュボード（簡易監視 UI）

---

## セットアップ手順

前提：Python 3.10+ を想定（コード内で型注釈などを使用）。

1. リポジトリをクローン／チェックアウト
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（最低限の例）
   ```
   pip install duckdb openai psutil requests streamlit
   ```
   ※ 実行に必要な追加パッケージ（kabuステーションクライアント等）がある場合は適宜追加してください。

4. 環境変数（.env）を用意
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を作成すると、自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

   例（.env の例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   読み込み順序: OS 環境変数 > .env.local (override) > .env

5. データベースパス（デフォルト）
   - DuckDB: data/kabusys.duckdb（Settings.duckdb_path）
   - Monitoring SQLite: data/monitoring.db（Settings.sqlite_path）
   - Paper trading DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

6. 監視 DB の初期化（MonitoringDB のスキーマ作成）
   Python から:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（主要な例）

- 設定を使う
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path  # pathlib.Path
  ```

- ポートフォリオ候補選定・重み計算
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights

  signals = [
      {"code": "7203", "signal_rank": 1, "score": 0.9},
      {"code": "6758", "signal_rank": 2, "score": 0.7},
      ...
  ]
  candidates = select_candidates(signals, max_positions=5)
  weights_eq = calc_equal_weights(candidates)
  weights_score = calc_score_weights(candidates)
  ```

- ポジションサイズ計算（risk_based 例）
  ```python
  from kabusys.portfolio import calc_position_sizes

  sizes = calc_position_sizes(
      weights=weights_score,
      candidates=candidates,
      portfolio_value=10_000_000,
      available_cash=1_000_000,
      current_positions={},
      open_prices={"7203": 2000.0, "6758": 1500.0},
      allocation_method="risk_based",
      risk_pct=0.005,
      stop_loss_pct=0.08,
  )
  ```

- DuckDB を使ったファクター計算（例: モメンタム）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP スコア生成（OpenAI API キーは引数または環境変数 OPENAI_API_KEY）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026,3,20), api_key="sk-...")
  ```

- レジーム判定（OpenAI を使用、失敗時はフェイルセーフで継続）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026,3,20), api_key="sk-...")
  ```

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- モニタリングエンジン（テスト的に1回だけ実行）
  ```python
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager
  # 必要な conn / duckdb_conn / order_repo 等を構築して渡す
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...))
  engine.run_once()  # テスト用
  ```

- 実行エンジン（実稼働時に run_session を呼ぶ）
  ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続など多くの依存が必要です。ユニットテストではモックを注入して `run_session()` を呼ぶことができます。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings（.env 自動読込を含む）
- portfolio/
  - __init__.py
  - portfolio_builder.py — select_candidates, calc_equal_weights, calc_score_weights
  - position_sizing.py — calc_position_sizes
  - risk_adjustment.py — apply_sector_cap, calc_regime_multiplier
- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank
- ai/
  - __init__.py
  - news_nlp.py — score_news（OpenAI 連携）
  - regime_detector.py — score_regime（ETF + マクロニュース）
- monitoring/
  - __init__.py
  - monitoring_db.py — init_monitoring_db, MonitoringDB
  - system_monitor.py — SystemMonitor
  - trade_monitor.py — TradeMonitor
  - risk_monitor.py — RiskMonitor
  - kill_switch.py — KillSwitch
  - alert_manager.py — AlertManager（LINE 通知）
  - monitoring_engine.py — MonitoringEngine
  - streamlit_dashboard.py — Streamlit 監視 UI
- execution/
  - broker_api.py — Protocol / Models / 例外
  - order_manager.py — OrderManager
  - reconciler.py — Reconciler
  - execution_engine.py — ExecutionEngine
  - (その他、order_repository, order_record, risk_manager 等は同階層に存在すると想定)

ドキュメントや設計メモ（例: PortfolioConstruction.md, StrategyModel.md）もリポジトリに含まれる想定です（コード中に参照あり）。

---

## 注意点 / 備考

- 環境変数読み込み
  - 自動ロードは .env, .env.local をプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行います。
  - OS 環境変数を保護するため .env の上書きは制御されています（.env.local は上書き）。
  - テスト時に自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI
  - news_nlp / regime_detector は OpenAI API を呼びます。API キーは環境変数 `OPENAI_API_KEY` または関数引数で渡してください。
  - API レート制限やネットワーク障害に対応するリトライとフェイルセーフ設計がありますが、無償トークンや誤ったプロンプトだと期待した結果にならない点に注意してください。

- DB と時刻
  - 研究処理やニュース集計では「ルックアヘッドバイアス」を避けるため、target_date を明示的に渡し、内部で datetime.today() を参照しない設計になっています。CI/バックテスト時は target_date を固定してください。

- テスト
  - OpenAI 呼び出し部分は内部で呼び出している関数をモック可能に実装しており、ユニットテストでの差し替えが容易です（例: unittest.mock.patch）。

---

必要であれば、以下の追加を作成できます：
- .env.example のサンプルファイル
- 簡易セットアップスクリプト（依存インストール + DB 初期化）
- 実行エンジン / モニタリングエンジンの起動サンプルスクリプト（ローカル用モック Broker を使った例）

どの追加が必要か教えてください。