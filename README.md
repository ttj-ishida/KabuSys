# KabuSys

日本株向け自動売買システム用ライブラリ（モジュール群）。ポートフォリオ構築、ポジションサイズ計算、ファクターリサーチ、AI ニュースセンチメント、マーケットレジーム判定、監視機能、発注エンジン周りのユーティリティを提供します。

---

## 概要

KabuSys は以下の責務をモジュールごとに分離したライブラリです。

- ポートフォリオ構築（銘柄選定・配分・リスク調整・株数決定）
- リサーチ（モメンタム・ボラティリティ・バリュー等のファクター計算、特徴量探索）
- AI（ニュースのセンチメント解析、マクロセンチメントと MA を組み合わせたレジーム判定）
- 監視（システム・注文・リスク監視、LINE 通知、ダッシュボード）
- 発注・実行（Order state machine、ブローカー API 抽象、再同期／リコンシリエーション）
- 環境変数 / 設定管理

設計方針として「本番ブローカーへの不必要なアクセスを避ける」「ルックアヘッドバイアスを避ける」「DB 書き込みは冪等に」「外部 API 呼び出しは明示的に行いリトライ/フォールバックを行う」等が採用されています。

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）／必要環境変数の取得（`kabusys.config.settings`）
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額・スコア加重の重み計算
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（risk-based / equal / score 配分、単元丸め、aggregate cap）
- リサーチ
  - momentum / volatility / value ファクター計算（DuckDB 接続で prices_daily, raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- AI
  - ニュースを LLM（OpenAI）でセンチメント付与し ai_scores に書き込む（`kabusys.ai.score_news`）
  - マクロニュース + ETF MA による市場レジーム判定（`kabusys.ai.score_regime`）
  - LLM 呼び出しはリトライ・バックオフ、失敗時フォールバック等の安全策あり
- 監視
  - MonitoringDB（SQLite）による永続化層と API（system_status / trade_logs / positions / risk_logs / dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE 通知）
  - Streamlit ベースの監視ダッシュボード
- 発注・実行
  - BrokerAPI の Protocol 定義とデータモデル
  - OrderManager（State Machine）、ExecutionEngine（シグナル処理 + WebSocket ドレイン）
  - Reconciler（起動時の自動復旧・ポジション照合）

---

## 要件（推奨）

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit
- 標準ライブラリ: sqlite3, logging, datetime など

（実際のプロジェクトでは `pyproject.toml` / requirements.txt を参照してください）

---

## セットアップ手順（開発）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境の作成と有効化
   - python -m venv .venv
   - source .venv/bin/activate  # (Unix)
   - .venv\Scripts\activate     # (Windows)

3. 依存パッケージをインストール（例）
   - pip install duckdb openai requests psutil streamlit

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨される .env のキー（一例）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABU_API_BASE_URL=http://localhost:18080/kabusapi
- OPENAI_API_KEY=...
- LINE_CHANNEL_ACCESS_TOKEN=...
- LINE_USER_ID=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

サンプル（.env.example）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な例）

※ 実行には DuckDB/SQLite データベースや Broker 実装が必要です。以下は利用例と呼び出し方の概要です。

### 設定の取得
Python から設定を読む例:
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path  # pathlib.Path
```

### リサーチ（ファクター計算）
DuckDB 接続を渡してファクターを計算：
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect(database="data/kabusys.duckdb", read_only=False)
target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
```

### AI ニューススコアリング
OpenAI API キーが必要。DuckDB 接続を渡して ai_scores テーブルに書き込みます。
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(database="data/kabusys.duckdb")
written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"wrote {written} scores")
```

### レジーム判定
マクロニュースと ETF MA を用いて market_regime テーブルへ書き込みます。
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(database="data/kabusys.duckdb")
score_regime(conn, date(2026, 3, 20), api_key="sk-...")
```

