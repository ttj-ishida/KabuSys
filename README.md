# KabuSys

軽量な日本株向け自動売買ライブラリ / ツール群です。ポートフォリオ構築、ポジションサイジング、リスク調整、特徴量研究、ニュースのLLMスコアリング、監視エンジン、発注エンジン用ユーティリティなどを含みます。DuckDB / SQLite をデータ層に用い、実トレード・ブローカー連携は抽象化された BrokerAPIProtocol 経由で行います。

---

## 主な特徴（機能一覧）

- 設定管理
  - .env / .env.local / OS 環境変数から自動読み込み（優先度: OS > .env.local > .env）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能
  - 主要設定: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, LINE_CHANNEL_ACCESS_TOKEN, KABUSYS_ENV, LOG_LEVEL など

- ポートフォリオ構築（純粋関数）
  - buy シグナルから候補選択（select_candidates）
  - 等配分 / スコア加重の重み計算（calc_equal_weights / calc_score_weights）
  - セクター集中制限（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ決定（calc_position_sizes）

- リサーチ / ファクター計算
  - Momentum / Value / Volatility / Liquidity 等のファクター計算（prices_daily / raw_financials に基づく）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー（factor_summary）

- AI（LLM）によるニュース処理
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ書き込み（score_news）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースの LLM スコアの混合→ market_regime へ書込: score_regime）

- 監視・アラート
  - MonitoringDB（SQLite）による system_status / trade_logs / positions / risk_logs / dashboard の永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine（ポーリング）
  - LINE Push によるアラート（AlertManager）
  - kill.flag による外部停止シグナル（KillSwitch）
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）

- 発注・実行関連
  - BrokerAPI の型定義・例外・データモデル
  - OrderRecord / OrderRepository（SQLite）と OrderManager（State Machine）による発注フロー管理
  - ExecutionEngine：シグナルプル + WebSocket push ドレインのセッション実行ロジック
  - Reconciler：再起動時の注文・ポジション突合せ（自動復旧）

---

## セットアップ手順

このリポジトリは Python モジュール群（src/kabusys）として設計されています。以下は開発用・実行用の最低限のセットアップ例です。

1. Python 環境を作成（例: venv）
   - python >= 3.10 を推奨

2. 必要なパッケージをインストール（代表的な依存）
   - duckdb
   - openai
   - requests
   - psutil
   - streamlit
   - （プロジェクトの pyproject.toml / requirements.txt があればそちらを使用してください）

   例:
   pip install duckdb openai requests psutil streamlit

3. 設定（.env の作成）
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動読み込みされます。
   - 読み込み優先度: OS 環境変数 > .env.local > .env
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

   代表的な環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_FILL_MODE=instant|partial|never|reject
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag
   - KILL_FLAG_CLEAR_ON_START=0|1

   注意: .env の書式は export KEY=val を含め多様な記法に対応します。クォートやインラインコメントの扱いも実装済みです。

4. データベース準備
   - MonitoringDB を初期化する場合は sqlite3.Connection を渡して `init_monitoring_db(conn)` を呼びます。
   - DuckDB は prices_daily / raw_financials / raw_news 等のテーブルを用いる処理が多いので、事前にインポートを行ってください。

---

## 使い方（代表例）

以下はライブラリの代表的な使い方例です。実運用では各種クライアント（BrokerAPI 実装や OrderRepository）を組み合わせます。

- 設定の利用
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  is_live = settings.is_live

- ポートフォリオ構築
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_equal_weights, calc_position_sizes
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  shares = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)

- リサーチ / ファクター計算
  import duckdb
  from datetime import date
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))

- ニューススコアリング（OpenAI API 必須）
  from kabusys.ai.news_nlp import score_news
  # conn: duckdb 接続、target_date: date オブジェクト
  n = score_news(conn, target_date, api_key="sk-...")

- レジーム判定（OpenAI API 必須）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key=None)  # None の場合は環境変数 OPENAI_API_KEY を参照

