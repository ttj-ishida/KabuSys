KabuSys — 日本株自動売買プラットフォーム（README）
=================================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・自動売買の基盤ライブラリです。  
主に以下を提供します。

- J-Quants API を用いた株価／財務／カレンダー等の差分 ETL パイプライン
- RSS ニュース収集と LLM（OpenAI）を用いたニュースセンチメント分析（銘柄別スコア化）
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアの合成）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- 監査ログ（signal → order → execution）用の DuckDB スキーマ初期化ユーティリティ
- データ品質チェック、マーケットカレンダー管理、ニュース収集の安全対策等

主な機能一覧
-------------
- データ ETL（kabusys.data.pipeline）
  - run_daily_etl: カレンダー取得 → 株価差分取得 → 財務差分取得 → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
  - ETLResult 型による実行結果の集約

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 認証（get_id_token）・ページネーション対応・リトライ・レート制御
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・URL 正規化・SSRF 対策・トラッキングパラメータ除去
  - raw_news への冪等保存（設計により ID は正規化 URL の SHA-256）

- ニュース NLP（kabusys.ai.news_nlp）
  - calc_news_window / score_news: 指定日ウィンドウのニュースを銘柄別に集約し OpenAI（gpt-4o-mini）でスコア化
  - バッチ処理、エラーハンドリング、レスポンスバリデーション、スコアクリップ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321) の 200 日移動平均乖離 + マクロニュース LLM スコアを合成して market_regime を書き込み

- 研究モジュール（kabusys.research）
  - calc_momentum, calc_value, calc_volatility（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索 / 評価）
  - zscore_normalize（kabusys.data.stats）

- 監査ログ（kabusys.data.audit）
  - 監査用テーブル・インデックスの冪等初期化（init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions テーブルとインデックス群

- データ品質チェック（kabusys.data.quality）
  - 欠損チェック、重複チェック、スパイク（急変）検出、日付不整合チェック
  - QualityIssue による問題の集約

セットアップ手順
----------------
1. リポジトリを取得:
   - git clone ...（プロジェクトルートには .git または pyproject.toml が必要です）

2. Python 仮想環境（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install duckdb openai defusedxml
   - （必要に応じて他のライブラリも追加してください。プロジェクトに requirements.txt / pyproject があればそちらを使用）

4. パッケージを editable インストール（開発時）:
   - pip install -e .

環境変数（.env）
----------------
config.py はプロジェクトルートの .env / .env.local を自動読み込みします（OS 環境変数を優先）。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な環境変数（.env に設定する例）
- JQUANTS_REFRESH_TOKEN=xxxxx          # 必須（J-Quants API 用）
- OPENAI_API_KEY=sk-...                # OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD=xxxx               # kabuステーション API パスワード（注文周り）
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # オプション
- LINE_CHANNEL_ACCESS_TOKEN=...        # LINE 通知（任意）
- LINE_USER_ID=...                     # LINE 通知（任意）
- DUCKDB_PATH=data/kabusys.duckdb      # DuckDB 保存先（デフォルト）
- SQLITE_PATH=data/monitoring.db       # 監視用 SQLite（任意）
- PAPER_FILL_MODE=instant              # paper_trading のモック約定動作（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- KILL_FLAG_CLEAR_ON_START=0
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development              # development | paper_trading | live
- LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

- DuckDB 接続を用意して ETL を実行する
  - Python REPL / スクリプト例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアの実行（銘柄別 AI スコア）
    from datetime import date
    from kabusys.ai.news_nlp import score_news
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込み銘柄数: {written}")

- 市場レジーム判定
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（発注監査用）
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って発注監査テーブルが準備される

- 研究用ファクター計算
    from datetime import date
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))
    res = calc_momentum(conn, date(2026,3,20))
    # res は dict のリスト（date, code, mom_1m, ...）

注意点 / 実装上のポイント
------------------------
- 自動読み込みされる .env はプロジェクトルート（.git または pyproject.toml）を基準に探索します。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI と J-Quants の API 呼び出しはリトライやバックオフ、フェイルセーフ（API 失敗時はスコアを 0 にフォールバックなど）を備えていますが、API キーの設定は必須です（関数は api_key を引数で受け取れる場合があります）。
- ETL / スキーマ操作は DuckDB を使用します。実際の運用ではバックアップやファイルロック、適切なファイル配置に注意してください。
- news_collector は SSRF 対策・XML パース防御（defusedxml）・受信サイズ制限など安全装置を備えています。

ディレクトリ構成（主なファイル）
-----------------------------
以下は src/kabusys 以下の主要モジュールと説明です（抜粋）。

- kabusys/
  - __init__.py                 （パッケージ初期化）
  - config.py                   （環境変数 / 設定管理）
  - ai/
    - __init__.py
    - news_nlp.py               （ニュースセンチメント解析）
    - regime_detector.py        （市場レジーム判定）
  - data/
    - __init__.py
    - jquants_client.py         （J-Quants API クライアント + DuckDB 保存）
    - pipeline.py               （ETL パイプライン）
    - etl.py                    （ETLResult の再エクスポート）
    - news_collector.py         （RSS ニュース収集）
    - calendar_management.py    （マーケットカレンダー管理）
    - quality.py                （データ品質チェック）
    - stats.py                  （統計ユーティリティ）
    - audit.py                  （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py        （モメンタム/バリュー/ボラティリティ等）
    - feature_exploration.py    （将来リターン / IC / summary 等）

開発・貢献
----------
- コードベースはテストしやすい設計（API 呼び出しの差し替え、関数引数での注入など）を意識しています。ユニットテストを書く場合は外部 API 呼び出しをモックしてください。
- .env.example を用意し、ローカルでの動作確認を行ってから本番キーを投入してください。

ライセンス
----------
（プロジェクトに合わせて適切なライセンスを明記してください）

付録 — よく使う API / 関数一覧
-----------------------------
- ETL: kabusys.data.pipeline.run_daily_etl
- J-Quants fetch: kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
- News scoring: kabusys.ai.news_nlp.score_news
- Regime scoring: kabusys.ai.regime_detector.score_regime
- Audit schema init: kabusys.data.audit.init_audit_db / init_audit_schema
- Factor calc: kabusys.research.calc_momentum / calc_value / calc_volatility

以上。必要であれば README をプロジェクト実体（pyproject / requirements）に合わせて調整するテンプレートも作成します。どの部分を詳しく追記しましょうか？