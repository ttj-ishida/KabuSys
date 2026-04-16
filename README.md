KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした軽量なシステムです。  
主な目的は以下の通りです。

- 注文発行・管理を行う ExecutionEngine（本番／Paper Trading モード対応）
- 監視（プロセス／リソース／注文異常／ドローダウン等）とアラート送信
- ポートフォリオ構築（銘柄選定・重み計算・株数決定）
- 研究用ファクター計算（DuckDB を用いたファクター群）
- ニュースの LLM による NLP スコアリング（OpenAI API）
- Paper Trading 検証レポートや Streamlit ダッシュボード等の運用ツール

主な機能一覧
-------------
- Execution
  - ExecutionEngine（再起動リコンシリエーション、リスク管理、注文状態管理）
  - Broker クライアントを抽象化し Paper Trading 用の Mock をサポート
  - Paper Trading 用に本番 DB と分離された SQLite（data/paper_trading.db を想定）

- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク使用率、データ鮮度、Execution プロセスの監視）
  - TradeMonitor（滞留注文、約定価格異常の検出）
  - RiskMonitor（ドローダウン・ポジション上限監視、ダッシュボード更新）
  - KillSwitch（重大リスクで ExecutionEngine 停止のための flag ファイル書き込み）
  - AlertManager（LINE Messaging API による通知）
  - monitoring DB（SQLite）と Streamlit ダッシュボード

- Portfolio
  - 銘柄候補選択（スコア順ソート）
  - 等配分 / スコア配分 重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ算出（リスクベース等）、単元株丸め、集約キャップ処理

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン・IC 計算・統計要約など
  - DuckDB を用いた高速な時系列集計

- AI
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF の MA200 乖離＋マクロニュースセンチメントで market regime を判定・保存
  - API 呼び出しはリトライ/バックオフ・レスポンス検証を実装しフェイルセーフを重視

セットアップ手順
----------------

1. 前提
   - Python 3.9+（コードは型アノテーションを利用）
   - system パッケージ: sqlite3 は標準に含まれる
   - 推奨 Python パッケージ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例（仮想環境推奨）:
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb psutil requests openai streamlit

2. プロジェクトルート検出と .env の自動読み込み
   - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env を自動で読み込みます。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

3. 必須環境変数
   - JQUANTS_REFRESH_TOKEN （J-Quants API を使用する場合）
   - KABU_API_PASSWORD （kabuステーション API を使用する場合）
   - OPENAI_API_KEY （AI 機能を使う場合）
   - これらが未設定の場合、Settings のプロパティアクセスで例外が発生します。

4. 任意設定（主要なもの）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動、default "instant"）
   - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（Paper Trading 用 DB）
   - SQLITE_PATH: data/monitoring.db（Monitoring 用 SQLite、デフォルト）
   - DUCKDB_PATH: data/kabusys.duckdb（DuckDB ファイルパス）
   - LOG_LEVEL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID など

5. データディレクトリ
   - data/ 配下に DB ファイルやフラグファイルを置くことが想定されています。
   - 例: data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb, data/execution.pid, data/stop_requested.flag, data/kill.flag

使い方（実行例）
----------------

- ExecutionEngine（本番 or Paper Trading）
  - Paper Trading モードで起動:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番モードで起動:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 起動時、process 優先度を上げ、PID ファイルを扱い、stop flag を監視して安全に停止します。
  - ExecutionEngine は stop フラグ（data/stop_requested.flag）や kill.flag によって停止されます。

- Monitoring（ポーリング監視）
  - 監視ループ起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（data/monitoring.db）を使用します。

- Streamlit ダッシュボード
  - 起動方法（例）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは monitoring DB を読み取り専用で開きます（存在しない場合はエラー表示）。

- Paper Trading 検証レポート
  - 生成スクリプト:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定できます。環境変数 PAPER_TRADING_SQLITE_PATH があればそちらが優先されます。

- 研究用 API（プログラム内で）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    conn = duckdb.connect("data/kabusys.duckdb")
    recs = calc_momentum(conn, date(2026, 4, 1))

