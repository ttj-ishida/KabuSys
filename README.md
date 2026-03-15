# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。

バージョン: 0.1.0

このリポジトリは、データ取得・スキーマ管理・監査ログなど自動売買システムの基盤機能を提供します。J-Quants API から市場データを取得して DuckDB に保存し、戦略・発注部分（strategy, execution）や監視（monitoring）を組み合わせて運用します。

---

## 機能一覧

- 環境変数 / 設定管理
  - .env / .env.local から自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）
  - 必須設定の取得と検証（例: トークン未設定時に例外を投げる）
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - ページネーション対応
  - レート制限（120 req/min）を固定間隔スロットリングで遵守
  - リトライ（指数バックオフ、最大 3 回）および 401 の自動トークンリフレッシュ
  - 取得時刻（UTC）を fetched_at として記録し、Look-ahead Bias を防止
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義を提供
  - テーブル初期化関数（init_schema）と接続取得関数（get_connection）
  - 主要クエリ向けのインデックス作成

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注 → 約定のトレーサビリティを残す監査テーブルを定義
  - order_request_id を冪等キーとして二重発注防止
  - UTC タイムスタンプ保存、監査用インデックス群

- package structure 単純化
  - strategy, execution, monitoring 用のモジュールプレースホルダ（将来的に拡張）

---

## セットアップ手順

前提:
- Python 3.10+（PEP 604 の型記法 a | b を使用）
- duckdb を利用（DuckDB を Python 経由で利用）

1. リポジトリをクローンし、仮想環境を作成
   - 例:
     - git clone <repo-url>
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 最低限: duckdb
   - 例:
     - pip install duckdb

   （プロジェクトに pyproject.toml / requirements.txt がある場合はそれらを使ってください。）

3. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は .env の内容を上書き可能）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack 通知に使用するボットトークン（必須）
   - SLACK_CHANNEL_ID : Slack のチャネル ID（必須）
   - その他（任意 / デフォルトあり）
     - KABU_API_BASE_URL : デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH : デフォルト "data/monitoring.db"
     - KABUSYS_ENV : "development"（他に "paper_trading", "live"）
     - LOG_LEVEL : "INFO"（"DEBUG","INFO","WARNING","ERROR","CRITICAL" が有効）

5. .env の例（.env.example を参考に作成）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

---

## 使い方（基本例）

以下はライブラリを使った典型的なフロー例です。

1) DuckDB スキーマの初期化

Python スクリプトや REPL 内で:

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")

2) J-Quants から日足データを取得して保存する例

from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既存DBに接続（initは先に実行）
records = fetch_daily_quotes(code="7203")  # 銘柄コードを指定（省略で全銘柄）
saved = save_daily_quotes(conn, records)
print(f"保存件数: {saved}")

ポイント:
- fetch_* 関数は自動的に id_token のキャッシュとリフレッシュ処理を行います。
- API レート制限は内部で管理されます（120 req/min）。
- save_* 関数は冪等（ON CONFLICT DO UPDATE）なので再実行が安全です。

3) 監査ログの初期化と使用例

from kabusys.data import schema, audit
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
# または監査専用DBを作る:
# audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

監査用テーブル（signal_events, order_requests, executions）が作成されます。アプリ側でこれらに対する INSERT/UPDATE を行い、発注トレースを残します。

4) 設定の利用例

from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)  # KABUSYS_ENV == "live" の場合 True

注意:
- settings は環境変数を参照します。必須キーが未設定だと ValueError を送出します。

---

## ディレクトリ構成

以下は主要ファイル／モジュールの一覧です（抜粋）。

src/
  kabusys/
    __init__.py                -- パッケージ定義（__version__=0.1.0）
    config.py                  -- 環境変数・設定管理（.env 自動読み込み、validation）
    data/
      __init__.py
      jquants_client.py        -- J-Quants API クライアント（取得・保存ロジック）
      schema.py                -- DuckDB スキーマ定義と初期化
      audit.py                 -- 監査ログ（signal/order/execution 用）
      # future: audit DB 初期化補助等
    strategy/
      __init__.py              -- 戦略層（拡張用プレースホルダ）
    execution/
      __init__.py              -- 発注実行層（拡張用プレースホルダ）
    monitoring/
      __init__.py              -- 監視用（拡張用プレースホルダ）

README.md（本ファイル）

---

## 設計上の注意点 / 重要な振る舞い

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env と .env.local を自動で読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - テストや特殊用途で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- J-Quants クライアントの堅牢性
  - レート制限を内部で保持するため、同一プロセス内での大量呼び出しでも API 制限を超えにくい設計です。
  - 401 発生時は自動でリフレッシュトークンを使って ID トークンを再取得し 1 回だけリトライします（無限再帰を防止）。
  - リトライ対象は 408/429/5xx 系。429 の場合は Retry-After ヘッダがあればそれを優先。

- データのトレーサビリティ
  - 取得時に fetched_at（UTC）を保存することで、実際に「いつデータを知り得たか」を追跡可能にします。
  - 監査ログは削除しない前提で設計され、FK は ON DELETE RESTRICT などで保護されています。

---

## 開発 & 貢献

- strategy / execution / monitoring パッケージは拡張点です。戦略の追加、発注ロジックや監視機能を実装してください。
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して外部 .env の影響を避けることを推奨します。
- DuckDB のインメモリモード（":memory:"）を使えばテストが容易です。

---

必要であれば、README に CI の手順、デプロイ手順、.env.example や API 利用上の注意（APIキーの管理方法）などの追記も対応します。追加で記載したい項目があれば教えてください。