# KabuSys

日本株向けの自動売買プラットフォームのコアライブラリ（プロトタイプ）です。  
データ収集、データスキーマ、監査ログ、J-Quants API クライアントなど、戦略実装・発注基盤のための基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群を含んでいます。

- J-Quants API からの市場データ・財務データ・マーケットカレンダーの取得
- 取得データの DuckDB への永続化（冪等性を考慮）
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution レイヤ）
- 監査ログ（シグナル → 発注 → 約定 のトレースを可能にする監査テーブル）
- 環境変数ベースの設定管理（.env 自動ロード機能）

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を守るスロットリング実装
- リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- 取得時刻（fetched_at）を UTC で記録し Look-ahead bias を抑制
- DuckDB への INSERT は ON CONFLICT DO UPDATE により冪等性を担保

---

## 主な機能一覧

- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - get_id_token（リフレッシュトークンから id_token 取得）
  - rate limiter / retry / token refresh を内蔵
  - DuckDB へ保存する save_* 関数（save_daily_quotes 等）

- DuckDB スキーマ管理
  - data.schema.init_schema(db_path) で全テーブル・インデックスを作成
  - get_connection(db_path) で既存 DB に接続
  - テーブルは Raw / Processed / Feature / Execution 層で整理

- 監査ログ（audit）
  - signal_events, order_requests, executions テーブルとインデックス
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化
  - order_request_id を冪等キーとして二重発注防止を想定

- 設定管理
  - 環境変数（.env / .env.local 自動読み込み）
  - settings オブジェクトで主要設定を参照可能

---

## 要件

- Python 3.10+
  - コードで PEP 604（| 型）などを使用しているため 3.10 以上を想定しています
- duckdb Python パッケージ
- 標準ライブラリ（urllib 等）

（プロジェクト配布時に requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン（例）

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 開発/インストール（ソース直下に `src/` 構成がある前提）

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb
   pip install -e .
   ```

   - パッケージ化されていない場合は最低限 `duckdb` をインストールしてお使いください。

3. 環境変数を設定
   - プロジェクトルートに `.env`（および開発用に `.env.local`）を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

   必須の環境変数（最低限設定が必要）:
   - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD - kabuステーション API のパスワード（発注統合がある場合）
   - SLACK_BOT_TOKEN - Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID - Slack チャンネル ID

   任意・デフォルト値あり:
   - KABU_API_BASE_URL - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV - environment（development / paper_trading / live） デフォルト: development
   - LOG_LEVEL - ログレベル（DEBUG/INFO/...）デフォルト: INFO

   例 .env の最小例:

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB スキーマ初期化（例）

   Python REPL またはスクリプトで:

   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   # conn は duckdb の接続オブジェクト
   ```

   監査ログを追加する場合（既存接続に対して）:

   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)
   ```

---

## 使い方（基本例）

- J-Quants から日足を取得して DuckDB に保存する簡単な例:

  ```python
  from kabusys.config import settings
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema

  conn = init_schema(settings.duckdb_path)

  # 単一銘柄 or 全銘柄
  records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
  saved = save_daily_quotes(conn, records)
  print(f"{saved} 件保存しました")
  ```

- 財務データ取得 / 保存：

  ```python
  from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements

  records = fetch_financial_statements(code="7203")
  saved = save_financial_statements(conn, records)
  ```

- マーケットカレンダー取得 / 保存：

  ```python
  from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

  records = fetch_market_calendar()
  saved = save_market_calendar(conn, records)
  ```

- id_token を直接取得する（必要に応じて）:

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

注意:
- fetch_* 系関数は内部でレート制御・リトライ・トークンリフレッシュを行います。
- save_* 系関数は冪等で、重複行は UPDATE によって上書きされます。
- すべてのタイムスタンプは UTC ベースで記録されます（監査ログモジュールは明示的に TimeZone='UTC' を設定）。

---

## 監査ログ（audit）の利用

監査用テーブルは戦略から発注・約定までをトレースするためのテーブル群を提供します。初期化は以下を実行します。

- 既存の DuckDB 接続に追加する:

  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

- 監査専用 DB を作る場合:

  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

設計上の特徴:
- order_request_id を冪等キーにして二重発注を防止
- executions テーブルは broker_execution_id をユニークにして約定の重複を防止
- すべての TIMESTAMP は UTC として保持

---

## ディレクトリ構成

（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境設定・.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得＋保存）
    - schema.py              -- DuckDB スキーマ定義・初期化
    - audit.py               -- 監査ログ用スキーマ
    - audit.py               -- 監査ログ用スキーマ（重複記載ここは概要）
    - (その他データ関連モジュール)
  - strategy/
    - __init__.py            -- 戦略モジュール空スケルトン
  - execution/
    - __init__.py            -- 発注・約定管理モジュール空スケルトン
  - monitoring/
    - __init__.py            -- 監視関連のエントリポイント
- pyproject.toml / setup.cfg   -- （存在する場合パッケージ情報）
- .env.example                 -- （プロジェクトルートに例がある想定）

---

## 注意事項 / 運用上のヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行います。CWD に依存しません。
- テスト等で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants のレート制限・レスポンスエラー（408/429/5xx）に対しては内部でリトライを行いますが、アプリケーションレベルでもエラーハンドリングを行ってください。
- DuckDB の初期化は冪等です。既存テーブルがあれば上書きせずスキップします。
- 監査ログは削除しない前提（FK は ON DELETE RESTRICT）で設計されています。履歴保持ポリシーを考慮してください。

---

## さらに進めるために

- 実際の戦略、ポートフォリオ管理、発注連携（kabu ステーション API 統合）を実装するモジュールを strategy / execution に追加してください。
- Slack 通知や監視ダッシュボード連携を monitoring モジュールに実装してください。
- 必要に応じて CI/CD、バックフィルスクリプト、ETL ジョブを追加してください。

---

問題や改善点、機能追加の要望があれば教えてください。README の内容をプロジェクトの実際の運用に合わせて調整できます。