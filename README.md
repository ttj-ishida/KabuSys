# KabuSys

日本株向けの自動売買プラットフォームのためのライブラリ群です。データ取得（J-Quants）、DuckDBスキーマ管理、監査ログ、設定管理など、自動売買システムを構築するための下地を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要な機能を持つモジュール群から成るパッケージです。

- J-Quants API からの市場データ（OHLCV・財務・マーケットカレンダー）取得
- 取得データの DuckDB への永続化とスキーマ管理（Raw / Processed / Feature / Execution 層）
- 発注・約定フローをトレースするための監査ログ（監査用スキーマ）
- 環境変数ベースの設定管理（.env 自動ロード機能を持つ）
- rate limiting / retry / token refresh 等を備えた堅牢な API クライアント設計

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を自動制御
- 401 受信時はリフレッシュトークンで id_token を自動更新して再試行
- データ取得タイミング（fetched_at）を UTC で記録し Look‑ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート判別）
  - 必須設定の取得 helper（Settings クラス）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - レート制御、リトライ、ページネーション対応、トークンキャッシュ

- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema(db_path)
  - get_connection(db_path)
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス

- 監査ログ（kabusys.data.audit）
  - init_audit_schema(conn)
  - init_audit_db(db_path)
  - signal_events / order_requests / executions と索引（監査トレース用）

- その他の名前空間（strategy, execution, monitoring）をプレースホルダとして用意

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントに Path | None 等を使用しているため）を推奨
- DuckDB を使用するため Python 用 duckdb パッケージが必要

1. リポジトリをクローン／配置

2. 開発インストール（任意）
   - pip を使う例:
     ```
     pip install -e .
     ```
   - 依存が minimal な場合:
     ```
     pip install duckdb
     ```

3. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（および必要に応じて `.env.local`）を作成します。
   - 必須のキー（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
     - （任意）KABUSYS_ENV (development | paper_trading | live)
     - （任意）LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - （任意）DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - （任意）SQLITE_PATH（デフォルト: data/monitoring.db）
   - .env のパースは次の点に対応:
     - `export KEY=val` 形式
     - シングル/ダブルクォート（エスケープ対応）
     - インラインコメント（スペース・タブ直前の `#` をコメントとして処理）

   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB 初期化（後述の手順を参照）

---

## 使い方（サンプル）

以下はよく使う操作の例です。実行前に .env を準備しておいてください。

- DuckDB スキーマを初期化して接続を取得する:
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返します
  ```

- J-Quants から日足データを取得して DuckDB に保存する:
  ```python
  from datetime import date
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)

  records = fetch_daily_quotes(
      code="7203",                       # 銘柄コード（省略で全銘柄）
      date_from=date(2023, 1, 1),
      date_to=date(2023, 12, 31),
  )

  inserted = save_daily_quotes(conn, records)
  print(f"保存されたレコード数: {inserted}")
  ```

- id_token を明示的に取得する:
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使って id_token を取得
  ```

- 監査ログスキーマの初期化（既存の DuckDB 接続に追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  init_audit_schema(conn)
  ```

- 監査ログ専用 DB を作る:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- Settings 利用例:
  ```python
  from kabusys.config import settings

  if settings.is_live:
      print("ライブ運用モードです")
  else:
      print("開発/ペーパーです")
  ```

注意点:
- J-Quants クライアントは内部で rate limiting（120 req/min）を行います。大量取得の際はページネーションと合わせて挙動に注意してください。
- API 呼び出しで 401 が返ると自動的にリフレッシュを試み、1 回だけリトライします（無限再帰を防止）。

---

## ディレクトリ構成

主要ファイル/モジュールの構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（取得・保存ロジック）
      - schema.py                    — DuckDB スキーマ定義・初期化
      - audit.py                     — 監査ログ（signal/order/execution）スキーマ
      - audit.py                     — 監査用 DB 初期化ユーティリティ
      - ...（将来のデータ関連モジュール）
    - strategy/
      - __init__.py                  — 戦略関連（プレースホルダ）
    - execution/
      - __init__.py                  — 発注実行関連（プレースホルダ）
    - monitoring/
      - __init__.py                  — 監視・メトリクス（プレースホルダ）

主なファイルの役割:
- config.py: .env 自動読み込み（プロジェクトルート判定）、Settings クラスで必須変数チェックと型変換
- data/schema.py: Raw → Processed → Feature → Execution 層のテーブル DDL とインデックスを定義
- data/jquants_client.py: API 呼び出しの共通実装（retry, backoff, rate limit, pagination, token refresh）と DuckDB 保存ヘルパ

---

## 環境変数一覧（代表例）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (オプション, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (オプション, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL, デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 をセットすると .env 自動ロードを無効化)

---

## 実装上の注意・運用上の注意

- DuckDB の初期化は init_schema() を一度呼ぶことを想定しています。既存 DB があれば DDL はスキップされるため安全に何度でも実行できます。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されています。監査データの改ざんや削除は避けてください。
- すべてのタイムスタンプは UTC を使用する設計です（監査スキーマ初期化時に TimeZone を UTC に設定）。
- J-Quants API の rate limit（120 req/min）を超えないように実装していますが、運用中は API レスポンスヘッダ（Retry-After 等）にも注意してください。
- .env のパースは比較的厳密です。クォートやコメントの扱いに注意してください。

---

## 参考・今後の拡張

- strategy/、execution/、monitoring/ はプレースホルダです。独自戦略や発注実装、監視ダッシュボードをここに実装していくことを想定しています。
- 将来的には Slack 通知、リスク管理モジュール、ポートフォリオ最適化、バックテスト機能などを統合できます。

---

ご不明な点や README に追加したい使用例（例: 発注ワークフロー、サンプル .env.example）などがあれば教えてください。必要に応じて具体的なコードスニペットや運用ベストプラクティスを追記します。