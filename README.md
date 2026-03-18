# KabuSys

日本株自動売買プラットフォームのコアライブラリ（データ取得、ETL、品質チェック、ニュース収集、監査スキーマ等）。  
このリポジトリは主に以下を提供します。

- J-Quants API を用いた市場データの取得と DuckDB への保存（冪等）
- RSS によるニュース収集と銘柄紐付け
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・夜間更新ジョブ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（認証、自動トークンリフレッシュ、レート制御、リトライ）
  - 株価日足、財務、マーケットカレンダーの取得と DuckDB への保存（冪等）
- data/news_collector.py
  - RSS フィード取得（SSRF対策、gzip制限、xml脆弱性対策）
  - 記事の正規化・ID生成（URL 正規化 + SHA-256）
  - raw_news への冪等保存、銘柄抽出と news_symbols への紐付け
- data/schema.py / data/audit.py
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution / Audit）
  - スキーマ初期化ユーティリティ
- data/pipeline.py
  - 日次 ETL（calendar → prices → financials → 品質チェック）
  - 差分更新、バックフィル対応、品質チェック統合
- data/calendar_management.py
  - 営業日判定、前後の営業日の取得、カレンダー夜間更新ジョブ
- data/quality.py
  - 欠損／重複／スパイク／日付不整合のチェック群
- config.py
  - 環境変数読み込み（.env / .env.local 自動ロード、OS 環境優先）
  - アプリ設定 accessor（トークン・DBパス・ログレベル・環境モード等）

---

## 必要条件

- Python 3.10 以上（型注釈に `X | None` を使用するため）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクトによっては追加のパッケージが必要になる可能性があります。実運用では requirements.txt / pyproject.toml を参照してください。）

例（仮）:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作成・有効化します。

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 依存パッケージをインストールします（必要に応じて追加）。

   pip install duckdb defusedxml

3. 環境変数を設定します（.env ファイル推奨）

   必須（ライブラリ内で _require() によってチェックされる変数）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API のパスワード
   - SLACK_BOT_TOKEN       : Slack ボットトークン（通知などに使用する場合）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID

   任意 / デフォルト値あり:
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 にすると .env 自動読み込みを無効化
   - KABU_API_BASE_URL     : kabu API のベースURL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

   自動読み込みルール: OS 環境変数 > .env.local > .env
   （プロジェクトルートは .git / pyproject.toml を基準に自動検出）

4. DuckDB スキーマを初期化します（初回のみ）

   python REPL やスクリプト内で:
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")

   監査ログ専用に分けたい場合:
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（簡易例）

- 日次 ETL の実行（市場カレンダー取得 → 株価・財務の差分取得 → 品質チェック）

  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

  run_daily_etl は内部で:
  - calendar を先に取得して営業日に調整
  - prices, financials を差分 + バックフィルで取得
  - 品質チェック（quality.run_all_checks）を実行（デフォルトで有効）

- 個別ジョブの実行例

  - 市場カレンダー更新（夜間バッチ）:
    from kabusys.data.calendar_management import calendar_update_job
    saved = calendar_update_job(conn)

  - ニュース収集:
    from kabusys.data.news_collector import run_news_collection
    # known_codes は銘柄抽出に使用する有効コード集合（None なら抽出スキップ）
    results = run_news_collection(conn, known_codes=set(["7203","6758"]))

  - J-Quants から日足を直接取得して保存:
    from kabusys.data import jquants_client as jq
    records = jq.fetch_daily_quotes(date_from=..., date_to=...)
    saved = jq.save_daily_quotes(conn, records)

- 品質チェックを直接呼ぶ:
  from kabusys.data import quality
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

- 環境設定取得:
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

注意点:
- J-Quants API にはレート制限（120 req/min）があるため jquants_client は内部で固定間隔スロットリングと指数バックオフを実装しています。
- 認証: get_id_token は refresh token を使って id_token を発行し、401 時の自動リフレッシュを 1 回行います。
- DuckDB への保存は多くの箇所で ON CONFLICT による冪等化を行っています。

---

## ディレクトリ構成（主なファイルと説明）

src/kabusys/
- __init__.py
  - パッケージのトップレベル。バージョン情報を含む。
- config.py
  - 環境変数読み込み・設定アクセス（settings）

src/kabusys/data/
- __init__.py
- jquants_client.py
  - J-Quants API クライアント（取得・保存・認証・レート制御）
- news_collector.py
  - RSS 収集、前処理、raw_news への保存、銘柄抽出・紐付け
- schema.py
  - DuckDB のスキーマ定義と init / get_connection
- pipeline.py
  - ETL パイプライン（run_daily_etl、個別 ETL 実行関数）
- calendar_management.py
  - 市場カレンダー管理・営業日ユーティリティ・夜間更新ジョブ
- audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）と初期化
- quality.py
  - データ品質チェック群（欠損、スパイク、重複、日付整合性）

src/kabusys/strategy/
- __init__.py
  - 戦略関連の名前空間（現状空のモジュール）

src/kabusys/execution/
- __init__.py
  - 発注・実行管理の名前空間（現状空のモジュール）

src/kabusys/monitoring/
- __init__.py
  - 監視関連の名前空間（現状空のモジュール）

---

## 運用上の注意・設計上のポイント

- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。
  - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 読み込み優先順: OS 環境変数 > .env.local > .env（既存 OS 環境変数は保護されます）

- セキュリティ／堅牢性設計:
  - news_collector は SSRF 対策（スキーム検証・プライベートIP拒否）および XML 脆弱性対策（defusedxml）を実装。
  - RSS レスポンスサイズの上限を設けてメモリDoSを防止（MAX_RESPONSE_BYTES）。
  - J-Quants クライアントは 401 自動リフレッシュ、指数バックオフ、リトライロジックを実装。

- 冪等性:
  - 多くの保存処理は ON CONFLICT DO UPDATE / DO NOTHING を使用し、再実行可能な ETL を実現しています。

- 品質チェック:
  - ETL は Fail-Fast ではなく、全てのチェックを実行して問題の一覧（QualityIssue）を返します。呼び出し側で重大度に応じた対応を行ってください。

---

## よくある質問（FAQ）

Q: Python バージョンは？
A: 3.10 以上を推奨します（新しい構文（|）を使用）。

Q: テスト用に自分の環境変数を使いたくない／自動読み込みを抑えたい
A: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みをスキップします。テスト時はテスト固有の env を明示的に設定してください。

Q: DuckDB の初期化でエラーが出る
A: パスの親ディレクトリが存在しない場合は schema.init_schema が自動で作成します。権限やファイルロックの問題がないか確認してください。

---

この README はコードベースに含まれるモジュールの概要・使い方に焦点を当てています。詳細な運用手順（CI/CD、デプロイ、監視、Slack 通知フロー等）は運用環境に合わせて追加してください。必要であればサンプルの .env.example や requirements.txt、簡易の CLI スクリプトを追加するテンプレートも作成できます。必要なら教えてください。