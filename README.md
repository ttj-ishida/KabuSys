# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視用ライブラリ群です。シグナル生成・ポートフォリオ構築・ポジションサイジング・発注エンジン・監視ダッシュボード・AI を用いたニューススコアリング等の機能を提供します。本 README はコードベース（src/kabusys 以下）を対象にした概要・セットアップ・簡易使い方・ディレクトリ構成をまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 環境変数 (.env) の例
- 使い方（主要 API / 実行例）
- ディレクトリ構成

---

プロジェクト概要
- 日本株自動売買システム向けに設計されたモジュール群。
- DuckDB / SQLite を使ったバックテーブル参照・永続化、外部ブローカー（kabuステーション想定）との連携インターフェース、LINE での通知、OpenAI を使ったニュース/マクロセンチメント評価、監視エンジンと Streamlit ダッシュボード等を含む。
- モジュールは「純粋関数」「DBアクセス層」「監視層」「実行層（ExecutionEngine）」など責務ごとに分離されています。

機能一覧（主な機能）
- 環境設定読み込み（.env 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- ポートフォリオ構築
  - 候補選定（スコア順で top N）
  - 等金額・スコア加重配分
  - セクターキャップ適用、レジーム乗数計算
  - ポジションサイジング（リスクベース / weight ベース、単元丸め、aggregate cap）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials テーブル参照）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI（OpenAI）統合
  - ニュース記事をまとめて LLM に送りセンチメントを ai_scores に保存（score_news）
  - マクロニュース＋ETF MA200 乖離から市場レジームを判定・保存（score_regime）
  - API 呼び出しはリトライ、レスポンスバリデーション、スコアクリップ等の堅牢化実装あり
- 実行 / 発注
  - ExecutionEngine：シグナル読み取り→Gate チェック→発注→WebSocket push ドレイン
  - OrderManager / Reconciler：永続化を意識した発注・同期・再起動復旧ロジック
  - Broker API 抽象（Protocol）とデータモデル（OrderRequest/OrderStatus 等）
- 監視・アラート
  - MonitoringDB: SQLite スキーマ／CRUD ラッパー（system_status, trade_logs, positions, risk_logs, dashboard）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager（LINE 送信）
  - Streamlit ダッシュボードで監視可視化

セットアップ手順（開発環境）
1. Python バージョン確認
   - 推奨: Python 3.10+（コードで型ヒント等を使用）
2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須（主要）：duckdb, openai, requests, streamlit, psutil
   - 例:
     - pip install duckdb openai requests streamlit psutil
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）
4. パッケージをインストール（開発インストール）
   - プロジェクトルートで:
     - pip install -e .

環境変数 / .env
- 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local があると自動で読み込まれます。
  - 読み込み順: OS 環境変数（優先） > .env.local > .env
  - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 主要な環境変数（必須／任意）:
  - 必須（利用機能に応じて）:
    - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必要な機能で参照）
    - KABU_API_PASSWORD — kabu API パスワード（発注用）
  - OpenAI:
    - OPENAI_API_KEY — AI 機能（news_nlp / regime_detector）を使う場合に必須
  - LINE 通知（任意）:
    - LINE_CHANNEL_ACCESS_TOKEN
    - LINE_USER_ID
  - DB パス等（任意、デフォルト有り）:
    - DUCKDB_PATH (default: data/kabusys.duckdb)
    - SQLITE_PATH (default: data/monitoring.db)
    - PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE, PID_FILE_PATH, KILL_FLAG_PATH など
- .env 例:
  # .env (プロジェクトルート)
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_api_password
  OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
  LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  LINE_USER_ID=Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  DUCKDB_PATH=data/kabusys.duckdb
  SQLITE_PATH=data/monitoring.db

使い方（主要 API / 実行例）

- 設定の読み取り
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.kabu_api_base_url, settings.duckdb_path などで取得可能

- DuckDB を用いたリサーチ関数（例: momentum 計算）
  - import duckdb
    from datetime import date
    from kabusys.research import calc_momentum
    conn = duckdb.connect(str(settings.duckdb_path))
    result = calc_momentum(conn, date(2026, 3, 20))
    # result は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]