- AI スコア링（プログラム内）
  - news_nlp.score_news を呼び出して ai_scores に書き込み:
    from kabusys.ai import score_news
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

注意点 / 運用上のポイント
-------------------------
- .env 読み込みはプロジェクトルートを基準に行われます（.git または pyproject.toml が目印）。
- Paper Trading は本番 DB と分離する設計（settings.is_paper による切替）。
- OpenAI など外部 API はリトライやフォールバック（失敗時は安全側の値）を組み込んでありますが、APIキーの設定は必須です。
- kill.flag / stop_requested.flag / execution.pid の扱い:
  - kill.flag: KillSwitch により書き込まれ、ExecutionEngine に停止シグナルを送ります。
  - stop_requested.flag: run_execution / run_monitoring の外部停止トリガーとして利用。
  - execution.pid: ExecutionEngine の PID を管理（stale PID の検出・削除処理あり）。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys をルートとするパッケージ構成の抜粋）

- src/kabusys/
  - __init__.py                     — パッケージ定義・バージョン
  - config.py                       — 環境変数/.env 読み込みと Settings（中央設定）
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト

  - execution/
    - order_manager.py              — 発注フローの外向き API
    - order_repository.py
    - reconciler.py                 — 起動時リコンシリエーション
    - execution_engine.py           — 実行エンジン本体（参照あり）
    - broker_factory.py / broker_api.py — ブローカー抽象・実装

  - monitoring/
    - monitoring_db.py              — SQLite 永続化層（system_status, trade_logs 等）
    - system_monitor.py             — システム監視（CPU/メモリ/プロセス/データ鮮度）
    - trade_monitor.py              — 注文滞留・約定異常検出
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — kill.flag 書き込みロジック
    - alert_manager.py              — LINE 通知クライアント
    - monitoring_engine.py          — 各 Monitor を束ねるループ
    - streamlit_dashboard.py        — Streamlit ダッシュボード

  - portfolio/
    - portfolio_builder.py          — 候補選定・重み計算
    - position_sizing.py            — 株数・資金配分計算
    - risk_adjustment.py            — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py            — Momentum / Volatility / Value 計算
    - feature_exploration.py        — 将来リターン・IC 等の解析
    - __init__.py

  - ai/
    - news_nlp.py                   — ニュース NLP（OpenAI） & ai_scores 書込
    - regime_detector.py            — マーケットレジーム判定（MA + マクロセンチメント）
    - __init__.py

  - data/ (想定ローカルディレクトリ・運用で作成)
    - monitoring.db                  — monitoring SQLite DB（init_monitoring_db によりテーブル作成）
    - paper_trading.db               — Paper Trading 用 SQLite
    - kabusys.duckdb                 — DuckDB データファイル
    - execution.pid
    - stop_requested.flag
    - kill.flag

  - utils/
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ

拡張・開発メモ
--------------
- DuckDB によるデータ処理を前提としているため、prices_daily / raw_financials / raw_news 等のテーブル準備が必要です（データパイプラインは kabusys.data.pipeline 参照）。
- OpenAI 呼び出し部はテスト可能性を考慮して内部呼び出し関数を patch しやすい設計になっています（ユニットテストでの模擬が容易）。
- settings はプロパティ駆動で厳格に検証するため、環境変数の設定ミスは早期に検出されます。

.env 例（テンプレート）
-----------------------
以下をプロジェクトルートの .env に置いてください（値は例）:

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=your_line_token
LINE_USER_ID=your_line_user_id

ライセンス / 依存関係
--------------------
- 特に明記がない場合はプロジェクトのルールに従ってください。  
- 実行に必要な外部ライブラリは上記「セットアップ手順」を参照してください。

問い合わせ・貢献
----------------
バグ報告・改善提案・プルリクエストはプロジェクトの Issue / PR にてお願いします。README の改善やドキュメント追記も歓迎します。

以上。必要であればインストール手順の詳細（requirements.txt 作成例、Dockerfile、systemd ユニットの雛形など）や各モジュールの API 使用例を追加で作成します。どの項目を詳述しましょうか？