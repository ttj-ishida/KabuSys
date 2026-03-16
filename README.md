# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）です。  
データ取得・スキーマ管理・データ品質チェック・監査ログ等、取引システムに必要な基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- J-Quants 等の外部 API からの市場データ取得（株価日足、財務諸表、マーケットカレンダー）
- DuckDB を用いた層別（Raw / Processed / Feature / Execution / Audit）データスキーマの初期化と接続管理
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- 簡易な環境変数管理（.env 自動読み込み、必須設定の検証）

設計上の主な意図:
- API レート制限・リトライ・トークン自動更新を考慮した堅牢なデータ取得
- DuckDB へ冪等的（ON CONFLICT DO UPDATE）に保存することによる一貫性
- データ品質チェックは Fail-Fast ではなく問題を収集して報告

---

## 主な機能一覧

- 環境設定
  - .env と OS 環境変数から設定を自動読み込み（.env.local を上書き）
  - 必須設定が未定義の場合は例外を発生させる `settings` オブジェクト

- データ取得（kabusys.data.jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - ID トークン取得（get_id_token）
  - レートリミット（120 req/min）遵守、指数バックオフ・リトライ、401 時のトークン自動更新
  - DuckDB へ保存するための save_* 関数（save_daily_quotes 等、冪等）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーの DDL を定義
  - init_schema(db_path) により DuckDB にテーブル・インデックスを作成
  - get_connection(db_path) で既存 DB に接続

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義
  - init_audit_schema(conn) を既存接続に追加、または init_audit_db(db_path) で専用 DB を作成

- データ品質チェック（kabusys.data.quality）
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks で一括実行し QualityIssue のリストを返す

- その他
  - strategy, execution, monitoring パッケージのプレースホルダ（拡張ポイント）

---

## 要求環境（例）

- Python 3.10+（型注釈に | を使用しているため 3.10 以上を推奨）
- pip により以下をインストール
  - duckdb
- インターネットアクセス（J-Quants API 等に接続する場合）

※ 実際のプロジェクトでは他に requests 等のライブラリが必要になる可能性があります。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します（任意）。

   $ python -m venv .venv
   $ source .venv/bin/activate  # Windows: .venv\Scripts\activate

2. 依存パッケージをインストールします（最低限 duckdb）。

   $ pip install duckdb

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

3. 環境変数を設定します。プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成してください。自動読み込みの挙動:
   - OS 環境変数が最優先
   - 次に `.env.local`（存在すれば上書き）
   - 次に `.env`
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 必要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API base URL（省略可、デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot Token（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: one of {development, paper_trading, live}（デフォルト: development）
   - LOG_LEVEL: one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（コード例）

以下は基本的な利用例です。実行する Python スクリプト内で使用できます。

- DuckDB スキーマの初期化と接続

```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path はデフォルトで "data/kabusys.duckdb"
conn = init_schema(settings.duckdb_path)
```

- J-Quants から日足を取得して DuckDB に保存

```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# 例: 特定銘柄・期間を指定
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"{n} レコードを保存しました")
```

- 財務データ、マーケットカレンダーの取得と保存

```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

- 監査ログスキーマを追加（既存の接続に対して）

```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)  # conn は init_schema が返した接続等
```

- データ品質チェックを実行

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
    for row in issue.rows:
        print("  sample:", row)
```

- 直接 ID トークンを取得する（必要時）

```python
from kabusys.data.jquants_client import get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用
```

注意: jquants_client の fetch 系は内部でレート制限とリトライを行います。API の使用回数上限に留意してください。

---

## ディレクトリ構成

リポジトリの主なファイル構成（抜粋、src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - schema.py              # DuckDB スキーマ定義・初期化
    - audit.py               # 監査ログスキーマ（signal/order/execution）
    - quality.py             # データ品質チェック
    - additional modules...   # 今後の拡張ポイント
  - strategy/
    - __init__.py            # 戦略ロジック（拡張ポイント）
  - execution/
    - __init__.py            # 発注関連（拡張ポイント）
  - monitoring/
    - __init__.py            # 監視・アラート（拡張ポイント）

説明:
- data/*: データプラットフォームに関する実装（取得 / 永続化 / 品質 / 監査）
- strategy/*, execution/*, monitoring/*: 戦略ロジックや発注・監視機能のための拡張エントリポイント

---

## 実運用上の注意点

- 環境変数に機密情報（トークン・パスワード）を置くため、リポジトリに .env をコミットしないでください。
- DuckDB ファイルやログはバックアップ・権限管理を考慮してください。
- J-Quants 等 API 利用にあたっては利用規約・レート制限を確認してください。
- KABUSYS_ENV を `live` にすると実運用想定のフラグが有効になります。paper_trading など運用ポリシーを環境で切り替えてください。
- run_all_checks 等は ETL パイプラインの一部として定期実行・Slack 通知等を組み合わせることを推奨します。

---

## 拡張ポイント / 今後の実装例

- strategy パッケージ内で特徴量テーブル (features, ai_scores) を生成する処理
- execution パッケージでの kabuステーション連携（注文送信／約定収集）
- monitoring での Slack 通知・メトリクス収集（settings.slack_bot_token を利用）
- テスト・CI、型チェック（mypy）、静的解析（flake8）などの整備

---

必要であれば README にサンプル .env.example、CI 設定、より詳細な API 使用例（ページネーションの注意点やログ設定）を追加できます。希望があれば教えてください。