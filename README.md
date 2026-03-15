# KabuSys

日本株自動売買システム用のコアライブラリ（データ取得・スキーマ定義・監査ログ・設定管理など）。

このリポジトリは、J-Quants API から市場データや財務データを取得して DuckDB に永続化し、戦略層／実行層へ渡すための基盤機能を提供します。また、発注から約定に至る監査ログ（トレーサビリティ）を保持する仕組みも含まれます。

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得
  - API レート制限（120 req/min）を尊重する内部 RateLimiter
  - リトライ / 指数バックオフ実装（最大 3 回、408/429/5xx 対応）
  - 401 受信時は自動トークンリフレッシュ（1 回）
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 防止
  - DuckDB への冪等な INSERT（ON CONFLICT DO UPDATE）

- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution レイヤーを含むテーブル定義
  - インデックス定義、外部キー・制約を含む堅牢な DDL
  - スキーマ初期化用 API（init_schema, get_connection）

- 監査ログ（Audit）
  - signal → order_request → execution のチェーンを UUID でトレース
  - 発注の冪等キー（order_request_id）管理、ステータス履歴保存
  - UTC タイムスタンプ、削除禁止（監査前提）

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須 env のラッパー（settings）を提供（不足時は ValueError）
  - テスト用に自動読み込み無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）

---

## 必要条件

- Python 3.10 以上（型ヒントで PEP 604 の `|` を使用）
- 依存パッケージ（例）:
  - duckdb
- 標準ライブラリ（urllib, logging, json など）を使用

インストール例:
```
python -m pip install duckdb
# （プロジェクトをローカルで editable install する場合）
pip install -e .
```

---

## 環境変数（主なキー）

このパッケージは環境変数から設定を読み込みます（.env/.env.local 自動ロードを行います。無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。

必須（Settings で _require_ が投げられるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL: `DEBUG` | `INFO` | `WARNING` | `ERROR` | `CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視系 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（値は任意）

.example（簡易）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python と依存パッケージをインストール
   ```
   python -m pip install --upgrade pip
   pip install duckdb
   # 開発用途なら:
   pip install -e .
   ```

3. .env ファイルをプロジェクトルートに作成（上記の必須キーを設定）
   - `.env` に機密情報を置く場合は .gitignore に含めることを推奨します。
   - 環境変数を直接渡すか、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自分で管理してもよいです。

4. DuckDB スキーマを初期化
   Python REPL かスクリプトで:
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")  # ファイルを作成・初期化して接続を返す
   # または既存DBへ接続
   conn2 = get_connection("data/kabusys.duckdb")
   ```

5. 監査ログテーブルを追加（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # conn は init_schema の戻り値など
   # または専用ファイルに init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（よく使う API の例）

- J-Quants の ID トークンを取得
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用して取得
```

- 日足データを取得して DuckDB に保存
```python
from datetime import date
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
n = save_daily_quotes(conn, records)
print(f"保存件数: {n}")
```

- 財務データ・マーケットカレンダーの取得と保存
```python
from kabusys.data.jquants_client import fetch_financial_statements, save_financial_statements, fetch_market_calendar, save_market_calendar

financials = fetch_financial_statements(code="7203")
save_financial_statements(conn, financials)

calendar = fetch_market_calendar()
save_market_calendar(conn, calendar)
```

- 監査ログ（order_requests / executions）を操作する場合
  - 監査テーブルは init_audit_schema により作成します。アプリケーション側で UUID を発行して signal_events / order_requests / executions に挿入してください（このライブラリはテーブル定義と初期化を提供します）。

---

## 実装上の注意点

- 自動 .env ロード:
  - パッケージ起点（src/kabusys/config.py の __file__ を基準）でプロジェクトルート（.git または pyproject.toml）を探索します。CWD に依存しません。
  - 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。

- レート制限・リトライ:
  - J-Quants API は 120 req/min に制限されています。本クライアントは内部で間隔制御（_RateLimiter）を行います。
  - ネットワーク障害や 429/408/5xx に対して指数バックオフで再試行します。
  - 401 時は保存されたリフレッシュトークンから ID トークンを再取得して 1 回だけリトライします。

- データの冪等性:
  - raw_* テーブル・市場カレンダー等に対しては ON CONFLICT DO UPDATE を使用して重複挿入を回避します。
  - fetched_at は UTC で記録され、いつそのデータが取得されたかをトレースできます。

- 型・バリデーション:
  - DuckDB の DDL には CHECK 制約が多数含まれます（負値や null チェックなど）。挿入前に値を整形してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                 - パッケージ初期化（__version__ 等）
  - config.py                   - 環境変数／設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py         - J-Quants API クライアント（取得・リトライ・保存）
    - schema.py                 - DuckDB スキーマ定義・初期化（Raw/Processed/Feature/Execution）
    - audit.py                  - 監査ログスキーマ（signal_events / order_requests / executions）
    - audit.py                  - 監査 DB 初期化ユーティリティ
    - (他に audit/monitoring 用モジュール等)
  - strategy/
    - __init__.py               - 戦略層のエントリ（将来の拡張ポイント）
  - execution/
    - __init__.py               - 実行（ブローカー接続・注文送信）のエントリ（将来の拡張）
  - monitoring/
    - __init__.py               - 監視／メトリクス関連（将来の拡張）

補足:
- schema.py 内に SQL DDL がまとまっており、init_schema() により一括でテーブルとインデックスを作成します。
- audit.py は監査用の DDL とインデックスを提供し、init_audit_schema(conn) で既存の conn に追記できます（UTC タイムゾーン設定あり）。

---

## 開発・運用上のヒント

- 機密情報（トークンやパスワード）は .env や環境変数で管理し、リポジトリにコミットしないでください。
- 本ライブラリはデータ取得・保存・スキーマ定義の基盤に注力しています。実際の戦略ロジック・発注実装（ブローカーAPI呼び出し等）は strategy/ execution 層で拡張してください。
- 単体テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしてテスト用の環境を自由にセットアップできます。
- DuckDB ファイルは軽量で高速ですが、本番での長期運用時はバックアップ戦略を検討してください。

---

必要であれば、README に「API リファレンス」「サンプルスクリプト」「運用チェックリスト」など追記します。どの項目を追加したいか教えてください。