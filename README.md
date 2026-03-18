# KabuSys

日本株向けの自動売買データ基盤／ETL・監査・ニュース収集ライブラリです。  
J-Quants API や RSS フィード等からデータを取得し、DuckDB に保存・整形して戦略や発注モジュールに渡すことを目的としています。

この README はコードベース（src/kabusys 以下）を元に作成しています。

---

## 機能概要

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限 (120 req/min) 対応、リトライ（指数バックオフ）、401 発生時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日から未取得分を取得）、バックフィル（日次の後出し修正吸収）
  - 市場カレンダー取得 → 株価日足取得 → 財務データ取得 → 品質チェック の一連実行
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実装

- ニュース収集（RSS）
  - RSS フィードから記事収集、前処理（URL 除去、空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性確保
  - SSRF 対策、gzip サイズ上限、defusedxml による XML 攻撃対策
  - DuckDB へ冪等保存（ON CONFLICT DO NOTHING）および記事と銘柄コードの紐付け

- マーケットカレンダー管理
  - JPX カレンダーの差分更新ジョブ、営業日判定・次/前営業日の取得
  - DB 登録値優先、未登録日は曜日ベースでフォールバック

- 監査ログ（Audit）
  - シグナル→発注→約定までのトレーサビリティテーブル群（UUID ベース）を定義・初期化
  - order_request_id による冪等制御、全ての TIMESTAMP は UTC 保存（初期化時に設定）

- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution / Audit 層のテーブル DDL を提供
  - 初期化関数でテーブルとインデックスを冪等に作成

---

## 主要な機能一覧（抜粋）

- kabusys.config.Settings：環境変数ベースの設定（J-Quants トークン、kabu API パスワード、Slack トークン、DB パス等）
- kabusys.data.jquants_client：J-Quants API 呼び出し + 保存関数（fetch_*/save_*）
- kabusys.data.pipeline：日次 ETL 実行エントリ（run_daily_etl）および個別ジョブ
- kabusys.data.news_collector：RSS 取得・正規化・保存・銘柄抽出
- kabusys.data.schema：DuckDB スキーマ初期化（init_schema / get_connection）
- kabusys.data.calendar_management：営業日判定・カレンダー更新ジョブ
- kabusys.data.audit：監査ログ用テーブルと初期化関数
- kabusys.data.quality：品質チェック関数（run_all_checks 等）

---

## 必要条件 / 依存パッケージ

- Python >= 3.10（型ヒントや新しい構文を使用）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- 標準ライブラリを中心に実装されていますが、実行環境に応じて下記をインストールしてください。

例：
pip install duckdb defusedxml

（プロジェクト配布用に requirements.txt / pyproject.toml がある想定です。ローカルで開発する場合は仮想環境を推奨します。）

---

## セットアップ手順

1. リポジトリをクローン（ローカル開発）
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成して有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows では .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install -e .   （パッケージ化されている場合）
   - または最低限： pip install duckdb defusedxml

4. 環境変数設定 (.env)
   - プロジェクトルートに .env を作成すると自動で読み込まれます（自動読み込みは .git または pyproject.toml を基準にプロジェクトルートを特定します）。
   - 読み込み順序（優先度）:
     - OS 環境変数（最優先）
     - .env.local（存在すれば .env を上書き）
     - .env
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で使用）。

必須の環境変数（例）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) : 監視用 SQLite 等のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) : development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

.env の例:
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単なコード例）

以下は代表的な利用例です。実際はロギング設定やエラーハンドリングを適宜追加してください。

- DuckDB スキーマ初期化
  from kabusys.config import settings
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)
  # conn は duckdb.DuckDBPyConnection オブジェクト

- 日次 ETL の実行
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)
  print(result.to_dict())

- 個別ジョブ（価格 / 財務 / カレンダー）
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

  today = date.today()
  fetched, saved = run_prices_etl(conn, today)
  fetched_f, saved_f = run_financials_etl(conn, today)
  fetched_c, saved_c = run_calendar_etl(conn, today)

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  # known_codes は銘柄抽出で使用する有効銘柄コードのセット（例: {'7203','6758'}）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  # results は {source_name: 新規保存件数} の辞書

- J-Quants の id_token 取得（直接必要な場合）
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使って POST

- 監査ログ用 DB 初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

- 品質チェックの実行
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn)
  for i in issues:
      print(i)

---

## 主要 API（抜粋）

- settings = kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token
  - settings.slack_channel_id
  - settings.duckdb_path, settings.sqlite_path
  - settings.env / settings.is_live / settings.is_paper / settings.is_dev
  - settings.log_level

- J-Quants クライアント
  - fetch_daily_quotes(id_token=None, code=None, date_from=None, date_to=None)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)

- News Collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles) -> list of new ids
  - save_news_symbols(conn, news_id, codes)
  - run_news_collection(conn, sources=None, known_codes=None)

- Schema / DB
  - init_schema(db_path)
  - get_connection(db_path)

- ETL
  - run_daily_etl(conn, target_date=None, id_token=None, run_quality_checks=True, ...)

- Calendar Management
  - calendar_update_job(conn, lookahead_days=90)
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - is_sq_day(conn, d)

- Audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

---

## ディレクトリ構成

リポジトリ内の主要ファイル・モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数設定・自動 .env ロード
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント & 保存ロジック
      - news_collector.py        # RSS 取得・前処理・保存・銘柄抽出
      - pipeline.py              # ETL パイプライン（run_daily_etl 等）
      - schema.py                # DuckDB スキーマ定義・初期化
      - calendar_management.py   # マーケットカレンダー管理
      - audit.py                 # 監査ログ用テーブル定義・初期化
      - quality.py               # データ品質チェック
    - strategy/                   # 戦略層（未実装のエントリポイント）
    - execution/                  # 発注・約定層（未実装のエントリポイント）
    - monitoring/                 # 監視系（未実装のエントリポイント）

※ 上記はこの README 作成時点でのコードベースに基づく抜粋です。strategy や execution、monitoring はパッケージとして存在しますが、詳細実装はこのスナップショットでは含まれていません。

---

## 運用上の注意点

- 環境変数は OS 環境 > .env.local > .env の順で上書きされます。OS の既存変数は保護されます。
- J-Quants API のレート制限（120 req/min）をクライアント側で厳守するよう実装済みですが、運用時は過負荷にならないようジョブ間隔等を調整してください。
- DuckDB の INSERT 文は ON CONFLICT DO UPDATE / DO NOTHING を使用して冪等性を保証していますが、外部からの直接操作により整合性が損なわれる可能性は常にあります。監査ログやバックアップを検討してください。
- ニュース収集で参照する RSS は外部 URL です。SSRF や大きなレスポンス、gzip bomb 等に対する対策を実装していますが、未知のフィードに対しては初期は少ないソースで試験運用することを推奨します。

---

## 貢献・拡張

- 戦略（strategy）や実際の発注実装（execution）はプロジェクト毎に差があります。features テーブルや ai_scores テーブルに合わせて戦略を作成してください。
- Slack 等への通知やモニタリング連携は monitoring モジュールに実装していく想定です。
- テストを追加する際は config の自動 .env ロードを抑止する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

README の内容に関して追記や特定の利用例（例：運用スケジュール cron 設定、Slack 通知例、kabu API 発注ラッパーの実装案など）が必要であれば、必要な箇所を指定していただければ詳細を作成します。