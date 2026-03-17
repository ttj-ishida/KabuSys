# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants API から市場データや財務データ、JPX カレンダーを取得して DuckDB に保存し、品質チェックやニュース収集、監査ログ（発注→約定トレーサビリティ）などの基盤機能を提供します。

主な想定用途:
- 日次 ETL（株価・財務・カレンダーの差分取得と保存）
- ニュース（RSS）収集・銘柄紐付け
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- DuckDB を用いたデータレイク（Raw / Processed / Feature / Execution 層）
- 発注／約定の監査ログ管理（監査用スキーマ）

対応 Python バージョン: Python 3.10 以降（型ヒントで | 演算子を使用）

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local をプロジェクトルートから自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須設定は Settings 経由で明示的に取得

- J-Quants クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット（120 req/min）制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得ロジック（最終取得日に基づく自動算出 + backfill）
  - 日次 ETL エントリ（run_daily_etl） + 個別ジョブ（prices, financials, calendar）
  - 品質チェックとの統合

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC）検出
  - スパイク検出（前日比閾値）
  - 重複検出（主キー）
  - 日付整合性チェック（未来日付 / 非営業日のデータ）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理（URL 除去・空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）
  - SSRF 防止、Gzip/サイズ制限、XML の安全パース（defusedxml）
  - DuckDB への冪等保存（INSERT ... RETURNING）と銘柄紐付け

- スキーマ管理（kabusys.data.schema / audit）
  - DuckDB 向けの完全なスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化ユーティリティ

---

## セットアップ手順

1. リポジトリをクローン（もしくはソースを配置）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```
   python -m venv .venv
   # Linux/macOS
   source .venv/bin/activate
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   ```

3. 必要パッケージをインストール
   - 最低依存: duckdb, defusedxml
   ```
   pip install duckdb defusedxml
   ```
   - 将来的にパッケージ化している場合は:
   ```
   pip install -e .
   ```

4. 環境変数（.env）を用意する
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（デフォルトで OS 環境変数が優先、.env.local は .env の上書き）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID
   - 任意・デフォルト:
     - KABUSYS_ENV (development, paper_trading, live) — デフォルト: development
     - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) — デフォルト: INFO
     - KABUS_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   - テストや CI で自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（簡単なサンプル）

以下はライブラリを使って DB 初期化・日次 ETL を実行する例です。

1. DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.config import settings
from kabusys.data import schema

# settings.duckdb_path は .env の DUCKDB_PATH を参照（デフォルト: data/kabusys.duckdb）
conn = schema.init_schema(settings.duckdb_path)
```

2. 日次 ETL を実行する
```python
from kabusys.data import pipeline

# id_token を明示的に渡すことも可能（省略時は内部キャッシュを使用）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

3. ニュース収集ジョブ（RSS）を実行する
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
# known_codes: 銘柄抽出のために有効なコードセットを渡す（省略可能）
known_codes = {"7203", "6758", "9433"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

4. 監査ログ（audit）スキーマ初期化
```python
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

5. J-Quants の id_token を取得する（必要に応じて）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

注意:
- run_daily_etl は内部で market_calendar を先に取得して営業日に調整し、prices/financials の差分取得を行います。
- 品質チェック（quality）は ETL の一部として実行可能（デフォルト ON）。重大度の高い問題は ETLResult に記録されます。

---

## 開発者向けメモ

- 自動 .env ロードはプロジェクトルート（__file__ の親階層で .git または pyproject.toml を探索）から行います（CWD に依存しない）。
- .env パーサは export プレフィックスやクォート、コメント（#）を適切に扱います。
- J-Quants API 呼び出しは内部で固定間隔の RateLimiter（120 req/min）とリトライ（指数バックオフ）を行います。
- ニュース収集では SSRF 対策、gzip 解凍制限、defusedxml を用いた安全な XML パースを実施しています。
- DuckDB への保存は基本的に冪等（ON CONFLICT / DO UPDATE / DO NOTHING）で設計されています。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント / 保存ロジック
    - news_collector.py               — RSS ニュース収集・前処理・DB 保存
    - schema.py                       — DuckDB スキーマ定義・初期化
    - pipeline.py                     — ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py          — 市場カレンダー管理・営業日判定
    - audit.py                        — 監査ログ（発注→約定トレーサビリティ）スキーマ
    - quality.py                      — データ品質チェック
  - strategy/                         — 戦略層（骨組み）
    - __init__.py
  - execution/                        — 発注実行層（骨組み）
    - __init__.py
  - monitoring/                       — 監視・モニタリング（骨組み）

---

## 注意事項（セキュリティ・運用）

- API トークンやパスワードは必ず環境変数で管理し、リポジトリにコミットしないでください。
- .env ファイルを使う場合は .gitignore に追加してください。
- J-Quants API のレート制限を遵守するため、外部から直接大量リクエストを行わないよう注意してください（クライアント側でも制御済み）。
- DuckDB ファイルはバックアップを推奨します。監査ログや約定情報は削除しない前提で設計されています。
- RSS の取得先は信頼できるソースのみに限定してください（SSRF 対策は実装されていますが運用上の注意が必要です）。

---

README はここまでです。必要であれば、CLI/サービス起動スクリプトのサンプル（systemd / cron / Airflow 用）や、より具体的な ETL スケジュール例、品質チェックの詳細な解説を追加できます。どの内容を追加しますか？