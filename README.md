# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計されたライブラリ群です。J-Quants API からの市場データ取得、RSS ニュース収集、DuckDB ベースのデータスキーマ／ETL、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレース）などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提条件
- セットアップ手順
- 環境設定（.env）
- 使い方（基本例）
- よく使う API の説明
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API を用いた株価（日足）・財務データ・市場カレンダー取得（ページネーション／リトライ／レート制御済み）。
- RSS フィードからニュース記事を安全に収集・前処理して DuckDB に保存。
- DuckDB に対するスキーマ定義と初期化ユーティリティ（Raw / Processed / Feature / Execution 層）。
- ETL パイプライン（差分更新、バックフィル、品質チェック）。
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）。
- 監査ログ（シグナル → 発注要求 → 約定）を保存する監査スキーマ。
- データ品質チェックモジュール（欠損・スパイク・重複・日付整合性）。

主な機能（抜粋）
- jquants_client:
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - トークン自動リフレッシュ、指数バックオフ、レート制御
- news_collector:
  - fetch_rss（SSRF・gzip・XML 脆弱性対策済み）
  - save_raw_news / save_news_symbols（DuckDB に冪等保存）
  - 銘柄コード抽出（既知の銘柄セットに基づく）
- data.schema:
  - init_schema(db_path) で DuckDB のスキーマを初期化
- data.pipeline:
  - run_daily_etl(...) による日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
- data.calendar_management:
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間カレンダー更新
- data.audit:
  - init_audit_schema / init_audit_db（監査ログ向けスキーマ）

前提条件
- Python 3.10 以上（型ヒントで | を使用）
- 主要依存パッケージ（最低限）:
  - duckdb
  - defusedxml
- ネットワーク経由で J-Quants API / RSS にアクセスできること

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）
4. パッケージを編集可能インストール（任意）
   - pip install -e .

環境変数（.env）
- KabuSys はプロジェクトルートにある .env / .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabu ステーション API 用パスワード
  - SLACK_BOT_TOKEN       : Slack Bot トークン（システム内で使う場合）
  - SLACK_CHANNEL_ID      : Slack 投稿先チャネル ID
- 任意（デフォルト値あり）
  - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH           : SQLite（monitoring 用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

例 (.env)
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（基本例）
- DuckDB スキーマの初期化（最初に一度だけ実行）
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（J-Quants トークンは settings から自動取得）
  - from kabusys.data import pipeline, schema
  - conn = schema.init_schema("data/kabusys.duckdb")
  - result = pipeline.run_daily_etl(conn)
  - print(result.to_dict())

- RSS ニュース収集（既知の銘柄セットを渡して紐付け）
  - from kabusys.data import news_collector, schema
  - conn = schema.get_connection("data/kabusys.duckdb")  # または init_schema
  - known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードのセット
  - results = news_collector.run_news_collection(conn, known_codes=known_codes)
  - print(results)

- カレンダー更新バッチ
  - from kabusys.data import calendar_management, schema
  - conn = schema.get_connection("data/kabusys.duckdb")
  - saved = calendar_management.calendar_update_job(conn)
  - print("saved:", saved)

- 監査ログ（監査用スキーマ初期化）
  - from kabusys.data import audit, schema
  - conn = schema.init_schema("data/kabusys.duckdb")
  - audit.init_audit_schema(conn)  # 監査テーブルを追加
  - # または監査専用 DB を作成
  - # audit_conn = audit.init_audit_db("data/audit.duckdb")

よく使う API の説明（抜粋）
- kabusys.config.settings
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.duckdb_path / settings.env など。環境変数依存の設定をラップしています。
  - 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を起点）から実行されます。

- kabusys.data.jquants_client
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)
    - 市場カレンダー → 株価 → 財務 → 品質チェック の順で差分 ETL を実行し ETLResult を返します。

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)  # RSS を安全にフェッチして記事リストを返す
  - save_raw_news(conn, articles)      # raw_news に冪等保存
  - save_news_symbols(conn, news_id, codes)

- kabusys.data.schema
  - init_schema(db_path)  # DuckDB のテーブルをすべて作成（冪等）
  - get_connection(db_path)

トラブルシューティング / 注意点
- 環境変数未設定で _require() が呼ばれると ValueError が発生します。必要な変数が .env にあるか確認してください。
- 自動 .env 読み込みはプロジェクトルート検出に .git または pyproject.toml を使用します。IDE 等でテストする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して読み込みを無効にできます。
- J-Quants API のレート制限（120 req/min）に合わせてクライアントは内部でスロットリングします。大量データ取得時は時間がかかります。
- news_collector は外部 URL を検証（SSRF 対策、gzip 解凍上限、defusedxml）して安全性に配慮していますが、環境やプロキシによっては追加の設定が必要になる場合があります。
- DuckDB への INSERT は各モジュールで冪等性を考慮（ON CONFLICT）しているため、再実行可能性が高い設計です。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/               (発注・ブローカー連携用, 未実装ファイルあり)
    - strategy/                (戦略関連モジュール置き場)
    - monitoring/              (監視用モジュール置き場)
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得・保存・認証）
      - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
      - pipeline.py            # ETL パイプライン（差分更新 + 品質チェック）
      - schema.py              # DuckDB スキーマ定義と初期化
      - calendar_management.py # マーケットカレンダー管理（営業日判定等）
      - audit.py               # 監査ログ（信頼性の高いトレース）
      - quality.py             # データ品質チェック
- README.md (このファイル)

将来の拡張候補
- strategy / execution 層の具体実装（発注システム連携、ポジション管理、リスク制御）
- Slack や監視連携（ETL の結果を Slack に通知）
- テストスイートと CI ワークフロー（自動化テスト、静的解析）
- コンテナ化・デプロイ用設定（Docker / Kubernetes）

---

お問い合わせ / 貢献
- 本リポジトリに issue / PR を立ててください。コード内の docstring やログメッセージは日本語で記載されています。外部 API キー等は公開しないよう注意してください。

以上。必要であれば、README にサンプル .env.example、requirements.txt、または具体的なクイックスタートスクリプトを追記できます。どの情報を追加しますか？