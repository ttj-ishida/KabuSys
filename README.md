# KabuSys

日本株のアルゴリズム売買・研究・監視プラットフォームの軽量実装（モジュール群のみ）。  
このリポジトリは「ポートフォリオ構築」「ファクター研究」「AI を使ったニュースセンチメント」「監視」「発注エンジン」などの主要機能を純粋関数／レイヤ分離で実装しています。

主な設計方針
- DuckDB / SQLite をローカル DB に用いる（外部 API への依存を最小化）
- 本番向けの安全弁（リコンシリエーション、kill switch、リスクゲート）を備える
- OpenAI 等の外部 API 呼び出しは分離され、テスト時は差し替え可能
- .env 自動ロード機能を提供（プロジェクトルートを .git または pyproject.toml で判定）

---

## 機能一覧

- ポートフォリオ構築（選定・重み付け・リスク調整・株数算出）
  - select_candidates / calc_equal_weights / calc_score_weights
  - apply_sector_cap / calc_regime_multiplier
  - calc_position_sizes（risk_based / equal / score）
- リサーチ（ファクター計算・将来リターン・IC・統計）
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- AI（ニュース NLP、レジーム判定）
  - ニュースのセンチメントを OpenAI に問い合わせて ai_scores に書き込む（score_news）
  - ETF + マクロニュースを組合せて市場レジーム判定（score_regime）
- 発注・実行（OrderManager / ExecutionEngine / Reconciler）
  - Order 状態管理、送信、同期、キャンセル、起動時リコンシリエーション
  - ExecutionEngine によるシグナル処理・WebSocket ドレイン・Gate によるリスク管理
- 監視（Monitoring）
  - MonitoringDB（SQLite スキーマ + 永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE Push）
  - Streamlit ダッシュボード（簡易可視化）

---

## 前提（推奨）

- Python 3.10+（typing と新しい構文を利用）
- 必要なライブラリ（例）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit
- 任意で仮想環境（venv / pyenv など）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
# 開発インストール (パッケージとして使う場合)
pip install -e .
```

（requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## 環境変数／設定

このパッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主要の環境変数（設定名とデフォルト/説明）:

- 認証 / API
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime の api_key 引数でも指定可）
  - LINE_CHANNEL_ACCESS_TOKEN — AlertManager 用（空なら送信をスキップ）
  - LINE_USER_ID — AlertManager 宛先（空なら送信をスキップ）

- DB / パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)

- 動作モード / ログ
  - KABUSYS_ENV (development | paper_trading | live) (default: development)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (default: INFO)

- Paper Trading
  - PAPER_FILL_MODE (instant | partial | never | reject) (default: instant)

- 監視 / PID / Kill flag
  - PID_FILE_PATH (default: data/execution.pid)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (1/0) (default: 0)
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（数値、監視用閾値）

- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化（テスト時に有用）

注意:
- .env のパース実装はコメント行、export 形式、クォート・エスケープ等に対応しています。
- 必須変数が未設定の場合、Settings プロパティは ValueError を投げます。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
2. 依存パッケージをインストール（上の推奨パッケージ参照）
3. プロジェクトルートに `.env` を作成（.env.example を参考に）
   - 例（最低限）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     OPENAI_API_KEY=sk-...
     LINE_CHANNEL_ACCESS_TOKEN=
     LINE_USER_ID=
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
4. 監視 DB 初期化（MonitoringDB スキーマ作成）:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```
5. DuckDB のスキーマ / テーブル（prices_daily, raw_financials 等）を準備する（研究機能で必要）。

---

## 使い方（主要 API / 実行例）

- Settings 利用例:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)         # Path オブジェクト
  print(settings.is_live, settings.log_level)
  ```

- リサーチ（DuckDB 接続が必要）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュース NLP（OpenAI を使う）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  ```

  - テスト時は内部の API 呼び出し関数をモックしてください（_call_openai_api をパッチ）。

- レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 監視コンポーネント（簡単な実行）:
  ```python
  import sqlite3, duckdb
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager

  mon_conn = sqlite3.connect("data/monitoring.db")
  duck_conn = duckdb.connect("data/kabusys.duckdb")
  system = SystemMonitor(mon_conn, duck_conn)
  # TradeMonitor requires OrderRepository instance; RiskMonitor uses MonitoringDB
  # MonitoringEngine を組み立てる場合は各依存を渡す
  ```

- Streamlit ダッシュボード（監視 DB を開いて表示）:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（本番的な起動は複数の依存注入が必要）:
  - broker（BrokerAPIProtocol 実装）
  - OrderRepository（SQLite 実装）
  - RiskManager / OrderManager / Reconciler（必要に応じて）
  - duckdb_conn と EngineConfig を渡して run_session() を呼び出す

  実際の利用では各インタフェース（broker 等）を具象実装して DI してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings
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
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py
  - execution_engine.py
  - order_manager.py
  - reconciler.py
  - (その他: order_repository, order_record, risk_manager などが想定)
- research / data 関連モジュール（duckdb・統計ユーティリティ等）
- その他ユーティリティ・データ層（data.pipeline, data.stats 等）

---

## 注意点 / 実運用のヒント

- OpenAI や broker API キーは安全に管理してください。.env は .gitignore に入れるのが基本です。
- score_news / score_regime の OpenAI 呼び出しは外部 API でコストがかかり、レート制限や失敗を想定しているためログ・リトライの挙動を理解した上で運用してください。
- ExecutionEngine は kill.flag / PID ファイルを用いてプロセス管理を行います。デプロイ時は OS 側のプロセスマネージャ（systemd 等）との連携方法を検討してください。
- テスト時は外部呼び出しをモックし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って環境の影響を切り離すと良いです。
- DuckDB / SQLite のスキーマ（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime / signals / portfolio_targets 等）は、各機能の前提となります。研究や AI 処理を使う前にテーブルを準備してください。

---

## 貢献 / テスト

- ユニットテストは各純粋関数（portfolio, research, monitoring の一部）を中心に書きやすい設計です。
- 外部 API を呼ぶ所は _call_openai_api を差し替え、ネットワークの副作用を排除してください。
- 自動 .env ロードはプロジェクトルート検出（.git / pyproject.toml）を行うため、テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

---

必要に応じて README に具体的な起動スクリプト例（systemd ユニット、Dockerfile、docker-compose）や DB スキーマ定義を追加できます。どの部分を詳しく補足したいか教えてください。