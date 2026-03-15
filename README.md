# KabuSys

日本株向け自動売買プラットフォーム（ライブラリ）です。  
データ取得、スキーマ管理、監査ログ、戦略・実行・モニタリングの各レイヤーを想定した構成になっています。本リポジトリはそのコア部分（主にデータ周りと設定）を実装しています。

---

## 概要

KabuSys は以下の目的で設計されたコンポーネント群を提供します。

- J-Quants API からの市場データ（株価日足・財務データ・マーケットカレンダーなど）の取得と DuckDB への保存
- DuckDB のスキーマ定義（Raw / Processed / Feature / Execution レイヤ）と初期化
- 監査ログ（signal → order_request → execution のトレース）用スキーマと初期化
- 環境変数／設定の管理（.env 自動ロード、必須値チェック）
- 将来的な戦略・発注・モニタリング用のパッケージ領域（strategy, execution, monitoring）

設計上のポイント：
- J-Quants API のレート制限（120 req/min）を遵守する固定間隔レートリミッター
- リトライ（指数バックオフ）、401 の場合は自動トークンリフレッシュ
- データ取得時に fetched_at を UTC で記録し、Look-ahead Bias を防止
- DuckDB への挿入は冪等（ON CONFLICT DO UPDATE）で実装
- 監査ログは削除しない運用を前提（FK は ON DELETE RESTRICT）

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ヘルパー
  - KABUSYS_ENV / LOG_LEVEL 等の検証ロジック
- データ取得（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes）
  - 財務データ（fetch_financial_statements）
  - マーケットカレンダー（fetch_market_calendar）
  - 認証トークンの取得・キャッシュ（get_id_token）
  - レートリミッタ・リトライ処理内蔵
- データ永続化（kabusys.data.jquants_client）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）
  - 保存時に fetched_at を付与して冪等に挿入
- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤの DDL を定義
  - init_schema(db_path) による初期化（テーブル・インデックス作成、親ディレクトリ自動生成）
  - get_connection(db_path) で既存 DB に接続
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の DDL とインデックス定義
  - init_audit_schema(conn) / init_audit_db(db_path) による初期化
- 将来的な拡張用パッケージ
  - strategy, execution, monitoring（現状はパッケージプレースホルダ）

---

## 要件

- Python 3.10+
- 依存パッケージ（必須）
  - duckdb

（その他の外部 API 呼び出しは標準ライブラリ urllib を使用しています）

---

## セットアップ手順

1. リポジトリをクローン/取得する

   git clone <repository-url>

2. 仮想環境の作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージのインストール

   pip install duckdb

   （パッケージとしてインストールしたい場合は setup/pyproject を整備後、pip install -e .）

4. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨される .env の最小例:

   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack（モニタリング用）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # データベース
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   必須項目（実行に必ず必要になる可能性のある環境変数）：
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   注意: Settings クラスは KABUSYS_ENV の値が "development", "paper_trading", "live" のいずれかであることを期待します。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかである必要があります。

---

## 使い方（簡単な例）

以下は J-Quants から日足を取得して DuckDB に保存する最小のフロー例です。

1. スキーマ初期化（1回のみ）

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

2. データ取得と保存

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 全銘柄・全期間を取得する例（必要に応じて code, date_from, date_to を指定）
records = fetch_daily_quotes()
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

3. 監査ログテーブルを追加する（必要に応じて）

```python
from kabusys.data import audit
audit.init_audit_schema(conn)
```

4. トークンを明示的に取得したい場合

```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

補足：
- fetch_* 系は内部でレートリミッタ・リトライ・401 の自動リフレッシュを行います。
- save_* 系は ON CONFLICT DO UPDATE を使って冪等に保存します。
- fetched_at は UTC の ISO8601（Z）で保存されます。

---

## 環境設定（Settings API）

kabusys.config.Settings で以下のプロパティが提供されています。アプリケーションコードからは以下のように参照します。

```python
from kabusys.config import settings
token = settings.jquants_refresh_token
duckdb_path = settings.duckdb_path
is_live = settings.is_live
```

主なプロパティ一覧：
- jquants_refresh_token: J-Quants のリフレッシュトークン（必須）
- kabu_api_password: kabuステーション API のパスワード（必須）
- kabu_api_base_url: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token, slack_channel_id: Slack 通知用（必須）
- duckdb_path: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- sqlite_path: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- env: KABUSYS_ENV（development / paper_trading / live）
- log_level: LOG_LEVEL（DEBUG 等）
- is_live / is_paper / is_dev: env の便捷判定

---

## ディレクトリ構成

リポジトリ中の主要ファイル・ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得・保存ロジック）
      - schema.py                # DuckDB スキーマ定義・初期化
      - audit.py                 # 監査ログ（signal/order_request/execution）スキーマ
      - audit.py
      - ...（将来のモジュール）
    - strategy/
      - __init__.py              # 戦略モジュール（プレースホルダ）
    - execution/
      - __init__.py              # 発注実行モジュール（プレースホルダ）
    - monitoring/
      - __init__.py              # モニタリング（プレースホルダ）

主なソース:
- src/kabusys/config.py
- src/kabusys/data/jquants_client.py
- src/kabusys/data/schema.py
- src/kabusys/data/audit.py

---

## 注意事項 / 運用上のポイント

- J-Quants API のレート制限に従うため、fetch 関数はモジュールレベルのレートリミッタを使用します。大量データ取得時は適切に間引きやバッチ処理を検討してください。
- get_id_token() は内部で POST を行い ID トークンを返します。_request は 401 に対して 1 回だけリフレッシュを試みます。
- DuckDB のスキーマは冪等的に作成されます。既存データを壊すことなくスキーマを初期化できますが、スキーマ変更時のマイグレーションは別途検討してください。
- 監査ログテーブルは削除を想定しない設計（ON DELETE RESTRICT）です。監査証跡は保持する運用を推奨します。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献・拡張

- strategy, execution, monitoring の各パッケージに具体的な戦略ロジック・発注コネクタ・監視機能を実装することで完全な自動売買システムになります。
- 必要に応じて外部ライブラリ（requests/HTTP セッション管理、バックオフィス連携、Slack クライアントなど）を追加してください。
- DB マイグレーション機能（schema versioning）を導入すると運用が楽になります。

---

必要であれば README にサンプルワークフロー（cron / Airflow での定期取得、発注フロー図、テーブル定義の詳細解説等）を追加できます。どの内容を追記したいか教えてください。