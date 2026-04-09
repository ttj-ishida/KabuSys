# KabuSys

KabuSys は日本株向けの自動売買／リサーチ／監視ツールキットです。DuckDB / SQLite をデータ層に使い、kabuステーション（またはその他の BrokerAPI 実装）経由で発注、LLM（OpenAI）を用いたニュースセンチメントや市場レジーム判定、監視・アラート機能を提供します。

以下はリポジトリ内の主要機能と使い方、セットアップ手順、ディレクトリ構成の概要です。

---

## プロジェクト概要

- 株式選定 → ポートフォリオ構築 → 注文発行 → 発注監視 の一連ワークフローをサポートするモジュール群。
- 研究用途のファクター計算（DuckDB の prices_daily / raw_financials を参照）を含む。
- OpenAI（gpt-4o-mini）を使ったニュースのセンチメント付与およびマクロセンチメントを統合した市場レジーム判定を提供。
- 監視用に SQLite ベースの監視 DB と Streamlit ダッシュボード、LINE での通知送信などを備える。
- 設定は環境変数（およびプロジェクトルートの `.env` / `.env.local`）から読み込む仕組み。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に検出）
  - 必須環境変数チェックユーティリティ（Settings クラス）

- ポートフォリオ構築（純粋関数）
  - 候補選定（スコア順）
  - 等配分・スコア加重配分
  - セクター集中制限（セクター上限の除外）
  - レジームに応じた乗数（bull/neutral/bear）
  - ポジションサイジング（リスクベース / equal / score）と単元丸め、資金割当のスケールダウン

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受け取る）
  - 将来リターン計算、IC（Spearman）計算、統計サマリーツール

- AI（LLM）関連
  - ニュース記事を集約して OpenAI でセンチメント評価 → ai_scores テーブルへ書き込み（score_news）
  - マクロ記事を用いた市場レジーム判定（score_regime）
  - API 呼び出しはリトライとバリデーションを備え、失敗はフォールバックして続行

- 発注・実行
  - Broker API の抽象プロトコル（データモデル・例外）
  - OrderManager: 注文状態管理（クラッシュ安全性を意識した永続化フロー）
  - ExecutionEngine: シグナル読み取り→Gate チェック→発注ループ（セッション管理・WebSocket push ドレイン等）
  - Reconciler: 再起動時の照合・自動同期

- 監視
  - MonitoringDB: SQLite ベースの永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE 送信）
  - Streamlit ダッシュボード（read-only 接続可）

---

## 必要な環境（例）

- Python 3.9+（型注釈により 3.9 以上を想定）
- 主な依存ライブラリ（リポジトリに requirements.txt があればそれを使ってください）:
  - duckdb
  - openai
  - requests
  - psutil
  - streamlit
  - （標準ライブラリ: sqlite3, typing, logging など）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

---

## 環境変数（主要）

以下はコード上で参照される主な環境変数とデフォルト値 / 備考です。`.env` に定義してプロジェクトルートに置くことが想定されています。

必須（アプリケーション起動時に未設定だと例外になるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・運用設定
- OPENAI_API_KEY : OpenAI の API キー（AI 関連機能で必須）
- LINE_CHANNEL_ACCESS_TOKEN : LINE Push 用トークン（AlertManager）
- LINE_USER_ID : LINE Push 宛先ユーザー ID
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE : paper trading の fill モード（instant|partial|never|reject、デフォルト "instant"）
- PAPER_TRADING_SQLITE_PATH : Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH 等（監視用ファイルパス）
- KABUSYS_ENV : development | paper_trading | live（デフォルト: development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動 .env 読み込みの制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト等で利用）。

読み込み順:
- OS 環境変数 > .env.local（override=True）> .env（override=False）
- プロジェクトルートは .git または pyproject.toml を基準に検出。見つからない場合は自動ロードをスキップ。

---

## セットアップ手順（ローカル実行の一例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # あれば
   # または最低限:
   pip install duckdb openai requests psutil streamlit
   ```

3. `.env` を作成（`.env.example` があれば参照）:
   ```
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

5. 監視 DB 初期化（MonitoringDB のスキーマ作成）
   Python スクリプト例:
   ```python
   import sqlite3
   from kabusys.monitoring.monitoring_db import init_monitoring_db

   conn = sqlite3.connect("data/monitoring.db")
   init_monitoring_db(conn)
   conn.close()
   ```

