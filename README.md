KabuSys — 日本株自動売買システム
================================

以下は、このコードベース（src/kabusys 以下）の概要・機能・セットアップ方法・使い方・ディレクトリ構成のまとめです。開発者／運用者向けの簡易ドキュメントとしてまとめています。

プロジェクト概要
----------------
KabuSys は日本株自動売買のためのライブラリ兼ミニフレームワークです。主要な機能群は以下の通りです：
- シグナル → 発注までの ExecutionEngine（発注管理、状態遷移、リコンシリエーション）
- ポートフォリオ構築（候補選定、重み計算、リスク調整、ポジションサイズ算出）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール（ニュースセンチメントの LLM 評価、レジーム判定）
- 監視（システム / 注文 / リスク監視、LINE 通知、Streamlit ダッシュボード）
- 環境変数・設定管理（.env 自動読み込み、Settings オブジェクト）

このリポジトリは DuckDB（価格データ・財務データ等の時系列リポジトリ）と SQLite（監視ログ等）を組み合わせて動作します。外部 API は主に kabu ステーション（ブローカー）と OpenAI（ニュース NLP / レジーム判定）を想定しています。

主な機能一覧
-------------
- 設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（OS 環境変数優先）
  - 必須値の確認（例: JQUANTS_REFRESH_TOKEN 等）
- ポートフォリオ構築（pure functions、DB参照なし）
  - 候補選定（select_candidates）
  - 等比重 / スコア重み（calc_equal_weights / calc_score_weights）
  - セクター上限の適用（apply_sector_cap）
  - レジームに応じた乗数（calc_regime_multiplier）
  - ポジションサイズ算定（calc_position_sizes：リスクベース／等配分など）
- リサーチ（DuckDB による集計）
  - Momentum / Value / Volatility ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- AI（OpenAI 連携）
  - ニュース記事を集約して LLM でセンチメントを算出、ai_scores に書き込み（news_nlp.score_news）
  - ETF（1321）MA とマクロニュースセンチメントを合成して市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しは冪等・リトライ・フェイルセーフ設計
- 監視
  - MonitoringDB：SQLite スキーマ定義 / 初期化
  - SystemMonitor / TradeMonitor / RiskMonitor：ログ記録・アラート記録
  - AlertManager：LINE Push による通知（クールダウン管理）
  - KillSwitch：フラグファイル（data/kill.flag）による ExecutionEngine 停止
  - Streamlit ダッシュボード（監視データの閲覧）
- 実行・発注層
  - Broker API Protocol / データモデル（OrderRequest, OrderStatus, Position, ...）
  - OrderManager：DB と Broker API の間での安全な状態遷移・発注処理
  - ExecutionEngine：シグナル取得 → Gate 検査 → 発注ループ + WebSocket ドレイン
  - Reconciler：再起動時の自動復旧・ブローカー照合

セットアップ手順
----------------

1. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. パッケージインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限の主要依存（手動インストール例）:
     - pip install duckdb openai requests psutil streamlit

   （注）sqlite3 は標準ライブラリです。その他の依存は実行する機能に応じて必要になります。

3. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます（起動時）。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。
   - 代表的な環境変数（例、.env に記載）:

     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxx
     LINE_USER_ID=Uxxxxxxxxxxxxxxxx
     DUCKDB_PATH=data/prices.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_FILL_MODE=instant
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

   - .env.local が存在する場合は .env の上から上書きされます（OS 環境変数は常に優先）。

4. 監視 DB 初期化（SQLite）
   - Python から初期化可能:

     python - <<'PY'
     import sqlite3
     from kabusys.monitoring.monitoring_db import init_monitoring_db
     conn = sqlite3.connect("data/monitoring.db")
     init_monitoring_db(conn)
     conn.close()
     PY

5. DuckDB データ準備
   - ファイナンス / 価格データを格納する DuckDB（paths は DUCKDB_PATH）を用意してください。
   - テーブル名（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime, signals, portfolio_targets 等）をコード内 SQL が参照します。データの投入は外部スクリプトまたは ETL パイプラインで行ってください。

基本的な使い方（例）
-------------------

- Settings（環境変数から設定を取得）
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_base_url, settings.duckdb_path などを参照できます。

