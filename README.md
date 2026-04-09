# KabuSys

日本株の自動売買／リサーチ向けユーティリティ群と実行基盤のライブラリ群です。  
このリポジトリは、戦略のファクター計算・ポートフォリオ構築、Execution エンジン、監視（Monitoring）機能、AI を使ったニュースセンチメント評価などをモジュール化して提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は主に以下の目的を持つコンポーネントで構成されています。

- リサーチ（ファクター計算 / 特徴量解析）: DuckDB 上の市場データからモメンタム・ボラティリティ・バリュー等のファクターを計算
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター制限など
- Execution（発注エンジン）: OrderManager / ExecutionEngine による安全な発注ワークフロー、リコンシリエーション
- 監視（Monitoring）: システム状態・注文滞留・リスク監視、LINE 通知、Streamlit ダッシュボード
- AI ユーティリティ: OpenAI を用いたニュースのセンチメント評価（銘柄別）・市場レジーム判定

設計方針の一例:
- DuckDB / SQLite を使い、実運用時のデータ参照はローカル DB のみ（本番注文 API へは明示的に接続）
- 可能な限り副作用を抑えた純粋関数をリサーチ・ポートフォリオ周りで採用
- OpenAI 呼び出しはフェイルセーフ（失敗時はスキップやフォールバック）で実装

---

## 主な機能一覧

- kabusys.research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上の市場データからファクターを計算
  - calc_forward_returns / calc_ic / factor_summary：将来リターン・IC計算・統計サマリ
- kabusys.portfolio
  - select_candidates：BUY シグナルから候補抽出
  - calc_equal_weights / calc_score_weights：重み計算
  - calc_position_sizes：単元株丸めやリスク制約を考慮した株数計算
  - apply_sector_cap / calc_regime_multiplier：セクター集中制限・レジーム乗数
- kabusys.ai
  - score_news：OpenAI を使った銘柄別ニュースセンチメントスコア計算と ai_scores への書き込み
  - score_regime：ETF の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定
- kabusys.execution
  - OrderManager / ExecutionEngine：注文ライフサイクル管理・シグナル処理・push drain、リコンシリエーション
  - broker_api：ブローカー抽象（Protocol / データモデル / 例外）
- kabusys.monitoring
  - MonitoringDB：SQLite ベースの永続化
  - SystemMonitor / TradeMonitor / RiskMonitor：監視ロジック
  - AlertManager：LINE へのプッシュ通知（クールダウン管理）
  - KillSwitch / MonitoringEngine：自動停止ロジックと定期ポーリング
  - streamlit_dashboard：監視ダッシュボード（Streamlit）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - 必要な主なパッケージ（例）
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit
   - 例:
     - pip install duckdb openai requests psutil streamlit
   - ※ プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください。
4. データベースの初期化（監視 DB）
   - monitoring DB を初期化するには Python から init_monitoring_db を呼びます:
     - from kabusys.monitoring.monitoring_db import init_monitoring_db
     - import sqlite3
     - conn = sqlite3.connect("data/monitoring.db")
     - init_monitoring_db(conn)
5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動ロードはデフォルトで有効）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 詳しいキーは次節を参照。

---

## 環境変数（主要）

config モジュールは .env / .env.local / OS 環境変数を読み込みます。優先順は OS 環境 > .env.local > .env。

主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / score_regime 等で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper trading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行管理用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env)
- JQUANTS_REFRESH_TOKEN=xxxxx
- KABU_API_PASSWORD=secret
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LINE_CHANNEL_ACCESS_TOKEN=
- LINE_USER_ID=
- KABUSYS_ENV=development
- LOG_LEVEL=INFO

---

## 使い方（主要な実行例）

以下は一部のユースケース例です。実運用では各コンポーネントを組み合わせて利用します。

1) DuckDB を使ったファクター計算（Python から）
- 例: momentum を計算
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum
  - res = calc_momentum(conn, datetime.date(2026, 3, 20))

2) OpenAI を使ったニューススコアリング
- ai.score_news は内部で OPENAI_API_KEY を参照（引数で上書き可）
  - from kabusys.ai import score_news
  - import duckdb, datetime
  - conn = duckdb.connect("data/kabusys.duckdb")
  - n = score_news(conn, datetime.date(2026, 3, 20), api_key="sk-...")

3) 市場レジーム判定
  - from kabusys.ai import score_regime
  - score_regime(conn, datetime.date(2026, 3, 20), api_key="sk-...")

4) 監視ダッシュボード（Streamlit）
- 起動コマンド（プロジェクトルートから）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

5) 監視 DB 初期化
- Python スクリプト等から init_monitoring_db を呼ぶ（上記セットアップ参照）

6) ExecutionEngine（概要）
- 実際の起動には Broker の実装（BrokerAPIProtocol 準拠）、OrderRepository（SQLite）、RiskManager 等が必要です。主要フローは ExecutionEngine.run_session()。
- ExecutionEngine は起動時に reconciler を実行し、kill.flag 等で安全停止します。
- 実運用の構成例（擬似コード）:
  - broker = MyKabuBroker(...)
  - repo = OrderRepository(sqlite_conn)
  - risk_manager = RiskManager(...)
  - order_manager = OrderManager(broker, repo)
  - engine = ExecutionEngine(broker, repo, risk_manager, order_manager, duckdb_conn, EngineConfig(target_date=...))
  - engine.run_session()

注意: ExecutionEngine の完全な稼働にはブローカークライアントと DB スキーマが整備されている必要があります。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み等）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - risk_adjustment.py      — セクター制限・レジーム乗数
    - position_sizing.py      — 株数決定・リスク制限
  - research/
    - factor_research.py      — Momentum / Volatility / Value の計算
    - feature_exploration.py  — 将来リターン・IC・統計
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）処理
    - regime_detector.py      — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / MonitoringDB
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py
    - order_manager.py
    - order_repository.py     — （実装ファイル例あり）
    - reconciler.py
    - execution_engine.py
    - ...（order_record, risk_manager 等）
  - ai, research, portfolio などは互いに小範囲で依存（主にデータ/DB を介した分離設計）

---

## 注意事項 / 運用上のポイント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を検出）から行われます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API を利用する機能は外部 API への依存があるため、API キーやコスト、レート制限に注意して運用してください。実装ではリトライやフェイルセーフが組み込まれていますが、プロダクションでの利用時にはさらに制御（バッチの throttling、監査ログ等）を検討してください。
- ExecutionEngine / OrderManager はクラッシュ安全化のため複数段階で永続化と同期ロジック（OrderSent の永続化→ブローカー呼び出し→broker_order_id の保存→OrderAccepted 昇格等）を実装しています。ブローカー実装は BrokerAPIProtocol に準拠してください。
- DuckDB / SQLite のスキーマ整備やデータ投入は別途スクリプトで行うことを想定しています（prices_daily / raw_financials / raw_news / news_symbols / ai_scores / market_regime 等のテーブルが前提）。

---

## 参考・補足

- 設定値の検証やデフォルトは src/kabusys/config.py を確認してください（PAPER_FILL_MODE の有効値など）。
- news_nlp と regime_detector は OpenAI の「JSON Mode」を前提としたレスポンス構造で実装されています。レスポンス検証とクリッピングを行った上で DB へ書き込みます。
- Streamlit ダッシュボードは監視 DB を read-only モードで開くため、実稼働中の DB を壊すことなく参照できます（URI パラメータで ?mode=ro を付与）。

---

もし README に追加したい情報（例えば利用例スクリプト、依存バージョンの固定、CI / デプロイ手順など）があれば教えてください。README をその内容に合わせて拡張します。