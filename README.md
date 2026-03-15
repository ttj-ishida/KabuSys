# KabuSys

日本株自動売買システムのためのユーティリティ群（ライブラリ）。  
J-Quants / kabuステーション 等の外部 API からデータ取得、DuckDB スキーマの初期化、監査ログ管理など、自動売買プラットフォーム構築に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴

- 環境変数ベースの設定管理（.env 自動読み込み対応）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）準拠のスロットリング
  - 指数バックオフ付きリトライ（408/429/5xx）と 401 に対する自動トークンリフレッシュ
  - Look-ahead bias を避けるため取得時刻（fetched_at）を UTC で保存
  - ページネーション対応、冪等性を考慮した DuckDB への保存
- DuckDB 用の包括的なスキーマ定義（Raw / Processed / Feature / Execution レイヤ）
- 監査ログ（signal_events / order_requests / executions）を別途初期化可能
- settings オブジェクト経由で環境変数へアクセスしやすいインターフェース

---

## 必要条件

- Python 3.10+
- duckdb
- （ネットワークアクセスと外部 API の認証情報）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb
# このリポジトリを editable インストールする場合:
# python -m pip install -e .
```

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ

1. リポジトリをクローンして、パッケージをインストール（任意）。
2. プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に環境変数が読み込まれます（ただしテストなどで無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
3. DuckDB データベースを初期化する（例を後述）。

注意: 自動読み込みは、パッケージ内の `kabusys.config` モジュールがプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` を探して読み込みます。OS 環境変数は上書きされません。

---

## 必要な環境変数（主なもの）

このライブラリで参照される主要な環境変数（.env に記載することを想定）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化するには 1 をセット

例（.env.example）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## データベース初期化

DuckDB スキーマ全体（データレイヤ、フィーチャ、実行レイヤ等）を初期化するには:

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# ファイルパスは settings.duckdb_path を使うことができる
conn = init_schema(settings.duckdb_path)  # もしくは ":memory:" でインメモリ DB
```

監査ログ（signal_events / order_requests / executions）だけ追加で初期化する場合:

```python
from kabusys.data.audit import init_audit_schema
# init_schema() で得た conn を渡す
init_audit_schema(conn)
```

監査用専用 DB を新規に作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（例）

J-Quants から日次株価を取得して DuckDB に保存する基本的な流れ:

```python
from datetime import date
from kabusys.config import settings
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

# DB 接続初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# データ取得（銘柄コード指定可、date_from/date_to 指定可）
records = fetch_daily_quotes(code="7203", date_from=date(2023, 1, 1), date_to=date(2023, 12, 31))

# DuckDB に保存（冪等）
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

トークン取得（内部で自動的に使用されるが直接呼び出すことも可能）:

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を用いて ID トークンを取得
```

設計上のポイント:
- fetch_* 系はページネーションとトークンリフレッシュに対応
- save_* 系は ON CONFLICT DO UPDATE により冪等性を確保
- 取得時刻（fetched_at）は UTC で記録されるため、データがいつ利用可能になったかをトレース可能

---

## 監査ログ（Audit）について

監査テーブルは以下の階層でトレースを可能にします:
business_date → strategy_id → signal_id → order_request_id → broker_order_id

設計方針:
- order_request_id を冪等キーとして二重発注を防止
- すべての TIMESTAMP は UTC で保存
- ログは削除せず履歴として保持

初期化には前述の `init_audit_schema` / `init_audit_db` を使用してください。

---

## 開発時の補足

- 自動 .env 読み込みは、プロジェクトルート（.git または pyproject.toml のある場所）を基準に行われます。プロジェクト配布後も動作するように __file__ を起点に探索します。
- テストなどで自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings オブジェクトはプロパティベースで環境変数の取得・検証を行います。存在必須のキーがない場合は ValueError が発生します。

使用例:
```python
from kabusys.config import settings
print(settings.env, settings.log_level, settings.duckdb_path)
```

---

## ディレクトリ構成（抜粋）

リポジトリのソースは `src/kabusys` 配下に配置されています。主要なファイル:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
    - schema.py              -- DuckDB スキーマ定義・初期化
    - audit.py               -- 監査ログスキーマ・初期化
    - audit.py
    - (その他) 
  - strategy/
    - __init__.py            -- 戦略層（拡張点）
  - execution/
    - __init__.py            -- 発注 / 約定管理（拡張点）
  - monitoring/
    - __init__.py            -- 監視・メトリクス（拡張点）

（README に載っているのは現状の主要モジュール。一部未実装のサブモジュールは将来的に拡張されます。）

---

## 今後の拡張ポイント（参考）

- strategy / execution / monitoring の具体実装（シグナル生成、ポートフォリオ最適化、kabuステーションとの発注連携）
- Slack / メトリクス連携の実装（settings に Slack 設定はある）
- CI / テストスイート、requirements 管理（pyproject.toml / requirements.txt）

---

不明点や追加で README に書きたい項目があれば教えてください。README をプロジェクトの実態に合わせてさらに肉付けします。