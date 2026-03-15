# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・DBスキーマ定義・監査ログ・APIクライアント等を備え、戦略・実行層の基盤を提供します。

---

## 概要

KabuSys は以下を目的としたモジュール群を含む Python パッケージです。

- J-Quants API からの市場データ（株価日足、財務データ、JPXカレンダー等）の取得
- DuckDB による多層スキーマ（Raw / Processed / Feature / Execution）の定義と初期化
- 発注〜約定フローの監査ログ（監査テーブル群）の定義と初期化
- 環境変数 / .env の読み込み・管理（自動ロード・保護機能付き）
- レートリミット・リトライ・トークン自動リフレッシュを備えた API クライアント

設計のポイント:
- レート制限（J-Quants: 120 req/min）遵守
- リトライ（指数バックオフ、401 時のトークン自動更新）
- データ取得時の fetched_at による Look-ahead Bias の抑制
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）

---

## 機能一覧

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - 必須環境変数の検証、環境（development/paper_trading/live）とログレベルの検証
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - get_id_token（リフレッシュトークンからの ID トークン取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット・リトライ・ページネーション対応
  - DuckDB へ保存する save_* 関数（冪等）
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL
  - init_schema(db_path) による初期化（テーブル・インデックス作成）
  - get_connection(db_path) による接続取得
- 監査ログ（src/kabusys/data/audit.py）
  - signal_events / order_requests / executions テーブル群
  - init_audit_schema(conn) / init_audit_db(db_path)
  - すべての TIMESTAMP を UTC で扱う（init_audit_schema は SET TimeZone='UTC' を実行）
- パッケージ構成のための __init__（src/kabusys/__init__.py）など

---

## 必要条件（推奨）

- Python 3.10+
- 依存パッケージ: duckdb
  - (他は標準ライブラリ中心。実行時に追加の依存がある場合は適宜インストールしてください)

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb
```

パッケージ化されている場合は:
```bash
pip install -e .
```

---

## 環境変数（必須 / 任意）

必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知（Bot）トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意・デフォルト有り:
- KABUSYS_ENV — "development"（デフォルト） / "paper_trading" / "live"
- LOG_LEVEL — "INFO"（デフォルト）等
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動ロードを無効化

.env の読み込みについて:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を起点に自動で .env と .env.local を読み込みます
- 優先順位: OS 環境変数 > .env.local > .env
- .env のフォーマットは一般的な KEY=VALUE、export KEY=VALUE、クォートやインラインコメントに対応します

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要なパッケージをインストール
   ```bash
   pip install duckdb
   # もしパッケージ化されていれば:
   # pip install -e .
   ```

4. 環境変数を設定
   - .env をプロジェクトルートに作成するか、環境変数を直接設定します。
   - .env.local を使用してローカル上書きが可能です。

5. DB スキーマの初期化（例: DuckDB ファイルを作る）
   - Python から実行:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログを別 DB に分けたい場合:
     ```python
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な例）

以下は J-Quants から日足を取得して DuckDB に保存する例です。

```python
from datetime import date
import duckdb
from kabusys.data import jquants_client
from kabusys.data import schema

# DB 初期化 / 接続
conn = schema.init_schema("data/kabusys.duckdb")

# 日足データ取得（例: 銘柄コード 7203 の 2023-01-01〜2023-12-31）
records = jquants_client.fetch_daily_quotes(
    code="7203",
    date_from=date(2023, 1, 1),
    date_to=date(2023, 12, 31),
)

# DuckDB に保存（冪等）
n_saved = jquants_client.save_daily_quotes(conn, records)
print(f"{n_saved} レコードを保存しました")
```

トークンを直接取得して利用したい場合:
```python
from kabusys.data.jquants_client import get_id_token, fetch_market_calendar

id_token = get_id_token()  # settings.jquants_refresh_token を使って取得
calendar = fetch_market_calendar(id_token=id_token)
```

監査ログの初期化（既存の接続に対して追加）:
```python
from kabusys.data import schema, audit

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

設定値は settings 経由で参照できます:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## ディレクトリ構成

リポジトリ内の主要なファイル・モジュールは次のとおりです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理（.env 自動ロード等）
    - data/
      - __init__.py
      - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
      - schema.py             — DuckDB スキーマ定義・初期化
      - audit.py              — 監査ログ（signal/order/execution）定義・初期化
      - audit.py
      - (その他データ関連モジュール)
    - strategy/
      - __init__.py
      - (戦略関連モジュールを配置)
    - execution/
      - __init__.py
      - (発注・ブローカー連携モジュールを配置)
    - monitoring/
      - __init__.py
      - (監視・メトリクス関連)

README や DataSchema.md / DataPlatform.md といった設計ドキュメントを併用すると、各テーブルの目的や監査フローが把握しやすくなります。

---

## 設計上の注意点

- J-Quants のレート制限を守るため、jquants_client は固定間隔スロットリングを使っています。大量取得を行う場合は設計に注意してください。
- get_id_token はリフレッシュトークンから ID トークンを取得し、401 時に自動でトークンを更新する仕組みがあります。
- DuckDB の初期化は冪等です。既存テーブルがあればスキップされます。
- 監査ログは削除しない前提（ON DELETE RESTRICT 等）で設計されています。更新時は updated_at を適切にセットしてください。
- すべての監査 TIMESTAMP は UTC を想定しています（init_audit_schema は SET TimeZone='UTC' を実行）。

---

## 開発・テストに関する補足

- 自動で .env を読み込む処理は、テストや環境によって無効化可能です:
  - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env の自動ロードをスキップします。
- DuckDB のインメモリ DB を使うときは db_path に `":memory:"` を指定できます（テスト向け）。

---

## 最後に

この README はコードベースから抽出した情報に基づいています。実運用環境で利用する際は .env.example の整備や、kabuステーション連携、Slack 通知の実装、実際の発注フローに関するエラーハンドリング・安全対策（速度制限、ポジション管理、リスク制約など）を十分に確認してください。