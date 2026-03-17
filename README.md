README
======

概要
----
KabuSys は日本株向けの自動売買プラットフォーム向けユーティリティ群です。  
主にデータ取得（J-Quants）、ニュース収集、DuckDB スキーマ定義・初期化、ETL パイプライン、データ品質チェック、監査ログ機能などの基盤機能を提供します。  
このリポジトリは戦略・発注・監視実装の土台として利用することを想定しています。

主な機能
--------
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーの取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 自動リフレッシュ対応
  - 取得時刻（UTC）を保存して Look-ahead バイアスを最小化
  - DuckDB への冪等保存（ON CONFLICT を利用）
- ニュース収集
  - RSS フィードから記事を取得して前処理（URL 除去・空白正規化）
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保
  - SSRF 対策（スキーム検証、プライベートIPブロック、リダイレクト検査）、受信サイズ制限、XML 攻撃対策（defusedxml）
  - DuckDB への一括挿入、記事と銘柄コード紐付け（news_symbols）
- DuckDB スキーマ
  - Raw / Processed / Feature / Execution 層のテーブル定義（多数の CHECK/PK/FK を含む）
  - 監査ログ（signal_events / order_requests / executions）用 DDL とインデックス
  - 初期化関数（init_schema / init_audit_schema / init_audit_db）
- ETL パイプライン
  - 差分取得（最終取得日から backfill を含めて再取得）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行してレポート
  - 各ステップは独立して例外をハンドル（1 ステップ失敗でも残り継続）
- データ品質チェック
  - 欠損（OHLC 欄）、スパイク（前日比の変動）、重複、日付不整合を検出
  - QualityIssue オブジェクトで情報を返却
- 設定管理
  - .env / .env.local / OS 環境変数から設定を自動読み込み（パッケージルートを探索）
  - 自動読み込み無効化のための KABUSYS_DISABLE_AUTO_ENV_LOAD

前提条件
--------
- Python 3.10+（型ヒントで | が使われているため）
- 依存パッケージ（例）
  - duckdb
  - defusedxml
  - （HTTP 標準ライブラリを利用しているため追加は最小限）
- J-Quants API のリフレッシュトークン、kabuステーション API パスワード等の環境変数が必要

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Unix)
   - .venv\Scripts\activate (Windows)

3. パッケージと依存をインストール
   - pip install -e .   （プロジェクトが setuptools/pyproject を持つ想定）
   - pip install duckdb defusedxml

4. 環境変数 (.env)
   - プロジェクトルートの .env または .env.local に必要な環境変数を設定します。
   - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

推奨される環境変数
------------------
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API のパスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須): Slack チャンネル ID
- DUCKDB_PATH (任意): DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (任意): DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

使い方（基本例）
----------------

1) DuckDB スキーマ初期化
- 新しい DB ファイルを作成してスキーマを初期化する例:

from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

- 監査ログテーブルを追加する:

from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)

2) 日次 ETL を実行する
- 基本的な日次 ETL:

from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
print(result.to_dict())

- ETLResult には取得件数・保存件数・品質問題・エラーメッセージ等が含まれます。

3) ニュース収集ジョブ
- RSS からニュースを取得して保存する例:

from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758"}  # 必要なら既知銘柄コードセットを渡す
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}

4) J-Quants API の直接呼び出し（テストやカスタム取得）
- ID トークン取得、株価取得例:

from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2023,1,1), date_to=date(2023,1,31))
print(len(records))

設計上の注意点
--------------
- J-Quants API クライアントはレート制御およびリトライを実装していますが、長時間の連続実行では利用制限に注意してください。
- fetch 系関数はページネーションに対応しています。ページネーション間で id_token を共有するためのキャッシュを内部で保持します。
- ニュース収集は SSRF・XML 攻撃・大きなレスポンスへの対策を含みます。テスト時に _urlopen をモックして外部アクセスを抑制できます。
- ETL の品質チェックは Fail-Fast ではなく問題を収集して戻す設計です。呼び出し側で結果を評価しアクションしてください。
- 環境変数の自動読み込みは package import 時にプロジェクトルート（.git または pyproject.toml）から .env/.env.local を読み込みます。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

開発・テストのヒント
--------------------
- 単体テストでは外部 HTTP コールをモック（例: kabusys.data.news_collector._urlopen, urllib の呼び出し）して実行するのがおすすめです。
- ETL のテストには DuckDB の ":memory:" 接続を使うとファイル IO を起こさずに実行できます。
- .env のパース実装は export プレフィックスや引用符、インラインコメントなどに対応しています。テストで自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

ディレクトリ構成
----------------
src/
  kabusys/
    __init__.py  -- パッケージ初期化、バージョン
    config.py    -- 環境変数・設定管理（自動 .env ロード含む）
    data/
      __init__.py
      jquants_client.py    -- J-Quants API クライアント、保存ユーティリティ
      news_collector.py    -- RSS 収集・前処理・保存ロジック
      schema.py            -- DuckDB スキーマ定義 / init_schema
      pipeline.py          -- ETL パイプラインとユーティリティ
      audit.py             -- 監査ログ（signal/order/executions）DDL と初期化
      quality.py           -- データ品質チェック
    strategy/
      __init__.py          -- 戦略層（拡張用）
    execution/
      __init__.py          -- 発注・実行管理（拡張用）
    monitoring/
      __init__.py          -- 監視・メトリクス（拡張用）

よくある質問（FAQ）
------------------
Q: .env の自動読み込みを無効にしたい
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしておくと自動読み込みをスキップします。

Q: DuckDB のスキーマを再作成したい
A: init_schema() は冪等（CREATE TABLE IF NOT EXISTS）なので既存のテーブルは保持されます。完全に再作成するには DB ファイルを削除して再実行してください。

Q: J-Quants のレート制限はどうなっていますか？
A: デフォルトで 120 req/min を守るように固定間隔の RateLimiter を実装しています。429 や 5xx に対して指数バックオフで再試行します。

サポート / 貢献
----------------
バグ報告や機能提案は issue を作成してください。プルリクエストは歓迎します。テストとドキュメントを追加のうえで送ってください。

おわりに
--------
この README はコードベースから抽出した主要な使い方と設計意図をまとめたものです。詳細や追加機能（戦略実装、発注連携、監視）は本パッケージを拡張して実装してください。