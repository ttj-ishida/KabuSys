# KabuSys

日本株の自動売買システム（ライブラリ / 実行コンポーネント群）

- バックテスト・リサーチ（DuckDBベースのファクター計算）
- ポートフォリオ構築（候補選定・配分・株数決定）
- AI 補助（ニュースのセンチメント評価、レジーム判定）
- 発注/実行（kabuステーション相当の Broker API プロトコルを想定）
- 監視（モニタリングDB, アラート, Streamlit ダッシュボード）

概要・設計方針の多くはソース内ドキュメント（各モジュールの docstring）に記載しています。

## 主な機能（抜粋）

- ファクター計算（momentum / volatility / value）
- 将来リターン計算・IC（Information Coefficient）評価、特徴量の統計サマリ
- ポートフォリオ構築：候補選定（スコア順）、等配分 / スコア加重、リスクベース配分
- セクター集中制限、レジームに応じた投下資金乗数
- 株数決定（単元丸め、per-stock / aggregate キャップ、コストバッファ考慮）
- AI: ニュース記事のセンチメント評価（OpenAI GPT 系モデル利用）→ ai_scores テーブルへ書込み
- AI: マクロニュースと ETF(ma200) の組合せで市場レジーム判定（market_regime へ書込）
- 発注エンジン: OrderManager / ExecutionEngine（信号受取り→Gate チェック→発注→push drain）
- 起動時のリコンシリエーション（Reconciler）
- 監視周り: MonitoringDB（SQLite）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager（LINE）
- Streamlit ダッシュボード（データ閲覧用）

## 必要条件（例）

- Python 3.10+
- パッケージ（代表例）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit
  - sqlite3（標準ライブラリ）
- （実行環境により）kabuステーション互換の broker 実装

requirements.txt はプロジェクトに応じて用意してください。例:

```bash
pip install duckdb openai requests psutil streamlit
```

推奨: 仮想環境を作成してからインストールしてください。

## 環境変数 / .env

プロジェクトはプロジェクトルート（.git または pyproject.toml を探索して決定）にある `.env` / `.env.local` を自動で読み込みます（CWD に依存しない）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に利用される環境変数（代表例）:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用トークン（AlertManager）
- LINE_USER_ID — LINE 通知先ユーザーID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring DB Path（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading のモック約定挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite path
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / LOG_LEVEL / KABUSYS_ENV など

例 `.env`（プロジェクトルート）:

```ini
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_pwd
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_FILL_MODE=instant
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- `.env.local` が存在すると `.env` の上から上書きされます（os 環境変数は保護される）。
- 自動ロードはプロジェクトルートが見つからない場合スキップされます。

## セットアップ手順（簡易）

1. リポジトリをクローン
2. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai requests psutil streamlit
   ```
4. プロジェクトルートに `.env` を用意（上記例を参照）
5. モニタリング DB 初期化（SQLite 接続を作って init_monitoring_db を呼ぶ）
   例（Python）:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

## 使い方（代表的な例）

- DuckDB を使ったファクター計算（momentum）:

```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, date(2026, 3, 20))
```

- ニュースの AI スコアリング（OpenAI API キーが必要）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} codes")
```

- レジーム判定:

```python
from kabusys.ai.regime_detector import score_regime
# conn: duckdb connection
score_regime(conn, date(2026,3,20))
```

- Streamlit ダッシュボード起動:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- MonitoringEngine（プログラム内でポーリング / 単一実行）:

```python
from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine, init_monitoring_db
import sqlite3, duckdb

mon_conn = sqlite3.connect("data/monitoring.db")
init_monitoring_db(mon_conn)
duck_conn = duckdb.connect("data/kabusys.duckdb")

sys = SystemMonitor(mon_conn, duck_conn)
# trade_monitor は OrderRepository が必要。テスト用に stub を作るか実装を渡す。
# risk_monitor は MonitoringDB を内部で利用する。
# alert_manager = AlertManager(token, user_id)
# engine = MonitoringEngine(sys, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(Path("data/kill.flag")), alert_manager=alert_manager)
# engine.run_once()
```

- ExecutionEngine（実運用）:
  ExecutionEngine は BrokerAPIProtocol 実装、OrderRepository、RiskManager など複数のコンポーネントを注入して使用します。起動前に kill.flag の有無チェック、PID 書き込み、Reconciler の実行が組み込まれています。詳細は `src/kabusys/execution/execution_engine.py` の docstring を参照してください。

## 重要な設計・運用注意点

- AI 系呼び出しは外部 API に依存するため、API エラー時はフェイルセーフ（スコア=0 等）で継続する設計の箇所が多いです。
- ExecutionEngine は起動時に PID ファイルを作成し、kill.flag による外部停止制御を持ちます。運用時は KILL_FLAG_CLEAR_ON_START の挙動を理解してください。
- Paper Trading 向けの設定（PAPER_FILL_MODE など）でモック挙動が変わります。
- DuckDB / SQLite のスキーマやテーブル名（prices_daily, raw_financials, raw_news, ai_scores, market_regime, monitoring テーブル群 等）に依存するため、データの準備が必要です。
- 環境変数の自動ロードはプロジェクトルート探索に依存します。CI / テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して明示的に読み込むことをお勧めします。

## ディレクトリ構成（主要ファイル）

（リポジトリ内 `src/kabusys` 想定）

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py      — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（ETF + マクロ）
  - research/
    - __init__.py
    - factor_research.py    — momentum / value / volatility
    - feature_exploration.py — forward returns, IC, stats
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定・配分
    - position_sizing.py     — 株数決定
    - risk_adjustment.py     — sector cap, regime multiplier
  - execution/
    - broker_api.py
    - order_record.py
    - order_repository.py
    - order_manager.py
    - reconciler.py
    - execution_engine.py
    - risk_manager.py
    - ...（その他発注周り）
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
  - portfolio/ (上記)
  - research/ (上記)
  - data/ （データ処理用パッケージがあれば配置）
  - monitoring.db / kabusys.duckdb （実行時に作成されるデータファイルの例）

（個々のモジュールに多くの docstring と使用例が書かれています。実装詳細は各ファイルを参照してください。）

---

ご不明点があれば、どの機能の README セクションをより詳しくしたいか（例: ExecutionEngine の接続例、OrderRepository の DB スキーマ、AI 呼び出しのプロンプト設計など）を教えてください。必要に応じて具体的な起動スクリプト例やユニットテストの書き方サンプルも作成します。