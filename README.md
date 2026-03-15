# KabuSys

日本株自動売買システムの基盤モジュール群です。  
データ取得（J-Quants）、データベーススキーマ（DuckDB）、監査ログ（発注〜約定のトレーサビリティ）、設定管理など、アルゴリズム取引プラットフォームのコア機能を提供します。

---

## 主な特徴

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - ページネーション対応
  - レート制限（120 req/min）を固定間隔スロットリングで厳守
  - リトライ（指数バックオフ、最大 3 回）、401 時は自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を回避
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理
  - 3 層（Raw / Processed / Feature）＋ Execution 層のテーブル定義
  - 頻出クエリ向けインデックス定義
  - Schema 初期化 API（init_schema, get_connection）

- 監査ログ（audit）
  - シグナル→発注要求→約定のトレーサビリティを保持
  - order_request_id による冪等性、すべて UTC で記録
  - audit 専用初期化 API（init_audit_schema / init_audit_db）

- 環境変数・設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - 必須・任意設定を集約した Settings オブジェクト
  - 環境（development / paper_trading / live）とログレベル検証

---

## 要件

- Python 3.10+
- duckdb
- （ネットワーク経由での実行時）インターネット接続
- J-Quants API のリフレッシュトークン、kabuステーション API などの外部資格情報

依存パッケージはプロジェクト側で requirements.txt や pyproject.toml に記載してください。最低限は duckdb が必須です。

---

## セットアップ

1. リポジトリをクローン（またはソースを配置）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. パッケージをインストール（開発用に編集可能インストール）
   ```
   pip install -e .
   pip install duckdb
   ```
   ※ pyproject.toml / requirements.txt があれば `pip install -r requirements.txt` を使用してください。

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml 配下）に `.env` または `.env.local` を置くと自動読み込みされます（既存 OS 環境変数は上書きされません）。`.env.local` は上書き優先で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例: .env（必須/推奨変数）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   # optional: KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development        # development / paper_trading / live
   LOG_LEVEL=INFO                 # DEBUG / INFO / WARNING / ERROR / CRITICAL
   ```

---

## 使い方（サンプル）

以下は主要 API の簡単な利用例です。実運用ではエラーハンドリングやログ設定、スケジューリング等を追加してください。

- 設定の取得
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.kabu_api_base_url)
  print(settings.is_paper)
  ```

- DuckDB スキーマ初期化
  ```python
  from kabusys.data.schema import init_schema, get_connection
  conn = init_schema("data/kabusys.duckdb")  # ファイルがなければ親ディレクトリを作成
  # または既存 DB に接続
  conn2 = get_connection("data/kabusys.duckdb")
  ```

- J-Quants から日次株価を取得して保存
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")

  # fetch
  records = fetch_daily_quotes(code="7203")  # 銘柄コード（省略可）
  # save (冪等: date+code の重複は更新)
  inserted = save_daily_quotes(conn, records)
  print(f"{inserted} 件保存/更新しました")
  ```

- 財務データやマーケットカレンダーの取得/保存も同様
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar

- audit スキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

設計上の注意点
- J-Quants クライアントは内部で ID トークンをキャッシュします。401 を受けた場合は一度だけ自動リフレッシュして再試行します。
- API 呼び出しは 120 req/min を超えないように固定間隔の RateLimiter が入っています。
- 取得データには fetched_at（UTC）を付与しており、データが「いつシステムに届いたか」を追跡できます。

---

## ディレクトリ構成

リポジトリ内の主要ファイルと役割（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、Settings クラス（J-Quants / kabu / Slack / DB パス / 環境判別）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック、レート制御、リトライ、トークン管理）
    - schema.py
      - DuckDB の DDL 定義（Raw / Processed / Feature / Execution 層）と init_schema/get_connection
    - audit.py
      - 監査ログテーブル（signal_events / order_requests / executions）と初期化関数
  - strategy/
    - __init__.py
    - （戦略ロジック用モジュールを配置）
  - execution/
    - __init__.py
    - （発注連携ロジックを配置）
  - monitoring/
    - __init__.py
    - （モニタリング・メトリクス関連）

README に掲載された API の実装ファイルは上記の通りです。実際の戦略や取引連携は strategy/ と execution/ に実装してください。

---

## 補足・運用上の注意

- 環境は必ず production（live）と paper_trading を分け、KABUSYS_ENV を適切に設定してください。settings.is_live / is_paper で判定できます。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われます。CI やテストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしてください。
- DuckDB のスキーマは冪等に作成されますが、データ移行やバックアップ方針は別途設計してください。
- 監査ログは削除しない前提（ON DELETE RESTRICT）で設計されています。履歴保存ポリシーを確立してください。

---

もし README に入れてほしい具体的な使い方（例: cron/airflow でのスケジューリング、kabu-station との接続例、Slack 通知の例など）があれば、追加のサンプルや手順を追記します。