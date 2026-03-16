# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
データ収集、DuckDB スキーマ管理、データ品質チェック、監査ログ（トレーサビリティ）機能などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群を含みます。

- J-Quants API からの市場データ取得（株価日足、財務データ、JPX マーケットカレンダー）
  - レート制限遵守、リトライ、トークン自動リフレッシュ、ページネーション対応
  - 取得時刻（UTC）を記録し Look-ahead Bias を抑止
- DuckDB を用いたスキーマ定義と初期化（Raw / Processed / Feature / Execution レイヤ）
- 監査ログ（signal → order_request → execution のトレース）用スキーマ
- データ品質チェック（欠損、異常スパイク、重複、日付不整合）
- 環境変数管理（.env / .env.local の自動読み込み、または OS 環境変数）

設計方針は冪等性・トレーサビリティ・運用安全性を重視しています。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）
  - 必須環境変数の取得とバリデーション
- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar()
  - DuckDB への保存用ユーティリティ: save_daily_quotes(), save_financial_statements(), save_market_calendar()
- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - init_schema(), get_connection()
  - テーブル群: raw_prices, raw_financials, market_calendar, prices_daily, features, signals, orders, trades, positions など多数
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルの初期化（init_audit_schema / init_audit_db）
  - 発注の冪等性と監査トレースのための設計
- データ品質チェック（kabusys.data.quality）
  - check_missing_data(), check_duplicates(), check_spike(), check_date_consistency(), run_all_checks()
  - QualityIssue オブジェクトで検出結果を返却

---

## セットアップ手順

前提
- Python 3.10 以上（型アノテーションで | を使用）
- DuckDB を利用するためネイティブバイナリが必要（pip で duckdb をインストール）

1. リポジトリをクローン / ワークツリーへ配置
2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb
   - （必要に応じて他の依存を追加）
4. 開発インストール（任意）
   - pip install -e .

環境変数 / .env
- プロジェクトルートに .env（および必要なら .env.local）を置くと自動で読み込まれます。
- 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。

必須環境変数（kabusys.config 参照）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

オプション（デフォルトあり）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（デフォルト: data/monitoring.db）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（抜粋・サンプル）

以下は基本的なワークフローの例です。

1) DuckDB スキーマを初期化する
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# デフォルトパスまたは settings.duckdb_path を利用
conn = init_schema(settings.duckdb_path)
# またはメモリ DB
# conn = init_schema(":memory:")
```

2) J-Quants から日足を取得して DuckDB に保存する
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

# モジュール内でトークンを自動取得 / 更新するため id_token は省略可能
records = fetch_daily_quotes(code="7203")  # 例: トヨタ (7203)
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

3) 財務データ / マーケットカレンダーの取得と保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements
from kabusys.data.jquants_client import fetch_market_calendar, save_market_calendar

fin = fetch_financial_statements(code="7203")
save_financial_statements(conn, fin)

cal = fetch_market_calendar()
save_market_calendar(conn, cal)
```

4) 監査ログスキーマの追加初期化
```python
from kabusys.data.audit import init_audit_schema

init_audit_schema(conn)
```

5) データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
```

注意点
- J-Quants API 呼び出しは 120 req/min に制限されており、内部でスロットリングとリトライを行います。
- get_id_token() はリフレッシュトークンから ID トークンを取得します（自動リフレッシュ対応）。
- データ保存関数は冪等になるよう ON CONFLICT DO UPDATE を使用しています。

---

## ディレクトリ構成

プロジェクトの主なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                # 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      # J-Quants API クライアント、保存ユーティリティ
      - schema.py              # DuckDB スキーマ定義・初期化
      - audit.py               # 監査ログ（トレーサビリティ）スキーマ
      - quality.py             # データ品質チェック
      - (その他: audit, news, ...)
    - strategy/
      - __init__.py
      # 戦略関連モジュールを配置する想定（未実装）
    - execution/
      - __init__.py
      # 発注・約定管理モジュールを配置する想定（未実装）
    - monitoring/
      - __init__.py
      # 監視・メトリクス関連モジュール（未実装）

README 以外の補助ドキュメント想定:
- .env.example (作成推奨): 必須環境変数のサンプル
- DataSchema.md, DataPlatform.md（設計ドキュメント想定）

---

## 運用上の注意 / 実運用向け留意点

- 本プロジェクトは実際の資金リスクを伴うため、paper_trading 環境や十分なテストでの検証を必須としてください。
- 発注処理や証券会社 API 経由の実行部分は別モジュールで実装し、監査ログとの連携（order_request_id の冪等性）を厳格に管理する必要があります。
- すべての TIMESTAMP は UTC を前提としています（監査ログ初期化時に TimeZone='UTC' を設定）。
- 環境変数（特にトークン・パスワード）は秘匿情報として管理してください（Vault 等の導入を推奨）。

---

もし README に追加してほしい内容（例: CI 設定、テスト手順、具体的な SQL サンプル、.env.example のテンプレートなど）があれば教えてください。必要に応じて追記します。