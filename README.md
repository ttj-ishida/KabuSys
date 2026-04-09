# KabuSys

日本株の自動売買 / リサーチ / 監視を目的とした小型フレームワーク (プロトタイプ)。  
このリポジトリは、ポートフォリオ構築、ポジションサイジング、ファクター計算、ニュースのLLMセンチメント評価、市場レジーム判定、監視／アラートなどの機能をモジュール化して提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の関心事を分離した設計を採用しています。

- ポートフォリオ構築（候補選定・重み付け・リスク調整・株数決定）
- 研究（ファクター計算、将来リターン・IC 計算など）
- AI モジュール（ニュース記事のセンチメント評価、マクロセンチメント→レジーム判定）
- 実行（OrderManager / ExecutionEngine / Broker API プロトコル）
- 監視（システム状態、注文滞留、リスク検出、LINE 通知、Streamlit ダッシュボード）
- 設定管理（.env / 環境変数の自動読み込み、Settings クラス）

設計方針の一部:
- データ層は DuckDB / SQLite を想定
- 本番ブローカー API 呼び出しは BrokerAPIProtocol を通して分離
- LLM 呼び出し（OpenAI）はフェイルセーフ（失敗時にスコアを 0.0 などでフォールバック）
- 自動ロードされる .env はプロジェクトルート (.git または pyproject.toml) を起点に探索

---

## 主な機能一覧

- 設定:
  - settings オブジェクト経由で環境変数にアクセス（例: settings.jquants_refresh_token）
  - .env / .env.local の自動読み込み（環境変数優先、.env.local で上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

- ポートフォリオ:
  - select_candidates（スコア降順で候補選定）
  - calc_equal_weights / calc_score_weights（重み付け）
  - apply_sector_cap（セクター集中制限）
  - calc_regime_multiplier（市場レジームに応じた乗数）
  - calc_position_sizes（株数・lot 単位丸め・aggregate cap）

- 研究:
  - calc_momentum / calc_volatility / calc_value（DuckDB 上の prices_daily / raw_financials を用いる）
  - calc_forward_returns / calc_ic / factor_summary（ファクター探索用ユーティリティ）
  - zscore_normalize（data.stats に実装されている想定）

- AI:
  - score_news: raw_news を集約して OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores テーブルへ書き込み
  - score_regime: ETF 1321 の MA200 とマクロニュースの LLM センチメントを組み合わせて market_regime に書き込み

- 実行 / 発注:
  - OrderManager（作成 → 送信 → 同期 → キャンセルのフロー管理）
  - Reconciler（起動時の注文／ポジション照合）
  - ExecutionEngine（Signal Queue Pull 型の発注エンジン、WebSocket push ドレイン）

- 監視:
  - MonitoringDB（SQLite に監視ログを永続化）
  - SystemMonitor / TradeMonitor / RiskMonitor（定期チェック）
  - AlertManager（LINE Push による通知、クールダウン管理）
  - KillSwitch（フラグファイルで ExecutionEngine を安全停止）
  - Streamlit ダッシュボード（監視情報の可視化）

---

## 依存パッケージ（主なもの）

プロジェクト内の各モジュールは以下のようなパッケージを利用します（環境に応じて必要なものをインストールしてください）:

- Python 3.10+
- duckdb
- openai
- requests
- psutil
- streamlit

requirements.txt が無い場合は手動でインストールしてください:
pip install duckdb openai requests psutil streamlit

---

## セットアップ手順

1. リポジトリをクローン
   git clone <このリポジトリ>

2. 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール
   pip install duckdb openai requests psutil streamlit

4. データディレクトリ作成（必要に応じて）
   mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD が未設定時）。  
   - 主要な環境変数は下記「環境変数一覧」を参照してください。

6. 監視用 SQLite DB 初期化
   以下のワンライナーで monitoring DB のテーブルを作成できます:
   python -c "import sqlite3; from kabusys.monitoring import init_monitoring_db; conn=sqlite3.connect('data/monitoring.db'); init_monitoring_db(conn); print('monitoring.db initialized')"

---

## 環境変数一覧（主なもの）

- 必須（モジュール利用時）
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（settings.jquants_refresh_token）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（settings.kabu_api_password）
  - OPENAI_API_KEY: OpenAI API を用いる AI モジュールで必要（score_news / score_regime）

