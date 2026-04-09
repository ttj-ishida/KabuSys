# KabuSys

日本株自動売買システム（ライブラリ / コンポーネント群）

---

## プロジェクト概要

KabuSys は日本株の自動売買に関するアルゴリズム、監視、実行、研究（リサーチ）機能をモジュール化したコードベースです。  
主要コンポーネントはポートフォリオ構築（銘柄選定・配分・サイズ決定）、ファクター計算・探索、AI を用いたニュースセンチメント評価、市場レジーム判定、実行エンジン（ブローカ API 経由での発注）および運用監視（ログ永続化・アラート・ダッシュボード）です。

設計方針の要点:
- DuckDB / SQLite を用いたローカル DB 主導の処理（外部 API 呼出しを最小化）
- LLM（OpenAI）を部分的に使用（ニュースセンチメント、マクロセンチメント）
- 自動環境変数読み込み（プロジェクトルートの .env / .env.local）
- テスト容易性を考慮した副作用の少ない純粋関数群

---

## 主な機能一覧

- Portfolio
  - 候補選定（スコア順ソート）select_candidates
  - 等金額・スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（リスクベース・等配分）calc_position_sizes
  - セクター集中制限、レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- Research（ファクター計算 / 特徴量解析）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使う）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ

- AI
  - ニュース記事をまとめて LLM に投げ、銘柄別センチメントを ai_scores に書込む（news_nlp.score_news）
  - マクロニュースと ETF（1321）の MA200 を組合せた市場レジーム判定（regime_detector.score_regime）

- Execution（発注）
  - OrderManager / ExecutionEngine：信号を DB から読み発注・状態管理・再同期（Reconciler）
  - Broker API 抽象（Protocol）を用いたブローカー依存分離
  - リスクチェック（Gate 構造）・KillSwitch による安全停止

- Monitoring（監視）
  - MonitoringDB（SQLite）による永続化レイヤ
  - System/Trade/Risk モニタ、アラート（LINE push）、Streamlit ダッシュボード

---

## 前提・依存関係

（本リポジトリで明示的な requirements.txt は無いので下記パッケージを環境に導入してください）

必須（実行する機能により変動）:
- Python 3.10+（typing 差分のため推奨）
- duckdb
- openai
- requests
- psutil
- streamlit (ダッシュボードを使う場合)
- sqlite3（標準ライブラリ）
- その他: logging 等標準ライブラリ

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai requests psutil streamlit
```

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repository-url>

2. 仮想環境作成・依存インストール
   - 上記「前提・依存関係」を参照

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env`（または `.env.local`）を作成します。
   - 自動読み込みはデフォルトで有効。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. モニタリング DB 初期化（SQLite）
   - Python REPL などで以下を実行:
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

5. DuckDB データ準備
   - prices_daily / raw_financials / raw_news 等テーブルはリサーチ・AI モジュールで参照されます。実運用ではデータパイプライン（kabusys.data.pipeline 等）で投入してください。

---

## 環境変数（主な設定項目）

KabuSys は .env / .env.local / OS 環境変数から設定を読み込みます。優先順位: OS 環境 > .env.local > .env。
自動ロードはプロジェクトルートを起点に行われ、見つからない場合はスキップされます。

主要キー:
- JQUANTS_REFRESH_TOKEN - 必須: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD - 必須: kabuステーション API パスワード
- KABU_API_BASE_URL - optional: デフォルト http://localhost:18080/kabusapi
- LINE_CHANNEL_ACCESS_TOKEN - optional: AlertManager 用
- LINE_USER_ID - optional: AlertManager 用
- OPENAI_API_KEY - optional: AI 機能（news_nlp / regime_detector）で使用
- DUCKDB_PATH - DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH - 監視 DB パス（default: data/monitoring.db）
- PAPER_FILL_MODE - paper trading の挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH - paper trading 用 SQLite
- PID_FILE_PATH - ExecutionEngine の PID ファイル path（default: data/execution.pid）
- KILL_FLAG_PATH - kill フラグファイル（default: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START - 1 にすると起動時に kill.flag を自動クリア
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT - 監視閾値
- KABUSYS_ENV - environment: development|paper_trading|live
- LOG_LEVEL - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

