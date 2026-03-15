# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（モジュール群）。  
データ取得（J-Quants）、データベーススキーマ（DuckDB）、監査ログ、戦略・発注フレームワークの基盤を提供します。

---

## 概要

KabuSys は次の目的を持つ内部ライブラリ群です。

- J-Quants API から株価・財務・マーケットカレンダー等の市場データを取得して保存
- DuckDB ベースの3層データスキーマ（Raw / Processed / Feature）を定義・初期化
- 発注フローの監査ログ（UUID 連鎖によるトレーサビリティ）を提供
- 将来の戦略・実行・監視モジュールのための土台を提供

設計上のポイント：
- API レート制御（120 req/min）とリトライ（指数バックオフ、401 は自動トークンリフレッシュ）を備えています
- 取得時刻（fetched_at）を UTC で保存し、Look-ahead Bias に配慮
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE）で重複上書きを防止

---

## 機能一覧

- 環境変数・設定管理（自動 .env ロード、必須チェック）
- J-Quants API クライアント
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務諸表（四半期）取得
  - JPX マーケットカレンダー取得
  - トークン取得 / 自動リフレッシュ
  - レートリミット制御・リトライ処理
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- 監査ログ（signal_events, order_requests, executions）用スキーマと初期化関数
- ユーティリティ関数（型変換、保存ユーティリティ）

---

## 必要条件

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
- （任意）J-Quants API 利用にはネットワーク環境と有効なリフレッシュトークンが必要

実行環境には最低限 duckdb が必要です。pip でインストールしてください:

pip install duckdb

（プロジェクト全体をパッケージ化している場合は `pip install -e .` 等で依存を管理してください。）

---

## 環境変数（設定）

KabuSys は環境変数から設定を読み込みます。自動的にプロジェクトルート（.git か pyproject.toml を基準）を探索し、優先順位に従い .env → .env.local をロードします（OS 環境変数が最優先）。

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード（将来の execution 用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID

その他（任意）
- KABUSYS_ENV: environment のモード（development / paper_trading / live）。デフォルト: development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。デフォルト: INFO
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env ロードを無効化

.env のパースはシェル風の形式（export KEY=val, クォート、コメント）に対応します。

サンプル .env（例）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（クイックスタート）

1. 仮想環境を作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 依存パッケージをインストール
   ```
   pip install duckdb
   # プロジェクトをパッケージ化している場合は pip install -e .
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数を設定してください（上のサンプル参照）。
   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

4. DuckDB スキーマを初期化
   - Python スクリプトや REPL から次のように呼び出します：

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

5. 監査ログスキーマを追加（任意）
   ```python
   from kabusys.data.audit import init_audit_schema
   # conn は init_schema で得た DuckDB 接続
   init_audit_schema(conn)
   ```

---

## 使い方（例）

- J-Quants 日次株価を取得して DuckDB に保存する最小例：

```python
from kabusys.data.jquants_client import (
    fetch_daily_quotes,
    save_daily_quotes,
)
from kabusys.data.schema import init_schema

# DB 初期化（初回のみ）
conn = init_schema("data/kabusys.duckdb")

# データ取得（特定銘柄や期間を指定可能）
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# 保存（冪等）
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- ID トークンを明示的に取得する例（通常は自動リフレッシュを使用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 引数に refresh_token を渡すことも可能
print(token)
```

- マーケットカレンダー取得
```python
from kabusys.data.jquants_client import fetch_market_calendar
records = fetch_market_calendar()
# 保存は save_market_calendar(conn, records) を使用
```

注意点：
- fetch_* 系関数は内部でレート管理とリトライを行います。
- save_* 関数は ON CONFLICT による更新で冪等に動作します。
- すべての timestamp や fetched_at は UTC で記録されます。

---

## 監査ログ（audit）利用例

監査ログは発注フローの証跡を残すために使います。初期化は上記の通り init_audit_schema を既存の DuckDB 接続に対して呼び出します。  
監査テーブルの主な役割：

- signal_events: 戦略が生成したシグナルを記録（棄却されたものも含む）
- order_requests: 発注要求（order_request_id を冪等キーとして二重発注を防止）
- executions: 証券会社から返った約定情報

すべての TIMESTAMP は UTC で保存され、FK は ON DELETE RESTRICT（削除不可）を前提としています。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/モジュールは以下のとおりです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                 # 環境変数・設定管理（.env 自動読み込み、Settings）
  - data/
    - __init__.py
    - jquants_client.py       # J-Quants API クライアント（取得・保存ロジック）
    - schema.py               # DuckDB スキーマ定義・初期化
    - audit.py                # 監査ログスキーマ（signal/order/execution）
    - audit.py
    - (その他 data モジュール)
  - strategy/
    - __init__.py
    # 戦略関連モジュール（今後実装）
  - execution/
    - __init__.py
    # 発注実装・kabu API クライアント等（今後実装）
  - monitoring/
    - __init__.py
    # 監視・メトリクス関連（今後実装）

主要な関数・クラス：
- kabusys.config.settings: Settings インスタンス（環境変数アクセス）
- kabusys.data.jquants_client: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_* / get_id_token
- kabusys.data.schema: init_schema / get_connection
- kabusys.data.audit: init_audit_schema / init_audit_db

---

## 開発上の注意

- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で判断します。CI/テストで無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- API 呼び出し回数は 120 req/min に制限されています。jquants_client は内部でレート制御を行いますが、上位設計でも注意してください。
- DuckDB のスキーマは冪等設計です。既存テーブルがあれば再実行しても安全です。
- 監査ログは通常削除しない前提です（FK 制約は ON DELETE RESTRICT）。

---

## 今後の拡張案（参考）

- kabuステーション API 実装（execution 層）
- 戦略実装サンプル（strategy 層）
- Slack / 通知モジュールの統合（monitoring）
- CI用のテストヘルパー（in-memory DuckDB を使った単体テスト）

---

項目や使い方で不明点があれば、どの部分をどのように使いたいか教えてください。README の補足（例: .env.example の自動生成、サンプルスクリプト）も作成します。