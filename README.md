KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買基盤向けライブラリ群です。  
J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存する ETL パイプライン、RSS ベースのニュース収集、カレンダー管理、データ品質チェック、監査ログ（発注〜約定のトレーサビリティ）などの機能を提供します。  
設計上、API レート制限やリトライ、SSRF 対策、冪等保存（ON CONFLICT）や品質チェックを重視しています。

主な機能
--------
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し、look-ahead bias を防止
- DuckDB スキーマ定義 / 初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブルを定義
  - インデックス定義や外部キーを含む冪等初期化
- ETL パイプライン
  - 差分取得（最終取得日ベース）＋バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL 実行エントリポイント
- ニュース収集モジュール
  - RSS を取得して前処理（URL除去・空白正規化）、記事IDは正規化URLのSHA-256で生成
  - SSRF 対策、受信サイズ上限、XML パース安全化（defusedxml）
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理
  - 営業日判定、next/prev_trading_day、calendar の夜間更新ジョブ
- 監査（Audit）ロギング
  - signal → order_request → execution のトレースを UUID 連鎖で保存
  - 発注の冪等キー、UTC タイムスタンプ管理
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合を SQL ベースで検出

動作環境
--------
- Python 3.10 以上（typing の新構文や型ヒントを使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, json, logging など）

セットアップ手順
----------------
1. リポジトリをクローン／プロジェクトルートへ移動。

2. 仮想環境作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール（プロジェクト側で requirements.txt や pyproject.toml を用意していればそちらを使用してください）。最低限の例:
   ```
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - .env または .env.local に環境変数を記述できます。config.py は自動的にプロジェクトルート（.git または pyproject.toml の存在するディレクトリ）から .env/.env.local を読み込みます。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   重要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション API パスワード
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID      : Slack 送信先チャンネル ID

   任意 / デフォルト値あり
   - KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL             : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視 DB（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. DuckDB スキーマ初期化（Python REPL やスクリプトで実行）
   - 例: プロジェクトルートで Python スクリプトを実行して初期化
   ```
   python -c "from kabusys.data import schema; schema.init_schema('data/kabusys.duckdb')"
   ```
   - 監査テーブルを追加する場合:
   ```
   python -c "import duckdb; from kabusys.data import schema, audit; conn = schema.init_schema('data/kabusys.duckdb'); audit.init_audit_schema(conn)"
   ```

使い方（簡易ガイド）
-----------------

1. 日次 ETL を実行する（Python から）
   ```python
   from kabusys.data import schema, pipeline

   conn = schema.init_schema('data/kabusys.duckdb')  # まだなら初期化
   result = pipeline.run_daily_etl(conn)
   print(result.to_dict())
   ```

   - run_daily_etl は市場カレンダー→株価→財務→品質チェックの順で処理します。
   - id_token を外部取得して渡すことも可能（テスト用など）:
     ```python
     from kabusys.data import jquants_client as jq
     token = jq.get_id_token()  # settings から自動取得
     pipeline.run_daily_etl(conn, id_token=token)
     ```

2. ニュース収集ジョブ
   ```python
   from kabusys.data import news_collector, schema

   conn = schema.get_connection('data/kabusys.duckdb')
   results = news_collector.run_news_collection(conn, known_codes={'7203','6758'})
   print(results)  # {source_name: 新規保存数}
   ```

3. カレンダーの夜間更新ジョブ（単体）
   ```python
   from kabusys.data import calendar_management, schema

   conn = schema.get_connection('data/kabusys.duckdb')
   saved = calendar_management.calendar_update_job(conn)
   print('saved', saved)
   ```

4. 監査ログ（発注→約定トレース）
   - 監査スキーマを有効にしたうえで、order_requests / executions テーブルへ挿入・更新を行います。
   - init_audit_schema(conn) を実行してテーブルとインデックスを作成します。

5. J-Quants API の直接操作（例）
   ```python
   from kabusys.data import jquants_client as jq

   # トークン取得（設定済みの JQUANTS_REFRESH_TOKEN を使う）
   id_token = jq.get_id_token()

   # 株価取得（ページネーション対応）
   records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
   ```

挙動上の注意点
--------------
- .env 読み込み順序: OS 環境 > .env.local > .env（.env.local は .env を上書き）
- 自動読み込みを無効にすると settings オブジェクトの必須キー取得で ValueError が出ます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用。
- J-Quants のレート制限（120 req/min）やリトライロジックは jquants_client に実装済みです。
- news_collector は RSS の受信サイズ上限やリダイレクト先のプライベートホスト対策を実装しています。
- DuckDB への保存は多くが ON CONFLICT（冪等）で行われます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
  - パッケージ初期化、バージョン情報
- config.py
  - 環境変数読み込みと Settings（J-Quants トークン、kabu API、Slack、DB パス、環境設定など）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py
    - RSS ニュース取得・前処理・DB保存ロジック（SSRF 対策、defusedxml）
  - schema.py
    - DuckDB スキーマ定義と init_schema / get_connection
  - pipeline.py
    - ETL パイプライン（差分取得、バックフィル、品質チェック）
  - calendar_management.py
    - マーケットカレンダー管理（営業日判定、更新ジョブ）
  - audit.py
    - 監査ログスキーマ（signal_events, order_requests, executions）
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py
  - （戦略ロジックを配置する想定）
- execution/
  - __init__.py
  - （発注/ブローカー連携ロジックを配置する想定）
- monitoring/
  - __init__.py
  - （監視・メトリクス関連を配置する想定）

拡張・運用のヒント
------------------
- ETL は cron / Airflow / Prefect 等で日次スケジュール実行することを想定しています。run_daily_etl の戻り値（ETLResult）を監査ログや Slack 通知に活用してください。
- production（live）環境では KABUSYS_ENV=live を設定し、ログレベルやモードに応じた挙動分岐を導入できます。
- 監査ログは削除せず永続化する設計です。order_request_id を冪等キーとして再送対策を行ってください。
- テストでは id_token の注入や KABUSYS_DISABLE_AUTO_ENV_LOAD の利用、news_collector._urlopen のモックなどが有用です。

ライセンス / 貢献
-----------------
（このリポジトリに適用するライセンスや貢献ガイドラインをここに記載してください）

お問い合わせ
------------
実装の意図や使い方、拡張について不明点があれば README に追記したいので、目的や想定シナリオを教えてください。