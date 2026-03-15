# KabuSys — 日本株自動売買システム

簡易説明（概要）
- KabuSys は日本株の自動売買プラットフォーム向けライブラリのコア部分です。
- データ取得（J-Quants）、データベーススキーマ（DuckDB）、監査ログ、設定管理、戦略／実行／モニタリングのための基盤を含みます。
- 本リポジトリはライブラリの内部モジュール実装（クライアント、スキーマ定義、設定ユーティリティ等）を提供します。

主な機能一覧
- 環境変数／設定読み込み
  - プロジェクトルートの .env / .env.local を自動ロード（OS 環境変数優先、.env.local は上書き）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
  - settings オブジェクトで型付きプロパティから取得可能（例：settings.jquants_refresh_token）
  - 有効な KABUSYS_ENV 値: development, paper_trading, live。LOG_LEVEL は標準的なレベルを検証。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）を固定間隔スロットリングで遵守
  - リトライ（指数バックオフ、最大 3 回。対象: 408/429/5xx）
  - 401 受信時にはリフレッシュトークンによる自動トークン更新を一度だけ実行して再試行
  - 取得時刻（fetched_at）を UTC で記録（Look-ahead Bias 対策）
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - インデックス、外部キー制約、チェック制約を含む堅牢なスキーマ
  - init_schema(db_path) で DB を初期化し接続を返却。get_connection() で既存 DB に接続。

- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions を含む監査テーブル群を定義
  - order_request_id を冪等キーにして二重発注防止
  - すべての TIMESTAMP を UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）
  - init_audit_schema(conn)／init_audit_db(db_path) を提供

- その他
  - モジュール構成により戦略・実行・監視機能の拡張が容易

対応環境・依存
- Python 3.10 以上（注: PEP 604 の | 型表記を使用）
- 必要な外部パッケージ（最低限）:
  - duckdb
- 標準ライブラリで HTTP は urllib を使用

セットアップ手順（ローカルで開発・実行する場合）
1. リポジトリをクローンし、作業ディレクトリへ移動
   - 例: git clone ... && cd your-repo

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install duckdb

   （将来的に requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数の準備
   - プロジェクトルートに .env を配置すると自動で読み込まれます（.env.local は上書き）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN        — Slack Bot トークン（必須）
     - SLACK_CHANNEL_ID       — Slack チャンネル ID（必須）
   - オプション:
     - KABUSYS_ENV            — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              — DEBUG/INFO/...（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動ロードを無効化

   サンプル .env（.env.example）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

使い方（基本的なコード例）
- 設定（settings）の参照
  ```python
  from kabusys.config import settings

  token = settings.jquants_refresh_token
  print("env:", settings.env)
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  # conn は duckdb.DuckDBPyConnection
  ```

- J-Quants データ取得と保存（株価日足の例）
  ```python
  from kabusys.data import jquants_client
  from kabusys.data import schema

  # DB 初期化/接続
  conn = schema.init_schema("data/kabusys.duckdb")

  # トークンは settings から自動取得される（必要に応じて自動リフレッシュあり）
  records = jquants_client.fetch_daily_quotes(code="7203", date_from=None, date_to=None)

  # 保存（冪等）
  inserted = jquants_client.save_daily_quotes(conn, records)
  print(f"saved {inserted} rows")
  ```

- 財務データ・カレンダーの取得/保存は fetch_financial_statements / save_financial_statements、
  fetch_market_calendar / save_market_calendar を使用します。

- id_token の明示取得（必要な場面があれば）
  ```python
  from kabusys.data import jquants_client
  id_token = jquants_client.get_id_token()  # settings.jquants_refresh_token を利用
  ```

- 監査ログの初期化
  ```python
  from kabusys.data import audit
  from kabusys.data import schema

  conn = schema.init_schema("data/kabusys.duckdb")
  audit.init_audit_schema(conn)
  # または専用 DB を作る:
  # conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

設計上の注意点・挙動
- J-Quants API クライアントは最大 120 req/min を想定しており、モジュール内でスロットリングします。
- HTTP エラーやネットワークエラー発生時は指数バックオフのリトライを行います。401 は一度だけリフレッシュして再試行します。
- DuckDB 側の保存処理は ON CONFLICT DO UPDATE を用いて冪等に実装されています。重複保存や再実行に耐性があります。
- 監査テーブル（order_requests 等）は削除を前提としておらず、監査性を保つためレコードは基本的に削除されません。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py                (パッケージ定義、__version__)
    - config.py                  (環境変数・設定管理)
    - data/
      - __init__.py
      - jquants_client.py        (J-Quants API クライアント、取得・保存ロジック)
      - schema.py                (DuckDB スキーマ定義・初期化)
      - audit.py                 (監査ログテーブル定義・初期化)
      - audit.py
      - (その他: raw / processed / feature / execution に関連する DDL)
    - strategy/
      - __init__.py              (戦略関連モジュール用のパッケージ化ポイント)
    - execution/
      - __init__.py              (発注・ブローカー連携等のポイント)
    - monitoring/
      - __init__.py              (モニタリング関連のポイント)

開発・拡張のヒント
- strategy／execution／monitoring パッケージは拡張ポイントです。戦略の出力（signal_id）から order_requests を作成し、order_request_id をキーにしてブローカー送信・約定の監査を残す設計になっています。
- DuckDB のスキーマは DataPlatform.md / DataSchema.md に基づく3層構造（Raw / Processed / Feature）を前提にしています。必要に応じて SQL を追加してください。
- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して .env の自動ロードを無効化できます。

ライセンス・貢献
- 本リポジトリのライセンス情報はリポジトリルートにある LICENSE ファイルを参照してください（存在しない場合はプロジェクト方針に従って追加してください）。
- Pull Request・Issue を歓迎します。変更はユニットテストとドキュメントを添えて送ってください。

----------

その他、README に追加したい具体的な例（kabu ステーションとの連携、Slack 通知、サンプル戦略のテンプレートなど）があれば教えてください。必要に応じて README に追記します。