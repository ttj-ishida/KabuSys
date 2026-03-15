# KabuSys

日本株向け自動売買基盤ライブラリ（KabuSys）の README

このリポジトリは、日本株の市場データ取得、DuckDB スキーマ管理、監査ログ等を含む自動売買プラットフォームの基盤モジュール群です。J-Quants API からのデータ取得や、取得データの永続化、監査用テーブルの初期化などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたライブラリです。

- J-Quants API から株価・財務・マーケットカレンダーを安全に取得するクライアント
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化
- 発注フローのトレーサビリティを担保する監査ログ（audit）機能
- 環境変数管理（.env の自動ロード、settings オブジェクト）

設計上の注力点：
- API レート制限（120 req/min）の順守
- リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
- データ取得時の fetched_at 記録による Look-ahead Bias の回避
- DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE）

---

## 主な機能一覧

- 環境設定管理（kabusys.config.Settings）
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数のチェック
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークン→IDトークン）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レートリミット、リトライ、ページネーション、トークン自動更新
  - DuckDB への保存 helper（save_daily_quotes 等）
- DuckDB スキーマ管理（kabusys.data.schema）
  - init_schema（全テーブル作成）
  - get_connection（既存 DB 接続取得）
- 監査ログスキーマ（kabusys.data.audit）
  - init_audit_schema / init_audit_db（発注・約定の監査用テーブル）
- その他モジュールプレースホルダ（strategy, execution, monitoring）

---

## 必要条件

- Python 3.10 以上（構文での型ヒント（|）を使用）
- 依存ライブラリ（例）
  - duckdb
（パッケージ化時に requirements を整備することを推奨）

開発環境でのインストール例（プロジェクトルートで）:
```
pip install -e .  # setup.py / pyproject.toml がある想定
pip install duckdb
```

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 環境を作成（venv / pyenv など）
3. 依存ライブラリをインストール（duckdb 等）
4. プロジェクトルートに .env（および任意で .env.local）を作成
5. DuckDB スキーマを初期化

環境変数の自動ロードについて:
- プロジェクトルートはこのパッケージファイルを起点に `.git` または `pyproject.toml` を探索して決定します。
- ロード順序は OS 環境 > .env.local > .env（.env.local は上書き）
- 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主要）

必須（例）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

オプション／デフォルト:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live。デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

settings はプログラムから以下のように参照できます:
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # pathlib.Path
```

---

## 使い方（簡単なコード例）

1) DuckDB スキーマを初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は Path オブジェクト
conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成、テーブルを全作成
```

2) J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# conn は init_schema の戻り値
records = fetch_daily_quotes(code="7203")  # トヨタの例（銘柄コード）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 財務諸表や市場カレンダーも同様
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)
```

4) 監査ログを初期化（監査専用 DB または既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema, init_audit_db

# 既存の conn に監査テーブルを追加
init_audit_schema(conn)

# または監査専用 DB を作成して接続
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 重要な設計ポイント（動作の要点）

- J-Quants クライアントは 120 req/min のレート制限を固定間隔で守ります（モジュール内部でスロットリング）。
- ネットワーク系の失敗や 429/408/5xx に対しては最大 3 回のリトライ（指数バックオフ）を行います。
- 401 Unauthorized を受けた場合は一度だけトークンを自動リフレッシュして再試行します（無限再帰を防止）。
- データの fetched_at（UTC）を保存して「いつシステムがそのデータを知り得たか」を追跡可能にしています。
- DuckDB への保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複登録を防ぎます。
- 監査ログは削除を想定しておらず、order_request_id 等を冪等キーとして二重発注を防ぎます。全ての TIMESTAMP は UTC で保存されます。

---

## ディレクトリ構成

パッケージルート（src/kabusys）のおおまかな構成:

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数・設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py           - J-Quants API クライアント（取得・保存）
    - schema.py                   - DuckDB スキーマ定義・初期化
    - audit.py                    - 監査ログスキーマ（信頼性・トレーサビリティ）
    - (その他)                    - 将来的なデータ関連モジュール
  - strategy/
    - __init__.py                 - 戦略層（プレースホルダ）
  - execution/
    - __init__.py                 - 発注・実行層（プレースホルダ）
  - monitoring/
    - __init__.py                 - 監視系（プレースホルダ）

主なファイル：
- src/kabusys/config.py: .env の自動読み込み、Settings クラス（プロパティで必須値を取得）
- src/kabusys/data/jquants_client.py: API 呼び出し、ページネーション、保存ユーティリティ
- src/kabusys/data/schema.py: 全テーブル DDL 集合と init_schema / get_connection
- src/kabusys/data/audit.py: 監査用 DDL と初期化関数

---

## 追加メモ / 運用上の注意

- DuckDB ファイルのバックアップ、運用時の排他制御（多プロセスでの同時書き込み）については運用設計が必要です。
- 本ライブラリはデータ層と監査層を提供する基盤であり、実際の売買ロジック（strategy）やブローカ連携（execution）の実装は別途行う必要があります。
- .env の扱いはローカル開発向けの便宜上の機能です。本番では OS 環境変数やシークレットマネージャを推奨します。

---

もし README に追加したい「具体的なサンプル戦略」「CI/CD 設定」「テスト実行方法」などがあれば、コードや方針を教えてください。それに合わせて README を拡張します。