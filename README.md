# KabuSys

日本株自動売買システムのコアライブラリ（軽量モジュール群）。  
データ収集（J-Quants）、ニュース収集（RSS）、ETLパイプライン、マーケットカレンダー管理、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）、および DuckDB スキーマ初期化を提供します。

---

## 概要

KabuSys は日本株向けのデータ基盤および自動売買補助ライブラリです。設計上は以下を重視しています。

- データ整備の冪等性（DuckDB 上で ON CONFLICT / DO UPDATE 等を利用）
- 外部 API の扱い方（レート制限・リトライ・トークン自動リフレッシュ）
- Look-ahead bias の防止（データ取得時刻を記録）
- セキュリティ対策（RSS収集の SSRF 対策、XML パースの安全化）
- データ品質チェックと監査ログによるトレーサビリティ

このリポジトリはライブラリ群なので、上位の戦略実装や実際のブローカー接続モジュールは別に実装して利用します。

---

## 主な機能一覧

- 環境変数 / 設定管理（kabusys.config）
  - .env/.env.local 自動読み込み（無効化可）
  - 必須項目の検証（例: JQUANTS_REFRESH_TOKEN）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期）、JPX カレンダーの取得
  - レート制限（120 req/min）とリトライ（指数バックオフ）
  - トークン自動リフレッシュ（401 時）
  - DuckDB への冪等保存ユーティリティ（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（gzip 対応、受信サイズ制限）
  - URL 正規化・トラッキングパラメータ除去・記事ID生成（SHA-256）
  - SSRF 対策（リダイレクト検査、プライベート IP ブロック）
  - DuckDB への冪等保存（raw_news / news_symbols）
  - 銘柄コード抽出（4桁数字 + 有効コードセット）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 用テーブルの DDL
  - init_schema / get_connection で DB 作成・接続
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（市場カレンダー → 株価 → 財務）と品質チェック一括実行
  - 差分取得・バックフィルロジック
  - run_daily_etl により ETL 実行結果（ETLResult）を取得
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 翌営業日・前営業日・期間内営業日取得
  - 夜間バッチ更新ジョブ（calendar_update_job）
- 監査ログ（kabusys.data.audit）
  - シグナル・発注要求・約定をトレースする監査テーブル初期化
  - init_audit_db / init_audit_schema による初期化
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
  - run_all_checks でまとめて実行・検出結果返却

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに union types や typing の新しい表記が使われているため 3.10 以上を想定）
- Git とインターネット接続（J-Quants API 等へのアクセスが必要）

1. リポジトリをクローン / コピー

   git clone <repo-url>
   cd <repo-dir>

2. 仮想環境を作成して有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install --upgrade pip
   pip install duckdb defusedxml

   ※プロジェクトに requirements.txt / pyproject.toml があればそちらでインストールしてください。
   （上記は最低限必要なパッケージの例です）

4. 開発インストール（任意）

   pip install -e .

5. 環境変数の設定

   .env ファイルをプロジェクトルートに配置するか、OS 環境変数で設定します。
   自動読み込みはデフォルトで有効です（kabusys.config がプロジェクトルートを検出した場合）。
   自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須の主な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション 等の API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB などに使用する SQLite パス（省略時 data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 .env

    JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
    KABU_API_PASSWORD=secret_pass
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C12345678
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=DEBUG

---

## 使い方（簡単な例）

以下は、基本的な初期化・ETL 実行・ニュース収集のサンプルです。

1) DuckDB スキーマ初期化

    from kabusys.data.schema import init_schema
    conn = init_schema("data/kabusys.duckdb")  # ファイル DB。":memory:" も可

2) 日次 ETL を実行して J-Quants からデータ取得（run_daily_etl）

    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    result = run_daily_etl(conn, target_date=date.today())
    print(result.to_dict())

3) ニュース収集ジョブの実行

    from kabusys.data.news_collector import run_news_collection
    # known_codes は銘柄抽出で利用する有効コードセット（省略可）
    known_codes = {"7203", "6758", "9984"}  # 例
    results = run_news_collection(conn, known_codes=known_codes)
    print(results)  # {source_name: 新規保存件数}

4) 監査 DB 初期化（監査ログ専用 DB を分ける場合）

    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/kabusys_audit.duckdb")

5) 設定値を参照する

    from kabusys.config import settings
    token = settings.jquants_refresh_token
    is_live = settings.is_live

注意点:
- J-Quants の API 呼び出しはレート制限（120 req/min）が内部的に制御されます。
- get_id_token() はリフレッシュトークンから idToken を取得します。API 呼び出しではキャッシュ・自動リフレッシュが働きます。
- テストや一時的に自動 .env ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## よく使う API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token, settings.kabu_api_password, settings.duckdb_path, settings.env など

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(refresh_token=None)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles) -> list of new ids
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None, timeout=30)

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, run_quality_checks=True, ...)

- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - calendar_update_job(conn, lookahead_days=90)

- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None)

- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py
    execution/
      __init__.py
    strategy/
      __init__.py
    monitoring/
      __init__.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      calendar_management.py
      schema.py
      audit.py
      quality.py

説明:
- data/: データ取得・ETL・スキーマ定義・品質チェック等、データプラットフォーム周りの実装。
- config.py: .env 自動読み込み・環境設定管理。
- jquants_client.py: J-Quants API のクライアント（取得・保存ユーティリティ含む）。
- news_collector.py: RSS 取得・前処理・DuckDB 保存・銘柄抽出。
- pipeline.py: 日次 ETL のオーケストレーション。
- calendar_management.py: JPX カレンダーの管理と営業日ロジック。
- schema.py: DuckDB の全テーブル DDL と初期化ロジック。
- audit.py: 発注/約定の監査ログ向けスキーマと初期化処理。
- quality.py: データ品質チェック群。

---

## 運用 / 注意事項

- 実稼働（live）環境へ移す場合は settings.is_live を使ったガード、注文系処理の二重チェック、監査ログの厳格化を行ってください。
- J-Quants API キーやブローカーの認証情報は絶対に公開リポジトリに置かないでください。`.env` は .gitignore に追加することを推奨します。
- news_collector は外部 URL を扱うため、ネットワーク設定やプロキシ、ファイアウォールなどの影響を受けます。SSRF 対策や受信サイズ制限を実装していますが、追加のセキュリティ要件に応じて設定してください。
- DuckDB は単一ファイル DB として運用可能ですが、同時書き込みなどの運用面は注意が必要です（特に複数プロセスでの更新）。

---

## 貢献・拡張

- strategy/、execution/、monitoring/ は空のパッケージです。ここに戦略実装、注文本体、監視ツール等を実装してください。
- 必要に応じて外部ブローカー接続（kabuステーションなど）を execution 層に実装し、audit テーブルと連携させてください。
- 品質チェックやスキーマの拡張は data/schema.py / data/quality.py を参照して追加してください。

---

必要に応じて README にサンプルスクリプトや CI / デプロイ手順を追加できます。具体的に追記したい項目があれば教えてください。