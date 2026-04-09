KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした小規模なライブラリ群です。  
主に以下の責務を持つモジュールで構成されています。

- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- ファクター計算・リサーチ（モメンタム／ボラティリティ／バリュー等）
- ニュースの NLP スコアリング（OpenAI を利用したセンチメント評価）
- 市場レジーム判定（ETF の MA とマクロニュースを組み合わせる）
- 注文管理・発注エンジン（ExecutionEngine、OrderManager、Reconciler 等）
- 監視（システム／注文／リスク監視、LINE 通知、Streamlit ダッシュボード）
- 環境変数管理（.env の自動読み込み、Settings）

注意: 本リポジトリは本番ブローカーや外部 API と連携する機能を含みます。実際の資金で利用する前に十分なテストを行ってください。

主な機能一覧
--------------
- 環境変数／設定管理（kabusys.config）
  - .env / .env.local の自動ロード（OS 環境変数優先、.env.local は上書き）
  - 必須値チェック（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）
  - 等配分・スコア加重配分（calc_equal_weights / calc_score_weights）
  - リスク調整（セクター上限 filter、レジーム乗数）
  - ポジションサイズ計算（複数手法、lot 単位丸め、aggregate cap）
- リサーチ（kabusys.research）
  - momentum / volatility / value のファクター計算（DuckDB の prices_daily/raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI（kabusys.ai）
  - ニュースセンチメントのバッチスコアリング（OpenAI を利用、結果を DuckDB に格納）
  - 市場レジーム判定（ETF MA と LLM によるマクロセンチメントの合成）
- 監視（kabusys.monitoring）
  - SQLite による監視ログ永続化（init_monitoring_db）
  - System / Trade / Risk モニタ、AlertManager（LINE 通知）
  - Streamlit ダッシュボード（監視 DB を可視化）
- 発注関連（kabusys.execution）
  - Broker API の抽象化（Protocol / データモデル / 例外）
  - OrderManager（作成→送信→同期→キャンセル）、Reconciler（復旧）
  - ExecutionEngine（シグナル処理ループ、WebSocket push ドレイン、kill flag 制御）

セットアップ手順
----------------
1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージのインストール（最低限）
   - pip install --upgrade pip
   - pip install duckdb openai requests psutil streamlit

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください。
   - pip install -r requirements.txt
   - またはパッケージを開発モードでインストール:
     pip install -e .

3. データベース（DuckDB / SQLite）の準備
   - DuckDB のデータファイル（デフォルト: data/kabusys.duckdb）に prices_daily / raw_financials 等のテーブルが必要です。
   - 監視用 SQLite DB（デフォルト: data/monitoring.db）は init_monitoring_db() で初期化できます。

4. 環境変数 / .env の設定
   - ルートに .env（または .env.local）を置くと自動読み込みされます（プロジェクトルートは .git または pyproject.toml を基準に自動探索）。
   - 自動ロードを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（Settings 参照）
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants 用）
- KABU_API_PASSWORD — 必須（kabu API）
- KABU_API_BASE_URL — 任意（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必須
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager のため
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE — Paper Trading の fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite パス
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値, KABUSYS_ENV, LOG_LEVEL

例: .env（最小）
    JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    OPENAI_API_KEY=sk-xxxx
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    LINE_CHANNEL_ACCESS_TOKEN=
    LINE_USER_ID=

使い方（代表的な例）
-------------------

- 環境設定を取得する
    from kabusys.config import settings
    print(settings.duckdb_path, settings.is_paper)

- DuckDB を使ったファクター計算（例: momentum）
    import duckdb
    from datetime import date
    from kabusys.research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, date(2026, 3, 20))
    # records は {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"} のリスト

- ニュース NLP スコアリング（OpenAI 必須）
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026,3,20), api_key="sk-xxx")
    print(f"Wrote {written} scores")

