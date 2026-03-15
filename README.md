# KabuSys

日本株自動売買プラットフォーム用ライブラリ（開発版）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買プラットフォーム向けの内部ライブラリ群です。主に以下を提供します。

- 市場データ取得（J-Quants API）および DuckDB への永続化
- DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- 環境変数ベースの設定管理

このリポジトリはライブラリのコアコンポーネントを含み、戦略（strategy/）、発注（execution/）、監視（monitoring/）の各モジュールは拡張用の空のパッケージとして配置されています。

---

## 主な機能一覧

- 環境設定管理（.env/.env.local の自動読み込み、必須設定のバリデーション）
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、401 時のトークン自動リフレッシュ対応）
  - Look-ahead バイアス対策のため fetched_at を UTC で記録
  - ページネーション対応
- DuckDB 用スキーマ定義（冪等でのテーブル作成、インデックス設定）
- 監査ログテーブル（signal_events, order_requests, executions）と初期化ユーティリティ
- データ保存用ユーティリティ（raw_prices / raw_financials / market_calendar などへの安全な保存）

---

## 必要条件

- Python 3.10 以上（型注釈に Python 3.10 の構文（|）を使用）
- 依存パッケージ: duckdb
  - インストール例: pip install duckdb

（追加の実行・拡張には標準ライブラリの urllib 等が使用されます。その他外部サービス（J-Quants、kabuステーション、Slack）との接続には各種トークンが必要です。）

---

## 環境変数（必須 / 任意）

以下の環境変数を用意してください。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD に依存せず、パッケージの __file__ を基準に探索します）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャネル ID

任意（デフォルト有り／推奨）:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動ロードの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを抑制します（テスト用途など）。

.env のパースは一般的な形式をサポートします（コメント、export プレフィックス、クォート、エスケープ等）。

---

## セットアップ手順

1. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Linux/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 必要パッケージをインストール
   - pip install duckdb

   もしパッケージ配布のために setup/pyproject を提供する場合は pip install -e . を使って開発インストールしてください。

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定します。例:

     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

   - `.env.local` を用いると `.env` の上書き（優先）として読み込まれます。

4. DuckDB スキーマ初期化（下記 使用例を参照）

---

## 使い方（主要ユースケース）

以下はライブラリ主要 API の利用例です。実際はアプリケーション内で適切にエラーハンドリングやログ設定を行ってください。

1) 設定アクセス

```
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

2) DuckDB スキーマの初期化

```
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path に基づきファイルを作成してテーブルを初期化
conn = schema.init_schema(settings.duckdb_path)

# 以降 conn を使ってクエリや保存関数を呼べます
```

3) J-Quants から日次株価を取得して保存する

```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data import schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)

# 特定銘柄または全件
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)

# raw_prices に冪等的に保存
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

4) 財務データ / マーケットカレンダー取得

```
from kabusys.data.jquants_client import fetch_financial_statements, fetch_market_calendar, save_financial_statements, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

5) トークン取得（内部で自動更新されるが直接呼ぶことも可能）

```
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

6) 監査ログ初期化（signal → order → execution のテーブル）

```
from kabusys.data import schema as data_schema
from kabusys.data import audit
from kabusys.config import settings

conn = data_schema.init_schema(settings.duckdb_path)
audit.init_audit_schema(conn)

# または監査専用 DB を別ファイルで作る
# audit_conn = audit.init_audit_db("data/audit.duckdb")
```

---

## 実装上の注意点 / 補足

- J-Quants API クライアントは内部で固定間隔スロットリング（120 req/min）を実装しており、連続リクエスト時に自動で待機します。
- HTTP エラーに対してはリトライ（最大 3 回、指数バックオフ）を行います。401 はトークン自動リフレッシュを試みます（ただし無限再帰防止あり）。
- データ保存は冪等を意識しており、DuckDB の ON CONFLICT ... DO UPDATE を利用して既存行を更新します。
- すべてのタイムスタンプは UTC を基本に記録しています（監査ログ初期化時に SET TimeZone='UTC' を実行）。
- settings.env は "development", "paper_trading", "live" のいずれかでなければエラーになります。
- .env の自動読み込みはプロジェクトのルート（.git または pyproject.toml を探して決定）を基準に行われます。見つからない場合は自動ロードをスキップします。

---

## ディレクトリ構成

（リポジトリのルートを想定）

- src/
  - kabusys/
    - __init__.py
    - config.py  — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（取得 / 保存ロジック）
      - schema.py         — DuckDB スキーマ定義と初期化ユーティリティ
      - audit.py          — 監査ログ（signal/order_request/execution）定義と初期化
      - (その他: raw/processed 層に関するモジュール追加想定)
    - strategy/
      - __init__.py       — 戦略モジュール（拡張ポイント）
    - execution/
      - __init__.py       — 発注実行モジュール（拡張ポイント）
    - monitoring/
      - __init__.py       — 監視 / モニタリング（拡張ポイント）

その他（プロジェクトルート）:
- .env, .env.local （任意）
- pyproject.toml / setup.cfg / setup.py（パッケージ化用、存在する場合はルート検出に使用）

---

## 貢献 / 拡張のヒント

- strategy/ と execution/ は拡張用のエントリポイントです。戦略は signal_events を生成し、order_requests を経て発注処理（外部ブローカーコネクタ）に渡す設計が想定されています。
- 監査ログは削除しない前提です（ON DELETE RESTRICT）。監査トレーサビリティを壊さないように注意してください。
- DuckDB スキーマにカラム変更を加える際は既存データの移行手順を検討してください（DDL の互換性を確認）。

---

ライセンスや .env.example 等の補助ファイルがあればそれに従ってください。その他質問やドキュメントの追加希望があればお知らせください。