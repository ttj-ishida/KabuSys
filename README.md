KabuSys — 日本株自動売買 / データ基盤ライブラリ
概要
- KabuSys は日本株向けのデータプラットフォームおよび自動売買補助ライブラリ群です。  
  主に以下機能群を含みます：データ ETL（J-Quants 経由）、ニュース収集と LLM ベースの NLP スコアリング、マーケットカレンダー管理、ファクター計算・研究ユーティリティ、監査ログ（発注→約定のトレーサビリティ）、および環境設定ユーティリティ等。
- 目的：データ品質を保ちながらバックテスト／リサーチ用データを構築し、ニュースセンチメントや市場レジームを計測して戦略層へ渡す基盤を提供します。

主な機能一覧
- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）、必須/オプション設定を Settings クラスで提供
- Data（kabusys.data）
  - J-Quants クライアント（fetch / save：日足・財務・上場情報・市場カレンダー）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得 → raw_news 保存、SSRF 対策、トラッキングパラメータ除去）
  - 監査ログ初期化ユーティリティ（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化等）
- AI（kabusys.ai）
  - ニュース NLP（gpt-4o-mini を想定した JSON Mode で複数銘柄のセンチメントを算出）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM スコアを合成）
  - 再試行・フォールバック設計（API エラー時の安全な挙動）
- Research（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 将来リターン計算・IC（Information Coefficient）計算、統計サマリー

前提（Prerequisites）
- Python 3.9+（型ヒント等に合わせる）
- DuckDB（Python パッケージ duckdb）
- OpenAI Python SDK（openai）を使った Chat Completions 呼び出し
- defusedxml（RSS パースの安全化）
- ネットワークアクセス：J-Quants API / OpenAI API への HTTP(s)
- J-Quants / OpenAI の API キー、kabuステーション用パスワード等（下記参照）

セットアップ手順
1. リポジトリをクローン（またはパッケージを配置）
   - git clone ... （パッケージが src/ 配下に置かれている前提）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt があればそれを使ってください。パッケージ配布時は pip install -e . 等にも対応してください。）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を作成すると、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-xxxx
     - KABU_API_PASSWORD=your_kabu_password
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルト
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_FILL_MODE=instant  # instant | partial | never | reject
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development  # valid: development | paper_trading | live
     - LOG_LEVEL=INFO

   - 注意: Settings クラスは必須値チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を行います。未設定時は ValueError が発生します。

使い方（簡単な例）
- 共通：Settings 参照
  - from kabusys.config import settings
  - settings.duckdb_path, settings.jquants_refresh_token などでアクセスできます。

- DuckDB 接続を作成（ETL / AI / research 共通）
  - import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日分を処理
    print(result.to_dict())

- ニュースセンチメントのスコア付け（1日分）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    n = score_news(conn, date(2026, 3, 20))  # 前日15:00 JST〜当日08:30 JST の記事を対象

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DB を作る）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

- マーケットカレンダー更新ジョブ（J-Quants 経由）
  - from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

- RSS フィード取得（単体ユーティリティ）
  - from kabusys.data.news_collector import fetch_rss
    articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")

注意点 / 設計上の振る舞い
- Look-ahead bias 回避
  - モジュールの多くは内部で datetime.today() を参照せず、与えられた target_date を基準に過去データのみを参照します。バックテスト用途に配慮した設計です。
- API 呼び出しの耐障害性
  - J-Quants および OpenAI 呼び出しにはリトライ・指数バックオフが組み込まれ、API エラー時もフェイルセーフ（多くはスコア=0.0 にフォールバック）で継続します。
- .env のパースは柔軟
  - export PREFIX=xxx やクォートありの値、インラインコメントなど多くの .env スタイルに対応しています。
- 自動 .env ロードの無効化
  - テスト等で .env 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください。

主要モジュール / ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py       -- ニュースセンチメント集計 / OpenAI 呼び出し
    - regime_detector.py-- ETF MA200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py -- J-Quants API クライアント（fetch/save）
    - pipeline.py       -- ETL パイプライン（run_daily_etl 等）
    - etl.py            -- ETL 公開型の再エクスポート（ETLResult）
    - news_collector.py -- RSS 取得・前処理・保存ロジック
    - calendar_management.py -- カレンダー判定・更新ロジック
    - quality.py        -- データ品質チェック
    - stats.py          -- 統計ユーティリティ（zscore）
    - audit.py          -- 監査ログ（DDL・初期化）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（全ファイルは src/kabusys 以下に配置されています。上は主要なファイル一覧の抜粋です）

開発・テストについて
- 単体テスト／モック
  - OpenAI / HTTP 呼び出しは外部依存が強いため、テストでは関数を patch / stub して差し替えることを前提としています（コード内にもモックしやすい設計や差し替えポイントが用意されています）。
- ロギング
  - 各モジュールは logging.getLogger(__name__) を使用。実行アプリ側でハンドラ／レベルを設定してください。

トラブルシューティング
- 環境変数未設定によるエラー
  - settings のプロパティ（例: jquants_refresh_token）が未設定だと ValueError を送出します。必要な値が .env にあるか確認してください。
- DuckDB テーブルが無い場合
  - ETL や保存関数はテーブルの存在を前提としている関数があります。初回はスキーマ作成用ユーティリティ（プロジェクト側の schema 初期化機能）を走らせる必要があります（本 README では省略、リポジトリ内の schema 初期化処理を参照してください）。
- RSS 取得時の SSRF／プライベートアドレス拒否
  - fetch_rss は内部でホストがプライベートかを検査し、拒否します。社内閉域の RSS を取り扱う場合は注意してください（設定／コード変更が必要）。

ライセンス・貢献
- ライセンス情報や開発ルール（CONTRIBUTING.md 等）はリポジトリのルートを参照してください。

最後に
- この README はコード内の docstring を基にまとめています。実装の詳細や追加ユーティリティは各モジュールの docstring / ソースを参照してください。特定の使い方（例: ETL の cron 化、paper trading の設定、kabuステーション連携）について実例が必要であれば用途に合わせてサンプルを作成します。