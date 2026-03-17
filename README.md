kabusys
=======

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。本リポジトリにはデータ収集（J-Quants、RSSニュース）、ETLパイプライン、DuckDB スキーマ定義、データ品質チェック、監査ログ（発注→約定のトレース）などを中心としたモジュール群が含まれます。戦略層（strategy）、実行層（execution）、監視（monitoring）用のパッケージ構造は用意されていますが、各実装は利用者が拡張することを想定しています。

主な機能
--------
- 環境変数 / .env の自動読み込み（プロジェクトルート検出）
- J-Quants API クライアント
  - OHLCV（日足）、四半期財務、JPX マーケットカレンダーの取得
  - レート制限遵守（120 req/min）、リトライ、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を記録し Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT）
- RSS ベースのニュース収集器
  - XML の安全なパース（defusedxml）
  - URL 正規化・トラッキングパラメータ削除・SSRF対策
  - 記事IDを SHA-256（先頭32文字）で冪等生成
  - DuckDB へのバルク挿入（トランザクション・チャンク処理）
  - 記事と銘柄コードの紐付け機能
- DuckDB スキーマ定義 / 初期化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン
  - 差分更新（最終取得日からの差分）とバックフィル
  - 市場カレンダーの先読み
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- マーケットカレンダー管理ユーティリティ（営業日判定、前後営業日取得）
- 監査ログ（signal → order_request → execution のトレースを UUID で保持）
- データ品質チェックモジュール（QualityIssue で問題を集約）

必要条件
--------
- Python 3.10 以上（型ヒントに PEP 604 の union 型 (|) を使用しているため）
- 主要外部パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクト利用側でさらに requests 等を使う場合は必要に応じて追加してください）

セットアップ手順
---------------
1. リポジトリをクローンして依存パッケージをインストールします（例は pip）。
   - requirements.txt がない場合は最低限 duckdb, defusedxml を入れてください。

   pip install duckdb defusedxml

2. 環境変数を準備します。少なくとも以下の変数が必要です（.env ファイルをプロジェクトルートに配置できます）。

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション向けパスワード（必須）
   - KABU_API_BASE_URL     : kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（Monitoring 用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : 環境 ('development' | 'paper_trading' | 'live')（任意, default=development）
   - LOG_LEVEL             : ログレベル ('DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL')

   注意:
   - パッケージ起動時、.env/.env.local はプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください（テスト用）。

3. DuckDB スキーマの初期化（サンプル）

   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)

   - テストや一時実行では ":memory:" を渡してインメモリ DB を使用できます。

4. 監査ログ用スキーマの初期化（任意）

   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（主要な操作例）
--------------------

設定の取得
- 環境変数は Settings クラス経由で取得できます。

  from kabusys.config import settings
  token = settings.jquants_refresh_token
  db_path = settings.duckdb_path

J-Quants API を直接呼ぶ（トークン取得／データ取得）
- IDトークン取得:

  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token から自動取得

- 日足を取得:

  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))

ニュース収集ジョブ
- RSS から記事を取得して raw_news に保存（既存 DB 接続を利用）:

  from kabusys.data.news_collector import run_news_collection
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})

ETL（デイリー）
- 日次 ETL を実行して株価/財務/カレンダーを取得し品質チェックを行う:

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # settings.duckdb_path に接続済み conn を渡す

  ETLResult には取得数・保存数・品質チェックの Issue リストやエラーメッセージが格納されます。

マーケットカレンダー管理
- 営業日判定や前後営業日取得:

  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  is_trade = is_trading_day(conn, date(2026,3,17))
  nxt = next_trading_day(conn, date(2026,3,17))

品質チェック（単独実行）
- ETL 後に実行する場合や手動でチェックを行う:

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)

スキーマ操作
- 初期化済みの DB に接続だけしたい場合:

  from kabusys.data.schema import get_connection
  conn = get_connection(settings.duckdb_path)

注意点 / 実装上の考慮事項
-----------------------
- J-Quants クライアントは API レート制限（120 req/min）に合わせて内部でスロットリングを行います。大量取得時は実行時間に注意してください。
- RSS 取得は SSRF 対策やレスポンスサイズ制限、gzip 解凍後のサイズチェックなどセキュリティ・リソース保護を考慮しています。
- DuckDB に対する挿入は基本的に冪等（ON CONFLICT）になっており、ETL は差分更新を行うように設計されています。
- audit.init_audit_schema はデフォルトで UTC タイムゾーンを設定します。監査証跡は UTC で管理する想定です。
- Settings クラスは環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL 等）を行います。不正値は ValueError を発生させます。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py                : パッケージ初期化（__version__ 等）
- config.py                  : 環境変数管理 (.env 自動ロード、Settings クラス)
- data/
  - __init__.py
  - jquants_client.py        : J-Quants API クライアント（取得 + DuckDB 保存）
  - news_collector.py        : RSS ニュース収集・記事正規化・保存
  - schema.py                : DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py              : ETL パイプライン（差分更新・品質チェック）
  - calendar_management.py   : マーケットカレンダーの管理ユーティリティ
  - audit.py                 : 監査ログスキーマ（signal/order_request/execution）
  - quality.py               : データ品質チェック
- strategy/
  - __init__.py              : 戦略層（拡張領域）
- execution/
  - __init__.py              : 発注実行層（拡張領域）
- monitoring/
  - __init__.py              : 監視関連（拡張領域）

付録（便利なヒント）
-------------------
- テストやスクリプト実行時に .env の自動読み込みを無効にしたい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定してください。
- インメモリ DuckDB で素早く動作確認するには db_path に ":memory:" を渡してください。
- 大量データの一括挿入はチャンク処理されますが、メモリや SQL 文長の制限に注意してください。

貢献
----
バグ報告、機能提案やPRは歓迎します。CI やテスト、依存管理（requirements.txt / pyproject.toml）を追加していただけると助かります。

ライセンス
--------
（ここにプロジェクトのライセンス情報を記載してください）

以上。必要であれば使い方の具体的なスニペットや .env.example のテンプレートを作成します。どの部分をより詳述しますか？