- 監視 DB 初期化
    import sqlite3
    from kabusys.monitoring import init_monitoring_db

    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)

- Streamlit ダッシュボード起動
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ExecutionEngine の起動（概念）
  ExecutionEngine は Broker 実装、OrderRepository、RiskManager、OrderManager、DuckDB 接続、EngineConfig を組み合わせて動きます。  
  実稼働ではブローカークライアント（kabu station クライアント等）を提供する必要があります。テスト時はモック実装を注入してください。

自動 .env ロードの挙動
---------------------
- 自動読み込みはプロジェクトルート（.git または pyproject.toml のある上位ディレクトリ）を基準に行います。
- 読み込み順序:
  1. OS 環境変数（既存）
  2. .env （未設定のキーのみセット）
  3. .env.local（既存 OS 環境変数は保護しつつ .env.local で上書き）
- 無効化:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします（テスト用）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py                 — パッケージ定義
- config.py                   — 環境変数 / Settings 管理（.env 自動ロード）
- ai/
  - news_nlp.py               — ニュースの LLM ベースセンチメントスコアリング
  - regime_detector.py        — 市場レジーム判定（ETF MA + マクロセンチメント）
- portfolio/
  - portfolio_builder.py      — 候補選定・重み計算
  - position_sizing.py        — 発注株数計算（リスクベース等）
  - risk_adjustment.py        — セクター制約・レジーム乗数
- research/
  - factor_research.py        — momentum/volatility/value の計算（DuckDB）
  - feature_exploration.py    — forward returns / IC / summary
- monitoring/
  - monitoring_db.py          — SQLite スキーマ / 永続化操作
  - system_monitor.py         — システム・データ鮮度監視
  - trade_monitor.py          — 注文滞留・約定異常検出
  - risk_monitor.py           — ドローダウン/ポジション上限監視
  - kill_switch.py            — kill.flag 書き込み・管理
  - alert_manager.py          — LINE プッシュ通知ラッパー
  - monitoring_engine.py      — 各 Monitor を束ねるループ
  - streamlit_dashboard.py    — Streamlit ダッシュボード
- execution/
  - broker_api.py             — Broker クライアントのデータモデル / Protocol / 例外
  - order_manager.py          — 注文作成・送信・同期・キャンセルのロジック
  - execution_engine.py       — Signal Queue ベースの発注エンジン
  - reconciler.py             — 起動時自動復旧（OrderSent 照合 / ポジション差分）
  - …（他に order_repository, order_record, risk_manager 等が存在する想定）
- monitoring/__init__.py      — 監視 API のエクスポート
- portfolio/__init__.py      — ポートフォリオ API のエクスポート
- research/__init__.py       — リサーチ API のエクスポート
- ai/__init__.py             — ai API のエクスポート

テスト・開発
-------------
- 単体テストは各モジュールをモック依存（DuckDB 接続や Broker）で実行することを推奨します。
- OpenAI / ブローカー呼び出し部分は外部依存のため patch / mock を用いてテストしてください。
- 環境変数の自動ロードをテストから抑制したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使用。

セキュリティ上の注意
--------------------
- API キーやパスワードは .env に平文で置く場合、ファイル保護とアクセス管理を行ってください。  
- .env.example を .gitignore に追加するか、実データを git に含めないでください。

ライセンス・貢献
----------------
- 本リポジトリにライセンスファイルが含まれる場合はその内容に従ってください。  
- バグ報告やプルリクエストは README を追加・改善する形で歓迎します（ただし実取引コードの変更は慎重に）。

付録: よくある実行コマンド
-------------------------
- 仮想環境作成:
  python -m venv .venv && source .venv/bin/activate
- 依存インストール（一括）:
  pip install duckdb openai requests psutil streamlit
- Streamlit ダッシュボード起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

質問や追加してほしい使用例があれば教えてください。README にサンプルコードやより詳細なセットアップ手順（CI, packaging, example DB 作成スクリプト等）を追記できます。