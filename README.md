KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買プラットフォームのライブラリ群です。  
J-Quants や kabuステーション等からデータを取得し、DuckDB に保存・整形して、戦略層・発注層・監査層までをサポートすることを目的としています。  
設計上の主な特徴は冪等性（ON CONFLICT 処理）、データ品質チェック、API レート制限管理、堅牢な RSS ニュース収集（SSRF 対策、XML 攻撃対策）などです。

主な機能
--------
- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX市場カレンダー取得
  - レート制限（120 req/min）、リトライ（指数バックオフ）、401 自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution 層のテーブルを定義
  - インデックス・外部キー・制約を含む冪等な初期化
- ETL パイプライン
  - 差分取得（最終取得日からの差分）と backfill のサポート
  - カレンダー先読み、品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）
  - URL 正規化、トラッキングパラメータ除去、記事 ID を SHA-256 で生成して冪等保存
  - defusedxml による XML パースの安全化、SSRF 防止、最大受信サイズ制限
  - raw_news / news_symbols への保存機能（チャンク INSERT、TRANSACTION）
- 監査（Audit）テーブル群
  - signal / order_request / executions の監査テーブル、UUID によるトレーサビリティ
  - 発注の冪等キー（order_request_id）やタイムゾーン管理（UTC）
- データ品質モジュール
  - 欠損データ、主キー重複、スパイク検出、将来日付や非営業日の検出

セットアップ手順
--------------
前提
- Python 3.10 以上（型ヒントや一部構文に依存）
- DuckDB を利用します（Python パッケージ duckdb）
- defusedxml（RSS の安全なパース）

簡易インストール例:
1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb defusedxml

3. リポジトリをローカルに取得して editable インストール（あれば）
   - pip install -e .

環境変数 / .env
- 自動で .env / .env.local をプロジェクトルートから読み込みます（CWD に依存せず __file__ の親から .git または pyproject.toml を探索）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。
- 主要な環境変数（必須なものは Settings プロパティで取得時にチェックされます）:
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
  - KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN (必須) — Slack ボットトークン
  - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

使い方（基本例）
----------------

1) DuckDB スキーマ初期化
- まず DB を初期化して接続を取得します。

Python 例:
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# :memory: を渡すとインメモリ DB となります
# conn は duckdb.DuckDBPyConnection

2) 日次 ETL 実行
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())

- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックの順で処理し、ETLResult を返します。

3) ニュース収集ジョブ
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "6954"}  # 例: 有効銘柄コード集合
results = run_news_collection(conn, known_codes=known_codes)
# results は各 RSS ソースごとの新規保存件数を返します

4) J-Quants API の直接利用（データ取得のみ）
from kabusys.data import jquants_client as jq
from kabusys.config import settings

id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,2,1))

注意点・実装上のポイント
----------------------
- J-Quants クライアントは内部で固定間隔レートリミッタ（120 req/min）を実装しており、リクエスト間隔を自動調整します。
- HTTP エラーに対するリトライ（最大3回）や、429 の場合は Retry-After を優先して待機します。401 の場合はリフレッシュトークンから id_token を再取得して 1 回のみリトライします。
- DuckDB への保存は冪等性を保つため ON CONFLICT DO UPDATE / DO NOTHING を使用しています。
- news_collector は以下の安全対策を含みます:
  - defusedxml による安全な XML パース
  - HTTP リダイレクト先のスキーム検証およびプライベート/ループバックアドレスへの接続遮断（SSRF 対策）
  - レスポンスサイズ上限（デフォルト 10MB）によるメモリ DoS 対策
  - URL のトラッキングパラメータ除去と正規化により冪等性を担保（記事ID は正規化 URL の SHA-256 先頭32文字）
- ETL の差分取得は DB の最終取得日を参照して自動で date_from を計算します。backfill_days を指定することで過去分の再取得（後出し修正吸収）を行えます。
- settings.env の有効値は development / paper_trading / live です。不正な値は ValueError を投げます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py            - パッケージ初期化、バージョン定義
- config.py              - 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py    - J-Quants API クライアント（取得 + DuckDB 保存関数）
  - news_collector.py    - RSS ニュース収集・前処理・保存ロジック
  - schema.py            - DuckDB スキーマ定義・init_schema / get_connection
  - pipeline.py          - ETL パイプライン（差分取得、品質チェック統合）
  - audit.py             - 監査ログ（signal / order_request / executions）テーブルの初期化
  - quality.py           - データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py          - 戦略モジュール用プレースホルダ
- execution/
  - __init__.py          - 発注実行層用プレースホルダ
- monitoring/
  - __init__.py          - 監視・監督モジュール用プレースホルダ

設定ファイルの例（.env）
-----------------------
# .env の例
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

開発・拡張のヒント
-------------------
- モジュールの関数は id_token を引数で注入できる設計になっており、テスト時にトークンや HTTP 呼び出しを差し替えやすくなっています。
- news_collector._urlopen や他の内部関数はテスト用にモック差し替えがしやすく設計されています。
- DuckDB の接続は単一オブジェクトを共有して使う想定です。並列処理を行う場合はコネクション管理に注意してください。

ライセンス・貢献
----------------
（このリポジトリに LICENSE ファイルがある場合はそちらを参照してください。コントリビューションは通常 PR ベースで行ってください。）

問い合わせ
----------
問題報告や仕様の相談は issue を作成するか、プロジェクトのメンテナに問い合わせてください。

以上。必要であれば README にサンプルの .env.example、依存関係一覧（requirements.txt）や CI 実行手順、ユニットテストの実行例を追加できます。どの情報を追記しますか？