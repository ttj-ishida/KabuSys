# KabuSys

日本株自動売買プラットフォーム用のライブラリ（KabuSys）。データ取得、DBスキーマ管理、監査ログ、戦略・実行・監視のための基盤モジュール群を含みます。

概要、設計方針、セットアップ手順、使い方、ディレクトリ構成を以下にまとめます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリです。主な目的は以下：

- J-Quants やマーケットカレンダーなど外部データの取得
- DuckDB によるデータ永続化（Raw / Processed / Feature / Execution の多層スキーマ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理（.env/.env.local の自動ロード）
- レート制限・リトライ・トークン自動リフレッシュ等の堅牢な API クライアント設計

設計上のポイント：
- J-Quants API は 120 req/min のレート制限に従い固定間隔スロットリングで制御
- HTTP レスポンスに対し指数バックオフによるリトライ（408/429/5xx 対応）、401 時はトークン自動リフレッシュを行い1回だけ再試行
- データ取得時に fetched_at を UTC で記録し、Look-ahead バイアス防止
- DuckDB への insert は ON CONFLICT DO UPDATE で冪等性を担保

---

## 主な機能一覧

- 環境変数/設定管理（kabusys.config）
  - .env / .env.local の自動ロード（OS 環境 > .env.local > .env）
  - 必須キー未設定時に例外を発生させるヘルパー
  - KABUSYS_ENV（development / paper_trading / live）による動作モード判定
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - ページネーション対応、レート制御、リトライ、トークン自動更新
  - DuckDB への保存（raw_prices / raw_financials / market_calendar）
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス定義、初期化関数（init_schema / get_connection）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルと初期化ロジック
  - すべての TIMESTAMP は UTC で保存
- パッケージ構造は戦略（strategy）、実行（execution）、監視（monitoring）モジュールを想定（ベースのみ含む）

---

## 必要条件 / 依存

- Python 3.10 以上（型ヒントに | を使用）
- duckdb（DuckDB Python パッケージ）
- その他標準ライブラリ（urllib, json など）

インストール例（仮にパッケージ化されている場合）:
```bash
# 仮想環境作成（推奨）
python -m venv .venv
source .venv/bin/activate

# 必要パッケージをインストール（duckdb が主な外部依存）
pip install duckdb

# 開発時: ローカルパッケージを editable install する場合
# pip install -e .
```

（プロジェクトの setup/pyproject ファイルがある場合はそちらに従ってください）

---

## 環境変数（主なキー）

以下はコード内で参照される主な環境変数です（.env/.env.local に定義して使用します）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位（上書き順）: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで利用）。

---

## セットアップ手順（ローカルでの基本例）

1. リポジトリをクローンし、仮想環境を作成・有効化
2. duckdb をインストール
   ```
   pip install duckdb
   ```
3. プロジェクトルートに `.env`（必要キーを記載）を配置
   例（.env.example を参考に作成）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
4. DuckDB スキーマを初期化
   - Python から init_schema を呼ぶことでファイル作成・テーブル作成が行われます（親ディレクトリ自動作成）。

---

## 使用例

以下は主要 API の簡単な使用例です。

- 設定読み取り
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)  # 必須（設定されていなければ例外）
print(settings.duckdb_path)            # Path オブジェクト（デフォルト: data/kabusys.duckdb）
print(settings.env)                    # development / paper_trading / live
```

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema

# settings.duckdb_path を使う例
from kabusys.config import settings
conn = init_schema(settings.duckdb_path)
# conn は duckdb の接続オブジェクト（duckdb.DuckDBPyConnection）
```

- J-Quants から日足を取得して保存する例
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)

# 銘柄指定なしで全銘柄を取得（注意: データ量が多くなる可能性あり）
records = fetch_daily_quotes(date_from=None, date_to=None)

# raw_prices テーブルに保存（冪等）
num_saved = save_daily_quotes(conn, records)
print(f"saved {num_saved} rows")
```

- 財務データ・マーケットカレンダーの取得・保存も同様です:
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar

- 監査ログの初期化（既存の DuckDB 接続に追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
init_audit_schema(conn)
```

- ID トークン取得（通常は jquants_client が内部で自動管理）
```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

注意点:
- J-Quants へのリクエストは内部でレート制限・リトライを実施しますが、大量データ取得の際は実行時間や API 利用制限に留意してください。
- fetch_* 系はページネーションに対応し、モジュールレベルで ID トークンをキャッシュして共有します。
- save_* 系は「ON CONFLICT DO UPDATE」を使い冪等に保存します。欠損 PK の行はスキップされ警告が出ます。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - schema.py              — DuckDB スキーマ定義・初期化
    - audit.py               — 監査ログ（signal/order/execution）スキーマ
    - audit.*                — 監査関連ユーティリティ（上記ファイルに含む）
    - (その他データ関連モジュール)
  - strategy/
    - __init__.py            — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 発注/ブローカ連携モジュール（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視/アラート用モジュール（拡張ポイント）

ドキュメント/設計参照:
- DataSchema.md / DataPlatform.md（コード内コメントで言及されている設計資料）をプロジェクトルートに置くことを想定しています。

---

## 運用上の注意 / ベストプラクティス

- 本ライブラリはバックエンド基盤の一部です。実運用の際は次を検討してください：
  - DB バックアップとマイグレーション戦略
  - 監査ログの永続性（監査テーブルは削除しない前提）
  - 実際の発注ロジックでは二重発注防止のため order_request_id（冪等キー）を必ず利用
  - ログレベルや通知（Slack）設定により運用時の可観測性を高める
- テスト時に自動 .env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

もし README に含めたい追加の情報（例: .env.example の完全なテンプレート、CI/CD 手順、ロギング設定の詳細、サンプル戦略）があれば教えてください。それに合わせて追記します。