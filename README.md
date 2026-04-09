# KabuSys

日本株向け自動売買フレームワーク（ライブラリ）です。ポートフォリオ構築、ポジションサイズ計算、ファクター研究、ニュースのLLMによるセンチメント評価、監視・アラート、発注エンジンなどをモジュールごとに提供します。

## 概要
- DuckDB / SQLite を使ったローカルデータ処理と永続化
- kabuステーション等のブローカー API 層を分離した発注エンジン
- ファクター計算・特徴量解析（モメンタム・ボラティリティ・バリュー等）
- OpenAI を使ったニュースセンチメント評価（AIスコア）
- 監視（システム・注文・リスク）と LINE による通知、Streamlit ダッシュボード
- 再起動時のリコンシリエーション（注文・ポジションの同期）とキルスイッチ

設計方針として、可能な限り純粋関数／副作用を分離し、DB・外部API呼び出しの影響を制御する設計になっています。

---

## 機能一覧（主要）
- 環境変数／.env 自動読み込み（settings API）
- Portfolio:
  - シグナル選定（select_candidates）
  - 等金額／スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- Research:
  - モメンタム / ボラティリティ / バリューのファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI:
  - ニュースのセンチメントスコアリング（score_news） — OpenAI（gpt-4o-mini）経由
  - 市場レジーム判定（score_regime） — ETF MA + マクロニュース LLM 合成
- Execution:
  - OrderManager / ExecutionEngine（発注、送信、同期、キャンセル、再起動時のリコンシリエーション）
  - Broker API 抽象プロトコル、OrderRequest/OrderStatus モデル
- Monitoring:
  - SQLite ベースの監視DB（init_monitoring_db / MonitoringDB）
  - System/Trade/Risk モニタ、KillSwitch、AlertManager（LINE）
  - Streamlit ダッシュボード用の簡易 UI

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 必要パッケージをインストール
   必須ライブラリ（例）:
   - duckdb
   - openai
   - requests
   - psutil
   - streamlit

   例:
   ```
   pip install duckdb openai requests psutil streamlit
   ```

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用してください。）

4. 環境変数設定
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、自動的に読み込まれます（起動時に自動ロード）。
   自動ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

5. データベース（初期化）
   - 監視用 SQLite を使う場合は、MonitoringDB を作成して `init_monitoring_db(conn)` を実行してください。
   - DuckDB の prices_daily / raw_financials などのテーブルは利用する用途に応じて準備してください。

---

## 環境変数（主要）
以下は code から読み取れる主な環境変数とデフォルト / 説明です。

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabu API 用）
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用（任意）
- LINE_USER_ID — LINE Push 用（任意）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_FILL_MODE — Paper trading の fill モード（instant|partial|never|reject）デフォルト: instant
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — デフォルト: "0"。1 にすると起動時に kill.flag をクリア
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュールで使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env の自動ロードを無効化

settings オブジェクト経由でアクセスできます:
```
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

---

## 使い方（主な例）

- Portfolio
  ```
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights, calc_position_sizes

  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  ```

- Research（DuckDB コネクションが必要）
  ```
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 3, 20))
  ```

- AI ニューススコアリング
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")
  ```

- 監視 DB 初期化
  ```
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  ```

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- MonitoringEngine をプログラムから使う（例: テストで1回実行）
  ```
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager
  # 必要なオブジェクト（conn, duckdb_conn, order_repo 等）を作成して渡す
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(...), alert_manager=AlertManager(...))
  engine.run_once()  # テスト用に1回だけ実行
  ```

- ExecutionEngine（本番的な利用）
  ExecutionEngine は broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB接続、EngineConfig（target_date など）を渡して使用します。フローは下記:
  - 起動時に Reconciler（存在すれば）を実行して注文・ポジションを整合
  - 指定時刻にシグナルを読み込み Gate を通して発注
  - WebSocket push を受け取って同期・Gate3 チェック
  - 異常時は KillSwitch による停止と全 active 注文のキャンセル

  実運用では PID ファイル、kill.flag の動作や設定に注意してください（settings 経由のパスを使用）。

---

## ディレクトリ構成（抜粋）
src/kabusys 以下の主要ファイル・モジュール:

- kabusys/
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
    - news_nlp.py                  — score_news（OpenAI）
    - regime_detector.py           — score_regime（ETF MA + macro LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py             — MonitoringDB, init_monitoring_db
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                — Broker API Protocol / DataModels / Exceptions
    - order_manager.py             — OrderManager
    - order_repository.py          — (DB側; not shown in snippet)
    - order_record.py              — (状態遷移ロジック; not shown in snippet)
    - execution_engine.py
    - reconciler.py
    - risk_manager.py              — (not shown in snippet)
  - monitoring/ (上記)
  - research/ (上記)
  - ai/ (上記)

（注：上記は提供されたコードスニペットに基づく抜粋です。実際のリポジトリでは追加ファイル／モジュールが存在する可能性があります。）

---

## 注意点 / 実運用のヒント
- OpenAI を使う機能は API キー（OPENAI_API_KEY）が必要です。テスト時はキーを引数で渡すか環境変数で設定してください。
- news_nlp と regime_detector は LLM 呼び出しのリトライやフェイルセーフを備えていますが、API 利用料とレート制限に注意してください。
- .env 読み込みはプロジェクトルートの検出（.git または pyproject.toml）を行います。配布後の環境では自動読み込みがスキップされるケースがあるため、必要なら明示的に環境変数を設定してください。
- ExecutionEngine は発注処理や WebSocket push 処理を含むため、本番運用前に必ずモック／ペーパートレード環境で十分にテストしてください。
- KillSwitch はファイルベースで停止信号を出します。ファイルの存在をサーバ起動時にチェックし、設定に応じてクリア／拒否動作を行います。

---

## ライセンス / 貢献
この README はコードスニペットから自動生成しています。実プロジェクトのライセンスや貢献方法についてはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

不明点や README に追加したいセクション（例えば CLI コマンド、より詳しい設定例、サンプル .env.example）を教えてください。必要に応じて追記します。