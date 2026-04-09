# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的としたシステムライブラリ群です。DuckDB / SQLite を用いたデータ処理、LLM を用いたニュースセンチメント評価、監視エンジン、発注エンジン（kabuステーション連携想定）などのコンポーネントを提供します。

この README はコードベース（src/kabusys）に基づく利用者向けの概要・セットアップ・使い方ドキュメントです。

---

## プロジェクト概要

主な目的・設計方針
- DuckDB を使ったリサーチ（ファクター計算 / 将来リターン / ファクター解析）。
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP（銘柄ごとのセンチメント算出）とマクロセンチメントを組み合わせた市場レジーム判定。
- SQLite による監視ログ永続化と Streamlit による監視ダッシュボード。
- 発注エンジン（ExecutionEngine）と OrderManager / Reconciler による堅牢な注文ライフサイクル管理（kabu ステーション向け API を想定）。
- 設定は環境変数 / .env で管理。プロジェクトルートを基準に `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）。

---

## 機能一覧

- 設定管理
  - 環境変数の自動ロード（`.env`, `.env.local`）と必須チェック（kabusys.config.Settings）。
- ポートフォリオ構築
  - 候補選定（スコア順）、等金額・スコア重み付け、セクターキャップ適用、レジーム乗数の計算。
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分）、単元株丸め、aggregate cap のスケーリング。
- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB を直接参照）。
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリ。
- AI（LLM）モジュール
  - ニュース記事のセンチメント評価と ai_scores への書込（OpenAI API を使用）。
  - マクロニュースを用いた市場レジーム判定および market_regime への書込。
  - API 呼び出しはリトライ・フェイルセーフ実装。
- 監視（Monitoring）
  - SQLite による system_status / trade_logs / positions / risk_logs / dashboard の永続化。
  - System / Trade / Risk 監視モジュール、KillSwitch（フラグによる実行停止）、AlertManager（LINE push）。
  - Streamlit ダッシュボード（読み取り専用）を提供。
- 発注・実行（Execution）
  - OrderManager（注文作成 / 送信 / 同期 / キャンセル）、Reconciler（起動時の自動再同期）、ExecutionEngine（Signal Queue ベースの実行ループ）。
  - Broker API の抽象化（Protocol）／例外モデル。

---

## 前提条件

- Python 3.9+（型注釈やパッチ構文の利用から推奨）
- 必要主要ライブラリ（例）
  - duckdb
  - openai（OpenAI SDK）
  - requests
  - psutil
  - streamlit（ダッシュボード利用時）
- SQLite（標準ライブラリに含まれます）

requirements.txt は本リポジトリに含まれていないため、プロジェクト利用時は上記パッケージをインストールしてください。

例:
pip install duckdb openai requests psutil streamlit

---

## 環境変数（主なキー）

config.Settings で参照される主な環境変数（.env で設定可能）:

必須
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード

任意（デフォルト値あり）
- KABUSYS_ENV — 動作環境（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
- DUCKDB_PATH — DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant/partial/never/reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 実行制御用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- OPENAI_API_KEY — OpenAI 呼び出しに必要

自動 .env 読み込みについて
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` -> `.env.local` の順で読み込みます。
- OS 環境変数は上書き保護されます（`.env.local` は上書き可だが OS 環境変数は保護）。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で有用）。

例 .env（簡易）
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

---

## セットアップ手順（ローカルでの簡易手順）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai requests psutil streamlit

3. 環境変数を設定
   - プロジェクトルートに `.env` を置くか、環境変数としてエクスポートしてください（上記の必須キーを忘れずに）。

4. DuckDB / SQLite の準備
   - DuckDB ファイル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets などのテーブル）はユーザー側で作成・ロードする想定です。
   - 監視用 SQLite DB を初期化する例:
     ```python
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     ```

5. OpenAI を利用する機能を使う際は `OPENAI_API_KEY` を設定してください。

---

## 使い方（代表的な例）

下記は各モジュールの代表的な呼び出し例です。実稼働では各種依存（Broker 実装、OrderRepository など）を用意する必要があります。

- 設定（Settings）を使う
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_paper)
  ```

- 監視 DB 初期化（SQLite）
  ```python
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  conn.close()
  ```

- Streamlit ダッシュボード起動
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- ニューススコア算出（OpenAI キー必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {n} stocks")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- リサーチ（モメンタム等）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, date(2026,3,20))
  ```

- 監視実行例（MonitoringEngine.run_once）
  - SystemMonitor / TradeMonitor / RiskMonitor 等のインスタンス化には SQLite 接続や DuckDB 接続、OrderRepository 等が必要です。テストではモックを渡して `MonitoringEngine.run_once()` を呼ぶことで 1 回のチェックを実行できます。

- ExecutionEngine（本番用）
  - ExecutionEngine を動かすには BrokerAPIProtocol 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続等が必要です。実稼働では各実装を注入して `ExecutionEngine.run_session()` を呼びます。
  - kill.flag の存在や PID 書き込み、起動時の Reconciler 実行など安全設計が組み込まれています。

---

## 注意点 / 運用メモ

- DuckDB / SQLite のスキーマは本リポジトリの各モジュールや SQL 文を参照して作成してください。prices_daily / raw_financials / raw_news / news_symbols / ai_scores 等のテーブルが必要です。
- OpenAI API を利用する機能はネットワーク・API レート制限の影響を受けます。ライブラリはリトライを実装していますが、API キーやコストに注意してください。
- `.env` 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 監視・発注の「Kill Switch」や「PID ファイル」などの仕組みがあるため、運用時は `KILL_FLAG_CLEAR_ON_START` 等の動作を理解しておく必要があります。
- ExecutionEngine / OrderManager 等、ブローカーへの発注に関わるコードは実装を間違えると実際の注文を出します。実運用前に十分なテスト・モックを活用してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数/設定管理
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py
- research/
  - factor_research.py — Momentum / Volatility / Value 計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - __init__.py
- ai/
  - news_nlp.py — ニュースセンチメント評価（OpenAI 呼出し）
  - regime_detector.py — マクロ + ETF MA によるレジーム判定
  - __init__.py
- monitoring/
  - monitoring_db.py — SQLite テーブル定義 / MonitoringDB
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
  - __init__.py
- execution/
  - broker_api.py — Broker インターフェース / データモデル / 例外
  - order_manager.py — 注文状態遷移 / 送信ロジック
  - reconciler.py — 起動時リコンシリエーション
  - execution_engine.py — シグナル処理ループ / Push ドレイン
  - （その他：order_repository.py, order_record.py, risk_manager.py などは実装対象）
- monitoring/、research/、portfolio/、ai/ のテスト用ユーティリティやサンプルは各モジュール内 docstring を参照してください。

---

この README はコードベースのコメントや docstring に基づき作成しています。実行や本番運用に際しては、環境固有の設定・テーブル作成・Broker 実装・適切なテストを行ってください。必要であれば各モジュールの詳細な使い方やスキーマ定義のドキュメントを追加します。