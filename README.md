# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ/モジュール群）。  
主に戦略の研究、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュースセンチメント評価などの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。  
設計方針のポイント:

- 各機能は可能な限り純粋関数／副作用の少ないモジュールに分離
- DuckDB（時系列株価・財務データ）および SQLite（監視ログ）を永続化に使用
- OpenAI（GPT 系）を用いたニュース/マクロセンチメント評価をサポート（任意）
- 実際のブローカー接続は BrokerAPIProtocol（抽象）を通して行うため差し替え容易
- .env（および .env.local）／環境変数から設定を読み込む軽量な設定管理

バージョン: __version__ = 0.1.0

---

## 主な機能一覧

- ポートフォリオ構築
  - シグナルの選定（select_candidates）
  - 等金額・スコア加重の重み算出（calc_equal_weights, calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリューファクター（calc_momentum, calc_volatility, calc_value）
  - 将来リターン・IC（calc_forward_returns, calc_ic）や統計サマリ

- AI（OpenAI）連携
  - ニュース記事のセンチメント評価と ai_scores への書き込み（score_news）
  - マクロニュース＋ETF MA を用いた市場レジーム判定（score_regime）

- 発注・実行系
  - ExecutionEngine：シグナルループ／WebSocket push ドレイン／kill switch 連携
  - OrderManager：DB と Broker API をつなぐステートマシン（create/send/sync/cancel）
  - Reconciler：起動時の状態復旧・ブローカー照合

- 監視・アラート
  - MonitoringDB：SQLite ベースの監視ログ層（system_status / trade_logs / positions / risk_logs / dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - AlertManager：LINE Push を用いた通知（クールダウン付き）
  - KillSwitch：フラグファイルによる外部停止シグナル
  - Streamlit ダッシュボード（監視画面）

- 設定管理
  - 環境変数・.env 自動ロード（.env, .env.local の優先度）と Settings API

---

## 必要要件（概略）

- Python 3.10+（型アノテーションの union などを使用）
- 主要依存ライブラリ（例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit（ダッシュボード）
- SQLite / ファイルストア（data ディレクトリ等）

具体的な依存バージョンはプロジェクトの pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は最低限 duckdb, openai, requests, psutil, streamlit をインストール）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に .env を置くと自動読み込みされます
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   例: .env (最低限の例)
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   Settings で参照しているその他のキー:
   - KABU_API_BASE_URL（省略時 http://localhost:18080/kabusapi）
   - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
   - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

5. 監視 DB 初期化（MonitoringDB テーブル作成）
   - Python から:
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

---

## 使い方（モジュール別の代表例）

- 環境設定の取得
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- ポートフォリオ構築（シンプルな例）
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

  buy_signals = [
      {"code": "1234", "signal_rank": 1, "score": 2.5},
      {"code": "2345", "signal_rank": 2, "score": 1.0},
      ...
  ]
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(
      weights, candidates, portfolio_value=10_000_000, available_cash=1_000_000,
      current_positions={}, open_prices={"1234": 1200.0, "2345": 800.0}
  )
  ```

- ファクター計算（DuckDB 接続が必要）
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

- ニュース NLP（OpenAI）によるスコアリング
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")
  ```

- レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 監視ダッシュボード（Streamlit）
  - 起動コマンド:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringEngine（定期監視）
  ```python
  import sqlite3, duckdb
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager, MonitoringDB, init_monitoring_db
  # 各種インスタンス生成（OrderRepository / broker 等は呼出側で提供）
  ```

- ExecutionEngine（本番風に動かすには broker, repo, risk_manager などの実装が必要）
  - ExecutionEngine は ExecutionEngine.run_session() を本番エントリポイントとして使用します。
  - 直接利用する場合は、BrokerAPIProtocol を実装したクライアント、OrderRepository（SQLite 実装）、RiskManager、OrderManager、Reconciler 等を組み合わせてインスタンスを作成してください。

---

## 重要な実装上の注意点

- 設定の自動ロード:
  - プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から .env と .env.local を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local（override）> .env（未設定のみセット）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。

- OpenAI の利用:
  - API 呼び出しで失敗（429、ネットワーク、タイムアウト、5xx）は指数バックオフでリトライしますが、最終的に失敗した場合は安全側のフォールバック（例: macro_sentiment=0）を行って例外を投げない設計の箇所があります。
  - score_news / score_regime は api_key 引数を受け取るため、環境変数に頼らず呼び出し時にキーを渡すことも可能です。

- DB 書き込みの冪等性:
  - ai_scores や market_regime などは「削除 → 挿入」の形でコードを限定して書き込み、部分失敗時に既存データを不必要に消さない工夫があります。
  - MonitoringDB.init_monitoring_db は冪等にテーブルを作成します。

- Execution の耐障害性:
  - OrderManager は「OrderSent を DB に永続化してから broker 呼び出し」を行う二相的な永続化を取り、クラッシュ後の Reconciler により復旧できる設計です。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — select_candidates, calc_equal_weights, calc_score_weights
    - position_sizing.py           — calc_position_sizes
    - risk_adjustment.py           — apply_sector_cap, calc_regime_multiplier
  - research/
    - __init__.py
    - factor_research.py           — calc_momentum, calc_volatility, calc_value
    - feature_exploration.py       — calc_forward_returns, calc_ic, factor_summary, rank
  - ai/
    - __init__.py
    - news_nlp.py                  — score_news（OpenAI によるニュースセンチメント）
    - regime_detector.py           — score_regime（ETF MA + マクロセンチメント）
  - execution/
    - broker_api.py                — Broker API の DataModel / Protocol / 例外
    - execution_engine.py          — ExecutionEngine（シグナル処理・push drain）
    - order_manager.py             — OrderManager（ステートマシン）
    - reconciler.py                — 再起動時リコンシリエーション
    - ...（order_repository, order_record 等は同階層に存在）
  - monitoring/
    - __init__.py
    - monitoring_db.py             — MonitoringDB / init_monitoring_db
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - research、portfolio、monitoring、ai モジュール群...
  - その他：data pipeline / stats 等のユーティリティ（duckdb 操作補助）

---

## .env の例（テンプレート）

以下は最低限よく使う設定例です (.env.example を参考に作成してください)。

```
# API / 認証
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# DB / パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# システム設定
KABUSYS_ENV=development
LOG_LEVEL=INFO

# 安全系
PID_FILE_PATH=data/execution.pid
KILL_FLAG_PATH=data/kill.flag
KILL_FLAG_CLEAR_ON_START=0

# 監視閾値（任意）
CPU_THRESHOLD_PCT=90.0
MEMORY_THRESHOLD_PCT=85.0
DISK_THRESHOLD_PCT=90.0
```

---

## 開発・拡張のポイント

- BrokerAPIProtocol に準拠するクライアントを実装すれば、実ブローカー / モック双方で ExecutionEngine を動かせます。
- DuckDB に格納されるテーブル（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime など）を用意することで、local 環境でリサーチや AI 評価を再現できます。
- Streamlit ダッシュボードは読み取り専用で監視情報を可視化します。運用中の監視には MonitoringEngine と組み合わせて使ってください。

---

ご不明点・追加で README に記載したい項目（CI・デプロイ手順・テスト実行例など）があれば教えてください。必要に応じて README を拡張します。