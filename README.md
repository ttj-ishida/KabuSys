# KabuSys

日本株向けの自動売買システム向けユーティリティ群（ライブラリ）

概要:
- J-Quants / kabuステーション 等の外部 API から市場データ・カレンダー・財務データ・ニュースを取得し、
  DuckDB に保存するための ETL / データ品質チェック / カレンダー管理 / ニュース収集 / 監査ログ初期化モジュール群を提供します。
- 実システムのデータ基盤（Raw / Processed / Feature / Execution / Audit レイヤ）構築を支援することを目的とします。

注意:
- 本ライブラリはパッケージの一部（strategy / execution / monitoring 等の実装は別途実装する想定）です。
- コードは Python 3.10 以上を想定しています（PEP 604 の | 型を使用）。

---

## 主な機能（抜粋）

- 環境変数管理
  - プロジェクトルートの `.env`, `.env.local` を自動でロード（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）
  - 必須値チェック（settings オブジェクト）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダーの取得（ページネーション対応）
  - レート制限（120 req/min）遵守、リトライ（指数バックオフ）、401 自動リフレッシュ対応
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT による更新）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理（URL 除去・空白正規化）、記事ID を SHA-256 で生成
  - SSRF / XML Bomb 対策（スキーム検証、プライベート IP 検査、defusedxml、レスポンスサイズ上限）
  - raw_news / news_symbols に冪等保存（トランザクション、INSERT ... RETURNING）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤのテーブル DDL を定義
  - init_schema でファイル作成（親ディレクトリ自動生成）およびテーブル作成（冪等）

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）：カレンダー取得 → 株価差分取得（backfill） → 財務差分取得 → 品質チェック
  - 差分更新ロジック（最終取得日からの差分と backfill 日数）
  - 品質チェックとの連携

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日の取得、期間内営業日リスト
  - 夜間バッチ（calendar_update_job）でカレンダー差分更新・バックフィル

- 監査ログ初期化（kabusys.data.audit）
  - シグナル → 発注 → 約定までトレース可能な監査テーブル群の DDL と初期化ユーティリティ

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付整合性（未来日付・非営業日）などのチェックを実行

---

## 必要環境 / 依存パッケージ（代表例）

- Python 3.10+
- duckdb
- defusedxml

（その他、標準ライブラリで coverage。プロジェクトでは追加の依存関係がある可能性があります。）

インストール例（仮）:
pip install duckdb defusedxml

---

## 環境変数

主に以下を利用します（settings 経由で参照）。必須のものは起動前に設定してください。

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuステーション API ベースURL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — environment（development / paper_trading / live、デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

自動ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 .env（最低限）:
JQUANTS_REFRESH_TOKEN="your_jquants_refresh_token"
KABU_API_PASSWORD="your_kabu_password"
SLACK_BOT_TOKEN="xoxb-..."
SLACK_CHANNEL_ID="C01234567"
DUCKDB_PATH="data/kabusys.duckdb"
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（手早い流れ）

1. Python 3.10+ を用意する。

2. 依存ライブラリをインストールする（例）:
   pip install duckdb defusedxml

3. 環境変数を設定する（.env をプロジェクトルートに作成するか、OS 環境でセット）。
   - 必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

4. DuckDB スキーマを初期化する:
   - Python REPL またはスクリプトから実行:
     from kabusys.data.schema import init_schema
     init_schema("data/kabusys.duckdb")
   - 監査ログ専用 DB を初期化する場合:
     from kabusys.data.audit import init_audit_db
     init_audit_db("data/audit.duckdb")

5. 初回 ETL 実行（例: 日次 ETL）:
   from kabusys.data.schema import get_connection
   from kabusys.data.pipeline import run_daily_etl
   conn = get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn)
   print(result.to_dict())

6. ニュース収集実行例:
   from kabusys.data.schema import get_connection
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   conn = get_connection("data/kabusys.duckdb")
   # known_codes は銘柄リスト（set of "7203", ...）を与えると記事→銘柄紐付けが行われる
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set(["7203", "6758"]))
   print(res)

7. カレンダー夜間バッチ実行例:
   from kabusys.data.schema import get_connection
   from kabusys.data.calendar_management import calendar_update_job
   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print("saved:", saved)

---

## 使い方（主要 API サンプル）

- settings を参照して環境変数を取得:
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)

- DuckDB スキーマ初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- ETL を日次で実行:
  from kabusys.data.schema import get_connection
  from kabusys.data.pipeline import run_daily_etl
  conn = get_connection("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集（RSS）:
  from kabusys.data.news_collector import fetch_rss, save_raw_news, save_news_symbols
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  # conn: DuckDB の接続を用意
  new_ids = save_raw_news(conn, articles)
  # 銘柄抽出 → save_news_symbols など（known_codes を使う run_news_collection が便利）

- J-Quants トークン取得（低レベル）:
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))

---

## 設計上の注意点 / ポリシー

- 全ての ETL 保存処理は冪等性を担保する（ON CONFLICT）ため、複数回実行しても上書きや重複が大きく起きない設計です。
- J-Quants API にはレート制限（120 req/min）があり、クライアント側で待機制御を行います。大量のリクエスト実行時は注意してください。
- ニュース収集モジュールは SSRF / XML Bomb / Gzip-Bomb 等に対する防御を実装していますが、運用に応じてタイムアウトやサイズ上限の調整を検討してください。
- DuckDB に対する DDL は init_schema で一括作成します。既存クライアントが接続中の状態で DDL の操作を行う際は注意してください（監査スキーマの初期化はトランザクションオプションあり）。

---

## ディレクトリ構成（リポジトリ内 /src 以下の主要ファイル）

- src/kabusys/
  - __init__.py  (パッケージメタ情報)
  - config.py    (環境変数・設定管理)
  - data/
    - __init__.py
    - schema.py               (DuckDB スキーマ定義・初期化)
    - jquants_client.py       (J-Quants API クライアント + 保存)
    - pipeline.py             (ETL パイプライン)
    - news_collector.py       (RSS 収集・保存・銘柄抽出)
    - calendar_management.py  (マーケットカレンダー管理)
    - quality.py              (品質チェック)
    - audit.py                (監査ログテーブルの DDL / 初期化)
    - pipeline.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（上記はこのコードベースで確認できるファイル構成の抜粋です。実際のリポジトリにはテスト、ドキュメント、CI 設定等がある場合があります。）

---

## 開発・運用のヒント

- テスト:
  - settings の自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できるため、ユニットテスト時に外部環境に依存せずにテストしやすくなっています。
  - jquants_client の HTTP 部分や news_collector._urlopen をモックすると外部通信を遮断してテスト可能です。

- ロギング:
  - settings.log_level を用いてログレベルを制御できます。運用時は INFO、デバッグ時は DEBUG に設定してください。

- 運用:
  - 日次 ETL は cron / Airflow / GitHub Actions 等でスケジューリングすると良いでしょう。
  - DuckDB のファイルパスは settings.duckdb_path で変更できます（共有ストレージやバックアップポリシーに合わせてください）。

---

## ライセンス・貢献

- 本 README はコードベースの説明であり、実際のライセンス表記や貢献ガイドはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、README にサンプルスクリプト（run_etl.py や collect_news.py など）を追加で作成できます。どのような例が欲しいか教えてください。