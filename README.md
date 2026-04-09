# KabuSys

日本株向けの自動売買 / リサーチ / 監視フレームワーク。  
ポートフォリオ構築、ポジションサイジング、リスク制御、ニュースのLLMセンチメント評価、実行エンジン（kabuステーション連携想定）、監視ダッシュボードなどのコンポーネントを含むモジュール群です。

この README はコードベース（src/kabusys 以下）を元にした概要、機能、セットアップ、使い方、ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール集合です。

- ファクター計算（モメンタム / バリュー / ボラティリティなど）と特徴量解析（IC, 統計サマリー）
- ポートフォリオ構築（候補選定、重み付け、リスク調整、単元丸め、株数算出）
- ニュースの自然言語処理（OpenAI API を用いた銘柄別センチメント算出）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM 評価を合成）
- 発注実行エンジン（Signal Queue → Broker API、再起動時リコンシリエーション、リスクゲート）
- 監視（システム状態、注文滞留、ドローダウン監視、LINE 通知、Streamlit ダッシュボード）
- 永続化層：DuckDB（時系列・リサーチデータ）と SQLite（監視ログ・注文履歴等）

設計方針として、本番ブローカー API への誤発注を避けるため、リサーチ系関数は DB（DuckDB）のみ参照し外部への副作用を持たないよう分離されています。LLM 呼び出し箇所はフェイルセーフ実装（失敗時は中立値などで継続）です。

---

## 主な機能一覧

- ポートフォリオ関連
  - select_candidates（スコア降順で候補選定）
  - calc_equal_weights / calc_score_weights（配分重み計算）
  - apply_sector_cap（セクター集中の除外）
  - calc_regime_multiplier（市場レジームに応じた乗数）
  - calc_position_sizes（株数算出、lot 単位丸め、aggregate cap）

- リサーチ / ファクター
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を利用）
  - calc_forward_returns, calc_ic, factor_summary（特徴量探索、IC 計算、統計サマリー）
  - zscore_normalize（kabusys.data.stats 経由で利用）

- AI（OpenAI）関連
  - score_news（raw_news を集約して LLM に送り ai_scores テーブルへ保存）
  - score_regime（ETF MA とマクロニュースを LLM で評価して market_regime テーブルへ保存）

- 実行 / 発注
  - ExecutionEngine（Signal 処理 → 発注 → WebSocket push ドレイン）
  - OrderManager（注文状態遷移・送信・同期・キャンセル）
  - Reconciler（起動時の自動復旧・ブローカとの突合）
  - broker_api（データモデル・Protocol・例外）

- 監視
  - MonitoringDB（SQLite による永続化テーブル作成・CRUD）
  - SystemMonitor / TradeMonitor / RiskMonitor（各種チェック）
  - KillSwitch / AlertManager（停止フラグ・LINE 通知）
  - Streamlit ダッシュボード（簡易 UI）

---

## セットアップ手順（開発用・ローカル実行想定）

必要な Python バージョン: 3.10 以上（typing の `X | Y` 構文を使用）

1. リポジトリをチェックアウト
   - ルートに pyproject.toml や .git がある想定です（config の自動 .env 検出に利用）。

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - openai
     - requests
     - psutil
     - streamlit
   - 例:
     - pip install duckdb openai requests psutil streamlit

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。
   ※ sqlite3 は標準ライブラリに含まれます。

4. 環境変数設定
   - プロジェクトルートの `.env` / `.env.local` が自動で読み込まれます（設定は src/kabusys/config.py を参照）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途）。

5. Monitoring DB の初期化（SQLite）
   - Python セッションで:
     from sqlite3 import connect
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = connect("data/monitoring.db")
     init_monitoring_db(conn)

6. DuckDB（時系列 / リサーチデータ）用 DB ファイルの用意
   - テーブル（prices_daily / raw_financials / raw_news / news_symbols / signals / portfolio_targets / ai_scores / market_regime など）が必要です。データ準備は別途 ETL / pipeline を実装するかサンプルデータをロードしてください。

---

## 環境変数一覧（主なもの）

設定は .env や OS 環境変数で行います。主要キーと用途:

- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで参照）
- LINE_CHANNEL_ACCESS_TOKEN — AlertManager のための LINE トークン
- LINE_USER_ID — LINE 通知の送信先ユーザー ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH — 実行 PID ファイルのパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値
- KABUSYS_ENV — 環境: development|paper_trading|live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

例 .env（最小例）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=DEBUG

---

## 使い方（代表的な呼び出し例）

※ ここではライブラリ API を直接呼ぶ簡易例を示します。実運用では各種依存（DB スキーマ・データ）を準備してください。

