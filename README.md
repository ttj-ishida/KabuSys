KabuSys
=======

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。  
J-Quants / RSS 等からのデータ取得、DuckDB を使ったスキーマ管理・ETL、ニュース収集、監査ログやカレンダー管理などの基盤機能を提供します。

概要
----
- 言語: Python（型アノテーション・ | 演算子を使用するため Python 3.10+ を想定）
- 目的: 市場データの取得・保存・品質チェック、ニュース収集、ETL パイプライン、監査ログの初期化などを行い、戦略層（strategy）や発注実装（execution）へデータを供給する。
- データ保存: DuckDB（単一ファイル / インメモリ）を想定

主な特徴（機能一覧）
------------------
- 環境設定管理
  - .env / .env.local から自動で環境変数を読み込む（プロジェクトルート検出）
  - 必須環境変数取得時のバリデーション（Settings オブジェクト）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、マーケットカレンダー取得
  - レートリミット、リトライ（指数バックオフ）、401 の自動トークンリフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）
  - RSS の取得・XML パース（defusedxml を利用）
  - URL 正規化、トラッキングパラメータ除去、記事ID は SHA-256（先頭32文字）
  - SSRF 対策（リダイレクト検査 / ホストがプライベートかチェック）
  - レスポンスサイズ上限・gzip 解凍チェック（DoS 対策）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO NOTHING / RETURNING）
  - 銘柄コード抽出（4桁数字、既知コードセットでフィルタ）
- ETL パイプライン
  - 差分取得（最終取得日 + バックフィル）、市場カレンダー先読み
  - run_daily_etl で一括処理（カレンダー → 株価 → 財務 → 品質チェック）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を収集して返す
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - init_schema(), get_connection() を提供
- 監査ログ（Audit）
  - signal / order_request / execution などの監査テーブル定義、初期化関数（init_audit_db / init_audit_schema）
  - UTC タイムゾーンの固定、冪等・トレーサビリティ設計
- カレンダー管理
  - 営業日判定、next/prev_trading_day、get_trading_days、calendar_update_job

セットアップ手順
----------------

1. Python 環境を用意
   - Python 3.10 以上を推奨

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクト化する場合は requirements.txt / pyproject.toml に依存を記載してください）

4. 環境変数の準備 (.env)
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数の例 (.env.example):

     JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     KABU_API_PASSWORD=<your_kabu_api_password>
     SLACK_BOT_TOKEN=<your_slack_bot_token>
     SLACK_CHANNEL_ID=<your_slack_channel_id>

   - 任意:
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
     - KABUS_API_BASE_URL=http://localhost:18080/kabusapi
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

5. データベース初期化
   - DuckDB スキーマを作成:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を作る:
     - from kabusys.data.audit import init_audit_db
     - audit_conn = init_audit_db("data/kabusys_audit.duckdb")

使い方（主要 API・サンプル）
---------------------------

- 設定オブジェクトの利用
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などで参照可能

- DuckDB スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema(settings.duckdb_path)

- 単体 API 呼び出し（J-Quants）
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # 必要に応じて refresh_token を渡せる
  - quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  - jq.save_daily_quotes(conn, quotes)

- 日次 ETL パイプライン実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定可能
  - result は ETLResult オブジェクト（取得数、保存数、品質問題、エラー等を含む）

- ニュース収集（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - results = run_news_collection(conn, sources=None, known_codes={"7203","6758"}) 
    - sources を省略すると組み込みの DEFAULT_RSS_SOURCES を使用
    - known_codes による銘柄紐付けを行う場合は銘柄コード集合を渡す

- カレンダー更新ジョブ（夜間バッチ用）
  - from kabusys.data.calendar_management import calendar_update_job
  - saved = calendar_update_job(conn)

- 監査ログ初期化（既存接続に追加）
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

- 品質チェックを個別に実行
  - from kabusys.data import quality
  - issues = quality.run_all_checks(conn, target_date=some_date)

サンプル: 最小 ETL の流れ（対話式）
- python -c "from kabusys.config import settings; from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; conn = init_schema(settings.duckdb_path); print(run_daily_etl(conn).to_dict())"

注意点 / 動作方針
-----------------
- 環境変数は .env/.env.local で自動ロードされますが、OS 環境変数が優先されます。.env.local は .env を上書きできます。
- J-Quants のレート制限（120 req/min）を守るため内部でスロットリングとリトライを行います。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で設計されています。
- ニュース収集は SSRF 対策・XML 安全パース・サイズ検査などを実装しています。
- 日付やタイムスタンプは可能な限り UTC で管理（監査モジュールは TimeZone を UTC に固定します）。

ディレクトリ構成
-----------------
（パッケージ内の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / Settings
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント、保存ロジック
      - news_collector.py      # RSS ニュース収集・保存・銘柄紐付け
      - schema.py              # DuckDB スキーマ定義 & 初期化
      - pipeline.py            # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py # マーケットカレンダー管理・クエリ
      - audit.py               # 監査ログ（signal/order/execution）初期化
      - quality.py             # データ品質チェック
    - strategy/                # 戦略モジュール（未実装領域：拡張用）
      - __init__.py
    - execution/               # 発注・ブローカー連携（未実装領域）
      - __init__.py
    - monitoring/              # 監視関連（未実装領域）
      - __init__.py

拡張・開発メモ
--------------
- strategy/ と execution/、monitoring/ はフレームワーク用の名前空間として用意されています。各プロジェクトで個別の戦略やブローカー実装を追加してください。
- テスト時に環境ロードを抑制するには、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のインメモリ DB を用いてユニットテストを行う場合は db_path に ":memory:" を渡してください。

ライセンス・貢献
----------------
- 本リポジトリに合わせてライセンス・貢献ルールを設定してください（このサンプルには記載がありません）。

フィードバック / 問い合わせ
-------------------------
- 実装や API 追加の提案がある場合は issue を作成してください。README にない使い方や動作想定が必要であれば追記します。

以上で README.md の概要を示しました。必要に応じて、セットアップ手順の詳細（CI、requirements.txt、例外処理ポリシーなど）を追加できます。どの部分を重点的に詳述しましょうか？