# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）

本リポジトリは、J-Quants や kabuステーション 等の外部データ・ブローカーと連携して、
データ取得・保存（DuckDB）・監査ログ・データ品質チェックを行うための基盤モジュール群を含みます。
バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータレイヤ（Raw / Processed / Feature / Execution）と
監査ログ（トレーサビリティ）・データ品質チェック機能を提供するライブラリ群です。

主な用途:
- J-Quants API から株価・財務・市場カレンダー等を取得して DuckDB に永続化
- 監査ログ（シグナル→発注→約定の追跡）用スキーマを提供
- データ品質チェックを通じて ETL の整合性を検証

設計上のポイント:
- API レート制御・リトライ・トークンリフレッシュを備えた J-Quants クライアント
- DuckDB を用いたスキーマ（冪等に作成／更新可能な INSERT ロジック）
- 監査テーブルは削除しない前提で設計（ON DELETE RESTRICT）
- すべての timestamp は UTC で保存する前提

---

## 機能一覧

- 環境設定管理
  - .env/.env.local 自動ロード（プロジェクトルートの検出: .git / pyproject.toml を基準）
  - 必須設定を明示する Settings インターフェース（settings オブジェクト）
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

- データ取得（J-Quants クライアント）
  - 日足（OHLCV）取得（fetch_daily_quotes）
  - 財務（四半期）取得（fetch_financial_statements）
  - JPX マーケットカレンダー取得（fetch_market_calendar）
  - レートリミット（120 req/min）・リトライ（指数バックオフ）・401でのトークン自動リフレッシュ対応
  - 取得履歴（fetched_at）を UTC で記録

- DuckDB スキーマ / 初期化
  - Raw / Processed / Feature / Execution の各テーブル定義
  - インデックス定義
  - init_schema / get_connection での接続管理

- 監査ログ（Audit）
  - signal_events, order_requests, executions のテーブル・インデックス定義
  - init_audit_schema / init_audit_db による初期化
  - 冪等キー（order_request_id）による重複発注防止設計

- データ品質チェック
  - 欠損データ検出（OHLC の欠損）
  - 異常値（スパイク）検出（デフォルト閾値: 50%）
  - 主キー重複チェック
  - 日付不整合チェック（未来日付 / 非営業日データ）
  - run_all_checks でまとめて実行し QualityIssue のリストを返す

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | Y` を使用しているため）
- Git（プロジェクトルート検出のため推奨）
- 必要なパッケージ: duckdb

1. リポジトリをクローン / 取得
   - git clone ... またはソース一式を配置

2. 仮想環境を作成（推奨）
   - unix/mac:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb

   備考:
   - このリポジトリに requirements.txt が無い場合は上記の最低限のみで動きます。
   - Slack 通知や kabuステーション と連携するコードを追加する場合は、別途 slack-sdk 等の依存が必要になる可能性があります。

4. 環境変数を設定
   - プロジェクトルート（.git や pyproject.toml のある場所）に `.env` を置くと自動読み込みされます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

必須環境変数（実行に必要な値。欠けていると ValueError を送出します）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルト値あり）:
- KABUSYS_ENV (development | paper_trading | live) デフォルト: development
- LOG_LEVEL (DEBUG/INFO/...) デフォルト: INFO
- DUCKDB_PATH デフォルト: data/kabusys.duckdb
- SQLITE_PATH デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)

例: .env の最小例（安全のため実際のトークンは設定しないでください）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本的な流れとサンプル）

以下は主要 API の簡単な使用例です。Python REPL やスクリプトで実行してください。

1) DuckDB スキーマ初期化
```
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数から決まります（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
```
- メモリDB を使う場合: init_schema(":memory:")

2) J-Quants から日足を取得して保存
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 銘柄コードや期間を指定して取得
records = fetch_daily_quotes(code="7203")  # トヨタなど
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

3) 財務データ / 市場カレンダーの取得と保存
```
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログの初期化（既存の conn に追加）
```
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```
- 監査専用 DB を別に作る場合:
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

5) データ品質チェックの実行
```
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)  # 全期間チェック
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

エラー／例外
- settings で必要な環境変数が無い場合、プロパティアクセス時に ValueError が投げられます。
- J-Quants リクエストはリトライやトークン自動更新の仕組みを内蔵していますが、ネットワークや認証エラーは最終的に例外となります。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（抜粋）:

- src/kabusys/
  - __init__.py            (パッケージメタ情報)
  - config.py              (.env 自動ロード・Settings)
  - execution/             (発注・約定関連モジュール置き場、空 __init__)
  - strategy/              (戦略関連モジュール置き場、空 __init__)
  - monitoring/            (監視関連、空 __init__)
  - data/
    - __init__.py
    - jquants_client.py    (J-Quants API クライアント: 取得・保存ロジック)
    - schema.py            (DuckDB スキーマ定義と init_schema / get_connection)
    - audit.py             (監査ログスキーマ初期化)
    - quality.py           (データ品質チェック)
    - (その他のデータモジュール)

補足:
- プロジェクトルートに `.env` / `.env.local` を置くと config.py により自動読み込みされます。
  読み込み順は OS 環境変数 > .env.local > .env です。
- .env パーサは export 形式やクォート・エスケープ・コメントに対応しています。

---

## 開発メモ / 注意事項

- Python のバージョンは 3.10 以上を想定しています（型表記の互換性）。
- J-Quants API のレート制御はモジュール内に固有実装があり、外側での追加制御も考慮してください（複数プロセスでの同時アクセスは別途制御が必要です）。
- DuckDB のスキーマ設計は冪等性を重視していますが、外部から直接 DB を操作する場合は一貫性に注意してください。
- 監査ログは削除しない運用を前提に設計されています。更新の際は updated_at を適切に設定してください。

---

もし README に追加したい具体的なコマンド例、CI 設定、パッケージ化手順（setup.cfg / pyproject.toml を含めた配布方法）などがあれば教えてください。それに合わせて追記・修正します。