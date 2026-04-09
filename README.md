# KabuSys

軽量な日本株自動売買システムのコアライブラリ群です。ポートフォリオ構築、ポジションサイズ計算、ファクター研究、ニュースセンチメント（LLM）評価、市場レジーム判定、発注エンジン、監視機能などを含みます。DB は DuckDB（市場データ等）および SQLite（監視ログ/オーダー永続化）を想定しています。

## 主な特徴
- ポートフォリオ構築
  - 候補選定（スコア降順）、等金額/スコア加重の重み計算
  - セクター集中制限・レジーム乗数の適用
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value などのファクターを DuckDB から計算
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー等の解析機能
- AI（LLM）連携
  - ニュースセンチメントのバッチ評価（OpenAI API を利用）
  - マクロニュースを用いた市場レジーム判定（Bull/Neutral/Bear）
  - リトライ・バリデーション・フェイルセーフ設計
- 実行（Execution）層
  - OrderManager / ExecutionEngine（信号処理・WebSocket push ドレイン）
  - Reconciler による再起動後の状態復旧
  - Broker API 抽象（Protocol）+ 例外設計
- 監視（Monitoring）
  - SQLite ベースの監視 DB（system_status / trade_logs / positions / risk_logs / dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE）
  - Streamlit による監視ダッシュボード（読み取り専用）

---

## 必要環境（推奨）
- Python 3.10+
- DuckDB
- SQLite（Python 標準ライブラリ）
- 外部ライブラリ（例）
  - duckdb
  - openai
  - psutil
  - requests
  - streamlit (ダッシュボード用)

（実際の requirements.txt はリポジトリにないため、以下のようにインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai psutil requests streamlit
```

---

## 環境変数 / 設定
このライブラリは .env ファイルまたは環境変数を読み込みます（自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行います）。読み込み優先順位は次の通りです：

OS 環境 > .env.local（上書き） > .env（未設定のみ）

自動ロードを無効化する場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（未設定なら送信しない）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — Monitoring 用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper trading の挙動 ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH — Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行制御・停止フラグ関連
- KABUSYS_ENV — "development" | "paper_trading" | "live"（検証あり）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

設定はプログラムから次のように参照できます:
```python
from kabusys.config import settings
token = settings.jquants_refresh_token
```

---

## セットアップ手順（例）
1. リポジトリをクローン:
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して依存をインストール:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb openai psutil requests streamlit
   ```

3. 環境変数の設定:
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成。
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY（AI 機能を使う場合）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   OPENAI_API_KEY=sk-xxxxx
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

4. DuckDB / SQLite の準備:
   - DuckDB の schema / テーブルはアプリケーション側（data pipeline）で準備することを想定。
   - 監視 DB を作成する場合（MonitoringDB の初期化）:
     ```python
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

---

## 使い方（主要な例）

- 設定を参照する:
  ```python
  from kabusys.config import settings
  print(settings.env, settings.log_level)
  ```

- ファクター計算（DuckDB 接続を渡す）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  momentum = calc_momentum(conn, target)
  volatility = calc_volatility(conn, target)
  value = calc_value(conn, target)
  ```

- 将来リターン / IC / サマリー:
  ```python
  from kabusys.research import calc_forward_returns, calc_ic, factor_summary

  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_5d")
  summary = factor_summary(momentum, ["mom_1m", "ma200_dev"])
  ```

- ニュースセンチメント評価（OpenAI API キーが必要）:
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026,3,20), api_key="sk-...")
  print("written scores:", n_written)
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  n = score_regime(conn, date(2026,3,20), api_key="sk-...")
  ```

- 監視ダッシュボード（Streamlit）:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- 監視 DB の操作（MonitoringDB）:
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  db = MonitoringDB(conn)
  db.log_system_status(cpu_percent=10.0, memory_percent=20.0, disk_percent=30.0, process_ok=True)
  ```

- ExecutionEngine / OrderManager 等は Broker API 実装（Protocol 準拠）と OrderRepository（SQLite）を組み合わせて利用します。直接使う場合は各実装を用意して初期化してください（サンプルはコード内ドキュメントを参照）。

---

## 注意点 / 実装上の設計方針（抜粋）
- DuckDB のテーブルは prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime などに依存します。各関数の docstring を参照して必要な列・型を準備してください。
- LLM（OpenAI）関連は API エラー耐性（429・タイムアウト・5xx のリトライ）とレスポンスのバリデーションを行い、失敗時はフェイルセーフなデフォルト（例: macro_sentiment=0.0）にフォールバックします。
- 自動 .env ロードはプロジェクトルートを基準に行われ、.env/.env.local の優先度を保証します。Key のパースはシェル風の export / quote / コメント記法に対応しています。
- Paper trading（模擬）用の挙動を environment で切り替え可能（PAPER_FILL_MODE など）。
- KillSwitch はファイルベース（data/kill.flag）でプロセス停止要求を扱います。起動時の振る舞いは KILL_FLAG_CLEAR_ON_START で制御可能。

---

## ディレクトリ構成（主要ファイル）
（リポジトリの src/kabusys を基準に抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / .env ロード、Settings オブジェクト
  - portfolio/
    - portfolio_builder.py — 候補選定、等配分・スコア配分
    - risk_adjustment.py — セクターキャップ、レジーム乗数
    - position_sizing.py — 発注株数計算（リスクベース、等分、スケーリング）
    - __init__.py
  - research/
    - factor_research.py — momentum / volatility / value 計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — マクロ＋MA によるレジーム判定（OpenAI）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義 / MonitoringDB クラス
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — DD / position limit チェック
    - kill_switch.py — kill.flag 書き込み・クリア
    - alert_manager.py — LINE Push 通知
    - monitoring_engine.py — 監視ポーリング実行
    - streamlit_dashboard.py — Streamlit 監視 UI
    - __init__.py
  - execution/
    - broker_api.py — Broker API のデータモデル / Protocol / 例外
    - order_manager.py — 注文作成・送信・同期・キャンセル
    - reconciler.py — 起動時リコンシリエーション（注文・ポジション照合）
    - execution_engine.py — Signal Queue Pull 型発注エンジン
    - (その他: order_repository, order_record などは別ファイルに実装されている想定)
  - その他（data, strategy, etc. は __all__ により公開され得る）

---

## 開発 / テストのヒント
- self-contained な関数が多く、ユニットテストが容易です（DuckDB を一時 DB にしてテストデータを注入する、OpenAI 呼び出しはモックする等）。
- OpenAI など外部 API はモック / patch 可能（コード内で _call_openai_api を分離している箇所あり）。
- 環境に依存する値（時刻、today 等）は関数に注入可能な設計になっている所が多数あるためテストしやすいです。

---

README は概要と使い方のガイドを中心にまとめました。より詳細な設計仕様（PortfolioConstruction.md、StrategyModel.md 等）はリポジトリの別ドキュメントを参照してください。必要であれば README に起動例やより詳しい env.example を追加します。どの部分を重点的に補足しますか？