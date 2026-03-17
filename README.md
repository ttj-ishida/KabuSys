README
======

概要
----
KabuSys は日本株の自動売買・データプラットフォーム向けのライブラリ群です。本リポジトリはデータ取得、ETL、データ品質チェック、マーケットカレンダー管理、ニュース収集、および監査ログ（発注→約定のトレース）に関する主要コンポーネントを提供します。J-Quants API を用いて株価・財務・カレンダー情報を取得し、DuckDB に保存・管理することを前提とした設計になっています。

主な特徴
--------
- J-Quants API クライアント
  - 日足（OHLCV）、四半期決算データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）を守るスロットリング
  - リトライ（指数バックオフ、401 時はトークン自動リフレッシュ）
  - 取得時刻（fetched_at）を記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を収集し前処理（URL 除去・空白正規化）
  - URL 正規化 → SHA-256 ハッシュ（先頭32文字）で記事IDを生成し冪等性を担保
  - SSRF / XML Bomb / メモリDoS に対する各種防御
  - DuckDB に対するトランザクション単位での冪等保存・銘柄紐付け

- ETL パイプライン
  - 差分取得（最終取得日ベース）とバックフィル（デフォルト3日）対応
  - 市場カレンダーを先に取得して営業日調整
  - 品質チェック（欠損・重複・スパイク・日付不整合）を実装

- マーケットカレンダー管理
  - JPX カレンダーの差分更新バッチ
  - 営業日判定 / 前後営業日の取得 / 期間内の営業日取得などのユーティリティ

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution 層を想定したスキーマ定義
  - 監査ログ用テーブル（シグナル→発注要求→約定のトレース）を初期化可能

- 品質・安全設計
  - SQL はパラメータバインドを利用
  - ネットワーク・XML・ファイル系の脆弱性対策（defusedxml, SSRF 検査, レスポンスサイズ制限等）
  - 各種操作は冪等で設計

必要条件（推奨）
---------------
- Python 3.10 以上（PEP 604 の型記法（|）などを使用）
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス環境（J-Quants API へアクセス可能であること）

環境変数
--------
自動で .env/.env.local を読み込む仕組みがあります（プロジェクトルートは .git または pyproject.toml で判定）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（README用抜粋）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（本コードでは設定参照のみ）
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境 (development | paper_trading | live)
- LOG_LEVEL (任意) — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 環境を準備
   - Python 3.10+ 仮想環境を作成して有効化（venv / pyenv など）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用）

4. 環境変数を準備
   - プロジェクトルートに .env を作成（.env.example を参考に）
   - 例 (.env の抜粋):
     JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
     KABU_API_PASSWORD=あなたのkabuパスワード
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

   - 自動読み込みを無効にしたい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB スキーマの初期化
   - Python REPL またはワンライナーで初期化できます:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ（audit）テーブルを追加したい場合:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)

使い方（代表的な例）
------------------

- 日次 ETL の実行（株価・財務・カレンダー取得＋品質チェック）
  - 最小のワンライナー例:
    from kabusys.data.schema import init_schema
    from kabusys.data.pipeline import run_daily_etl
    conn = init_schema("data/kabusys.duckdb")
    result = run_daily_etl(conn)
    print(result.to_dict())

  - 引数で target_date / id_token / run_quality_checks などを制御可能。

- 市場カレンダーの夜間更新ジョブ
  from kabusys.data.schema import init_schema
  from kabusys.data.calendar_management import calendar_update_job
  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)

- ニュース収集の実行
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  # known_codes を渡すと記事と銘柄の紐付けを行う（例: set of "7203", ...）
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=None)
  print(results)

- J-Quants の ID トークン取得
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()

- DuckDB へ直接アクセスしてクエリ実行
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  rows = conn.execute("SELECT date, code, close FROM raw_prices LIMIT 10").fetchall()

設計上の注意点 / 運用メモ
-----------------------
- レート制限:
  - J-Quants API は 120 req/min を想定。jquants_client 内で固定間隔スロットリングを実装しています。外部から大量リクエストを投げないでください。

- 冪等性:
  - データ保存時は ON CONFLICT DO UPDATE / DO NOTHING を利用しており、再実行しても重複や二重挿入を防ぎます。

- セキュリティ:
  - RSS 取得では SSRF 対策（リダイレクト先の検査、内部アドレス拒否）、XML パースでは defusedxml を使用、レスポンスサイズ制限などの防御を実装しています。

- テスト可能性:
  - jquants_client のトークンはモジュールキャッシュに格納されますが、関数に id_token を注入できるためテストしやすくなっています。
  - news_collector の _urlopen はテスト時にモックできるように設計されています。

ディレクトリ構成
----------------
- src/
  - kabusys/
    - __init__.py
    - config.py                  -- 環境変数・設定管理（.env 自動ロード含む）
    - data/
      - __init__.py
      - jquants_client.py        -- J-Quants API クライアント（取得・保存機能）
      - news_collector.py        -- RSS ニュース収集・前処理・保存
      - schema.py                -- DuckDB スキーマ定義・初期化
      - pipeline.py              -- ETL パイプライン（差分取得・品質チェック）
      - calendar_management.py   -- マーケットカレンダー管理・ユーティリティ
      - audit.py                 -- 監査ログ（シグナル→発注→約定のトレース）
      - quality.py               -- データ品質チェック
    - strategy/
      - __init__.py              -- 戦略層（将来的な拡張ポイント）
    - execution/
      - __init__.py              -- 発注/約定管理（将来的な拡張ポイント）
    - monitoring/
      - __init__.py              -- 監視関連（将来的な拡張ポイント）

付録：よくある操作コマンド（例）
--------------------------------
- 開発用仮想環境作成（Unix 系）
  python -m venv .venv
  source .venv/bin/activate
  pip install -U pip
  pip install duckdb defusedxml
  pip install -e .

- DB 初期化（ワンライナー）
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- ETL 実行（ワンライナー）
  python -c "from kabusys.data.schema import init_schema; from kabusys.data.pipeline import run_daily_etl; c=init_schema('data/kabusys.duckdb'); print(run_daily_etl(c).to_dict())"

サポート / 貢献
----------------
バグ報告や機能提案は Issue にて受け付けてください。プルリクエスト歓迎です。設計方針やスキーマに関する議論が必要な場合は Issue に要旨を書いてください。

ライセンス
----------
（ライセンス情報がプロジェクトに含まれている場合はここに記載してください。README にはライセンスの明記を推奨します。）

--- 

必要に応じて README を拡張します。例えば、実際の .env.example、requirements.txt、サンプルジョブの systemd/cron 設定、Dockerfile、CI ワークフローなどを追加できます。どれを追加しますか？