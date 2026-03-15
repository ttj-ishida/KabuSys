# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（プロトタイプ）。  
このリポジトリはデータ取得、スキーマ管理、監査ログなど自動売買システムの基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような目的で設計されています。

- J-Quants API 等から市場データ（株価、財務、取引カレンダー等）を取得するクライアント
- DuckDB を用いたデータスキーマ（Raw / Processed / Feature / Execution）の定義・初期化
- 監査（トレーサビリティ）テーブル群の定義・初期化
- 環境変数ベースの設定管理（.env / .env.local 自動読み込み）
- レートリミット、再試行、トークン自動更新など API 呼び出しの堅牢化機能

設計上の注意点：
- J-Quants API のレート制限（120 req/min）を尊重するレートリミッタ実装
- 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動ロード（OS環境変数優先）
  - 必須環境変数をプロパティで取得（例: settings.jquants_refresh_token）
  - KABUSYS_ENV、LOG_LEVEL の検証

- J-Quants API クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから id_token を取得）
  - fetch_daily_quotes（株価日足、ページネーション対応）
  - fetch_financial_statements（四半期財務データ）
  - fetch_market_calendar（JPX マーケットカレンダー）
  - save_* 系関数で DuckDB に冪等保存（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル群を作成
  - インデックス作成、ファイルパスの自動ディレクトリ生成
  - init_schema(db_path) / get_connection(db_path)

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の監査用テーブル
  - order_request_id を冪等キーとして二重発注防止
  - init_audit_schema(conn) / init_audit_db(db_path)

- プレースホルダーパッケージ
  - strategy, execution, monitoring パッケージの雛形

---

## セットアップ手順

前提: Python 3.10 以上（ソース内で型ヒントに `|`（PEP 604）を使用しているため）

1. リポジトリをクローン
   ```
   git clone <このリポジトリのURL>
   cd <リポジトリ>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 依存ライブラリをインストール
   - 本プロジェクトで明示的に使用している外部ライブラリは duckdb です。
   ```
   pip install duckdb
   ```
   - 将来的に requirements.txt / pyproject.toml があれば、そちらを利用してください:
   ```
   pip install -r requirements.txt
   # または
   pip install -e .
   ```

4. 環境変数を設定
   - プロジェクトルートの `.env` または `.env.local` に必要な値を設定すると、自動的に読み込まれます（デフォルト）。  
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD : kabuステーション API のパスワード
- SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID : Slack チャネル ID

オプション（デフォルトあり）:
- KABUSYS_ENV : development / paper_trading / live （デフォルト: development）
- LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL （デフォルト: INFO）
- KABU_API_BASE_URL : kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite のパス（デフォルト: data/monitoring.db）

例: `.env`
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単な例）

以下は主要なユースケース（DuckDB 初期化 → データ取得 → 保存）の例です。

- DuckDB スキーマを初期化して接続を取得
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数から取得されます
conn = schema.init_schema(settings.duckdb_path)
```

- J-Quants から日足を取得して raw_prices に保存
```python
from kabusys.data import jquants_client

# 日付指定は datetime.date オブジェクト
from datetime import date
records = jquants_client.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
saved_count = jquants_client.save_daily_quotes(conn, records)
print(f"保存した件数: {saved_count}")
```

- 財務データやマーケットカレンダーも同様
```python
fins = jquants_client.fetch_financial_statements(code="7203")
jquants_client.save_financial_statements(conn, fins)

calendar = jquants_client.fetch_market_calendar()
jquants_client.save_market_calendar(conn, calendar)
```

- 監査ログ（Audit）を初期化する
```python
from kabusys.data import audit

# 既存の conn に監査テーブルを追加
audit.init_audit_schema(conn)

# または監査専用 DB を初期化
audit_conn = audit.init_audit_db("data/audit.duckdb")
```

- 環境設定の利用
```python
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.is_live)  # KABUSYS_ENV が 'live' の場合 True
```

注意点:
- jquants_client は内部でレートリミットと再試行を行います（120 req/min、指数バックオフ、401 時はトークン自動更新を試行）。
- データ保存時は fetched_at を UTC で記録し、将来のバイアスを防ぐ設計です。
- DuckDB に対する INSERT は ON CONFLICT DO UPDATE により冪等化されています。

---

## ディレクトリ構成

リポジトリの主要なファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py       # J-Quants API クライアント（取得・保存ロジック）
      - schema.py               # DuckDB スキーマ定義・初期化
      - audit.py                # 監査ログ（signal, order_request, executions）
      - audit.py
      - ...                     # 将来的に data 内の他モジュールが入る
    - strategy/
      - __init__.py             # 戦略モジュール（雛形）
    - execution/
      - __init__.py             # 発注・ブローカー連携（雛形）
    - monitoring/
      - __init__.py             # 監視用モジュール（雛形）

主要ファイルの説明
- src/kabusys/config.py
  - .env の自動読み込み機能、settings オブジェクトを提供。プロジェクトルートは .git または pyproject.toml を基準に探索します。
- src/kabusys/data/jquants_client.py
  - API との通信、レート制御、リトライ、データ保存ユーティリティを実装。
- src/kabusys/data/schema.py
  - DuckDB のテーブル定義（DDL）をまとめ、init_schema() で DB を初期化します。
- src/kabusys/data/audit.py
  - 監査用の DDL と初期化ロジック。

---

## 運用上の注意・ベストプラクティス

- 本リポジトリはインフラやブローカー連携の完全な実装を含みません。実際の発注や運用時は、実環境（live）フラグの扱い、リスク管理、二重発注防止の確認を必ず行ってください。
- KABUSYS_ENV を production 的に使う場合は `live` を設定し、安全措置（例えばオフラインでのドライラン、追加のガードレール）を導入してください。
- .env ファイルには秘密情報が含まれるため、git 等で管理しないようにしてください（.gitignore に追加）。

---

## 今後の拡張案（参考）

- kabu ステーションやその他証券会社 API 向けの concrete 発注実装（execution）
- strategy レイヤーに複数戦略の実装とバックテスト機能
- monitoring モジュールで SQL ベースの監視ダッシュボード／アラート
- CI / テストケース（ユニットテスト・統合テスト）

---

必要であれば README にサンプル .env.example、ユニットテストの実行方法、デプロイ手順（Dockerfile、systemd サービスの例）などを追加します。どの情報を優先して追加しますか？