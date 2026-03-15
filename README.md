# KabuSys

日本株自動売買システム用ライブラリ（ライブラリ的コンポーネント群）

このリポジトリは、日本株のデータ取得、データベーススキーマ、監査ログ、戦略・実行・モニタリングの基盤を提供する Python パッケージです。実際の売買ロジックやブローカー接続は別途組み合わせて使用します。

主な設計方針：
- J-Quants API からのデータ取得（OHLCV / 財務 / マーケットカレンダー）
- DuckDB を用いた三層データレイヤ（Raw / Processed / Feature）と実行・監査レイヤ
- API レート制限・リトライ・トークン自動更新など堅牢な HTTP レイヤ
- 監査ログ（signal → order_request → execution のトレーサビリティ）を確保

---

## 機能一覧

- 環境変数・設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出ベース）
  - 必須環境変数のチェック、環境種別判定（development / paper_trading / live）など

- データ取得（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得：
    - 日足（OHLCV）：fetch_daily_quotes()
    - 財務データ（四半期 BS/PL）：fetch_financial_statements()
    - JPX マーケットカレンダー：fetch_market_calendar()
  - レート制限（120 req/min）を守る RateLimiter 実装
  - 冪等保存（DuckDB への ON CONFLICT DO UPDATE）：
    - save_daily_quotes()
    - save_financial_statements()
    - save_market_calendar()
  - トークン自動リフレッシュ、リトライ、Look-ahead Bias 防止の fetched_at 記録

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit に対応するテーブル定義とインデックス
  - init_schema(db_path) でスキーマ初期化、get_connection() で接続取得

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルを提供
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化
  - 監査のための各種制約・インデックス、UTC タイムスタンプ運用

- パッケージの名前空間
  - kabusys: data, strategy, execution, monitoring（各サブパッケージの雛形）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository_url>
   cd <repository_dir>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .\.venv\Scripts\activate     # Windows (PowerShell の場合)
   ```

3. 依存パッケージをインストール
   - このコードベースで直接参照している主な外部依存は `duckdb` のみです。実運用では Slack 通知やブローカー SDK（例: kabuステーション接続用）など追加の依存が必要になります。
   ```
   pip install duckdb
   ```
   - 開発用にローカルインストールする場合:
   ```
   pip install -e .
   ```
   （setup.py / pyproject.toml が存在する場合に有効）

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（`.env.local` は優先的に上書き）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（簡単な例）

- DuckDB スキーマの初期化：
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを作成してスキーマを初期化
  # またはインメモリ
  # conn = schema.init_schema(":memory:")
  ```

- J-Quants から日足を取得して保存：
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  from kabusys.data import schema
  import duckdb

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続(初回は init_schema を実行してください)

  # 取得（ID トークンは自動でキャッシュ・リフレッシュされます）
  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

  # 保存
  n = save_daily_quotes(conn, records)
  print(f"{n} レコードを保存しました")
  ```

- 財務データ / カレンダーの取得と保存は fetch_financial_statements / save_financial_statements / fetch_market_calendar / save_market_calendar を同様に使用できます。

- 監査ログ（audit）を初期化する：
  ```python
  from kabusys.data import schema
  from kabusys.data.audit import init_audit_schema

  conn = schema.get_connection("data/kabusys.duckdb")
  init_audit_schema(conn)  # 監査テーブルを追加初期化
  ```

- 監査用データベース単体で初期化する：
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

注意点：
- J-Quants API へのリクエストは内部でレート制御とリトライを行います（120 req/min、最大 3 回リトライ、401 時はトークンリフレッシュを試行）。
- DuckDB への保存は冪等的（ON CONFLICT DO UPDATE）に実装されているため、同じデータを上書きしても安全です。
- 取得時の fetched_at は UTC で記録され、Look-ahead Bias を防ぐために「いつデータが得られたか」をトレースできます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント（取得／保存）
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログスキーマ（signal / order_request / execution）
      - audit.py
      - other data modules...
    - strategy/
      - __init__.py            # 戦略層（雛形）
    - execution/
      - __init__.py            # 発注・ブローカーインタフェース（雛形）
    - monitoring/
      - __init__.py            # モニタリング（雛形）
- .env.example (プロジェクトルートに置く想定)
- pyproject.toml / setup.py (存在する場合はパッケージ化に利用)

---

## 参考 / 補足

- 環境変数の自動ロードは、パッケージ内部でプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。テストなどで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 実運用では、ブローカー（kabuステーション等）との接続モジュールや Slack 通知モジュールを実装し、戦略（strategy）でシグナルを生成、execution 層で発注・監査テーブルに記録するフローを作成してください。
- セキュリティ上の注意：API トークンやパスワードをリポジトリに含めないでください。`.env.local` を使ってローカル上で安全に保管してください。

---

必要であれば、README にサンプルワークフロー（データ取得 → 特徴量作成 → シグナル生成 → 発注 → 監査）や、よく使う SQL クエリ例、運用時の FAQ（バックアップ、マイグレーション、ロギング設定）なども追加できます。どの内容を優先して追加しますか？