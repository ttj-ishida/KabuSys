# KabuSys

KabuSys は日本株の自動売買プラットフォームを想定したライブラリ群です。データ取り込み、スキーマ定義、監査ログ、J-Quants API クライアントなど、売買戦略の実行基盤に必要なコンポーネントを提供します。

主な目的は「データの取得・永続化」「監査トレーサビリティ」「戦略 → 発注までのデータ構造」を整備することです。

---

## 主な機能

- 環境変数 / .env の自動読み込みと設定管理
  - プロジェクトルート（`.git` または `pyproject.toml`）基準で `.env` / `.env.local` を読み込み
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能
  - 必須設定が未設定の場合は例外を送出するユーティリティを提供

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）を守る固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx 対象）
  - 401 を受けた場合はリフレッシュトークンから自動で ID トークンを更新してリトライ
  - ページネーション対応
  - DuckDB へ冪等に保存するユーティリティ（ON CONFLICT DO UPDATE）

- DuckDB スキーマ管理（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層に分けたテーブル DDL を定義
  - インデックス定義、外部キーの考慮済み作成順を提供
  - DB 初期化関数: init_schema(db_path)

- 監査ログ（src/kabusys/data/audit.py）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブルを提供
  - 冪等キー（order_request_id）やステータス管理を前提とした設計
  - init_audit_schema(conn) / init_audit_db(db_path) を提供

- パッケージ構成を想定したモジュール分割（data / strategy / execution / monitoring）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
- ネットワークアクセス（J-Quants API、kabuステーション 等）
- （運用時に）J-Quants リフレッシュトークン、kabu API パスワード、Slack トークンなどの環境変数

（実際の pyproject.toml / requirements.txt があればそちらを参照してください）

---

## インストール

プロジェクトルートに pyproject.toml 等があることを想定します。開発環境では次のようにインストールします:

pip install -e .

必要パッケージを個別にインストールする場合:

pip install duckdb

---

## 設定（環境変数）

パッケージは起動時にプロジェクトルートの `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには環境変数を設定します:

export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID（必須）

任意 / デフォルトがあるもの:
- KABUSYS_ENV — 実行環境。`development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL — ログレベル。`INFO`（デフォルト）等
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト: `data/monitoring.db`）
- KABUS_API_BASE_URL — kabu API の base URL（デフォルト: `http://localhost:18080/kabusapi`）

.env ファイルのパース仕様:
- `KEY=val`、`export KEY=val`、およびシングル/ダブルクォートやエスケープに対応
- 行頭 `#` はコメント
- クォート無しで ` #`（空白の後の #）以降はコメントとして扱う

未設定の必須キーにアクセスすると ValueError が発生します。

---

## クイックスタート（例）

1) DuckDB スキーマの初期化

from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")

2) J-Quants から日足を取得して保存する

from kabusys.data import jquants_client
from kabusys.data import schema
import duckdb

# DB 初期化（既に作成済みであればスキップ可能）
conn = schema.init_schema("data/kabusys.duckdb")

# 全銘柄の 2023/01/01〜2023/12/31 の日足を取得
records = jquants_client.fetch_daily_quotes(
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
)

# DuckDB に保存（冪等）
saved = jquants_client.save_daily_quotes(conn, records)
print(f"saved: {saved} rows")

3) 監査ログの初期化（監査専用 DB または既存 conn に対して）

from kabusys.data import audit
# 既存 conn に監査テーブルを追加
audit.init_audit_schema(conn)
# または専用 DB を初期化
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")

4) 自動 env 読み込みを無効にする（テスト等）

import os
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"
# その後 import kabusys.config を行う

---

## 使い方（API のポイント）

- 設定アクセス:
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env, settings.is_live など

- J-Quants API 呼び出し:
  - fetch_daily_quotes(...), fetch_financial_statements(...), fetch_market_calendar(...)
  - get_id_token(refresh_token=None) — 必要に応じてトークンを明示取得可能

- DuckDB スキーマ管理:
  - init_schema(db_path) — 初期化（テーブル作成・インデックス作成）
  - get_connection(db_path) — 既存 DB への接続

- 監査ログ:
  - init_audit_schema(conn) — 既存 conn に監査用テーブルを追加
  - init_audit_db(db_path) — 監査専用 DB を作る

注意点:
- J-Quants クライアントは内部でレート制御およびリトライを行いますが、アプリ全体での API 呼び出し頻度は運用側でも管理してください。
- J-Quants から取得したデータには fetched_at（UTC）を付与しており、Look-ahead bias を防ぐためのトレースが可能です。
- DuckDB への INSERT 系は ON CONFLICT DO UPDATE による冪等性を担保しています。

---

## ディレクトリ構成

以下は本リポジトリの主要ファイル・ディレクトリ構成（抜粋）です:

src/
  kabusys/
    __init__.py                 -- パッケージ定義（version等）
    config.py                   -- 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py         -- J-Quants API クライアント（取得・保存ロジック）
      schema.py                 -- DuckDB スキーマ定義・初期化
      audit.py                  -- 監査ログ（トレーサビリティ）
      (raw / processed / feature / execution 用の DDL を含む)
    strategy/
      __init__.py               -- 戦略関連のエントリポイント（未実装）
    execution/
      __init__.py               -- 発注実行関連（未実装）
    monitoring/
      __init__.py               -- 監視関連（未実装）

トップレベル:
  pyproject.toml (想定)
  .env, .env.local (任意のローカル設定)

---

## 設計上の留意点

- 時刻は監査ログを含め UTC で保存する設計です（監査初期化時に SET TimeZone='UTC' を実行）。
- 発注・監査の監査テーブルは削除を想定しない設計（ON DELETE RESTRICT 等）。
- order_request_id 等の UUID を冪等キーとして二重発注を防止するフローを想定しています。
- J-Quants API に関しては 120 req/min のレート制限を厳守するためのロジックが組み込まれています。

---

## 参考 / 次のステップ

- strategy / execution / monitoring モジュールに具体的なアルゴリズムや broker 接続を実装して運用ワークフローを完成させます。
- 実運用時は live / paper_trading 切替、ロギング・監視（Slack 通知等）を組み込んでください。
- .env.example を用意してチームで共有すると設定ミスを減らせます。

---

質問や README に追記してほしいサンプル（例: 実際の .env.example、より詳しい使用例、CI 初期化手順 等）があれば教えてください。