- AI ニューススコアリング（score_news）
  - from kabusys.ai import score_news
    import duckdb
    from datetime import date
    conn = duckdb.connect("data/kabusys.duckdb")
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    # OPENAI_API_KEY 環境変数を設定していれば api_key=None でも可

- マーケットレジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監視 DB 初期化
  - import sqlite3
    from kabusys.monitoring import init_monitoring_db
    conn = sqlite3.connect("data/monitoring.db")
    init_monitoring_db(conn)

- Streamlit ダッシュボード起動
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- MonitoringEngine（ポーリング実行）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager を組み合わせ、MonitoringEngine を作成して run() または run_once() を呼ぶ。
  - テストでは run_once() で各監視を一回だけ実行できます（例: CI / 単体テスト）。

- ExecutionEngine（発注エンジン）
  - 実運用では BrokerAPIProtocol 実装（例えば KabuStationClient）と OrderRepository（SQLite）／RiskManager 等を組み合わせて ExecutionEngine を構築します。
  - ExecutionEngine.run_session() がセッション単位の実行エントリポイントです（PID ファイルの生成・kill.flag 監視・WebSocket スレッド起動等を行います）。

注意点 / 実運用上のポイント
- AI 機能は OpenAI API キーが必須。API 呼び出しにはレート制限やエラー処理（リトライ）が実装されていますが、利用量に応じたコスト管理を行ってください。
- ExecutionEngine / OrderManager の発注フローはクラッシュ耐性を考慮して永続化の順序を工夫していますが、実ブローカー接続時は十分なテストが必要です。
- .env 読み込みはプロジェクトルートを .git または pyproject.toml で判定します。パッケージ配布後にプロジェクトルートが見つからない場合は自動ロードをスキップします。
- AI レスポンスのバリデーションは厳格に行いますが、LLM の出力仕様変更等には注意してください。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py                (パッケージ定義)
    - config.py                  (環境変数 / Settings)
    - ai/
      - __init__.py
      - news_nlp.py              (ニュース NLP / score_news)
      - regime_detector.py       (市場レジーム判定 / score_regime)
    - portfolio/
      - __init__.py
      - portfolio_builder.py     (候補選定・等重/スコア重み)
      - position_sizing.py       (株数決定・aggregate cap)
      - risk_adjustment.py       (セクターキャップ・レジーム乗数)
    - research/
      - __init__.py
      - factor_research.py       (momentum/value/volatility 計算)
      - feature_exploration.py   (forward returns, IC, summary)
    - monitoring/
      - __init__.py
      - monitoring_db.py         (SQLite 永続化層)
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - execution/
      - broker_api.py            (データモデル・Protocol・例外)
      - order_manager.py
      - order_repository.py      (※実装ファイルはこのリストに含まれますが、該当コードベースでの存在を確認してください)
      - reconciler.py
      - execution_engine.py
      - risk_manager.py          (※リスク管理ロジック)
    - monitoring/ (上記)
    - research/ (上記)
    - portfolio/ (上記)
    - data/ (補助モジュール群、例: pipeline, stats など。DuckDB ユーティリティ)
    - execution/ (上記)
- pyproject.toml / setup.cfg / requirements.txt (プロジェクトルートに存在する想定)

（注）上記はコードベースの主要ファイルに基づいた簡易ツリーです。実際の配布パッケージではテスト・ドキュメント・追加ユーティリティ等が含まれることがあります。

---

追加情報 / 開発者向けヒント
- 単体テスト: 各純粋関数（portfolio / research 等）は外部副作用が少ないためユニットテストを書きやすい設計です。DuckDB を in-memory で用いることで高速にテストできます。
- ロギング: 各モジュールは logger を用いて詳細なデバッグログを出します。運用時は LOG_LEVEL 環境変数で制御してください（Settings.log_level）。
- セキュリティ: API キー・パスワードは .env を使って管理し、公開リポジトリにコミットしないでください。

---

この README はコード内コメント・ドキュメント文字列に基づいて作成しました。実行方法や初期化手順はローカル環境の構成（DB の有無、ブローカー実装、OpenAI キー等）に依存します。必要があれば具体的なユースケース（例: ローカルでのリサーチ実行、ローカル監視ダッシュボード立ち上げ、テスト用 ExecutionEngine の起動例）を示した追加ドキュメントを作成しますので教えてください。