注意:
- .env のクォート・コメントのパースは内部実装に従っています（export 形式や引用符、インラインコメントの扱いに対応）。
- OS 環境変数は .env の上書きから保護されます（.env ファイル読み込み時に OS 環境は protected として扱われる）。

---

## 使い方（代表的な例）

- 設定値の参照:
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path
  ```

- MonitoringDB 初期化:
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  ```

- Streamlit ダッシュボード起動:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- AI: ニューススコアリング（例）
  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- AI: レジーム判定（例）
  ```python
  from kabusys.ai.regime_detector import score_regime
  n = score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- ExecutionEngine の使用（実運用には BrokerAPI 実装が必要）
  - BrokerAPIProtocol を実装したクライアントと OrderRepository / RiskManager / OrderManager / Reconciler を組み合わせて ExecutionEngine を生成し、run_session() を呼びます。
  - 実行時に kill.flag の存在や PID ファイル操作、リコンシリエーション処理が行われます。
  - 詳細は src/kabusys/execution/*.py を参照してください。

- MonitoringEngine（ポーリング監視）:
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager を組み合わせて MonitoringEngine を作成し、run() または run_once() を呼ぶ。

---

## 注意点 / 運用上のポイント

- AI（OpenAI）キーは安全に管理してください。API 呼び出しはレート制限やエラー時のリトライロジックがありますが、環境に応じた運用が必要です。
- ExecutionEngine は発注ロジックやブローカー API に依存するため、実運用前に入念なテストとフェイルセーフ確認を行ってください。
- kill.flag による停止や KILL_FLAG_CLEAR_ON_START の設定は運用ポリシーに合わせて慎重に設定してください。
- DuckDB / SQLite テーブルスキーマやデータ投入ロジック（prices_daily / raw_financials / raw_news / ai_scores / market_regime 等）は本コードの期待仕様に従ってください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                                — 環境変数 / 設定管理
- portfolio/
  - __init__.py
  - portfolio_builder.py                    — 候補選定・重み計算
  - risk_adjustment.py                      — セクター上限・レジーム乗数
  - position_sizing.py                      — 株数決定・丸め・aggregate cap
- research/
  - __init__.py
  - factor_research.py                      — Momentum / Volatility / Value
  - feature_exploration.py                  — 将来リターン / IC / summary
- ai/
  - __init__.py
  - news_nlp.py                             — ニュース -> LLM -> ai_scores
  - regime_detector.py                      — マクロ + MA200 -> market_regime
- monitoring/
  - __init__.py
  - monitoring_db.py                        — SQLite テーブル定義 / MonitoringDB
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - alert_manager.py                        — LINE Push
  - kill_switch.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - broker_api.py                           — Protocol / 型定義 / 例外
  - order_manager.py
  - order_repository.py                     — (参照される実装)
  - order_record.py
  - reconciler.py
  - execution_engine.py
  - risk_manager.py                         — (参照される実装)
- monitoring/ (上記)
- research/ (上記)
- その他: data モジュールや pipeline 等は別ファイル（参照あり）

（上記はリポジトリの主要ファイルの抜粋です。詳細はソースを参照してください。）

---

## 開発・テスト

- 自動環境読み込み（.env）を無効にしたい場合:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
- OpenAI 呼び出し等外部 API をテストで差し替える際は、各モジュールが内部で使用する呼出関数（例: _call_openai_api）を unittest.mock.patch で差し替え可能なよう設計されています。
- DuckDB / SQLite 用のフェイルセーフ（executemany の空リスト制約など）に注意して DB 操作を行ってください。

---

README に含めて欲しい追加の手順（例: サンプル .env.example、requirements.txt、データパイプラインの手順など）があれば指示ください。必要に応じて README を拡張して作成します。