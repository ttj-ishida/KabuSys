KabuSys — 日本株自動売買システム (README)
===========================================

概要
----
KabuSys は日本株向けのデータ収集・ETL・品質チェック・監査ログ機能を持つ自動売買システムの基盤ライブラリです。本リポジトリは主に次のレイヤーを提供します。

- データ取得: J-Quants API から株価・財務・市場カレンダーを取得
- ニュース収集: RSS フィードから記事を収集して DuckDB に保存
- ETL パイプライン: 差分取得・バックフィル・保存・品質チェック
- スキーマ管理: DuckDB のスキーマ定義と初期化
- 監査ログ: シグナル〜発注〜約定までのトレーサビリティ用テーブル定義
- 設定: .env / 環境変数からの設定読み込み（自動読み込み機能あり）

主な機能
--------
- J-Quants クライアント
  - 日足（OHLCV）、四半期財務、JPX カレンダーのページネーション対応取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - データ取得時刻（fetched_at）を UTC で記録し Look‑ahead Bias を抑制
  - DuckDB へ冪等保存（ON CONFLICT を利用）
- ニュース収集（RSS）
  - URL 正規化・トラッキングパラメータ除去、記事 ID を SHA‑256（先頭32文字）で生成
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - レスポンス上限・gzip 解凍チェック、defusedxml による安全な XML パース
  - bulk insert（チャンク）、ON CONFLICT DO NOTHING、挿入 ID を返す
  - 記事と銘柄コードの紐付け（news_symbols）
- ETL パイプライン
  - 差分更新（DB の最終取得日に基づく自動算出）と backfill 日数の指定
  - カレンダー先読み、品質チェック（欠損、スパイク、重複、日付整合性）
  - run_daily_etl で一括実行。各ステップは独立してエラーハンドリング
- スキーマ管理
  - raw / processed / feature / execution / audit 層のテーブル DDL 定義
  - init_schema / init_audit_db 等で DuckDB ファイルを初期化可能
- 監査ログ
  - signal_events / order_requests / executions によるトレーサビリティ
  - UUID ベースの冪等キー、UTC タイムスタンプ、適切な制約・インデックス

セットアップ手順
----------------

1. Python 環境を用意
   - Python 3.9+ を推奨
   - 仮想環境を作成（例）
     - python -m venv .venv
     - source .venv/bin/activate (Unix)
     - .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 必要な主要依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （実際の requirements.txt がある場合はそちらを使用してください）

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネルID
   - 任意／デフォルト:
     - KABUS_API_BASE_URL — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   - サンプル .env（プロジェクトルート）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. スキーマ初期化
   - DuckDB を初期化して全テーブルを作成します。
   - 例（Python REPL / スクリプト）:
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     # またはインメモリ
     conn = schema.init_schema(":memory:")

5. 監査ログ DB の初期化（監査を別DBに分ける場合）
   - from kabusys.data import audit
     audit_conn = audit.init_audit_db("data/audit.duckdb")

使い方（主要な API 例）
----------------------

- 設定の参照
  from kabusys.config import settings
  settings.jquants_refresh_token  # 未設定なら ValueError を投げる
  settings.duckdb_path  # Path オブジェクト

- J-Quants API: トークン取得 / データ取得
  from kabusys.data import jquants_client as jq
  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用して取得
  records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)

- データ保存（DuckDB）
  conn = schema.init_schema("data/kabusys.duckdb")
  saved = jq.save_daily_quotes(conn, records)

- ETL の実行（1日分の自動差分 ETL）
  from kabusys.data import pipeline
  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema 済みを想定
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- RSS ニュース収集
  from kabusys.data import news_collector as nc
  conn = schema.get_connection("data/kabusys.duckdb")
  results = nc.run_news_collection(conn, known_codes=set(["7203","6758"]))  # known_codes を渡すと銘柄紐付け実行

- 監査ログ初期化（別DB）
  from kabusys.data import audit
  audit_conn = audit.init_audit_db("data/audit.duckdb")

主な設計上の注意点・挙動
-----------------------
- 環境変数の自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込みます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants クライアント
  - 120 req/min のレート制御を内部的に行います。
  - リトライは 408/429/5xx に対して行われ、429 の場合は Retry-After ヘッダを尊重します。401 は1回だけトークンリフレッシュしてリトライします。
  - 取得時の fetched_at は UTC で記録されます（Look-ahead の抑止）。
- News Collector（RSS）
  - URL の正規化、トラッキングパラメータ除去、SSRF 対策、gzip のサイズチェック（10MB 上限）など安全対策を行っています。
  - 記事 ID は正規化後 URL の SHA‑256 の先頭 32 文字です。
- ETL
  - 差分取得は DB の最終取得日から必要分を自動算出します（backfill により直近 N 日を再取得）。
  - 品質チェックは run_daily_etl の一部として実行でき、問題は QualityIssue オブジェクトとして返されます。重大度に応じて処理を止めるかどうかは呼び出し側が判断します。
- DuckDB
  - init_schema / init_audit_db は必要に応じて親ディレクトリを作成します。
  - ":memory:" 指定でインメモリ DB を利用可能です。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py             — パッケージ定義、バージョン
- config.py               — 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py     — RSS ニュース収集・保存・紐付け
  - pipeline.py           — ETL パイプライン（run_daily_etl 他）
  - schema.py             — DuckDB スキーマ定義・初期化
  - calendar_management.py— 市場カレンダー管理（営業日判定・更新ジョブ）
  - audit.py              — 監査ログスキーマ & 初期化
  - quality.py            — データ品質チェック
- strategy/
  - __init__.py           — 戦略関連（将来的な拡張）
- execution/
  - __init__.py           — 発注・約定関連（将来的な拡張）
- monitoring/
  - __init__.py           — 監視・メトリクス（将来的な拡張）

トラブルシューティング
----------------------
- ValueError: 環境変数が未設定
  - settings.* のプロパティは未設定時に ValueError を送出します。.env.example を参考に .env を作成してください。
- DuckDB に接続できない / ファイル作成失敗
  - 指定した DUCKDB_PATH の親ディレクトリに書き込み権限があるか確認してください。init_schema はディレクトリを自動作成しますが、権限がないと失敗します。
- ネットワーク / API エラー
  - jquants_client はリトライやバックオフを実装していますが、頻繁に 429 が返る場合は取得間隔や API 利用計画を見直してください。

開発上のメモ
------------
- テスト時に .env の自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからモジュールを import してください。
- モジュールの多くは引数で id_token を注入できるようになっており、テスト容易性を考慮しています。
- DuckDB の SQL 実行ではパラメータバインディング（?）を用いてインジェクションリスクを低減しています。

貢献
----
機能追加やバグ修正のプルリクエスト歓迎です。大きな設計変更を行う場合は issue で先に相談してください。

ライセンス
----------
（この README にライセンスの明記はありません。適切なライセンスファイルをプロジェクトに追加してください。）

-- End of README --