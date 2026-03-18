KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API からの時系列・財務・マーケットカレンダー取得、RSS ニュース収集、DuckDB を用いたデータスキーマと ETL パイプライン、データ品質チェック、監査ログ（発注→約定トレース）などを提供します。  
設計上、API レート制限・リトライ・冪等性・Look‑ahead バイアス対策・SSRF 対策などを考慮しています。

主な機能
--------
- J-Quants クライアント
  - 日次株価（OHLCV）/四半期財務/マーケットカレンダーの取得（ページネーション対応）
  - レートリミット管理（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録してトレーサビリティを確保
  - DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）、バックフィル（API 後出し修正吸収）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）を実行可能

- ニュース収集（RSS）
  - RSS フィード取得、コンテンツ前処理、記事ID＝正規化URLのSHA‑256ハッシュ（先頭32文字）
  - SSRF 対策、gzip 解凍サイズ上限、XML の安全パース（defusedxml）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO NOTHING、RETURNING で実挿入数を取得）
  - 記事に含まれる銘柄コード抽出（既知銘柄のみ）

- マーケットカレンダー管理
  - 営業日判定、前後の営業日取得、期間内営業日列挙
  - DB が未取得の場合は曜日（平日）をフォールバック

- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレーサビリティテーブルを提供
  - 発注の冪等キー（order_request_id）やタイムスタンプ管理（UTC）をサポート

セットアップ
----------
前提
- Python 3.10 以上（typing の | 演算子等を使用）
- 必要パッケージ例: duckdb, defusedxml（実プロジェクトでは requirements.txt 等を参照）

インストール例（ソース直下で）
- 開発インストール:
  python -m pip install -e .

- 必要パッケージを個別にインストールする例:
  python -m pip install duckdb defusedxml

環境変数 / .env
- 自動的にプロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を読み込みます。
  - 読み込み順序: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効化するには: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（実行に必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注系で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必要時）
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意 / デフォルト
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db

簡易 .env.example
- .env ファイルの例:
  JQUANTS_REFRESH_TOKEN=your_refresh_token_here
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  DUCKDB_PATH=data/kabusys.duckdb

使い方（簡単なコード例）
--------------------

1) DuckDB スキーマ初期化（最初に一度）
- 全テーブルを作成して接続を取得します。

from kabusys.config import settings
from kabusys.data import schema

conn = schema.init_schema(settings.duckdb_path)

2) 日次 ETL の実行（株価 / 財務 / カレンダー取得 + 品質チェック）
- run_daily_etl は ETLResult を返します。

from kabusys.data import pipeline

result = pipeline.run_daily_etl(conn)  # 引数で target_date, id_token, オプションを指定可
print(result.to_dict())

3) ニュース収集（RSS）と保存
- RSS フィードを取得して raw_news に保存し、必要があれば銘柄紐付けを行います。

from kabusys.data import news_collector, schema

# すでに schema.init_schema で conn を作成済みとする
articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
new_ids = news_collector.save_raw_news(conn, articles)

# known_codes を与えれば自動で news_symbols への紐付けを試みる（run_news_collection 内でも行われます）

4) カレンダー夜間更新ジョブ
- calendar_update_job を使って market_calendar を差分更新します。

from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)

5) 監査ログ用 DB 初期化（監査専用DBを別で作る場合）
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")

ログとデバッグ
---------------
- 設定は環境変数 LOG_LEVEL で制御します。デフォルト INFO。
- エラー時はロギングで詳細を出力するので、ハンドリングして再試行やアラートに繋げてください。

セキュリティ & 設計に関する注意
------------------------------
- J-Quants クライアントは 120 req/min のレート制限を厳守するよう実装されています（モジュール内 RateLimiter）。
- HTTP エラー（408/429/5xx）に対するリトライ（指数バックオフ）および 401 時の自動トークンリフレッシュを備えています。
- ニュース収集では SSRF 対策（スキーム検査、ホストのプライベートアドレス判定、リダイレクト検査）や XML の安全パース（defusedxml）、受信サイズ制限を実装しています。
- DuckDB への保存は可能な限り冪等（ON CONFLICT）にして二重保存／再実行に耐える設計です。
- すべてのタイムスタンプは UTC をベースに記録する方針になっています（監査ログ等で明示的に SET TimeZone='UTC' を実行）。

ディレクトリ構成
----------------
リポジトリの主なファイル・モジュール（抜粋）

- src/kabusys/__init__.py           (パッケージ定義 / バージョン)
- src/kabusys/config.py             (環境変数 / Settings)
- src/kabusys/data/
  - __init__.py
  - jquants_client.py                (J-Quants API クライアント、保存ロジック)
  - pipeline.py                      (ETL パイプライン)
  - news_collector.py                (RSS 収集・保存・銘柄抽出)
  - schema.py                        (DuckDB スキーマ定義・初期化)
  - calendar_management.py           (カレンダー管理・営業日判定)
  - audit.py                         (監査ログスキーマ / 初期化)
  - quality.py                       (データ品質チェック)
- src/kabusys/strategy/              (戦略関連モジュール: 空パッケージ / 拡張ポイント)
- src/kabusys/execution/             (発注/実行管理: 空パッケージ / 拡張ポイント)
- src/kabusys/monitoring/            (監視関連: 空パッケージ / 拡張ポイント)

開発者向け
-----------
- 自動 .env ロードはプロジェクトルートを .git または pyproject.toml で判定します。テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを無効にできます。
- モジュールの多くは引数で id_token や known_codes を注入可能にしており、単体テストが容易になるよう設計されています（ネットワーク I/O をモックしてテスト可能）。

ライセンス / 貢献
-----------------
- 本 README 内ではライセンスは明記していません。実際のリポジトリに LICENSE ファイルを置いてください。  
- バグ修正や機能追加のプルリクエスト歓迎します。変更を加える際は既存の設計方針（冪等性・セキュリティ・トレーサビリティ）に配慮してください。

問い合わせ
----------
実装・使い方に関する質問・要望はリポジトリの issue に登録してください。