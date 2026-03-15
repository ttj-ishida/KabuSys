# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ取得・保存（J-Quants / DuckDB）、スキーマ定義、監査ログ、設定管理などの基盤機能を提供します。

---

## 概要

KabuSys は下記の目的を持つ小さな Python パッケージです。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得と DuckDB への保存
- DuckDB を使ったデータスキーマ（Raw / Processed / Feature / Execution 層）の定義と初期化
- 発注フローを追跡する監査ログ（監査用スキーマ）の初期化
- 環境変数管理・自動ロード（.env / .env.local）を行う設定ユーティリティ

設計における注目点:
- J-Quants API 呼び出しはレート制限（120 req/min）およびリトライ（指数バックオフ、401 時に自動トークンリフレッシュ）を備えています。
- データの取得時刻（fetched_at）を UTC で保存し、Look-ahead Bias を防止します。
- DuckDB への INSERT は冪等（ON CONFLICT DO UPDATE）で上書き可能。

---

## 機能一覧

- 環境設定管理（.env ファイル自動読み込み、必須値チェック）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - トークン自動リフレッシュ・レート制御・リトライ
- DuckDB スキーマ（Raw / Processed / Feature / Execution）定義と初期化
- 監査ログスキーマ（signal_events / order_requests / executions）定義と初期化
- DuckDB へのデータ保存（冪等な保存関数）

---

## 必要条件 / 依存関係

- Python 3.10 以上（型アノテーションで | を利用）
- duckdb（Python パッケージ）
- 標準ライブラリの urllib 等

インストール例（仮にパッケージをローカルで扱う場合）:
```bash
python -m pip install -U pip
python -m pip install -e .[dev]   # setup があれば。最小限は duckdb のみ
python -m pip install duckdb
```

---

## セットアップ手順

1. リポジトリをクローンまたは展開
2. 必要な Python パッケージをインストール（少なくとも duckdb）
3. プロジェクトルートに .env または .env.local を作成（下節の例参照）
   - パッケージは起動時に .git または pyproject.toml を親ディレクトリで検出して自動的に .env を読み込みます
   - 自動読み込みを無効化する場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
4. DuckDB スキーマを初期化（次節参照）

---

## 環境変数（.env の例）

以下の環境変数がコード中で参照・必須になっています。`.env.example` に合わせて作成してください。

必須（未設定だとエラーになります）:
- JQUANTS_REFRESH_TOKEN=あなたのJ-Quantsリフレッシュトークン
- KABU_API_PASSWORD=（kabuステーション API 用パスワード）
- SLACK_BOT_TOKEN=Slack Bot のトークン
- SLACK_CHANNEL_ID=通知先 Slack チャンネル ID

任意 / デフォルトあり:
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  # デフォルト値あり
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- KABUSYS_ENV=development|paper_trading|live  （default: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （default: INFO）

.env の自動読み込みルール:
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- .env のパースはシェル風（export KEY=val、クォート、# コメント等に対応）
- プロジェクトルートは .git または pyproject.toml を探索して決定

---

## データベース初期化（DuckDB）

DuckDB のスキーマを初期化して接続を取得するには次のようにします。

- 基本的なスキーマ初期化（全テーブルを作成）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ファイルがなければディレクトリを自動作成
```

- 既存 DB に接続する（スキーマ初期化なし）:
```python
from kabusys.data.schema import get_connection
conn = get_connection("data/kabusys.duckdb")
```

- 監査ログ専用のスキーマ初期化:
```python
from kabusys.data.audit import init_audit_db, init_audit_schema
# 単独 DB を作る場合
conn = init_audit_db("data/audit.duckdb")
# 既存 conn に監査テーブルを追加する場合
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn)
```

監査スキーマは TIMESTAMP を UTC で保存するように設定されます（init_audit_schema 内で SET TimeZone='UTC' を実行）。

---

## 主要な使い方（コード例）

- J-Quants の ID トークン取得:
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って POST で取得
```

- 日足データを取得して DuckDB に保存:
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- 財務データの取得と保存:
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
records = fetch_financial_statements(code="7203")  # 例: 銘柄コード
n = save_financial_statements(conn, records)
```

- JPX カレンダーの取得と保存:
```python
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar
records = fetch_market_calendar()
save_market_calendar(conn, records)
```

- 設定値の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env)  # development / paper_trading / live
```

J-Quants クライアントは以下の点に配慮しています:
- レート制御: 120 req/min（内部で固定間隔スロットリング）
- リトライ: 408, 429, 5xx 等で指数バックオフ（最大 3 回）
- 401 を受けた場合はリフレッシュトークンから ID トークンを再取得して再試行（1 回のみ）

---

## ディレクトリ構成

主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py            # 環境設定・.env 自動読み込み・設定クラス
  - data/
    - __init__.py
    - jquants_client.py  # J-Quants API クライアント（取得・保存ロジック）
    - schema.py         # DuckDB スキーマ定義と init_schema / get_connection
    - audit.py          # 監査ログスキーマと初期化関数
    - audit.py
    - audit.py
  - strategy/
    - __init__.py        # 戦略関連（雛形）
  - execution/
    - __init__.py        # 実行（発注）関連（雛形）
  - monitoring/
    - __init__.py        # モニタリング関連（雛形）

README にない補足:
- schema.py は Raw / Processed / Feature / Execution 層にわたる多数のテーブル DDL を含んでいます。
- audit.py はシグナル→発注→約定のトレーサビリティを担保するテーブル群を提供します。

---

## 注意事項 / 運用上のポイント

- 本ライブラリは実運用（特に live モード）での使用に際して、適切な検証・テストが必要です。KABUSYS_ENV による挙動切替（development / paper_trading / live）を利用してください。
- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml）から行われます。CI / テスト環境での副作用を避けるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。バックアップや権限管理に注意してください。
- 監査ログは削除しない前提で設計されています（ON DELETE RESTRICT 等）。履歴の管理方針を事前に決めてください。

---

以上が KabuSys の簡易 README です。詳細な API ドキュメントや運用手順（発注の実装、Slack 通知連携、kabuステーション API のラッパー等）は別途追加・展開してください。必要であれば README を拡張して実運用手順や具体的な例（CI / cron / scheduler の設定例、サンプル .env.example）を作成します。