6. DuckDB に必要なテーブル（prices_daily, raw_financials 等）を準備
   - DuckDB に CSV / parquet からロードするか、別の ETL スクリプトで投入してください。関数は prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime などを前提に動作します。

---

## 使い方（主要なユースケース）

- 設定を取得する
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  duckdb_path = settings.duckdb_path
  ```

- ファクター計算（例: Momentum）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, date(2026, 3, 20))
  ```

- ニュースのセンチメントスコア付与（AI）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を引数で渡すか、OPENAI_API_KEY を環境変数に設定
  written = score_news(conn, date(2026, 3, 20), api_key=None)
  ```

- 市場レジーム判定（AI）
  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, date(2026, 3, 20))
  ```

- 監視 DB の操作は MonitoringDB 経由で
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db

  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)  # 初期化
  db = MonitoringDB(conn)
  db.log_system_status(cpu_percent=1.0, memory_percent=2.0, disk_percent=3.0, process_ok=True)
  ```

- Streamlit ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ExecutionEngine（実運用向け）
  - ExecutionEngine は BrokerAPI の具体実装（kabu station client 等）、OrderRepository（SQLite 実装）、RiskManager 等の具象オブジェクトを注入して使用します。これらはプロジェクト外で実装される想定です。
  - 高レベルの流れ:
    1. 起動時に Reconciler.run()（オプション）で照合
    2. シグナル期（例 8:50-9:10）にシグナルを読み発注（Gate チェックを適用）
    3. WebSocket push をドレインして約定同期
    4. KillSwitch / RiskManager により必要時に全注文をキャンセル

  サンプル（擬似コード）:
  ```python
  engine = ExecutionEngine(
      broker=my_broker_impl,
      repo=my_order_repo,
      risk_manager=my_risk_manager,
      order_manager=my_order_manager,
      duckdb_conn=my_duckdb_conn,
      config=EngineConfig(target_date=date.today())
  )
  engine.run_session()
  ```

---

## ディレクトリ構成（主要ファイル）

（path はリポジトリ内の src/kabusys/ を基準）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / Settings 管理（.env 自動読み込み）
  - portfolio/
    - __init__.py
    - portfolio_builder.py          — 候補選定・配分（等配分・スコア配分）
    - position_sizing.py            — 株数計算・資金割当
    - risk_adjustment.py            — セクターキャップ・レジーム乗数
  - research/
    - __init__.py
    - factor_research.py            — Momentum / Volatility / Value 等
    - feature_exploration.py        — 将来リターン・IC・統計
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py            — マクロ + MA200 によるレジーム判定（OpenAI）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite スキーマ / MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                 — Broker API データモデル / Protocol / 例外
    - order_manager.py              — 注文状態遷移・送信フロー
    - execution_engine.py           — Signal Pull 型発注エンジン
    - reconciler.py                 — 再起動時の照合
    # （他、order_repository, order_record, risk_manager などはこのリポジトリに存在する想定）
  - monitoring/ (既出)
  - research/ (既出)
  - portfolio/ (既出)

---

## 注意点 / 実運用における留意事項

- AI（OpenAI）呼び出しは外部ネットワークを使用します。APIキー・コスト・レート制限に注意してください。news_nlp / regime_detector はリトライ・フォールバックを備えていますが、結果の一貫性や遅延は設計上の考慮が必要です。
- ExecutionEngine / OrderManager の一部は BrokerAPI 実装に依存します（テスト用のモック実装を用意すると安全です）。
- .env のパースはシェル風のフォーマットをサポートしますが、特殊なエスケープや複雑な構文は限界があります。重要なキーは OS 環境変数で管理することを検討してください。
- monitoring_db.init_monitoring_db() は既存 DB に対する簡単なマイグレーション（列追加）を行いますが、大きなスキーマ変更がある場合は明示的なマイグレーション手順を用意してください。
- KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等は設定値検証を行います。誤った値は ValueError を発生させます。

---

## 貢献・拡張ポイント（提案）

- 単元株（lot_size）を銘柄ごとに扱えるように stocks マスタを導入して position_sizing を拡張
- DuckDB スキーマ用の ETL / ingestion スクリプトを整備
- BrokerAPI の具体実装（kabu station client）を別パッケージで提供
- テスト用のモッククライアント・CI を整備（AI 呼び出しはモック化）

---

README は以上です。実行時の具体的なエラーや追加の環境依存設定が発生した場合は、その箇所（ログとスタックトレース）を教えていただければ、手順の補足やトラブルシュート手順を提供します。