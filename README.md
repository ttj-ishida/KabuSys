KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API や RSS フィードからデータを収集し、DuckDB に保存・品質チェックを行う ETL パイプラインや、監査ログ用スキーマ・カレンダー管理・ニュース収集等の機能を提供します。

バージョン
---------
0.1.0

概要
----
KabuSys は、J-Quants 等の外部データソースから日本株データ（株価日足、財務情報、JPX カレンダー）やニュースを収集し、DuckDB に保存して整備するためのライブラリ群です。ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集、監査ログスキーマなど、データプラットフォームに必要な基本機能を備えています。戦略層・実行層・監視層のためのパッケージ枠も用意されています。

主な機能
--------
- 環境設定管理
  - .env / .env.local および OS 環境変数の読み込み（自動ロード、無効化オプションあり）
  - 必須環境変数の明示的取得（settings オブジェクト）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得
  - レート制限（120 req/min）・リトライ（指数バックオフ）・トークン自動更新対応
  - DuckDB への冪等保存（ON CONFLICT で更新）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブルを定義・作成
  - インデックスや外部キーを含むスキーマを冪等に初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日に基づく差分 + バックフィル）
  - 日次 ETL エントリ run_daily_etl（カレンダー→価格→財務→品質チェック）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等
  - 夜間バッチでのカレンダー差分更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - URL 正規化・記事 ID（SHA-256 の先頭32文字）生成
  - SSRF/サイズ上限対策（gzip 解凍後サイズ検査等）
  - DuckDB への冪等保存（INSERT ... RETURNING）
  - テキストから銘柄コード抽出と紐付け
- 品質チェック（kabusys.data.quality）
  - 欠損データ・スパイク検出・重複・日付不整合などのチェック
  - QualityIssue オブジェクトで結果を返す
- 監査ログスキーマ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用テーブル群
  - UTC タイムゾーン固定・冪等初期化

動作環境（推奨）
----------------
- Python 3.10 以上（PEP 604 の | 型注釈を使用）
- 依存パッケージ（最低限）
  - duckdb
  - defusedxml

セットアップ手順
----------------

1. リポジトリをクローン／ワークツリーへ移動して仮想環境を作成・有効化します（例: venv）。
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストールします（例）:
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください。）

3. 環境変数を設定します。
   - プロジェクトルートに .env（および必要なら .env.local）を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定します。

必須環境変数（例）
------------------
以下は Settings クラスで必須とされる変数です。実稼働前に .env に設定してください。

- JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
- KABU_API_PASSWORD      （kabu API のパスワード）
- SLACK_BOT_TOKEN        （Slack 通知用 Bot トークン）
- SLACK_CHANNEL_ID       （Slack 通知先チャンネル ID）

任意設定（デフォルトあり）
- KABU_API_BASE_URL      （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH            （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            （デフォルト: data/monitoring.db）
- KABUSYS_ENV            （development / paper_trading / live、デフォルト development）
- LOG_LEVEL              （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

.env の自動読み込み
-------------------
- 自動ロード順は OS 環境 > .env.local > .env です。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動ロードを無効化できます（テスト用）。

使い方（簡易例）
---------------

以下は主要な利用例です。ライブラリを直接インポートして使用します。

- DuckDB スキーマ初期化
  - from kabusys.data import schema
  - conn = schema.init_schema("data/kabusys.duckdb")

- 監査ログ用 DB 初期化（独立 DB にする場合）
  - from kabusys.data import audit
  - audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェックをまとめて実行）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定して任意日を処理可能
  - print(result.to_dict())

- ニュース収集ジョブ
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  - print(results)  # {source_name: 新規保存数}

- J-Quants の ID トークン取得・直接データ取得
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # settings.jquants_refresh_token を使う
  - records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  - jq.save_daily_quotes(conn, records)

- カレンダー判定ユーティリティ
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day
  - is_trading = is_trading_day(conn, some_date)
  - next_td = next_trading_day(conn, some_date)

ログとエラーハンドリング
------------------------
- 各モジュールは logging を利用して情報・警告・エラーを出力します。LOG_LEVEL で出力レベルを制御してください。
- jquants_client はレート制限・リトライを組み込んでいますが、最終的に例外が発生する場合は呼び出し元で捕捉してください。
- ETL は各ステップ毎にエラーハンドリングを行い、ETLResult.errors に概要を追加して処理を継続する設計です。

ディレクトリ構成
----------------
（プロジェクトの主要ファイル一覧 / 概略）
- src/kabusys/
  - __init__.py            - パッケージ定義（__version__ 等）
  - config.py              - 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py    - J-Quants API クライアント（取得・保存）
    - news_collector.py    - RSS 取得・記事抽出・保存
    - schema.py            - DuckDB スキーマ定義・初期化
    - pipeline.py          - ETL パイプライン（run_daily_etl 等）
    - calendar_management.py - マーケットカレンダー管理・更新ジョブ
    - audit.py             - 監査ログスキーマ初期化
    - quality.py           - データ品質チェック
  - strategy/
    - __init__.py          - 戦略層のパッケージ枠（拡張ポイント）
  - execution/
    - __init__.py          - 発注/約定管理のパッケージ枠（拡張ポイント）
  - monitoring/
    - __init__.py          - 監視/メトリクス用パッケージ枠（拡張ポイント）

設計上の注意点
--------------
- DuckDB のテーブル作成は冪等（IF NOT EXISTS）で行われます。初回は schema.init_schema() を必ず実行してください。
- jquants_client は 120 req/min の制限を守るため固定間隔のレートリミッタを使用しています。バッチ処理やループで多数のリクエストを行う場合に注意してください。
- ニュース収集では SSRF や XML 関連の攻撃対策を実装していますが、外部 URL を扱う際は環境・権限に応じて追加の制約を推奨します。
- Settings は環境変数に依存します。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを抑制すると便利です。

開発・拡張
-----------
- strategy / execution / monitoring ディレクトリは拡張用に用意されています。戦略実装・実際のブローカ API 連携・監視アラート連携などをここに実装してください。
- テストを書く際は settings の自動ロードを無効化し（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、必要な環境値をモックしてください。
- news_collector._urlopen や jquants_client の HTTP 呼び出しはモック可能な設計になっています（テスト容易性を考慮）。

ライセンス
---------
（ライセンス情報が明示されていないため、プロジェクトに合わせて追加してください）

問い合わせ / 貢献
-----------------
バグ報告や改善提案、プルリクエストはリポジトリの issue / PR で受け付けてください。

---

必要であれば、この README に「.env.example」の具体的なテンプレート例や、より詳しい使用例（スクリプトや cron / バッチの例）、データベースに保存されるテーブルのカラム説明などを追加します。どの情報を追記しましょうか？