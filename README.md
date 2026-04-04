KabuSys — 日本株自動売買基盤
概要
- KabuSys は日本株のデータ取得（J‑Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレース）などを含む研究・ETL・取引基盤向けのライブラリ群です。
- DuckDB を内部データベースとして利用し、J‑Quants API / OpenAI（LLM）を外部依存として想定しています。
- 設計上、バックテストでのルックアヘッドバイアスを避ける実装方針（datetime.today() 等を直接参照しない）や、API リトライ／フェイルセーフ、冪等保存（INSERT … ON CONFLICT）などが施されています。

主な機能一覧
- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）・必須値チェック
  - 設定オブジェクト settings から各種パス / トークン /閾値取得
- データ ETL（kabusys.data.pipeline, jquants_client, news_collector）
  - J‑Quants からの株価日足 / 財務データ / 市場カレンダー取得（ページネーション対応・レートリミット）
  - 差分取得・バックフィル・品質チェック（欠損/スパイク/重複/日付不整合）
  - ニュース RSS 取得・前処理・raw_news への冪等保存（SSRF 対策、トラッキングパラメータ除去）
- データ品質・統計ユーティリティ（kabusys.data.quality, stats）
  - 各種チェックを実行し QualityIssue を返す
  - Zスコア正規化ユーティリティ
- 研究用モジュール（kabusys.research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算・IC（Spearman）・統計サマリ等
- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント生成（チャンク・バッチ・リトライ）
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF(1321)の MA200 乖離 + マクロニュースセンチメント を合成して日次レジーム（bull/neutral/bear）を算出し保存
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ（監査・トレーサビリティ）

セットアップ手順
1. 前提
   - Python 3.10+ を推奨（型注釈に union | を使用）
   - 必要パッケージ（一例）:
     - duckdb
     - openai
     - defusedxml
     - （その他標準ライブラリ以外の依存がある場合は requirements.txt を参照）
2. 開発インストール（リポジトリルートで）
   - pip install -e . もしくは pip install duckdb openai defusedxml
3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を基準）に .env を配置すると自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=＜your_jquants_refresh_token＞
     - KABU_API_PASSWORD=＜kabu_api_password＞
     - OPENAI_API_KEY=＜openai_api_key＞
     - KABUYS_ENV=development|paper_trading|live  （有効値: development, paper_trading, live）
     - LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
   - 注意: settings.jquants_refresh_token 等は必須となる箇所があります。未設定時は ValueError が発生します。

使い方（代表的な API）
- 設定参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token / settings.duckdb_path / settings.env / settings.log_level など
- ETL（日次パイプライン）実行例
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())
- ニューススコアリング（LLM）例
  - from kabusys.ai.news_nlp import score_news
    import duckdb
    from datetime import date
    conn = duckdb.connect(str(settings.duckdb_path))
    # OPENAI_API_KEY が環境変数にある場合、api_key 引数は省略可能
    written = score_news(conn, target_date=date(2026,3,20))
    print(f"書き込み銘柄数: {written}")
- 市場レジーム判定例
  - from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20))
- ファクター計算（研究）例
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    conn = duckdb.connect(str(settings.duckdb_path))
    mom = calc_momentum(conn, target_date=date(2026,3,20))
- 監査テーブル初期化 / 監査 DB の作成
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")  # :memory: も可
- J‑Quants 直接 API 呼び出し（トークン取得・フェッチ）
  - from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
    token = get_id_token()  # settings.jquants_refresh_token を使用して id_token を取得
    records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)

運用に関する注意・設計方針
- LLM 呼び出しや API 呼び出しはリトライ・バックオフを実装しており、API失敗時はフェイルセーフ（多くの場合 0 やスキップ）で継続します。
- 各モジュールはルックアヘッドバイアスを避けるために date や target_date を外部から渡す設計です。モジュール内部で datetime.today() / date.today() を直接参照しないようにしています（例外は一部ユーティリティのログ・健康チェック等）。
- .env の自動ロードはプロジェクトルート検出に基づき行われます。テスト環境などで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- データ保存は可能な限り冪等（ON CONFLICT DO UPDATE など）にしています。

ディレクトリ構成（主要ファイルと簡単な説明）
- src/kabusys/
  - __init__.py : パッケージ初期化、バージョン情報
  - config.py : 環境変数 / .env 読込と Settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py : ニュース NLP（OpenAI）による銘柄別スコアリング
    - regime_detector.py : 市場レジーム判定（ETF + マクロニュース統合）
  - data/
    - __init__.py
    - jquants_client.py : J‑Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py : ETL パイプライン（run_daily_etl 他）
    - etl.py : ETLResult の再エクスポート
    - news_collector.py : RSS フィード取得・前処理・raw_news 保存
    - calendar_management.py : 市場カレンダー管理 / 営業日判定 / calendar_update_job
    - quality.py : データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py : 統計ユーティリティ（zscore 正規化等）
    - audit.py : 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
  - research/
    - __init__.py
    - factor_research.py : Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py : 将来リターン計算・IC・統計サマリ等
  - monitoring, execution, strategy など（パッケージ公開 __all__ に含める予定のサブパッケージ）

よくある質問（FAQ）
- .env はどこに置くべきですか？
  - リポジトリルート（.git があるディレクトリ、または pyproject.toml がある場所）に置くと自動読込されます。CI／テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い手動で設定することを推奨します。
- OpenAI の応答が不正（JSON パース失敗）した場合はどうなりますか？
  - パース失敗時はログに WARNING を出して当該チャンクはスキップまたは 0.0（中立）にフォールバックします。全体処理は継続します。
- DB スキーマはどこで管理していますか？
  - audit.py に監査ログ用 DDL を用意しています。raw_prices/raw_financials/market_calendar 等のスキーマは ETL 初期化ルーチンで管理する想定です（プロジェクトに schema 初期化コードが別途ある想定）。
- DuckDB のデフォルトファイルパスは？
  - settings.duckdb_path のデフォルトは data/kabusys.duckdb（ホーム展開をサポート）。

追加情報・貢献
- コードはモジュール毎に設計方針や注意点が豊富にコメントされています。新機能追加やバグ修正の際はモジュール内の設計方針（特にルックアヘッドバイアス回避）に従ってください。
- テスト／CI では環境変数自動読込の影響を排除するため、KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するか、テスト内で明示的に os.environ を操作してください。

問題や改善提案があれば、README に記載の方法で issue を作成してください。