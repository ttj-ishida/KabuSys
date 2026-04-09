# KabuSys

KabuSys は日本株の自動売買システム（バックテスト／運用補助／監視ツール群）を目的とした Python コードベースです。本リポジトリはポートフォリオ構築、ポジションサイジング、ファクター研究、ニュース NLP によるセンチメント算出、市場レジーム判定、発注エンジン、監視（モニタリング）といった機能群を持ちます。

主に DuckDB / SQLite を使ったローカルデータ処理と、OpenAI（LLM）を活用したニュース分析を組み合わせる設計です。実際の発注は kabuステーション等のブローカー API をラップしたクライアント経由で行います。

---

## 主な機能一覧

- 環境変数 / .env の自動読み込みと設定管理（kabusys.config）
- ポートフォリオ構築
  - 候補選定（スコア順）
  - 等金額配分 / スコア加重配分
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
  - セクター集中制限（セクターキャップ）とレジーム乗数
- リサーチ / ファクター計算
  - Momentum（1M/3M/6M、MA200乖離）
  - Volatility（20日 ATR、出来高・売買代金）
  - Value（PER、ROE）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- ニュース NLP（OpenAI）による銘柄別センチメントスコア算出（ai.news_nlp）
- 市場レジーム判定（ETF MA200 とマクロニュースの LLM センチメントを合成）
- 発注周り（OrderManager / ExecutionEngine）
  - 注文作成 → 送信 → 同期（Reconciler）までの耐障害設計
  - Gate チェック（シグナル／実行／ドローダウン）
- 監視（Monitoring）
  - system / trade / risk の監視
  - SQLite ベースの監視 DB（init_monitoring_db, MonitoringDB）
  - LINE push 通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード

---

## 動作要件（想定）

- Python 3.10+
- パッケージ（主なもの）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (監視ダッシュボード利用時)
- 標準ライブラリ: sqlite3, logging, datetime, pathlib など

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 無い場合の例:
     ```
     pip install duckdb openai requests psutil streamlit
     ```

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。

   例（.env）
   ```
   # OpenAI
   OPENAI_API_KEY=sk-xxxx...

   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxx

   # Kabu API
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # LINE 通知（任意）
   LINE_CHANNEL_ACCESS_TOKEN=xxxx
   LINE_USER_ID=Uxxxxxxxxxxxx

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. 監視 DB の初期化（監視機能を使う場合）
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（代表的な例）

- 設定にアクセスする
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  ```

- リサーチ（Momentum）を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- ニューススコア算出（OpenAI API キー必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None なら env を参照
  print(f"scored {n} codes")
  ```

- 市場レジーム判定（Regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine の起動（運用環境での例）
  ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続、EngineConfig などを注入して実行します。簡易的な流れは以下の通り（実運用では broker 実装や DB 初期化が必要です）:

  ```python
  from datetime import date, time
  import duckdb
  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
  # broker, repo, risk_manager, order_manager, reconciler は実装済みインスタンス
  conn = duckdb.connect("data/kabusys.duckdb")
  config = EngineConfig(target_date=date.today(), signal_send_start=time(8,50), signal_send_end=time(9,10))
  engine = ExecutionEngine(broker, repo, risk_manager, order_manager, conn, config, reconciler)
  engine.run_session()
  ```

  （※ 実行前に kill.flag の存在や PID 書き込み権限に注意してください）

---

## 注意事項 / 実装上のポイント

- .env の自動ロード順序:
  OS 環境変数 > .env.local > .env の優先度で読み込みます。プロジェクトルートが検出できない場合は自動ロードをスキップします。
- 自動ロードを無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- OpenAI 呼び出しはリトライやフォールバック（失敗時は 0.0 等）を備えていますが、API キーの設定は必須な機能もあります（例: news_nlp.score_news, regime_detector.score_regime）。
- DuckDB / SQLite のスキーマやテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）は別途準備が必要です。
- 発注・ブローカー周りの実装は BrokerAPIProtocol に依存します。実際に本番注文を行う際はブローカークライアントを用意してください。
- 価格が欠損している場合の扱い（0.0）による挙動や、lot_size（単元株）に関する制約などがコード内にコメントされています。運用前に設定値を確認してください。

---

## ディレクトリ構成（抜粋）

代表的ファイル・モジュール一覧（src/kabusys 配下）

- src/
  - kabusys/
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
      - risk_monitor.py
      - trade_monitor.py
      - system_monitor.py
      - alert_manager.py
      - kill_switch.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - broker_api.py
      - execution_engine.py
      - order_manager.py
      - reconciler.py
      - (その他: order_repository, order_record, risk_manager など)
    - (data/)  ※ prices_daily / raw_financials 等にアクセスするモジュールが存在（別ファイル）
    - (その他ユーティリティ)

---

## 開発・テスト時のヒント

- テストや CI 環境で .env 自動ロードを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しをユニットテストから除外するには、news_nlp._call_openai_api や regime_detector._call_openai_api をモックします（ドキュメント中にテスト差し替え意図が記載されています）。
- DuckDB のローカル DB を使ったリサーチ機能は外部 API を呼ばない設計です（prices_daily / raw_financials テーブルのみ参照）。

---

プロジェクトの詳細設計（PortfolioConstruction.md、StrategyModel.md 等）やデータスキーマはソースコード内の docstring やコメントにも多く記載されています。実運用する際はそれらの設計文書を参照した上で、DB スキーマ・ブローカー設定・リスクパラメータを適切に調整してください。