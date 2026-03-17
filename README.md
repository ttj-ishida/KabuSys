KabuSys
=======

KabuSys は日本株の自動売買 / データプラットフォーム向けのライブラリ群です。  
J-Quants API から市場データを取得して DuckDB に保存し、データ品質チェック、ニュース収集、監査ログの管理、ETL パイプラインを提供します。  
（このリポジトリはライブラリとしてのコア実装を含み、実行用の CLI/サービスは別途用意する想定です）

主な特徴
--------
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーを取得
  - レート制限(120 req/min) ガイド、固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）・401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を抑制
  - DuckDB へ冪等的に保存（ON CONFLICT 句）

- ETL パイプライン
  - 差分更新（最終取得日を参照して未取得範囲のみ取得）
  - backfill による後出し修正の吸収
  - 市場カレンダー先読み（lookahead）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集（RSS）
  - RSS 取得・前処理・記事ID の SHA-256 ベース生成による冪等保存
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - defusedxml による XML 攻撃対策
  - 記事→銘柄コードの紐付け（4桁銘柄コード抽出）

- DuckDB スキーマ定義・監査ログ
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 監査（signal → order → execution のトレース）用スキーマ初期化

- データ品質チェックモジュール
  - 欠損データ、スパイク（前日比閾値）、重複、日付整合性チェック
  - QualityIssue オブジェクトで結果を返す（error/warning）

セットアップ
----------
前提
- Python 3.10 以上（type hints の union 表記などを使用）
- Git リポジトリとしてプロジェクトルートに置くことを想定

1) 仮想環境作成（例）
- python -m venv .venv
- source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2) 必要パッケージをインストール
- pip install duckdb defusedxml

（プロジェクトで pyproject.toml / requirements.txt があればそれを使用してください）

環境変数
- KabuSys は環境変数 / .env(.local) を読み込みます（自動ロード。テスト時は無効化可能）。
  必要な主な環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD     : kabu API パスワード（必須）
  - KABU_API_BASE_URL     : kabu API ベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN       : Slack 通知用トークン（必須）
  - SLACK_CHANNEL_ID      : Slack チャンネルID（必須）
  - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : SQLite（監視用）パス（デフォルト data/monitoring.db）
  - KABUSYS_ENV           : environment (development | paper_trading | live)（デフォルト development）
  - LOG_LEVEL             : ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)（デフォルト INFO）

- .env 自動ロードの挙動:
  - 優先度: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方（基本例）
----------------

以下はライブラリの主要な利用例です。実運用では適切なロギング・例外ハンドリング・スケジューラを組み合わせてください。

1) DuckDB スキーマを初期化する
- Python スクリプト例:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # パスは設定に合わせて変更

2) 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

3) ニュース収集ジョブを実行する
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  # known_codes は有効な銘柄コード集合（例: 証券コード一覧）を用意
  known_codes = {"7203", "6758", "9432"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)

4) 監査ログ用 DB 初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/kabusys_audit.duckdb")

主な公開 API（抜粋）
- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（全テーブルを作成）
  - get_connection(db_path)
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - save_daily_quotes(conn, records), save_financial_statements(...), save_market_calendar(...)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL）
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
  - extract_stock_codes(text, known_codes)
- kabusys.data.audit
  - init_audit_db(db_path)
  - init_audit_schema(conn, transactional=False)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

注意・運用メモ
-------------
- Python バージョンは 3.10 以上を推奨（型ヒントや union 表記を使用）。
- ネットワーク呼び出し（J-Quants / RSS）は例外を投げる可能性があるため、運用コードではリトライや通知処理を追加してください。
- DuckDB はローカルファイルベースですが、高頻度更新で同時書き込みする場合は設計に注意してください（同時実行制御）。
- .env ファイルや環境変数に機密情報（API トークン）を格納する際はアクセス権限に注意してください。
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で便利です）。

ディレクトリ構成
----------------
（主要ファイル/モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                    -- 環境変数・設定管理（.env 自動ロード、Settings）
    - data/
      - __init__.py
      - schema.py                  -- DuckDB スキーマ定義・初期化
      - jquants_client.py          -- J-Quants API クライアント（取得/保存ロジック）
      - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
      - news_collector.py          -- RSS 取得・記事前処理・DB保存・銘柄抽出
      - calendar_management.py     -- 市場カレンダー更新 / 営業日判定ユーティリティ
      - audit.py                   -- 監査ログスキーマ初期化
      - quality.py                 -- データ品質チェック
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

貢献・開発
----------
- バグ修正・機能追加は Pull Request を歓迎します。  
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます。  
- 外部 API 呼び出しはモック可能な設計（ID トークンキャッシュや _urlopen の差し替えポイント）になっています。テスト時はこれらをモックして利用してください。

ライセンス
---------
（このテンプレートではライセンス情報は含まれていません。実プロジェクトでは LICENSE ファイルを追加してください。）

以上。README の補足やサンプルを追加したい箇所があれば教えてください。