### 監視 DB 初期化
MonitoringDB 用スキーマを作成します（SQLite）。
```python
import sqlite3
from kabusys.monitoring import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

### Streamlit ダッシュボード起動
監視 DB を読み込む read-only モードで起動できます。
コマンド:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

### ExecutionEngine（発注エンジン）
ExecutionEngine は Broker 実装（BrokerAPIProtocol に従う）、OrderRepository、RiskManager、OrderManager、DuckDB 接続等を渡して使用します。実稼働環境ではこれらの実装が必要です。簡略例（擬似）:
```python
from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig

# broker, repo, risk_manager, order_manager, duckdb_conn を用意する必要があります
engine = ExecutionEngine(
    broker=broker,
    repo=order_repo,
    risk_manager=risk_manager,
    order_manager=order_manager,
    duckdb_conn=duckdb_conn,
    config=EngineConfig(target_date=date.today()),
)
engine.run_session()
```
（Broker 実装は外部に依存するため、プロジェクトに合わせて実装してください）

---

## 注意点 / 運用上のポイント

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を自動読み込みします。
  - 読み込み順は OS 環境 > .env > .env.local（.env.local が override=True で後勝ち）。
  - テストなどで自動読込を無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出し:
  - API 呼び出しはリトライやフォールバックを行う設計ですが、API キーは必須です（`OPENAI_API_KEY` または関数引数で指定）。
  - レスポンスが期待フォーマットでない場合は安全にスキップします（例外を投げずフォールバック）。
- データベース:
  - DuckDB は価格・ファクトテーブル（`prices_daily` / `raw_financials` / `raw_news` 等）を前提にしています。必須スキーマは各関数の docstring を参照してください。
  - MonitoringDB（SQLite）は `init_monitoring_db()` で作成できます。
- Kill / PID:
  - ExecutionEngine は PID ファイルの書き込み、kill.flag による停止、起動時の kill.flag 処理（`KILL_FLAG_CLEAR_ON_START` で挙動変更）を行います。
- フェイルセーフ:
  - 多くの箇所で API 失敗やデータ欠損時に安全にフォールバックする実装になっています（例: LLM の失敗、DB マイグレーション、price 欠損など）。
- 型・互換性:
  - Python 3.10 以上を想定（`|` 型や typing 記法を使用）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数 / .env ローディング、Settings オブジェクト
- portfolio/
  - __init__.py
  - portfolio_builder.py         — 候補選定・重み計算
  - risk_adjustment.py          — セクター制限、レジーム乗数
  - position_sizing.py          — 株数計算・ aggregate cap
- research/
  - __init__.py
  - factor_research.py          — momentum / volatility / value 計算
  - feature_exploration.py      — 将来リターン・IC・統計サマリ
- ai/
  - __init__.py
  - news_nlp.py                 — ニュースセンチメント（OpenAI 呼び出し）
  - regime_detector.py          — マクロ + MA によるレジーム判定
- monitoring/
  - __init__.py
  - monitoring_db.py            — SQLite スキーマ / MonitoringDB
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py               — Broker API の Protocol / データモデル / 例外
  - order_manager.py
  - order_repository.py         — （DB 操作ファイルがここにある想定）
  - reconciler.py
  - execution_engine.py
  - risk_manager.py             — （リスクガードの実装）
  - order_record.py             — OrderState 等
- monitoring/ (上記)
- research/ (上記)
- その他モジュール（data などは present されていませんがプロジェクト内に存在する想定）

---

## 開発・貢献

- コードスタイル・テスト・CI 等はリポジトリの方針に従ってください。
- OpenAI キーや API 周りは機密情報のため、`.env.local` や CI シークレットで管理してください。
- 新しい Broker 実装は `BrokerAPIProtocol` を実装して提供してください。

---

この README はコードベースの主要機能・使い方のサマリです。各モジュールの詳しい使い方や DB スキーマは該当ソースの docstring を参照してください。必要であれば README に追記したいコマンド例や具体的なセットアップ（Docker / systemd サービスなど）を追加します。どの情報を補足しますか？