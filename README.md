# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants や RSS を用いたデータ収集、DuckDB ベースのスキーマ管理、ETL パイプライン、データ品質チェック、監査ログ（発注〜約定トレーサビリティ）などを提供します。

## 概要
KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から株価（日足）・財務・マーケットカレンダーを取得して DuckDB に保存
- RSS フィードからニュース記事を収集し正規化して保存、銘柄コードとの紐付け
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定、前後営業日の探索、夜間更新ジョブ）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ

設計上の特徴として、API レート制限の尊重・リトライとトークン自動リフレッシュ・入出力の冪等性（ON CONFLICT）などを重視しています。

## 主な機能一覧
- 環境変数管理（.env 自動読み込み、プロジェクトルート検出）
- J-Quants クライアント
  - 株価日足(fetch_daily_quotes)、財務(fetch_financial_statements)、マーケットカレンダー(fetch_market_calendar)
  - トークン取得/自動リフレッシュ（get_id_token）
  - レートリミッタ、リトライ（指数バックオフ）、401 時のリフレッシュ処理
- DuckDB スキーマ管理
  - init_schema: Raw / Processed / Feature / Execution レイヤーのテーブルとインデックスを作成
  - get_connection: 既存 DB へ接続
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー取得 → 株価差分 ETL → 財務差分 ETL → 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl 個別ジョブ
- ニュース収集（kabusys.data.news_collector）
  - fetch_rss: RSS 取得・解析（SSRF 対策、サイズ制限、gzip 対応、defusedxml）
  - save_raw_news / save_news_symbols / run_news_collection（バルク保存・銘柄抽出）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job: 夜間バッチで JPX カレンダーを差分更新
- 品質チェック（kabusys.data.quality）
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 監査ログスキーマ（kabusys.data.audit）
  - init_audit_schema / init_audit_db: signal_events / order_requests / executions 等を作成

## 要求環境 / 依存
- Python 3.10 以上（型記法に | を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, logging, datetime, pathlib など

インストール例（最低限の依存をインストール）:
```bash
python -m pip install "duckdb" "defusedxml"
# パッケージが配布されている前提なら:
# pip install -e .
```

（実際にはプロジェクトでの requirements.txt / setup.py / pyproject.toml に沿って依存を入れてください）

## 環境変数
kabusys は .env ファイル（プロジェクトルートの .env / .env.local）を自動で読み込みます（無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。主要な設定:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルトあり）
- KABUSYS_ENV: environment（development / paper_trading / live）デフォルト: development
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env の自動読み込みを無効化します（テスト用等）。

サンプル .env.example:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

## セットアップ手順（ローカルでの利用例）
1. Python 3.10+ を用意する
2. 依存をインストールする:
   - pip install duckdb defusedxml
   - （もし package 配布があれば pip install -e .）
3. プロジェクトルートに .env を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化:
   - Python REPL やスクリプトで次を実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # data ディレクトリがなければ自動作成
     ```
5. 監査ログ DB を別途用意する場合:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

## 使い方（基本的なコード例）

- 日次 ETL を実行する（簡単な例）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可能
print(result.to_dict())
```

- 個別ジョブ（価格 ETL）の実行:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_prices_etl

conn = init_schema("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date.today())
print(f"fetched={fetched}, saved={saved}")
```

- ニュース収集ジョブ:
```python
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
# known_codes を用意（例: 既知銘柄リストを DB から読み込む等）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- カレンダー更新ジョブ（夜間バッチ想定）:
```python
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- 品質チェックだけ実行する:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

## ディレクトリ構成（主要ファイル）
以下はパッケージ内の主なファイルと役割です（src/kabusys 以下）:

- __init__.py
  - パッケージ定義、バージョン
- config.py
  - 環境変数・設定読み込み（.env 自動ロード、Settings クラス）
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得・保存・認証）
  - news_collector.py: RSS 収集、記事正規化、DB保存、銘柄抽出
  - schema.py: DuckDB スキーマ定義と初期化（init_schema / get_connection）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - calendar_management.py: 市場カレンダー管理と夜間更新ジョブ
  - audit.py: 監査ログ（signal / order_request / executions）スキーマ初期化
  - quality.py: データ品質チェック（欠損、スパイク、重複、日付不整合）
- strategy/
  - __init__.py（戦略関連のエントリポイント）
- execution/
  - __init__.py（発注・証券会社 API 統合のエントリポイント）
- monitoring/
  - __init__.py（監視・アラート関連）

（上記以外にプロジェクトルートに .env/.env.local、pyproject.toml 等がある想定です）

## 設計上の注意点・運用メモ
- J-Quants API のレート制限（120 req/min）を守るため内部でスロットリングしています。大量データ取得時は制限に注意してください。
- ETL は冪等性を重視します（ON CONFLICT）。既存データの上書きが発生するためロールバック設計等を運用時に確認してください。
- ニュース収集では SSRF 対策（スキーム検証、プライベートアドレス除外）、XML パース安全化（defusedxml）、レスポンスサイズ制限を行っています。
- DuckDB の接続/トランザクションの扱いに注意。audit.init_audit_schema は transactional オプションを持ちます（デフォルト False）。
- 環境変数未設定時は Settings プロパティが ValueError を投げます。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動読み込みを無効化できます。

## 貢献 / 拡張案
- execution 層の証券会社 API 実装（kabuステーションや他ブローカーの adapter）
- strategy 層のバックテスト・ポートフォリオオプティマイザとの統合
- 監視・アラート（Slack 通知）やスケジューラ（cron / Airflow）との連携
- unit/integration テスト追加（外部 API はモック化）

---

この README はコードベースの主要機能をまとめた簡易ガイドです。実際の運用や商用利用の際は各モジュールのドキュメント（関数ドキュメンテーション、DataPlatform.md 想定の設計書）を参照して詳細な設定・運用手順を整備してください。