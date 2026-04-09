# KabuSys

日本株の自動売買・リサーチ・監視を目的とした軽量ライブラリ群／アプリケーション群です。  
本リポジトリは、ポートフォリオ構築、シグナル→発注エンジン、AI を用いたニュースセンチメント評価、マーケットレジーム判定、監視（アラート／ダッシュボード）などの主要コンポーネントを純粋関数／小さなクラスに分割して実装しています。

主な設計方針：
- DB（DuckDB / SQLite）やブローカー API を明確に分離。純粋関数は副作用を持たない。
- ルックアヘッドバイアスを避けるため、日付参照は呼び出し側で明示指定。
- OpenAI 呼び出し等はフェイルセーフでフォールバック（API 失敗時は処理継続）。
- .env ファイルを自前パーサーで自動ロード（プロジェクトルート検出）する仕組みあり。

---

## 機能一覧

- 設定管理
  - 環境変数/.env ロード自動化（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 各種設定（DB パス、API トークン、稼働モードなど）を Settings オブジェクトで提供

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（スコア降順）
  - 等配分 / スコア加重の重み計算
  - セクター上限適用（apply_sector_cap）
  - レジームに応じた資金乗数（calc_regime_multiplier）
  - 株数決定・単元丸め・コストバッファ対応（calc_position_sizes）

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials テーブル参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク計算

- AI（kabusys.ai）
  - ニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ格納（news_nlp.score_news）
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定（regime_detector.score_regime）

- 発注／実行（kabusys.execution）
  - Broker API 用データモデル・Protocol・例外定義
  - OrderManager（注文作成→送信→同期→キャンセルのワークフロー）
  - Reconciler（起動時の自動復旧・照合）
  - ExecutionEngine（シグナル処理ループと WebSocket push ドレイン）

- 監視 / アラート（kabusys.monitoring）
  - SQLite による監視ログ永続化（MonitoringDB + init_monitoring_db）
  - System / Trade / Risk モニタ、KillSwitch、AlertManager（LINE Push）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

---

## 必要環境（推奨）

- Python 3.10+
- 主な Python パッケージ:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit (監視ダッシュボードを使用する場合)
- 標準ライブラリ: sqlite3, logging, datetime, pathlib, typing, json など

インストール例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
# 開発用
pip install pytest
```

（プロジェクトに requirements.txt がある場合はそれを使用してください）

---

## 環境変数（主要）

自動でプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを止めるには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数：
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabu API パスワード（kabuステーション）
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールで使用）
- LINE 通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / パス関連（任意、デフォルトあり）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
- 動作環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL (デフォルト: INFO)
- その他
  - PAPER_FILL_MODE: instant|partial|never|reject

Settings は `from kabusys.config import settings` で取得できます。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して依存をインストール
   （前述の pip install 参照）

3. .env を作成 / 設定
   - プロジェクトルートに `.env` を作成し、必要な環境変数を記載します。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     ```

4. 監視 DB の初期化（MonitoringDB のスキーマ作成）
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

---

## 使い方（代表的な利用例）

- 設定取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path object
  ```

- ポートフォリオ候補選定・重み付け
  ```python
  from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights

  buy_signals = [{"code":"1234","signal_rank":1,"score":0.8}, ...]
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)  # または calc_equal_weights
  ```

- ポジションサイズ計算
  ```python
  from kabusys.portfolio import calc_position_sizes
  sizes = calc_position_sizes(weights, candidates, portfolio_value=10_000_000, available_cash=1_000_000, current_positions={}, open_prices={...})
  ```

- リサーチ／ファクター計算（DuckDB 接続を渡す）
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

- ニュースセンチメントスコア算出（OpenAI API キー必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026,3,20), api_key=None)  # api_key None → OPENAI_API_KEY を参照
  print(f"written scores: {written}")
  ```

- レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, date(2026,3,20), api_key=None)
  ```

- 監視ダッシュボード起動（Streamlit）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- MonitoringEngine を一度だけ実行（テスト用）
  ```python
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager

  # 必要な依存（SQLite/duckdb/OrderRepository 等）を初期化して渡す
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
  engine.run_once()  # テスト用に1回だけ実行
  ```

- ExecutionEngine（本番用エントリポイントの例）
  - ExecutionEngine の起動には Broker 実装（BrokerAPIProtocol を満たすクラス）、OrderRepository、RiskManager、OrderManager、DuckDB 接続など多くの依存が必要です。  
  - テストではモックを渡して `_process_signals()` や `_drain_push_queue()` を直接呼ぶのが推奨されます。

---

## 自動 .env 読み込みの挙動

- プロジェクトルート（スクリプトの場所ではなく、src/kabusys/config.py の親ディレクトリを起点に .git または pyproject.toml を上方向に探索して決定）にある `.env` を読み込みます。
- 読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）です。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト向け）。

.env のパースはシェルライクな形式に対応（export プレフィックス、クォート、行末コメントの処理等）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理
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
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py
    - execution_engine.py
    - order_manager.py
    - reconciler.py
    - (その他: order_repository, order_record, risk_manager など本リポジトリ全体に実装ファイルが存在する想定)
  - ai/（上記）およびその他のユーティリティ群

上記は本 README に含まれるファイルの抜粋です。各モジュールは小さな関数／クラスで責務を分離しています。

---

## テスト / 開発ノウハウ（簡易）

- 単体テストでは外部 API（OpenAI / Broker API）や filesystem 副作用をモックしてください。news_nlp._call_openai_api や regime_detector._call_openai_api はテストで patch 可能です。
- 環境変数の自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、テスト内で os.environ を制御してください。
- DuckDB はテスト用に一時 DB ファイルを作成し、必要なテーブル（prices_daily / raw_financials / raw_news 等）を用意してから関数を呼び出します。

---

## 補足

- 本 README はコードベースの解説を中心にまとめています。実際のデプロイや本番運用の前には、ブローカー API 実装、権限管理、詳細な監視設定、手数料・スリッページ試験、負荷テストなど追加の作業が必要です。
- セキュリティ上、API キーやパスワードは .env を使う場合でもリポジトリに含めないでください。

---

問題や追加で README に載せたい内容（例: デプロイスクリプト、詳細 API ドキュメント、サンプル .env.example） があれば教えてください。必要に応じて追記・整理します。