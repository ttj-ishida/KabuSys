# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（骨組み）。データ取得、DuckDBスキーマ定義、監査ログ（トレーサビリティ）、環境設定処理などの基本機能を提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした内部用ライブラリです。

- J-Quants API から市場データ（株価日足、四半期財務、マーケットカレンダー）を取得するクライアント
- DuckDB 上に整形済みテーブルを作成するスキーマ初期化機能（Raw / Processed / Feature / Execution 層）
- 発注フローの監査ログ（トレーサビリティ）用スキーマと初期化機能
- 環境変数の自動読み込み・管理（.env、.env.local の優先順位、保護）
- データ保存ユーティリティ（DuckDB への冪等保存）
- API レート制御、リトライ・トークン自動更新等の堅牢な HTTP 処理

設計上のポイント:
- J-Quants API のレート制限（120 req/min）を固定間隔スロットリングで遵守
- 408/429/5xx に対する指数バックオフによるリトライ（最大 3 回）
- 401 受信時はリフレッシュトークンから ID トークンを再取得して 1 回リトライ
- データ取得時に fetched_at を UTC で記録して Look-ahead Bias を防止
- DuckDB への挿入は ON CONFLICT DO UPDATE で冪等性を確保

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得（未設定時は例外）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能

- データモジュール（kabusys.data）
  - J-Quants API クライアント
    - get_id_token()
    - fetch_daily_quotes()
    - fetch_financial_statements()
    - fetch_market_calendar()
  - DuckDB 用スキーマ初期化・接続
    - init_schema()
    - get_connection()
  - DuckDB へデータを冪等保存する関数
    - save_daily_quotes()
    - save_financial_statements()
    - save_market_calendar()

- 監査（kabusys.data.audit）
  - 発注フローの監査テーブル定義・初期化
    - init_audit_schema()
    - init_audit_db()

- その他
  - execution, strategy, monitoring パッケージのプレースホルダ（拡張用）

---

## 動作環境・依存

- Python 3.10 以上（型ヒントに union 演算子 `|` を使用）
- 依存パッケージ（少なくとも）
  - duckdb

インストール例（開発環境）:
```bash
python -m pip install --upgrade pip
python -m pip install duckdb
# パッケージを編集しながら使う場合（プロジェクトルートに setup or pyproject がある想定）
python -m pip install -e .
```

※ 将来的に Slack クライアントや kabuステーション連携等の追加依存が必要になる可能性があります。

---

## セットアップ手順

1. リポジトリをクローン／展開する
   - 例: git clone ... もしくはソースを所定のディレクトリに置く

2. Python 3.10+ と依存パッケージをインストール
   - 上記の「動作環境・依存」を参照

3. 環境変数を用意する
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として必要な値を置くと、パッケージ読み込み時に自動で読み込まれます。
   - `.env.local` を置くと `.env` の設定を上書きできます（OS 環境変数は保護されます）。
   - 自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用途）。

4. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
   - SLACK_BOT_TOKEN : Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID : Slack 通知チャンネル ID（必須）
   - オプション:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）

5. DuckDB スキーマ初期化
   - 例: Python REPL またはスクリプトから
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイル DB。":memory:" でインメモリ
   ```
   - 監査ログ（order/signal/execution）の初期化:
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # conn は init_schema の返り値
   ```
   - 監査専用 DB を別ファイルにする場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（簡単な例）

- J-Quants から日足を取得して DuckDB に保存する例:
```python
from datetime import date
import duckdb
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

# DB 初期化（必要なら）
conn = init_schema("data/kabusys.duckdb")

# データ取得（トークンは内部で settings.jquants_refresh_token から取得）
records = fetch_daily_quotes(date_from=date(2023, 1, 1), date_to=date(2023, 12, 31), code="7203")

# 保存（冪等）
n_saved = save_daily_quotes(conn, records)
print(f"保存件数: {n_saved}")
```

- ID トークンだけ直接取得したい場合:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
print(token)
```

- fetch_* 系はページネーション対応で全件取得します。内部的にレート制御・リトライ・トークンリフレッシュを行います。

---

## よくある注意点

- .env のパースは POSIX 系の簡易パーサを実装しています。シングル／ダブルクォートに対応し、コメント処理も考慮していますが、極端に複雑なフォーマットには対応しない場合があります。
- 自動で .env を読み込む際、OS 環境変数は保護されます（.env の値で上書きされません）。`.env.local` は .env を上書きしますが、OS 環境変数は依然保護されます。
- J-Quants API のレート制限（120 req/min）を厳守するため、短時間に大量リクエストを投げる設計は避けてください。ライブラリは固定間隔スロットリングを行いますが、複数プロセスから同時に呼ぶと合計で制限を超える恐れがあります。
- DuckDB のテーブル DDL には多くの CHECK 制約・外部キーがあるため、データ挿入時にはスキーマ仕様に合うデータであることを確認してください。

---

## ディレクトリ構成

プロジェクト内の主要ファイル・パッケージ構成（抜粋）:

- src/kabusys/
  - __init__.py                (パッケージメタ情報: __version__)
  - config.py                  (環境変数・設定管理、settings オブジェクト)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント、取得・保存関数)
    - schema.py                (DuckDB スキーマ定義 & init_schema / get_connection)
    - audit.py                 (監査ログスキーマ & 初期化)
    - audit.py
  - strategy/
    - __init__.py              (戦略関連プレースホルダ)
  - execution/
    - __init__.py              (発注/実行関連プレースホルダ)
  - monitoring/
    - __init__.py              (モニタリング周りのプレースホルダ)

README はこのファイルを含めてプロジェクトルートに配置してください。pyproject.toml や setup.py がある場合はそれに従ってパッケージ化できます。

---

## 今後の拡張案（参考）

- kabuステーション（kabu API）との実際の発注モジュールの実装
- Slack 通知用ユーティリティ（設定済みトークン利用）
- feature 作成パイプライン / バックフィル用 CLI
- マルチプロセス・分散実行時のグローバルなレート制御（Redis 等の共有ロック）

---

作業にあたって不明点や README に追記したい項目があれば教えてください。必要に応じて使用例や API ドキュメントを追加します。