# KabuSys

日本株の自動売買プラットフォーム向けユーティリティ群とデータ基盤ライブラリ。  
J-Quants API からのマーケットデータ取得、DuckDB スキーマ管理、監査ログ、データ品質チェックなど、ETL〜戦略実行に必要な基盤処理を提供します。

---

## 主な特徴（機能一覧）

- 環境変数／.env の自動読み込みと型安全な設定アクセス（kabusys.config）
  - プロジェクトルート（.git または pyproject.toml）基準で .env/.env.local を自動ロード
  - 必須変数は取得時に検査（未設定時はエラー）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロード無効化可能

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）を守る固定間隔レートリミッタ
  - リトライ（指数バックオフ、最大 3 回）、429 の Retry-After 優先
  - 401 を検知したらリフレッシュトークンで自動的に ID トークン更新して 1 回リトライ
  - 取得時刻（UTC）を記録し、Look-ahead バイアスに配慮
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層からなる包括的なスキーマ定義
  - テーブル作成・インデックス作成を行う init_schema()、既存 DB への接続取得 get_connection()
  - 監査ログ用スキーマ初期化（kabusys.data.audit.init_audit_schema / init_audit_db）

- 監査ログ（kabusys.data.audit）
  - シグナル→発注要求→約定 まで UUID 連鎖によるトレーサビリティテーブル
  - 発注要求は冪等キー（order_request_id）を持ち再送を防止
  - TIMESTAMP は UTC 保存（init_* は SET TimeZone='UTC' を実行）

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC の NULL）、主キー重複、スパイク（前日比閾値）、将来日付・非営業日データ等を検出
  - 各チェックは QualityIssue のリストを返す（Fail-Fast せず全件収集）
  - run_all_checks() で一括実行可能

---

## 前提 / 必要環境

- Python 3.10 以上（| 型注釈を使用）
- 必要な Python パッケージ例:
  - duckdb
- ネットワーク接続（J-Quants API、kabuステーション 等）
- 各種外部サービスの認証情報（J-Quants, kabu API, Slack 等）

必要パッケージはプロジェクトの requirements.txt / pyproject.toml に合わせてインストールしてください。最低限は:
```
pip install duckdb
```

（本リポジトリに packaging 情報があれば pip install -e . などでインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成することで自動読み込みされます。
   - サンプル（.env.example）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

     # kabuステーション API
     KABU_API_PASSWORD=your_kabu_api_password_here
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack（通知用）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

     # DB パス等（オプション）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで次を実行:
     ```python
     from kabusys.data.schema import init_schema, get_connection
     conn = init_schema("data/kabusys.duckdb")
     # 監査ログだけ別 DB にする場合
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（代表的な API と例）

- J-Quants の ID トークン取得
  ```python
  from kabusys.data.jquants_client import get_id_token
  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- 日次株価の取得と DuckDB への保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
  saved = save_daily_quotes(conn, records)
  print(f"Saved {saved} rows")
  ```

- 財務データ取得・保存
  ```python
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements

  recs = fetch_financial_statements(code="7203")
  saved = save_financial_statements(conn, recs)
  ```

- マーケットカレンダー取得・保存
  ```python
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
  cal = fetch_market_calendar()
  save_market_calendar(conn, cal)
  ```

- 監査スキーマを既存の接続に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)  # conn は init_schema の戻り値
  ```

- データ品質チェックの実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.table, issue.severity, issue.detail)
  ```

---

## 環境変数（主なキー）

- J-Quants / kabu / Slack 等、必須のキー:
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- オプション／デフォルト:
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env ロードを無効化）

注意: Settings クラスは必須変数が未設定だと ValueError を送出します。

---

## ディレクトリ構成

（コードベースに含まれる主要ファイル）

- src/
  - kabusys/
    - __init__.py            - パッケージ定義（__version__ 等）
    - config.py              - 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py    - J-Quants API クライアント（取得・保存ロジック）
      - schema.py           - DuckDB スキーマ定義・初期化
      - audit.py            - 監査ログテーブル定義・初期化
      - quality.py          - データ品質チェック
      - (その他: news/audit など拡張可能)
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

説明:
- data/ 以下がデータ取得・永続化・品質管理・監査に関する中核モジュール群です。
- strategy/・execution/・monitoring/ は将来の戦略実装・発注実行監視等を置くための名前空間です。

---

## 注意事項 / 設計上のポイント

- J-Quants API はレート制限と認証トークン更新に対する配慮が組み込まれていますが、実運用ではさらに堅牢な監視やメトリクス、例外ハンドリングを追加してください。
- DuckDB スキーマは冪等設計（CREATE IF NOT EXISTS / ON CONFLICT）になっています。既存データの取り扱いには注意してください。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。運用時のデータ保持方針を明確にしてください。
- 全ての TIMESTAMP は UTC を基本としています（監査スキーマ初期化で SET TimeZone='UTC' を実行）。

---

README はプロジェクトの概要を簡潔に示すためのものであり、実際の運用時には CI、環境毎の設定、シークレット管理（Vault 等）、ログ集約、監視アラート設計を別途整備してください。必要であれば、利用例や API リファレンスの追加版 README を作成します。