- 任意（デフォルトあり）
  - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager の LINE 通知用
  - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH: デフォルト "data/monitoring.db"
  - PAPER_FILL_MODE: Paper Trading 時の fill モード（instant|partial|never|reject、デフォルト "instant"）
  - PAPER_TRADING_SQLITE_PATH: デフォルト "data/paper_trading.db"
  - PID_FILE_PATH: デフォルト "data/execution.pid"
  - KILL_FLAG_PATH: デフォルト "data/kill.flag"
  - KILL_FLAG_CLEAR_ON_START: "1" の場合、起動時に kill.flag を自動クリアする
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値のデフォルトはコード内参照（90/85/90）
  - KABUSYS_ENV: "development" (default) | "paper_trading" | "live"
  - LOG_LEVEL: "DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL"

自動 .env 読み込み:
- 起動時にプロジェクトルート（.git または pyproject.toml を持つディレクトリ）を探索して `.env` → `.env.local` の順に読み込みます。
- 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（簡易例）

※ ここに示すのはモジュール呼び出し例です。実際の実行には DuckDB/SQLite のテーブル構造・データ、BrokerAPI 実装などが必要です。

- Settings の利用例:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
db_path = settings.duckdb_path  # Path オブジェクト
```

- DuckDB を使ったファクター計算:
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
results = calc_momentum(conn, date(2026, 3, 20))
```

- ニュースセンチメントのスコアリング（AI）:
```python
from datetime import date
import duckdb
from kabusys.ai import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

- 監視 DB 初期化（上記セットアップ参照）:
```python
import sqlite3
from kabusys.monitoring import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

- Streamlit ダッシュボード起動:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- ExecutionEngine の概念的な起動（実際は BrokerAPI 実装などが必要）:
```python
from datetime import date, time
import duckdb
import sqlite3
# broker: BrokerAPIProtocol 実装
# repo: OrderRepository のインスタンス
# risk_manager, order_manager: 実装済みのインスタンス
from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig

duck = duckdb.connect("data/kabusys.duckdb")
orders_conn = sqlite3.connect("data/orders.db")
config = EngineConfig(target_date=date(2026,3,20))
engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duck, config)
engine.run_session()
```

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（提供コードに基づくスナップショット）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュースの LLM センチメント評価（score_news）
    - regime_detector.py          — マクロ + MA200 で市場レジーム判定（score_regime）
  - portfolio/
    - __init__.py
    - portfolio_builder.py        — 候補選定・重み計算
    - risk_adjustment.py          — セクター制限・レジーム乗数
    - position_sizing.py          — 株数計算・aggregate cap
  - research/
    - __init__.py
    - factor_research.py          — momentum/volatility/value 計算
    - feature_exploration.py      — 将来リターン / IC / summary
  - monitoring/
    - __init__.py
    - monitoring_db.py            — MonitoringDB 初期化 + 操作
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py               — Broker API のデータモデル・Protocol・例外
    - order_manager.py
    - reconciler.py
    - execution_engine.py
    - (ほか: order_record.py, order_repository.py 等が想定される)
  - monitoring/ (上記)
  - research/ (上記)
  - その他: data パッケージや stats 周りが想定される（このスナップショットでは参照あり）

実際のリポジトリではさらに data, execution の詳細実装や tests が存在する想定です。

---

## 注意点 / 運用上のメモ

- .env のパースは非常に寛容かつ慎重に設計されています。クォートやエスケープ、コメント処理を考慮しますが、予期しない行はスキップされます。
- 自動 .env 読み込みはプロジェクトルートの検出に .git または pyproject.toml を使用するため、配布パッケージや別パスでの実行時に期待通り動かない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数をセットしてください。
- OpenAI API を用いる処理は外部 API 呼び出しを含むため、API 料金とレート制限に注意して運用してください。モジュールはリトライとフォールバックを実装していますが、頻繁な呼び出しは避けてください。
- ExecutionEngine は PID ファイルと kill.flag を扱います。複数プロセスの同時実行や残留ファイルに注意してください。KILL_FLAG_CLEAR_ON_START 環境変数で起動時の挙動を制御できます。
- 実ブローカー接続を行う際は BrokerAPIProtocol を満たす実装を用意し、十分にテストを行ってください（paper trading モードや mock broker の利用を推奨）。

---

## 参考 / 追加情報

- 各モジュールの docstring に設計ノートや期待する DB スキーマ、入力／出力の詳細が記載されています。実装や運用時は該当モジュールの docstring を参照してください。
- DuckDB / SQLite 上のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets など）は一部モジュールで参照されます。実行前に必要なテーブルが存在し、データが投入されていることを確認してください。

---

README の内容は現状のコードスナップショットに基づく概略です。より具体的な例・スクリプト・テーブル定義が必要であれば、用途（研究・バックテスト・実運用）の優先度に合わせて追記します。