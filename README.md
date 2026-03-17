# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants / RSS などから市場データ・ニュースを取得して DuckDB に蓄積し、ETL・品質チェック・監査ログなどを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 必要な環境変数（設定）
- セットアップ手順
- 使い方（初期化・ETL・ニュース収集などの例）
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API を用いた日本株データ（株価日足・四半期財務・JPXカレンダー）の取得と DuckDB への蓄積機能を提供します。
- RSS フィードからニュースを収集・正規化して DuckDB に保存し、記事と銘柄コードの紐付けを行います。
- ETL パイプライン（差分取得・バックフィル・品質チェック）を備え、監査ログ（シグナル→発注→約定のトレース）用スキーマも提供します。
- レート制限、再試行（リトライ）、トークン自動リフレッシュ、SSRF 対策、XML の安全パース、Gzip サイズ制限など実運用を意識した設計になっています。

主な機能
- 環境変数管理（自動 .env ロード、保護、無効化フラグ）
- J-Quants クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存関数 save_*
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（data.pipeline）
  - 差分更新、バックフィル、品質チェックの実行（run_daily_etl など）
- ニュース収集（RSS）
  - RSS 取得・前処理、記事ID生成（URL正規化 + SHA256）、SSRF 対策、Gzip上限
  - raw_news への冪等保存、記事→銘柄コード紐付け
- 市場カレンダー管理（営業日判定、next/prev/get_trading_days、夜間更新ジョブ）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal_events / order_requests / executions）スキーマと初期化

---

必要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須）
- KABU_API_BASE_URL : kabuAPI のベースURL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャンネルID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH : SQLite（モニタリング用）パス（省略時 data/monitoring.db）
- KABUSYS_ENV : 実行環境（development / paper_trading / live）デフォルト development
- LOG_LEVEL : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

例: .env（.env.example を参考に作成）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

セットアップ手順（開発環境向け）
1. Python 環境を準備（推奨: 3.9+）
   - 例: python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール
   - 基本的に使用されているライブラリ:
     - duckdb
     - defusedxml
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください。

3. パッケージをインストール（開発モード）
   - プロジェクトルートで:
     ```
     pip install -e .
     ```
     （pyproject.toml / setup.py がある場合）

4. 環境変数を用意
   - .env / .env.local を作成するか、環境変数をエクスポートしてください。

---

初期化・簡単な使い方（コード例）
- 最小限の準備: DuckDB スキーマの初期化と日次 ETL の実行例

```python
from datetime import date
from kabusys.config import settings
from kabusys.data import schema, pipeline
import duckdb

# DuckDB の初期化（ファイルは settings.duckdb_path）
conn = schema.init_schema(settings.duckdb_path)

# 日次 ETL を実行（今日分を対象）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- 監査ログ用スキーマを別 DB に初期化する場合

```python
from kabusys.data import audit
audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

- J-Quants から直接データを取得して保存する例

```python
from kabusys.data import jquants_client as jq
import datetime

conn = jq.get_connection("data/kabusys.duckdb")  # または schema.init_schema(...)
# トークンを settings から自動取得して fetch -> save
records = jq.fetch_daily_quotes(date_from=datetime.date(2023,1,1), date_to=datetime.date(2023,1,31))
jq.save_daily_quotes(conn, records)
```

- ニュース収集を実行して DB に保存する例

```python
from kabusys.data import news_collector as nc
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
results = nc.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(results)  # {source_name: 新規保存件数}
```

- カレンダー夜間更新ジョブ

```python
from kabusys.data import calendar_management as cm
conn = schema.init_schema("data/kabusys.duckdb")
saved = cm.calendar_update_job(conn)
print("saved:", saved)
```

- 注意点
  - run_daily_etl 等は内部で J-Quants のトークンを settings.jquants_refresh_token から取得し自動リフレッシュします。
  - テスト時に自動 .env ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

データベース初期化 API（主なもの）
- kabusys.data.schema.init_schema(db_path) : DuckDB スキーマを作成して接続を返す
- kabusys.data.schema.get_connection(db_path) : 既存 DB への接続を返す
- kabusys.data.audit.init_audit_db(db_path) : 監査ログ用 DB を初期化して接続を返す

ETL / 実行 API（主なもの）
- kabusys.data.pipeline.run_daily_etl(conn, target_date=None, ...) : 日次 ETL（カレンダー・株価・財務・品質チェック）
- kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl : 個別 ETL ジョブ
- kabusys.data.news_collector.run_news_collection(conn, sources=None, known_codes=None) : RSS 収集と DB 保存

ユーティリティ
- kabusys.config.settings : アプリ設定（環境変数を透過的に取得）
  - settings.jquants_refresh_token / settings.kabu_api_password / settings.slack_bot_token / settings.duckdb_path など

---

ディレクトリ構成
（重要なファイル・モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                     : 環境変数・設定管理（.env 自動ロード）
    - data/
      - __init__.py
      - schema.py                   : DuckDB スキーマ定義・初期化
      - jquants_client.py           : J-Quants API クライアント（fetch/save）
      - pipeline.py                 : ETL パイプライン（差分取得・品質チェック）
      - news_collector.py           : RSS ニュース収集・保存
      - calendar_management.py      : 市場カレンダー管理・営業日判定
      - audit.py                    : 監査ログスキーマ（signal/order/execution）
      - quality.py                  : データ品質チェック
      - pipeline.py                 : ETL orchestration（上記）
    - strategy/
      - __init__.py                 : 戦略レイヤー（拡張ポイント）
    - execution/
      - __init__.py                 : 発注・ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py                 : 監視・メトリクス（拡張ポイント）

（上記以外にユーティリティや将来的なモジュールが追加される想定です）

---

運用上の注意
- J-Quants のレート制限（120 req/min）や HTTP エラーに対するリトライ・Backoff ロジックが実装されていますが、運用時は API 利用規約を確認してください。
- DuckDB はローカルファイル DB を前提にしているため、複数プロセスから同時アクセスする設計に注意してください（必要に応じて DB の配置や排他設計を行ってください）。
- XML / RSS 解析には defusedxml を使用し、SSRF / XML bomb に配慮しています。ただし外部リンクのフェッチやパースを行うコードを改修する際は同様の安全対策を忘れないでください。
- 監査ログ（audit）は削除しない想定です。運用ではディスク容量管理・アーカイブを検討してください。

---

貢献・拡張
- strategy / execution / monitoring パッケージは拡張ポイントです。戦略ロジック、実際の発注アダプタ、監視用のエクスポーター等を実装して統合してください。
- 新しいフィードや API を追加する際は、既存の安全性（URL 正規化、SSRF 検査、最大レスポンスサイズ制限など）を踏襲してください。

---

問題・問い合わせ
- リポジトリの issue に報告してください。エラーログや再現手順を添えていただけると助かります。

以上。必要があれば README に実行例の詳細や .env.example のテンプレート、CI 用手順、依存関係リスト（requirements.txt）を追加します。どの情報を優先して追記しますか？