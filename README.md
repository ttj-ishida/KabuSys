# KabuSys

日本株向けの自動売買／リサーチ基盤コンポーネント群です。DuckDB／SQLite を用いたデータ処理・リサーチ、kabuステーション連携を前提とした発注エンジン、監視（Monitoring）・アラート、LLM を使ったニューススコアリング／レジーム判定などを含みます。

---

## 概要

KabuSys はモジュール化されたライブラリ群で、以下のユースケースを想定しています。

- 局所的なファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索
- ポートフォリオ構築（候補選定・重み付け・株数算出・セクター制約）
- 発注エンジン（ExecutionEngine）と Order 管理（OrderManager / OrderRepository）
- 再起動時のリコンシリエーション（Reconciler）
- 監視（System / Trade / Risk）と通知（LINE）
- LLM（OpenAI）を使ったニュースセンチメントスコアリング（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- 監視ダッシュボード（Streamlit）

設計方針の特徴として、「DuckDB / SQLite によるローカル完結」「本番口座・API への不要なアクセスを避ける」「ルックアヘッドバイアスを排する」などが挙げられます。

---

## 主な機能一覧

- 環境変数 / .env の自動読み込み（src/kabusys/config.py）
- ファクター計算（Momentum / Volatility / Value） — src/kabusys/research/factor_research.py
- ファクター探索・IC・統計サマリー — src/kabusys/research/feature_exploration.py
- ポートフォリオ構築（候補選定・等金額/スコア加重・リスク基づく単元丸め） — src/kabusys/portfolio/*
- 株数算出と投資金額スケーリング（cost_buffer, lot_size 等考慮）
- セクター集中制限・レジーム乗数の適用 — src/kabusys/portfolio/risk_adjustment.py
- ニュース NLP による銘柄別センチメント算出（OpenAI） — src/kabusys/ai/news_nlp.py
- マクロニュース + ETF MA による市場レジーム判定（OpenAI） — src/kabusys/ai/regime_detector.py
- ExecutionEngine：シグナル読取→Gate チェック→発注→WebSocket drain までのセッション管理 — src/kabusys/execution/*
- Reconciler：起動時に未確定注文をブローカー照合して復旧
- 監視層：MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager（LINE） — src/kabusys/monitoring/*
- Streamlit での監視ダッシュボード起動スクリプト — src/kabusys/monitoring/streamlit_dashboard.py

---

## 前提 / 必須ソフトウェア

- Python 3.10 以上（ソースで PEP 604 型記法や | 型を使用）
- pip / 仮想環境推奨

主な Python 依存パッケージ（軽く列挙）:

- duckdb
- openai
- psutil
- requests
- streamlit

（プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作る

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール（例）

   ```
   pip install duckdb openai psutil requests streamlit
   ```

   ※ 実際は pyproject.toml / requirements.txt が提供されていればそれを使用してください。

3. 環境変数の準備

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（src/kabusys/config.py が実装）。自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   代表的な環境変数（サンプル）:

   - JQUANTS_REFRESH_TOKEN — J-Quants 用トークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — アラート送信用
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
   - PAPER_FILL_MODE — Paper Trading の fill モード（instant|partial|never|reject）
   - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
   - KABUSYS_ENV — development | paper_trading | live
   - LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL

   .env の書式はシンプルな KEY=VALUE をサポートします（コメント、export 形式、クォートやエスケープ等に対応）。

4. 監視 DB の初期化（SQLite）

   MonitoringDB のスキーマを作成するユーティリティがあります。監視 DB を初期化するには Python から:

   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（代表的な例）

- settings（環境設定）を参照

  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  duckdb_path = settings.duckdb_path
  ```

- DuckDB を用いたファクター計算（例: Momentum）

  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  # records は [{"date": date, "code": "XXXX", "mom_1m": ..., ...}, ...]
  ```

- ニュースセンチメント（OpenAI）スコア計算

  score_news は OpenAI API キー（引数か OPENAI_API_KEY 環境変数）が必要です。DuckDB に raw_news / news_symbols / ai_scores テーブルが存在することが前提です。

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-XXXX")
  ```

- 市場レジーム判定（OpenAI）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-XXXX")
  ```

  注意: API 失敗時は macro_sentiment=0.0 でフォールバックする等、堅牢性に配慮した実装です。

- 監視ダッシュボード（Streamlit）

  以下で起動します（スクリプト内にも同コマンドの記載あり）:

  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（本番発注セッション）

  ExecutionEngine は Broker 実装（BrokerAPIProtocol を満たす）、OrderRepository、RiskManager、OrderManager、DuckDB 接続などを組み合わせて実行します。実稼働にはブローカークライアントの実装が必要です。テスト環境ではモックを差し込み、_process_signals() / _drain_push_queue() を直接呼んで検証できます。

  （詳細は src/kabusys/execution/* のロジックを参照してください）

---

## 注意点 / 動作設計上のポイント

- .env 自動読み込みはプロジェクトルート（.git か pyproject.toml を基準）を探索して行います。CWD に依存しない実装です。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用など）。
- ai/news_nlp と ai/regime_detector は OpenAI を利用します。API 呼び出しはレート制限や 5xx に対する再試行・フェイルセーフを備えています。
- ExecutionEngine / OrderManager はクラッシュ安全性を配慮しています（OrderSent を DB に残した上で broker 呼び出し、再起動時に Reconciler で復旧）。
- monitoring 側は SQLite を永続化に利用し、streamlit ダッシュボードは読み取り専用で参照可能です（URI に ?mode=ro を付けて開きます）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ初期化、バージョン等
  - config.py — 環境変数 / .env 自動ロードと Settings クラス
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py — ETF MA とマクロ記事を用いた市場レジーム判定
  - portfolio/
    - portfolio_builder.py — 候補選定・重み算出
    - position_sizing.py — 株数算出・スケーリング・lot 単位丸め
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / value / volatility の計算
    - feature_exploration.py — forward returns / IC / summary 統計
  - monitoring/
    - monitoring_db.py — MonitoringDB スキーマと DB 操作用クラス
    - system_monitor.py / trade_monitor.py / risk_monitor.py — 各監視ロジック
    - kill_switch.py — フラグファイルによる停止シグナル
    - alert_manager.py — LINE push 通知
    - monitoring_engine.py — 各監視を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード起動スクリプト
  - execution/
    - broker_api.py — Broker API のデータモデル・Protocol・例外
    - order_manager.py — OrderStateMachine の外向き API
    - execution_engine.py — Signal Pull 型発注エンジン
    - reconciler.py — 再起動時の照合 / 復旧
    - （他: order_repository, order_record, risk_manager 等 想定）
  - monitoring/, portfolio/, research/, ai/ 等は上記に対応するモジュール群

---

## 開発時のヒント

- DuckDB 接続を渡して純粋関数を呼ぶ設計なので、ユニットテストでは in-memory DB や fixture を用いると便利です。
- OpenAI 呼び出し部分は内部で API 呼び出しラッパー（_call_openai_api）を経由している箇所があり、ユニットテスト時はパッチで置き換えやモックを使って API 呼び出しを抑止できます（コメント参照）。
- .env のパースは細かいケース（export 形式、クォート、エスケープ、インラインコメント）に対応しています。

---

## ライセンス / バージョン

パッケージバージョンは src/kabusys/__init__.py 内の __version__ を参照してください（例: "0.1.0"）。

---

この README はコードベースの主要な使用方法・構成をまとめたものです。より詳細な API 仕様や実稼働手順、Broker 実装例、データスキーマ（prices_daily / raw_news / raw_financials / ai_scores / market_regime 等）は別途ドキュメント（設計書・マニュアル）で追記してください。