# KabuSys

日本株自動売買システム（ライブラリ） — シグナル → ポートフォリオ構築 → 発注 → 監視／リスク管理までを含むモジュール群のコレクションです。  
本 README はコードベース（src/kabusys 以下）に基づく概要、機能、セットアップ、利用方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたコンポーネント群です。主な要素は以下です。

- ファクター計算・リサーチ（DuckDB 上の時系列データを参照）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- Execution 層（OrderManager / ExecutionEngine / Broker API 抽象）
- 起動時リコンシリエーション（復旧処理）
- 監視機能（システム、注文、リスク監視）とアラート送信（LINE）
- ニュース NLP を用いた銘柄ごとのセンチメント評価（OpenAI）
- レジーム判定（ETF とマクロニュースの合成）

設計方針のポイント：
- DuckDB / SQLite を用いたローカル DB 中心の計算／永続化（本番 API に依存しない研究環境が可能）
- OpenAI を利用する箇所は明示的に API キーを渡すか環境変数参照
- 自動ロードされる .env の処理はプロジェクトルート（.git または pyproject.toml）を基準に行われる
- フェイルセーフ設計（API 失敗時のフォールバック、部分書き込みで既存データ保護 等）

---

## 主な機能一覧

- research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- portfolio
  - 候補選定（スコア降順）
  - 等金額・スコア加重の重み計算
  - セクター集中の制限（apply_sector_cap）
  - レジームに応じた投下資金乗数（calc_regime_multiplier）
  - ポジションサイズ決定（risk_based / equal / score ベース）
- ai
  - ニュース記事を LLM（OpenAI）でセンチメント評価し ai_scores テーブルに保存（score_news）
  - マクロニュース + ETF を用いた市場レジーム判定（score_regime）
- execution
  - OrderManager：注文状態マシン（作成 → 送信 → 同期 → キャンセル）
  - ExecutionEngine：シグナル処理ループ／WebSocket ドレイン／kill switch 等
  - Reconciler：起動時のリコンシリエーション（OrderSent の復旧、ポジション差分検出）
  - broker_api：ブローカー側の抽象（Protocol／データモデル／例外）
- monitoring
  - MonitoringDB：SQLite ベースの監視ログ永続化層
  - SystemMonitor / TradeMonitor / RiskMonitor：定期チェックとリスクログ記録
  - AlertManager：LINE Push による通知（クールダウン機能）
  - KillSwitch：フラグファイルで Execution を停止
  - Streamlit ダッシュボード（読み取り専用で監視情報を可視化）

---

## セットアップ手順（ローカル開発）

以下は最小限のセットアップ例です。プロジェクトに pyproject.toml や requirements ファイルがある想定で、適宜置き換えてください。

1. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb openai requests psutil streamlit
   - その他プロジェクトに必要なパッケージがあれば追加してください。

3. リポジトリルートに .env を配置（自動で読み込まれます）
   - 自動読み込みは、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に実行されます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. 必要な DB を初期化
   - 監視用 SQLite（例: data/monitoring.db）を作成して MonitoringDB スキーマを初期化する例（Python REPL で）:
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     import sqlite3
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()

5. DuckDB データや prices_daily/raw_financials/raw_news 等の投入は別スクリプトで行ってください（本 README では扱いません）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（ai.score_news / score_regime で使用）
- LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（AlertManager）
- LINE_USER_ID — LINE Push 宛先ユーザ ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 SQLite のパス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — PID ファイルのパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill フラグファイルのパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリアするフラグ（"1" で有効）
- KABUSYS_ENV — 環境 (development|paper_trading|live)
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）

注意: Settings クラスは必須環境変数が未設定の場合 ValueError を送出します（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。

---

## 使い方（簡単な例）

以下はライブラリ API を直接呼ぶ例です。実運用時は適切な DB 構成 / broker 実装 / API キー設定を行ってください。

- 設定値参照
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト

- ファクター計算（DuckDB 接続を渡す）
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  result = calc_momentum(conn, date(2026, 3, 20))

- ニュース NLP スコアリング（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, date(2026, 3, 20), api_key="sk-...")

- レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="sk-...")

- 監視 DB 初期化（SQLite）
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)
  conn.close()

- Streamlit ダッシュボード起動（読み取り専用）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringEngine を単発実行（テスト用 run_once）
  from kabusys.monitoring import SystemMonitor, TradeMonitor, RiskMonitor, MonitoringEngine, KillSwitch, AlertManager
  # それぞれのインスタンス化（conn, duckdb_conn, order_repo 等は適切に渡す）
  engine = MonitoringEngine(system_monitor, trade_monitor, risk_monitor, interval_sec=60, kill_switch=KillSwitch(Path("data/kill.flag")), alert_manager=AlertManager(token, user_id))
  engine.run_once()

- ExecutionEngine（本番実行はブローカー実装が必要）
  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
  engine = ExecutionEngine(broker, order_repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
  engine.run_session()

---

## 実装上の注記 / 安全策

- ai.news_nlp / regime_detector は外部 API（OpenAI）呼び出しを伴います。API 失敗時はフォールバック（スコア 0.0 など）して継続するよう設計されていますが、キー未設定時は ValueError が発生します。
- ExecutionEngine は kill.flag をチェックし、存在時は起動を拒否するか（設定次第でクリア）kill スイッチを発動します。
- OrderManager はクラッシュ安全性を考慮して OrderSent の永続化を broker 呼び出し前に行い、broker_order_id は可能な限り保存して復旧を容易にします。
- MonitoringDB は冪等でテーブル作成を行います。マイグレーション（例: dashboard.peak_value 列追加）も軽微にサポートしています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — 市場レジーム判定（ETF + マクロ）
  - portfolio/
    - __init__.py
    - portfolio_builder.py         — 候補選定 / 重み計算
    - risk_adjustment.py           — セクターキャップ / レジーム乗数
    - position_sizing.py           — 株数計算 / 上限・丸め
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value
    - feature_exploration.py       — forward returns / IC / summary
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite schema + MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py                — Broker API 抽象・データモデル・例外
    - order_manager.py
    - execution_engine.py
    - reconciler.py
    - (その他 order_repository, order_record, risk_manager 等が存在する想定)
  - monitoring, research, portfolio, ai, execution ...（その他モジュール群）

---

## 開発・テストのヒント

- 自動 .env ロードは便利ですが、テスト中に外部設定を読み込ませたくない場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部は内部で分離されており、単体テストでは _call_openai_api を patch / mock して挙動を検証できます（ニュース NLP / regime_detector 共に設計で想定）。
- DuckDB / SQLite を用いるため、テスト用の一時 DB を用意して関数群を検証することが容易です。

---

この README はコードベースに基づく概要ドキュメントです。実運用にあたってはブローカー実装や DB の整備、運用監視・ログ設定、テストを十分に行ってください。必要であれば各モジュールの詳細な API ドキュメント（関数別使用例、期待するテーブルスキーマ等）も作成しますのでお知らせください。