- リサーチ関数（DuckDB 接続を渡して呼ぶ）
  - 例: calc_momentum

    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/prices.duckdb")
    rows = calc_momentum(conn, date(2026, 3, 20))
    # rows は [{"date": ..., "code": "1234", "mom_1m": 0.12, ...}, ...]

- ニュース NLP（OpenAI を用いたスコアリング）
  - score_news は DuckDB 接続と target_date、api_key を受け取り ai_scores テーブルへ書き込みます。

    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/prices.duckdb")
    score_news(conn, date(2026, 3, 20), api_key="sk-...")

  - api_key を渡さない場合は環境変数 OPENAI_API_KEY を使用します。API 呼び出しはリトライ・バリデーションを行います。

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=...) は market_regime テーブルに書き込みます。

- Streamlit ダッシュボード起動（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringEngine（ポーリング実行）
  - SystemMonitor / TradeMonitor / RiskMonitor 等を組み合わせて MonitoringEngine を作成し .run() または .run_once() を呼びます。
  - AlertManager を与えることで LINE 通知が可能です（トークン／ユーザーID が必要）。

- ExecutionEngine（実稼働の発注ループ）
  - ExecutionEngine の利用には BrokerAPI の実装、OrderRepository、RiskManager、OrderManager、Reconciler 等を用意する必要があります。Production で利用する際はこれらを組み合わせて起動してください。
  - ExecutionEngine.run_session() が主な実稼働のエントリポイントです。起動時の PID 書き込み・kill.flag チェック・reconciliation を経てセッションを実行します。

設定（主要な環境変数）
--------------------
主に config.Settings で参照される環境変数（抜粋）：

- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API トークン
- KABU_API_PASSWORD（必須） — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（LINE）用
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の挙動（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading DB パス
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行管理関連
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視しきい値
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/…（ログレベル）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを停止

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールの構成（抜粋）：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env 管理（Settings）
  - portfolio/
    - __init__.py
    - portfolio_builder.py   — 候補選定・重み計算
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - position_sizing.py     — 株数決定・スケールダウンロジック
  - research/
    - __init__.py
    - factor_research.py     — momentum/value/volatility 計算
    - feature_exploration.py — 将来リターン / IC / summary
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース集約 → OpenAI でセンチメント、ai_scores 書込
    - regime_detector.py     — MA と マクロ記事からレジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite スキーマ / MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - broker_api.py          — Broker API のデータモデル / Protocol / 例外
    - order_manager.py       — 発注状態遷移と broker 呼び出しの整合
    - order_repository.py    — （DB 層、ファイル内で参照されるが実装別）
    - reconciler.py          — 起動時の自動復旧（Order / Position 照合）
    - execution_engine.py    — Signal → 発注の実行エンジン（WebSocket drain など）

注意事項 / 運用メモ
------------------
- .env のパーサはシェル風の export KEY=val、クォート、インラインコメント（#）などに対応していますが、特殊ケースは想定外の動作をすることがあります。.env.example を参照して正しく設定してください。
- OpenAI API 使用時はコストとレート制限に注意。news_nlp / regime_detector はリトライロジックとフェイルセーフ（API失敗時はスコアを 0.0 にフォールバック）を備えていますが、運用上の監視は必要です。
- ExecutionEngine は実際の資金を動かすための重要なコンポーネントです。リスク管理（RiskManager）、kill.flag の取り扱い、PID ファイル管理、Reconciler の確認など運用手順を厳密に整備してください。
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して .env 自動ロードを無効化できます。

貢献・拡張案
--------------
- 銘柄ごとの lot_size をサポートする（position_sizing の拡張）
- prices_daily の欠損価格を補完するフォールバックロジック（risk_adjustment の TODO）
- ai モジュールのレスポンス検証の強化、バッチ処理の永続化戦略
- CLI / エントリポイントスクリプト（monitoring 起動、engine 起動など）の追加

最後に
------
この README はコード内の docstring / コメントに基づき要点をまとめたものです。実稼働前に各モジュールの詳細な挙動（特に発注／再試行／DB トランザクション周り）を十分確認してください。必要であれば各モジュールごとの詳細ドキュメントを追加できます。