# KabuSys

KabuSys は日本株向けの自動売買基盤のためのライブラリ群です。J-Quants 等の外部データソースからのデータ収集、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、監査ログなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

このパッケージは以下を目的としています：

- J-Quants API からの株価（日足）・財務・マーケットカレンダー等のデータ収集
- RSS フィードからのニュース収集と銘柄紐付け
- DuckDB によるデータスキーマ（Raw / Processed / Feature / Execution / Audit）の管理と初期化
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- 監査ログ（シグナル → 発注 → 約定 のトレース）用スキーマ

設計上のポイント：

- J-Quants に対して 120 req/min のレート制限を守る実装
- リトライ（指数バックオフ）と 401 時の自動トークン更新対応
- ETL / DB 操作は冪等（ON CONFLICT / トランザクション利用）
- RSS 収集では SSRF 対策・XMLパースに defusedxml を利用・レスポンスサイズ制限等の安全対策を実装

---

## 機能一覧

- 環境設定管理（.env 自動読み込み / 環境変数取得）
- J-Quants API クライアント
  - ID トークン取得（refresh token から）
  - 株価日足（ページネーション対応）
  - 財務データ（四半期）
  - マーケットカレンダー
  - レート制御・リトライロジック
- DuckDB スキーマ管理
  - init_schema(db_path)：全テーブル作成
  - init_audit_schema(conn) / init_audit_db(db_path)：監査ログ用テーブル作成
- ETL パイプライン
  - run_daily_etl(conn, ...)：市場カレンダー→株価→財務→品質チェック の一括処理
  - 個別ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl
- ニュース収集
  - RSS フィードの取得、テキスト前処理、記事ID生成、DuckDB への冪等保存
  - 銘柄コード抽出と news_symbols への紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 必要条件 / 依存関係

- Python 3.10 以上（| 型ヒント等の構文を利用）
- 以下の主要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワーク接続（J-Quants API / RSS）

（実際の requirements.txt や pyproject.toml に従ってインストールしてください）

---

## 環境変数（主なもの）

.env ファイル、または OS 環境変数で設定します。パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）を見つけると自動で `.env` → `.env.local` を読み込みます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主なキー：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用途の sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: Settings は必須キーが未設定だと ValueError を投げます（settings.jquants_refresh_token など）。

---

## セットアップ手順

1. リポジトリをクローンして開発インストール（ルートに pyproject.toml や setup がある想定）:
   - pip editable インストール:
     - pip install -e .
   - または pyproject の場合:
     - pip install -e ".[dev]"（該当する extras がある場合）

2. 必要な Python ライブラリをインストール（例）:
   - pip install duckdb defusedxml

3. .env を作成（上記参照）。プロジェクトルートに `.env`/.env.local を置くと自動で読み込まれます。

4. DuckDB スキーマ初期化:
   - Python REPL やスクリプトで:
     ```
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # デフォルトパスなら不要に作成可能
     ```
   - 監査ログテーブル（audit）を追加する場合:
     ```
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```
   - 監査専用 DB を別途作る場合:
     ```
     from kabusys.data.audit import init_audit_db
     conn_audit = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（基本例）

以下はパッケージの代表的な利用例です。実行はスクリプトまたは CLI ラッパーから行います。

- ID トークン取得（J-Quants）:
  ```
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使ってトークンを取得
  ```

- 日次 ETL を実行する（全体）:
  ```
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema
  result = run_daily_etl(conn)  # target_date を指定することも可能
  print(result.to_dict())
  ```

- 個別 ETL（例: 株価だけ）:
  ```
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, date.today())
  print(fetched, saved)
  ```

- ニュース収集ジョブ:
  ```
  from kabusys.data.schema import get_connection
  from kabusys.data.news_collector import run_news_collection

  conn = get_connection("data/kabusys.duckdb")
  results = run_news_collection(conn)  # sources や known_codes を指定可能
  print(results)  # {source_name: saved_count}
  ```

- ニュース RSS の直接フェッチ（単体テストや挙動確認）:
  ```
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["title"])
  ```

- スキーマ初期化（ETL を始める前に必ず実行）:
  - init_schema はテーブルが既に存在する場合はスキップするので冪等に呼べます。

---

## 監査ログ / 発注フロー

- 監査用スキーマ（signal_events / order_requests / executions）は audit モジュールに定義されています。
- init_audit_schema(conn) で既存の DuckDB 接続に追加できます。
- すべてのタイムスタンプは UTC で保存する方針です（init_audit_schema は SET TimeZone='UTC' を実行します）。
- order_request_id は冪等キーとして設計されています。

---

## ロギング・デバッグ

- settings.log_level でログレベルを制御（環境変数 LOG_LEVEL）。
- jquants_client 側でレート制御・リトライに関する警告ログが出ます。
- ETL 実行結果は ETLResult として返り、品質チェックやエラー情報を含みます。

---

## セキュリティ・運用の注意点

- J-Quants のリフレッシュトークンは漏洩しないように管理してください。
- RSS フィード取得では SSRF 対策（スキーム検証・プライベートアドレス拒否）を行っていますが、公開運用時はネットワーク ACL 等で外部アクセスを制御することを推奨します。
- DuckDB ファイルは適切なファイル権限で保護してください。
- KABUSYS_ENV を `live` に設定すると実運用モードになる想定なので、テスト・ステージング環境と分離してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py             # J-Quants API クライアント（fetch / save / auth）
      - news_collector.py             # RSS ニュース収集・保存
      - schema.py                     # DuckDB スキーマ定義・初期化
      - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
      - audit.py                      # 監査ログ（signal/order/execution）スキーマ
      - quality.py                    # データ品質チェック
      - pipeline.py
    - strategy/
      - __init__.py                    # 戦略関連のプレースホルダ
    - execution/
      - __init__.py                    # 発注/約定処理のプレースホルダ
    - monitoring/
      - __init__.py                    # 監視周りのプレースホルダ

---

## 追加メモ

- 自動で .env を読み込むロジックはプロジェクトルート（.git または pyproject.toml）を探索します。テストなどで自動ロードを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- jquants_client は ID トークンをモジュールレベルでキャッシュし、ページネーション中にトークンを共有します。401 発生時は一度だけ自動リフレッシュして再試行します。
- NewsCollector は defusedxml を活用し、レスポンスサイズ・gzip 解凍後サイズチェックなど DoS 対策を組み込んでいます。

---

必要であれば、README に CLI や Docker 化、CI/CD 運用手順、サンプル .env.example や unit tests の実行方法なども追記できます。どの情報を優先して追加しますか？