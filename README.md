# KabuSys

日本株のデータ収集・品質管理・自動売買基盤のコアライブラリです。  
J-Quants API / RSS ニュース等からデータを取得し、DuckDB に格納、ETL（差分更新）・品質チェック・監査ログ用スキーマを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python パッケージ（ライブラリ）です。

- J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを取得して DuckDB に保存
- RSS フィードからニュースを収集し前処理・銘柄紐付けして DuckDB に保存
- ETL パイプライン（差分更新・バックフィル）とデータ品質チェックを提供
- 監査ログ（シグナル→発注→約定までのトレース）用スキーマを提供
- レート制御、リトライ、トークン自動リフレッシュ、SSRF 対策など運用上の安全装置を備える

設計上のポイント:
- レート制限の順守（J-Quants: 120 req/min）
- リトライ（指数バックオフ、401 の場合はトークンリフレッシュ）
- データ取得時の fetched_at によるトレーサビリティ（Look-ahead Bias 防止）
- DuckDB への保存は冪等（ON CONFLICT / DO UPDATE / DO NOTHING）に対応
- RSS 収集での SSRF / XML 脆弱性対策（defusedxml, リダイレクト検査, 応答サイズ制限）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック（Settings クラス）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化

- J-Quants クライアント（kabusys.data.jquants_client）
  - get_id_token（リフレッシュトークンから ID トークン取得）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB へ冪等保存）
  - レートリミッタ、リトライ、401 自動リフレッシュ実装

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（gzip 対応、受信サイズ上限、defusedxml）
  - URL 正規化・記事ID生成（SHA-256 の先頭 32 文字）
  - テキスト前処理（URL 除去、空白正規化）
  - raw_news / news_symbols への一括保存（トランザクション、チャンク分割）
  - SSRF 対策（スキーム検証、リダイレクト先プライベートIP検査）

- スキーマ管理（kabusys.data.schema）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) でデータベース初期化（冪等）
  - get_connection(db_path)

- ETL パイプライン（kabusys.data.pipeline）
  - run_prices_etl / run_financials_etl / run_calendar_etl（差分更新・バックフィル）
  - run_daily_etl（市場カレンダー→株価→財務→品質チェックの一連処理）
  - 差分検出（DB の最終取得日を参照して必要分のみ取得）

- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（夜間バッチで JPX カレンダーを差分更新）

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions テーブルとインデックス
  - init_audit_schema / init_audit_db（UTC タイムゾーン固定）

- 品質チェック（kabusys.data.quality）
  - 欠損データ検出 / スパイク検出 / 重複チェック / 日付不整合チェック
  - run_all_checks でまとめて実行し QualityIssue のリストを返す

---

## セットアップ

前提
- Python 3.10+（typing の Union 表記などに合わせてください）
- 仮想環境推奨

インストール（例）

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   ※プロジェクトをパッケージ化している場合は `pip install -e .` 等でセットアップします。

環境変数
以下はこのライブラリが参照する主な環境変数（必須項目は明示）。

必須:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API パスワード
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL：DEBUG/INFO/…（デフォルト: INFO）
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 を設定すると .env の自動読み込みを無効化

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

自動 .env ロード:
- パッケージの config モジュールはプロジェクトルート（.git か pyproject.toml を探索）を元に .env / .env.local を自動で読み込みます。
- テスト等で自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単な例）

以下は代表的な操作のサンプルです。実行は Python スクリプトやジョブから行います。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ作成される）
conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

2) 監査ログスキーマ初期化（既存接続に追加）
```python
from kabusys.data import audit

# conn は init_schema の戻り値
audit.init_audit_schema(conn, transactional=True)
```

3) 日次 ETL 実行
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

4) ニュース収集ジョブ（RSS 収集→DB 保存→銘柄紐付け）
```python
from kabusys.data import news_collector, schema
import duckdb

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 事前に用意した有効銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) J-Quants API から株価を直接取得して保存
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved}")
```

6) カレンダー関連ヘルパー
```python
from kabusys.data import calendar_management as cm, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
d = date(2024, 1, 4)
print(cm.is_trading_day(conn, d))
print(cm.next_trading_day(conn, d))
```

---

## 運用上の注意点 / セキュリティ

- J-Quants 認証情報や kabuAPI のパスワード等は .env に平文で置くことになるため、アクセス制御を適切にしてください。
- RSS 取得では SSRF 対策・応答サイズ制限を実装していますが、外部データを扱うため十分な監視とエラーハンドリングを行ってください。
- DuckDB に格納されるタイムスタンプはモジュールにより UTC に正規化される箇所と、DB 側の現在時刻を利用する箇所があるため、UTC 前提でログ・監査を設計してください。
- run_daily_etl は各ステップで例外を独立に扱い、1ステップの失敗で全体が止まらない挙動です。結果の ETLResult.errors を確認して運用判断してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール構成:

- src/kabusys/
  - __init__.py
  - config.py                         # 環境設定 / .env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント（取得・保存）
    - news_collector.py                # RSS ニュース収集・保存・銘柄紐付け
    - schema.py                        # DuckDB スキーマ定義・初期化
    - pipeline.py                      # ETL パイプライン（差分更新・品質チェック）
    - calendar_management.py           # 市場カレンダー管理・営業日判定
    - audit.py                          # 監査ログスキーマ（signal/order/execution）
    - quality.py                        # 品質チェック
  - strategy/
    - __init__.py                       # 戦略関連（拡張ポイント）
  - execution/
    - __init__.py                       # 発注実装（ブローカー連携の実装場所）
  - monitoring/
    - __init__.py                       # 監視用コード（メトリクス収集等を想定）

---

## 拡張・統合のポイント

- strategy / execution / monitoring パッケージは拡張ポイントです。ここに戦略の実装、発注仲介（kabuステーション等）や監視アダプタを実装してください。
- ETL の id_token 注入や関数分割はテストしやすいように設計されています。ユニットテストで HTTP クライアントや _urlopen などをモックして利用できます。
- DuckDB スキーマは機能ごとに分かれていますので、必要に応じてカラムやインデックスを追加して性能改善を行ってください。

---

もし README にサンプルの .env.example や requirements.txt、あるいは運用スクリプト（systemd / cron / GitHub Actions など）向けの例が必要であれば、追って追加で作成します。必要な出力（英語版、簡潔版、具体的なデプロイ手順等）があれば教えてください。