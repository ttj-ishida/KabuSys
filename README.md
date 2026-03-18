# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ

概要
- KabuSys は日本株のデータ収集（J-Quants）、データ品質検査、特徴量生成、リサーチユーティリティ、ニュース収集、監査ログ（発注→約定の追跡）などを通した自動売買プラットフォームの基盤モジュール群です。
- DuckDB を用いたローカルデータベース層を中心に設計され、ETL（差分更新）、品質チェック、ファクター計算、ニュース収集といった主要処理を備えています。
- 設計上、Research / Data モジュールは本番の発注 API にアクセスしないことを保証しており、安全に解析・評価が行えます。

主な特徴（機能一覧）
- 環境設定の自動読み込み（.env / .env.local / OS 環境変数）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務、JPX カレンダーの取得
  - レートリミット制御（120 req/min）・リトライ・トークン自動更新
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ETL パイプライン（差分更新 / バックフィル / 品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック
  - 欠損・スパイク（急変）・重複・日付不整合チェック
- DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
- ニュース収集（RSS）
  - URL 正規化、SSRF 対策、XML 安全パース、記事ID のハッシュ化、記事→銘柄紐付け
- リサーチ / ファクター計算
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman rank）計算、ファクターサマリー
  - z-score 正規化ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマと初期化ユーティリティ

前提（Prerequisites）
- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、各RSS）

インストール（例）
1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml

3. 開発パッケージとしてローカルにインストールする場合（プロジェクトルートに setup/pyproject がある前提）
   - pip install -e .

環境変数（主なキー）
以下はコード内で参照される主要な環境変数です。実運用前に .env または環境変数で設定してください（.env.example を参照する想定）。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token に使う）
- KABU_API_PASSWORD (必須)  
  kabuステーション API 用パスワード（発注関連）
- KABU_API_BASE_URL (任意)  
  kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)  
  Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須)  
  Slack 通知対象チャネル ID
- DUCKDB_PATH (任意)  
  DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)  
  監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)  
  実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)  
  ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると、自動で .env を読み込む機能を無効化できます（テストなどで便利）。

セットアップ手順（簡易ガイド）
1. .env を作成
   - プロジェクトルート（.git や pyproject.toml がある場所）に .env を置くと自動的に読み込まれます（.env.local は上書き可能な優先度で読み込まれます）。
   - 例:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

2. DuckDB スキーマの初期化
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)

   - 監査ログ専用 DB を別に作る場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/audit.duckdb")

3. ETL 実行（例: 日次 ETL）
   - from kabusys.data.pipeline import run_daily_etl
     from kabusys.data.schema import init_schema
     from kabusys.config import settings
     conn = init_schema(settings.duckdb_path)
     result = run_daily_etl(conn)
     print(result.to_dict())

使い方（代表的な例）
- DuckDB 初期化
  - from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")

- 日次 ETL（市場カレンダー取得 → 株価差分ロード → 財務差分ロード → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
    res = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト

- 個別 ETL ジョブ
  - run_prices_etl(conn, target_date, id_token=None)
  - run_financials_etl(conn, target_date)
  - run_calendar_etl(conn, target_date)

- J-Quants データ取得（直接 API を叩く / テスト用）
  - from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
    quotes = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))

- ニュース収集ジョブ（RSS）
  - from kabusys.data.news_collector import run_news_collection
    # known_codes は既知の銘柄コード集合（抽出フィルタ用）
    result_map = run_news_collection(conn, known_codes={"7203", "6758"})

- ファクター計算 / リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
    m = calc_momentum(conn, date(2024,3,1))
    v = calc_value(conn, date(2024,3,1))
    normed = zscore_normalize(m, ["mom_1m", "mom_3m"])
    fwd = calc_forward_returns(conn, date(2024,3,1))
    ic = calc_ic(normed, fwd, factor_col="mom_1m", return_col="fwd_1d")

- カレンダーAPI/ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
    is_trading_day(conn, date(2024,1,1))
    next_trading_day(conn, date(2024,1,1))

ログ・運用上の注意
- jquants_client は 120 req/min のレート制限を守る実装（モジュール内部でスロットリング）と、特定の HTTP エラーに対するリトライを実装しています。過剰な同時実行に注意してください。
- ETL はバックフィルロジックで API の「後出し修正」を吸収する仕組みがあります（デフォルト backfill_days=3）。
- research / data モジュールは発注 API にはアクセスしない設計ですが、execution／monitoring／audit系を組み合わせると本番連携が可能です。live 環境での実行は十分な安全確認（サンドボックスや paper_trading 設定）を行ってから行ってください。
- KABUSYS_ENV を "live" にすると is_live プロパティが True になります。発注や外部連携が有効なコードでは環境に応じたガードを実装してください。

ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                 # J-Quants API クライアント（取得・保存）
    - news_collector.py                 # RSS ニュース収集・保存
    - schema.py                         # DuckDB スキーマ定義・初期化
    - stats.py                          # 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
    - features.py                       # features の公開インターフェース
    - calendar_management.py            # マーケットカレンダー管理
    - audit.py                          # 監査ログ系の DDL / 初期化
    - etl.py                            # ETL 公開インターフェース（ETLResult 再エクスポート）
    - quality.py                        # データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py            # 将来リターン / IC / 統計概要
    - factor_research.py                # モメンタム / ボラティリティ / バリュー計算
  - strategy/                            # 戦略層（プレースホルダ）
  - execution/                           # 発注・実行層（プレースホルダ）
  - monitoring/                          # 監視系（プレースホルダ）

開発・拡張のヒント
- DuckDB のスキーマは init_schema() で冪等に作成されます。新しいテーブルを追加する際は schema.py の _ALL_DDL に追加してください。
- ニュース収集は RSS の形式差分にかなり耐性を持たせていますが、特定ソースの HTML / エンコーディングに応じた前処理が必要になることがあります。
- jquants_client の _request 関数は urllib を使用しています。より高度な HTTP 機能（セッション管理等）が必要な場合はラップして差し替えてください。
- テスト中に自動 .env ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ライセンス・その他
- 本リポジトリにライセンス情報や contributing ガイドがある場合はそちらに従ってください（この README はコードベースから自動生成した要約ドキュメントです）。

問題報告・改善提案
- バグや改善提案は issue / PR を通してお願いします。特に ETL の品質チェック・スキーマの互換性・API リトライ挙動は運用時に重要になるため詳細な再現手順があると助かります。

以上。README に載せたい追加の情報（例: .env.example の具体例、CLI ユーティリティ、運用 cron サンプルなど）があれば教えてください。必要に応じて追記します。