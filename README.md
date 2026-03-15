# KabuSys

日本株自動売買システム用のライブラリ群（KabuSys）。  
データ取得・DBスキーマ・監査ログなど自動売買システムの基盤処理を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つ小さな Python パッケージ群です。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを取得
- 取得データを DuckDB に冪等に保存するためのスキーマとユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- 環境変数管理（.env 自動ロード、必須変数の明示）
- RateLimiter / retry / token refresh 等を備えた頑健な API クライアント

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を順守
- リトライ（指数バックオフ、401 のトークン自動リフレッシュ対応）
- データ取得時の fetched_at を UTC で記録し Look-ahead Bias の抑制を支援
- DuckDB への INSERT は ON CONFLICT ... DO UPDATE により冪等性を確保

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルートを探索）
  - 環境変数取得用 Settings オブジェクト（必須変数チェック）
- J-Quants クライアント (`kabusys.data.jquants_client`)
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - レート制御、リトライ、token キャッシュ等
- DuckDB スキーマ (`kabusys.data.schema`)
  - init_schema(db_path) — 全テーブルを作成（冪等）
  - get_connection(db_path) — 既存 DB への接続
  - 定義済みテーブル群: raw / processed / feature / execution 層、インデックス
- 監査ログスキーマ (`kabusys.data.audit`)
  - init_audit_schema(conn) — 既存接続に監査テーブルを追加
  - init_audit_db(db_path) — 監査専用 DB を初期化して返す
- その他: パッケージ構成は strategy / execution / monitoring 等の拡張ポイントを想定

---

## 要件

- Python 3.10+（型記述に Union|None などを使用）
- duckdb
- ネットワークアクセス（J-Quants API）
- （用途に応じて）kabuステーション API、Slack トークン など

必要なパッケージは pyproject.toml / requirements によってインストールしてください（本 README には含めていません）。

---

## インストール

開発環境でソースを直接使う場合（プロジェクトルートで）:

```bash
pip install -e .
```

依存パッケージを直接入れる最小例:

```bash
pip install duckdb
```

---

## 環境変数（.env）

KabuSys は .env / .env.local を自動で読み込みます（プロジェクトルートを .git または pyproject.toml により探索）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG" | "INFO" | ...)

簡単な .env 例（`.env.example` をプロジェクトに用意すると良い）:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

.env のパースはシェル風（export 付き行、引用符、インラインコメント等）にある程度対応しています。

---

## セットアップ手順

1. リポジトリをチェックアウトして依存をインストール
   - pip install -e . や pip install -r requirements.txt

2. `.env` を作成して必要な環境変数を設定

3. DuckDB スキーマを初期化

Python スクリプト例:

```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path でデフォルトパスを取得
conn = schema.init_schema(settings.duckdb_path)
print("DuckDB schema initialized:", settings.duckdb_path)
```

監査ログを別 DB にする場合:

```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/audit.duckdb")
print("Audit DB initialized")
```

既存接続に監査テーブルを追加する場合:

```python
from kabusys.data import schema, audit
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

---

## 使い方（簡単な例）

以下は J-Quants から日足を取得して DuckDB に保存する簡単な例です。

```python
from kabusys.data import jquants_client
from kabusys.data import schema
from kabusys.config import settings
import duckdb

# DB 初期化（初回のみ）
conn = schema.init_schema(settings.duckdb_path)

# データ取得（日付指定や銘柄指定が可能）
records = jquants_client.fetch_daily_quotes(date_from=None, date_to=None, code=None)

# 保存（冪等: PK が一致すれば更新）
saved = jquants_client.save_daily_quotes(conn, records)
print(f"saved rows: {saved}")
```

財務データ・カレンダーも同様の流れで取得→保存できます:

- fetch_financial_statements / save_financial_statements
- fetch_market_calendar / save_market_calendar

注意点:
- J-Quants は 120 req/min のレート制限を持つため、頻繁にループさせる際は RateLimiter に注意してください（クライアントは内部で制御します）。
- 401 を受けた場合は自動でリフレッシュトークンから id_token を再取得してリトライします（1 回のみ）。

監査ログを書き込むフローは、strategy 層が生成した signal_id → order_request_id → 実際の executions を順に保存していく設計です。監査用 APIs:

- init_audit_schema(conn)
- init_audit_db(db_path)

---

## 設計上の注意 / 運用上の注意

- すべての TIMESTAMP は UTC を前提に保存しています（監査スキーマは初期化時に TimeZone='UTC' をセットします）。
- DuckDB の初期化は冪等（存在するテーブルはスキップ）です。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト等で自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- settings により環境（development / paper_trading / live）が切り替わります。live 運用時は設定ミスが重大になるため、運用前に必須変数が正しく設定されているかを確認してください。

---

## ディレクトリ構成

プロジェクト内の主要ファイル・モジュール（抜粋）:

- src/kabusys/
  - __init__.py             — パッケージ定義（バージョン: 0.1.0）
  - config.py               — 環境変数 / Settings 管理、.env 自動ロード
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得・保存ロジック）
    - schema.py             — DuckDB スキーマ定義 / init_schema / get_connection
    - audit.py              — 監査ログ（signal / order_request / executions）の DDL と初期化
    - (その他: raw/audit 用ユーティリティ)
  - strategy/
    - __init__.py           — 戦略層（拡張ポイント）
  - execution/
    - __init__.py           — 発注 / ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py           — 監視用モジュール（拡張ポイント）

その他: pyproject.toml や .git 等プロジェクトルートファイルを想定

---

## 追加情報 / 今後の拡張

- strategy / execution / monitoring パッケージは拡張を想定したプレースホルダになっています。実際の売買ロジックや kabu ステーション連携はこれらに実装してください。
- AI スコアや特徴量生成、ポートフォリオ管理機能はスキーマを用意済み（features / ai_scores / portfolio_* テーブル）です。特徴量生成処理や学習パイプラインは別実装になります。

---

もし README に加えたい具体的な使用例（例えば「日次バッチの crontab 設定例」「Slack 通知のサンプル」）や、実行可能なサンプルスクリプトがあれば教えてください。README をそれに合わせて追記します。