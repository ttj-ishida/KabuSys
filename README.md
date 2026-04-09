# KabuSys

日本株自動売買プラットフォームの一部を実装した Python ライブラリ集です。ポートフォリオ構築、リスク制御、ファクターリサーチ、ニュースの NLP スコアリング、監視・アラート、そして発注エンジン周りのコンポーネントを含みます。設計方針は「DB/外部 API へのアクセスを明確に分離」「ルックアヘッドバイアス回避」「フェイルセーフ（部分失敗許容）」です。

主な用途は研究環境でのファクター計算／特徴量解析、AI を使ったニュースセンチメント評価、そして実行エンジン（ExecutionEngine）や監視（MonitoringEngine）の組み合わせによる運用です。

## 主な機能一覧

- 環境/設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

- ポートフォリオ構築（純粋関数、DB参照なし）
  - 候補選定（score / signal_rank ベース）
  - 等金額／スコア加重での重み計算
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap 対応）
  - セクター集中制限適用、レジーム乗数の計算

- リサーチ（DuckDB ベース）
  - Momentum, Volatility, Value ファクター計算（prices_daily / raw_financials テーブル参照）
  - 将来リターン（forward returns）計算
  - IC（Spearman rank）計算、ファクターサマリー

- AI モジュール
  - ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア算出）: batch、リトライ、レスポンス検証、DuckDB への書込
  - レジーム判定（ETF ma200 乖離 + マクロニュース LLM センチメントで bull/neutral/bear 判定）

- 監視 / アラート
  - MonitoringDB（SQLite）ラッパー + スキーマ初期化
  - System / Trade / Risk Monitor（閾値監視、リスクイベント記録）
  - KillSwitch（フラグファイルによる停止シグナル）
  - AlertManager（LINE Push 通知、クールダウン管理）
  - Streamlit ダッシュボード（監視結果の可視化）

- 実行（発注）周り
  - Broker API 層（データモデル・例外・Protocol）
  - OrderManager（状態機械を用いた発注ワークフロー）
  - Reconciler（起動時の自動復旧・リコンシリエーション）
  - ExecutionEngine（シグナル処理 + WebSocket プッシュドレイン、Gate チェック、kill switch 組込）

## 必要要件（想定）

本リポジトリ内のコードは以下を前提に実装されています（バージョン目安）:

- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (ダッシュボード利用時)
  - その他（標準ライブラリのみで実装されている箇所も多い）

実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を明示してください。

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai requests psutil streamlit
   # もしくは requirements.txt / pyproject.toml を用意して pip install -r requirements.txt
   ```

4. パッケージを編集可能モードでインストール（任意）
   ```bash
   pip install -e .
   ```

5. .env を準備
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動読み込みされます。`.env.local` は `.env` を上書きします。

   例（.env.example）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_FILL_MODE=instant
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=0
   CPU_THRESHOLD_PCT=90.0
   MEMORY_THRESHOLD_PCT=85.0
   DISK_THRESHOLD_PCT=90.0
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

6. データベース初期化（監視用 SQLite）
   ```python
   from pathlib import Path
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   Path("data").mkdir(parents=True, exist_ok=True)
   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

7. DuckDB のスキーマ（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets など）は運用側で用意する必要があります。各リサーチ関数の docstring に参照テーブルが記載されています。

## 簡単な使い方 / 例

- 環境設定の取得（settings）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- リサーチ（モメンタム例）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  for r in res[:5]:
      print(r)
  ```

- ニュース NLP スコア付け（AI モジュール）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で渡すか、OPENAI_API_KEY を環境変数に設定
  n_written = score_news(conn, date(2026, 3, 20), api_key=None)
  print(f"wrote {n_written} ai_scores rows")
  ```

- レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  res = score_regime(conn, date(2026,3,20))
  ```

- 監視エンジン（単回実行、テスト用）
  ```python
  import sqlite3, duckdb
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager, init_monitoring_db

  # DB 接続
  mconn = sqlite3.connect("data/monitoring.db")
  dconn = duckdb.connect("data/kabusys.duckdb")
  init_monitoring_db(mconn)

  system = SystemMonitor(mconn, dconn)
  # TradeMonitor は OrderRepository の実装が必要（モック可）
  # RiskMonitor は MonitoringDB を利用
  # KillSwitch/AlertManager を用意して MonitoringEngine を構築
  ```

- Streamlit ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（本番用）  
  ExecutionEngine を使うには Broker の実装（BrokerAPIProtocol）と OrderRepository、RiskManager、OrderManager、DuckDB 接続などが必要です。エンジンの run_session() を呼ぶとセッション（シグナル処理→プッシュドレイン）を実行します。実運用時は PID / kill.flag の管理、Reconciler の使用、監視アラート等と組み合わせてください。

## 主要な環境変数（Settings による取得）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_FILL_MODE（paper trading の挙動）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）

設定取得は kabusys.config.settings 経由で行ってください。未設定の必須値は ValueError が発生します。

## ディレクトリ構成（概要）

以下は `src/kabusys` 以下の主要モジュールです（抜粋）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - (その他: order_record.py, order_repository.py 等は本コードベースに依存)
  - (data/ 以下に pipeline, stats 等の補助モジュールを想定)

※ 上記以外にも補助的なモジュール（data、strategy、execution の追加ファイル）が存在します。実際の全体構成はソースツリーを参照してください。

## 注意事項 / 補足

- DuckDB / SQLite のスキーマはコード内の SQL / docstring に仕様が記載されています。データ投入、マスタ・時系列テーブルの準備は利用者側で行ってください。
- OpenAI API 呼び出しはベストエフォートで失敗時にフォールバックする設計です（全失敗時は 0.0 やスキップ）。API キーの管理には注意してください。
- ExecutionEngine / OrderManager 周りはブローカー実装（BrokerAPIProtocol）に依存します。模擬ブローカーやモックを用意してテストしてください。
- 自動 .env 読込はプロジェクトルート検出を行います。パッケージ化後やテストで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

この README はコードベースの主要部分を要約したものです。詳しい挙動や設計の理由は各モジュールの docstring に記載されていますので、実装を確認しながら利用してください。必要であれば各機能の使い方（例: ExecutionEngine の具体的な初期化例、OrderRepository のインタフェース定義、DuckDB スキーマサンプル）を追記します。どの部分をより詳細にしたいか教えてください。