- Streamlit 監視ダッシュボード
  - コマンド:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - （読み取り専用 URI を使ってデータベースを開きます。MonitoringEngine を稼働させてデータを生成してください）

- ニューススコアリング（AI）
  - 例（Python）:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
    print(f"written: {n_written}")

- レジーム判定（AI）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- MonitoringDB 初期化 / 利用
  - 例:
    import sqlite3
    from kabusys.monitoring.monitoring_db import init_monitoring_db, MonitoringDB
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)
    mdb = MonitoringDB(conn)
    mdb.log_system_status(cpu_percent=10.0, memory_percent=20.0, disk_percent=30.0, process_ok=True)

- ExecutionEngine の実行（概要）
  - 実行には BrokerAPI の実装（BrokerAPIProtocol に準拠）や OrderRepository, RiskManager, OrderManager, Reconciler 等の組み立てが必要です。ライブラリ本体は ExecutionEngine クラスを提供しており、以下の流れで使用します（擬似的）:
    - 準備: duckdb_conn, broker_impl, order_repo, risk_manager, order_manager, reconciler（任意）
    - config = EngineConfig(target_date=date(YYYY,MM,DD))
    - engine = ExecutionEngine(broker_impl, order_repo, risk_manager, order_manager, duckdb_conn, config, reconciler)
    - engine.run_session()
  - 実運用ではプロセス管理（PID / kill.flag / ログ）に注意してください。

---

## テスト・デバッグ向けのヒント

- 自動 .env ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 関連関数は外部呼び出しをテストで差し替えられるよう設計されています（例えば unittest.mock.patch で _call_openai_api をモック）。
- DuckDB / SQLite の読み取り専用オープンは Streamlit ダッシュボードで想定されています（URI ベースの接続）。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py — パッケージ宣言（バージョン情報、主要サブパッケージの __all__）
- config.py — 環境変数/設定の読み込み・管理（.env 自動読み込み、Settings クラス）
- ai/
  - __init__.py — ai パッケージ公開 API（score_news 等）
  - news_nlp.py — ニュース集約・OpenAI を使ったセンチメント評価 → ai_scores 書き込み
  - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定
- portfolio/
  - __init__.py — ポートフォリオ関連関数のエクスポート
  - portfolio_builder.py — 候補選定・配分（等配分 / スコア加重）
  - risk_adjustment.py — セクターキャップ、レジーム乗数
  - position_sizing.py — 株数計算・aggregate cap・単元丸め
- research/
  - __init__.py — 研究用 API エクスポート
  - factor_research.py — momentum/value/volatility ファクター計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- monitoring/
  - __init__.py — 監視パッケージエクスポート
  - monitoring_db.py — SQLite スキーマ作成・簡易操作ラッパー
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常検出
  - risk_monitor.py — ダローダウン / ポジション上限チェック + dashboard 更新
  - kill_switch.py — kill.flag の書き込み/削除（Execution 停止）
  - alert_manager.py — LINE Push 通知の送信（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるポーリング実行（run / run_once）
  - streamlit_dashboard.py — Streamlit による簡易監視ダッシュボード
- execution/
  - broker_api.py — Broker API のデータモデル・Protocol・例外
  - execution_engine.py — Signal Queue Pull 型発注エンジン（Session 実行ロジック）
  - order_manager.py — Order State Machine の外向き API（create/send/sync/cancel）
  - reconciler.py — 再起動時リコンシリエーション（OrderSent 照合・ポジション差分）
  - （その他、order_record.py, order_repository.py, risk_manager.py 等はコードベースに存在すると想定）
- monitoring/（上記）
- data/（実際のデータベースファイルや ETL はプロジェクトルートに配置する想定）
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db

---

## 注意事項 / 制約

- DuckDB / SQLite のテーブルスキーマや必須データ（prices_daily, raw_financials, raw_news, news_symbols, signals, portfolio_targets, ai_scores, market_regime など）は本 README では省略します。実行前に適切なスキーマとデータを準備してください（factor_research や news_nlp の SQL クエリを参照すると必要カラムが分かります）。
- OpenAI API を使用する機能は API キー・利用制限・コストに注意してください。呼び出しはリトライや失敗時のフォールバック処理が実装されていますが、運用時のレート設計を検討してください。
- 本コードはサンプルの自動売買フレームワークです。実際の資金を扱う場合は追加の安全弁・検証・法的な確認が必要です。

---

この README はコードベースの主要機能と利用方法の概要を示しています。より詳細な API / DB スキーマ / 運用手順は個別ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）やコード内の docstring を参照してください。README に関して追記・修正したい点があれば教えてください。