# KabuSys

日本株向けの自動売買 / 研究・監視フレームワーク（ライブラリ）です。  
ポートフォリオ構築、ポジションサイズ計算、ファクター計算、ニュースのLLMベースセンチメント評価、市場レジーム判定、監視・アラート、発注エンジン／注文状態管理など、実運用を想定したコンポーネント群を含みます。

主な設計方針
- 各モジュールは可能な限り純粋関数あるいは副作用を限定したクラスとして実装
- DuckDB / SQLite を用いたローカルデータ層（本番APIを呼ばない解析モジュールも存在）
- OpenAI（gpt-4o-mini）を利用したニュースNLP / レジーム判定の統合（APIキー必須）
- .env / 環境変数による設定管理（自動ロード機能あり）

---

## 機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - Settings オブジェクト経由で各種設定にアクセス

- ポートフォリオ構築（kabusys.portfolio）
  - シグナルから候補選定（select_candidates）
  - 等金額 / スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（risk-based / equal / score; 単元株丸め・コストバッファ対応）
  - セクター集中制限適用（apply_sector_cap）
  - 市場レジーム乗数（calc_regime_multiplier）

- リサーチ（kabusys.research）
  - Momentum / Volatility / Value ファクター計算（DuckDB の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（kabusys.ai）
  - ニュース記事のセンチメントスコアリング（OpenAI API を用いる、ai_scores へ書き込み）
  - 市場レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメントを合成）

- 監視（kabusys.monitoring）
  - MonitoringDB（SQLite）: system_status / trade_logs / positions / risk_logs / dashboard テーブル
  - 各種モニタ（SystemMonitor / TradeMonitor / RiskMonitor）
  - AlertManager（LINE Push を利用）
  - KillSwitch（フラグファイルで Execution を停止）
  - Streamlit ダッシュボード（監視用）

- 実行・発注（kabusys.execution）
  - Broker API 抽象（Protocol）
  - OrderManager（Order state machine）
  - ExecutionEngine（シグナル取得→Gate チェック→発注→push ドレイン）
  - Reconciler（起動時リコンシリエーション）
  - 各種例外・モデル（OrderRequest / OrderStatus / Position 等）

---

## セットアップ手順

前提
- Python 3.10+（型記法や union 演算子 (|) を使っているため）
- ネットワーク接続（OpenAI API を利用する場合）

推奨パッケージ（最小限）
- duckdb
- openai
- streamlit
- psutil
- requests

例: 仮想環境を作成して必要パッケージをインストールする
```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb openai streamlit psutil requests
```

環境変数 / .env
- プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（.git または pyproject.toml を基準にルート検出）。
- 自動ロードを無効化するには：`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。

主な環境変数（コード上で参照されるもの）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（AlertManager で通知する場合）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE（paper trading の挙動: instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（"1" で起動時に kill.flag を自動クリア）
- KABUSYS_ENV（development | paper_trading | live、デフォルト development）
- LOG_LEVEL（DEBUG|INFO|...、デフォルト INFO）

ファイル権限やディレクトリ作成は一部モジュールで自動作成されます（例: PID / data ディレクトリ）。

---

## 使い方（代表的な例）

設定参照
```python
from kabusys.config import settings

print(settings.duckdb_path)   # Path オブジェクト
print(settings.is_paper)
```

DuckDB を使ったファクター計算
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
result = calc_momentum(conn, date(2026, 3, 20))
# result は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

ニュース NPL スコアリング（OpenAI API キー必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} scores")
```

MonitoringDB 初期化（SQLite）
```python
import sqlite3
from kabusys.monitoring import init_monitoring_db

conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(conn)
```

Streamlit ダッシュボード起動
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

ExecutionEngine の起動（概要・実運用では Broker 実装 / OrderRepository 等が必要）
- ExecutionEngine は多数の依存（BrokerAPI の具体実装、OrderRepository、RiskManager、DuckDB 接続等）を必要とします。テストではモックを差し替えて部分的に利用できます。
- 実行例（概念）:
```python
from datetime import date, time
import duckdb, sqlite3
from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
# broker, repo, risk_manager, order_manager, reconciler は各自の実装/モックを用意
engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
engine.run_session()
```

注意
- AI モジュール使用時は OpenAI API のコスト／レート制限に注意してください。429 や 5xx は内部でリトライ／フォールバック処理がありますが、APIキー未設定では例外が発生します。
- research モジュールは prices_daily / raw_financials 等のテーブルが存在する DuckDB を前提とします。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- __version__ = "0.1.0"

サブパッケージと主なファイル
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
  - system_monitor.py
  - trade_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py
  - order_manager.py
  - order_repository.py   # （参照: repo 層がある想定。コードベースに依存）
  - order_record.py
  - order_operations...
  - execution_engine.py
  - reconciler.py
  - risk_manager.py
- data/ (想定データ格納場所)
  - kabusys.duckdb (デフォルトパス)
  - monitoring.db (SQLite)
- その他:
  - README.md（本ファイル）
  - pyproject.toml / .git （プロジェクトルートの検出に利用）

（コードベースは上記に加え細かな補助モジュールが含まれます。README 用に主要ファイルのみ列挙しています。）

---

## 開発・貢献

- 単体モジュールは可能な限り副作用を持たないよう実装されています。ユニットテストは DuckDB / SQLite に対する操作をモック／一時DBで実行することを推奨します。
- 環境変数や外部API（特に OpenAI）はテスト用に差し替え可能なように引数で注入しています（例: score_news の api_key 引数、API 呼び出しラッパーの patch）。

---

README に書かれている使い方例は最小限の導入手順です。実際の運用では BrokerAPI 実装、OrderRepository（SQLite スキーマ）、RiskManager 等の準備が必要です。必要であれば各コンポーネントの使い方サンプル（ExecutionEngine の完全な起動例、OrderRepository スキーマ、Broker のモック実装など）を追加で作成します。どの部分の例が欲しいか教えてください。