- 監視データベース初期化
  import sqlite3
  from kabusys.monitoring.monitoring_db import init_monitoring_db
  conn = sqlite3.connect("data/monitoring.db")
  init_monitoring_db(conn)

- Streamlit ダッシュボード起動
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine の実行（概略）
  # BrokerAPIProtocol 実装（broker）、OrderRepository（repo）、RiskManager（risk_manager）等を用意
  from kabusys.execution.execution_engine import ExecutionEngine, EngineConfig
  engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=date.today()))
  engine.run_session()

  実際には broker 実装や OrderRepository の初期化、Reconciler の組み込み、PID 管理、kill flag の扱い等が必要です。

---

## ディレクトリ構成

（プロジェクトルートに `src/kabusys` が配置される想定）

- src/kabusys/
  - __init__.py  — パッケージ定義、バージョン
  - config.py    — 環境変数 / .env の読み込み、Settings クラス
  - portfolio/
    - __init__.py
    - portfolio_builder.py  — 候補選定、重み計算
    - position_sizing.py    — ポジションサイズ計算、単元丸め、aggregate cap
    - risk_adjustment.py    — セクターキャップ、レジーム乗数
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース集約・OpenAI スコアリング・ai_scores 書き込み
    - regime_detector.py    — 市場レジーム判定（MA200 + マクロニュース）
  - monitoring/
    - __init__.py
    - monitoring_db.py      — SQLite スキーマ初期化・MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py      — LINE push
    - kill_switch.py
    - monitoring_engine.py  — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py
  - execution/
    - broker_api.py         — Broker API 型定義・例外・データモデル・Protocol
    - order_manager.py      — Order state machine 外向け API
    - order_repository.py   — （DB）OrderRepository（実装ファイルは省略）
    - order_record.py       — OrderRecord（状態遷移ロジック）（実装ファイルは省略）
    - reconciler.py         — 起動時リコンシリエーション
    - execution_engine.py   — Signal Pull 型発注エンジン
    - risk_manager.py       — （実装ファイルは省略）発注 Gate / CB 等
  - data/（データ格納先のデフォルト）
    - kabusys.duckdb (default DUCKDB_PATH)
    - monitoring.db (default SQLITE_PATH)

---

## 実装上の注意点 / 重要事項

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に実施します。配布後に import されても CWD に依存せず正しく動作するよう設計されています。
- 環境変数の優先順位: OS 環境変数 > .env.local > .env。ただし OS 環境変数は保護され、.env.local の override があっても上書きされません。
- Paper Trading 用の挙動は設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）で制御できます。
- OpenAI を利用する機能（news_nlp, regime_detector）は API キーが必須です。API エラー時はフェイルセーフ（部分的に0.0でフォールバック）を取る実装がありますが、キーの設定は忘れずに。
- ExecutionEngine は PID ファイル / kill.flag による運用制御、Reconciler による再起動後の自動復旧、OrderManager の二相永続化などクラッシュ安全性を考慮して設計されています。実運用では BrokerAPI 実装と永続層の整合性に注意してください。
- Streamlit ダッシュボードは SQLite を読み取り専用で開くことを推奨しています。

---

## サポート / 開発メモ

- テストしやすさを考慮して外部 API 呼び出し箇所（OpenAI 呼び出し等）は直接パッチ / モック可能な形に実装されています（例: _call_openai_api を unittest.mock.patch）。
- DuckDB / SQLite のスキーマ依存が多いため、既存データの整備（prices_daily / raw_financials / raw_news 等の投入）が前提になります。
- コアのアルゴリズム（position sizing, sector cap, regime multiplier）はドキュメント（PortfolioConstruction.md、StrategyModel.md など）に基づいた実装を想定しています（該当ドキュメントは別途管理されている想定）。

---

必要であれば、以下を追加で作成できます：
- 詳細な .env.example（全キーの説明付き）
- 開発用の docker-compose / 起動スクリプト
- BrokerAPI のスタブ実装サンプル
- OrderRepository / OrderRecord の完全実装例
- ユニットテストの README（テスト実行方法）

ご希望があれば上記いずれかを作成します。