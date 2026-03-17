# KabuSys

日本株向けの自動売買基盤ライブラリ（KabuSys）。J-Quants / kabuステーション 等の外部 API からデータを取得して DuckDB に蓄積し、ETL／品質チェック／ニュース収集／カレンダー管理／監査ログの初期化等を行うためのモジュール群を提供します。

---

## 概要

KabuSys は以下を目的とした Python ライブラリです。

- J-Quants API から株価（OHLCV）、財務データ、JPX マーケットカレンダーを安全に取得する
- DuckDB を使ったデータレイク（Raw / Processed / Feature / Execution 層）のスキーマ定義・初期化
- 日次 ETL（差分取得・バックフィル・品質チェック）のパイプライン
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、サイズ制限、トラッキング除去）
- JPX カレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ（シグナル→発注→約定をトレース可能にする監査スキーマ）

設計上の特徴として、API のレート制御・リトライ・認証トークン自動リフレッシュ・冪等な DB 書き込み等に配慮しています。

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API クライアント（レートリミット、再試行、トークン自動更新、ページネーション対応）
  - fetch/save: 日足 (daily_quotes)、財務データ (statements)、マーケットカレンダー
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化

- data.pipeline
  - 日次 ETL（run_daily_etl）
  - 差分取得、バックフィル、品質チェックの統合実行

- data.news_collector
  - RSS フィード収集（SSRF 対策、gzip 限度、XML セキュアパーサ）
  - 記事ID の正規化ハッシュ化、raw_news への冪等保存、銘柄コード抽出と news_symbols への紐付け

- data.calendar_management
  - 市場カレンダーの差分更新ジョブ（calendar_update_job）
  - 営業日判定 / next_trading_day / prev_trading_day / get_trading_days / is_sq_day

- data.quality
  - 欠損・スパイク・重複・日付不整合のチェック（QualityIssue オブジェクトを返却）
  - run_all_checks で一括実行

- data.audit
  - シグナル／発注／約定の監査スキーマ初期化（init_audit_schema / init_audit_db）
  - 監査トレースに必要なテーブルとインデックスを提供

- config
  - .env または環境変数からの設定読み込み（自動ロード機能、必要な環境変数チェック）

---

## 動作環境 / 依存

- Python >= 3.10（型注釈で `X | None` を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# もしパッケージとして配布されていれば:
# pip install -e .
```

その他、実運用で Slack 連携や kabu ステーション API を使う場合はそれぞれの依存や SDK が必要になる可能性があります。

---

## 環境変数（主な設定項目）

config.Settings によって読み込まれる主な環境変数:

- J-Quants / 認証
  - JQUANTS_REFRESH_TOKEN (必須)

- kabuステーション API
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)

- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)

- データベースパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)

- 動作モード / ログ
  - KABUSYS_ENV (development | paper_trading | live、デフォルト: development)
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL、デフォルト: INFO)

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml がある場所）配下にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡単な .env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / ソース取得
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成と有効化
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージのインストール
   ```
   pip install duckdb defusedxml
   # あるいはプロジェクトの requirements を使う（存在する場合）
   # pip install -r requirements.txt
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 必須の値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定します。

5. DuckDB スキーマの初期化
   - 以下のようにして初期化します（Python REPL またはスクリプト）:
   ```python
   from kabusys.data import schema
   from kabusys.config import settings
   conn = schema.init_schema(settings.duckdb_path)
   ```

6. 監査ログ DB の初期化（必要な場合）
   ```python
   from kabusys.data import audit
   from kabusys.config import settings
   # 監査を専用DBに分ける場合
   audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的なユースケース）

以下はライブラリを直接 Python から呼び出す例です。プロダクションではこれらを cron / Airflow / 任意のジョブランナーで定期実行します。

- 日次 ETL を実行する
```python
from kabusys.data import schema, pipeline
from kabusys.config import settings
conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブを実行する
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.get_connection(settings.duckdb_path)  # スキーマが作成済みであること
# known_codes を用意（存在する銘柄コードのセット）
rows = conn.execute("SELECT DISTINCT code FROM prices_daily").fetchall()
known_codes = {r[0] for r in rows}
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- カレンダーの夜間更新ジョブ（calendar_update_job）
```python
from kabusys.data import calendar_management, schema
from kabusys.config import settings
conn = schema.get_connection(settings.duckdb_path)
saved = calendar_management.calendar_update_job(conn)
print("saved:", saved)
```

- 監査スキーマの追加初期化（既存接続に対して）
```python
from kabusys.data import audit, schema
conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

- 品質チェックを個別に実行
```python
from kabusys.data import quality, schema
from datetime import date
conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    - 環境変数・設定管理（.env 自動読み込み・バリデーション）
  - data/
    - __init__.py
    - schema.py                   - DuckDB スキーマ定義・初期化
    - jquants_client.py           - J-Quants API クライアント（取得・保存）
    - pipeline.py                 - 日次 ETL パイプライン
    - news_collector.py           - RSS ニュース収集・保存・銘柄抽出
    - calendar_management.py      - 市場カレンダー管理／営業日ロジック
    - quality.py                  - データ品質チェック
    - audit.py                    - 監査ログスキーマ初期化
    - pipeline.py                 - ETL パイプライン（差分更新・品質チェック）
  - strategy/
    - __init__.py                 - 戦略モジュールプレースホルダ
  - execution/
    - __init__.py                 - 発注／実行関連プレースホルダ
  - monitoring/
    - __init__.py                 - 監視モジュールプレースホルダ

---

## 注意点 / トラブルシューティング

- Python バージョン
  - 型注釈に `X | None` などを使用しているため Python >= 3.10 を推奨します。

- 環境変数の自動読み込み
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込みます。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- J-Quants API の制限
  - ライブラリは 120 req/min のレート制御を行いますが、API の仕様変更やネットワーク状況により調整が必要になる場合があります。

- DuckDB スキーマ変更
  - init_schema は冪等ですが、スキーマ定義を変更した場合はマイグレーション戦略を検討してください（現状は単純な CREATE IF NOT EXISTS を用いています）。

- RSS フィードの制限
  - RSS レスポンスサイズ（デフォルト 10MB）を超える場合は取得をスキップします。gzip の取り扱いにも注意してください。

---

## 開発 / 貢献

- テストの追加、品質チェックの拡張、戦略・実行モジュールの実装や broker adapter の追加などを歓迎します。
- 新しい機能を追加する場合は既存の設計原則（冪等性、セキュリティを考慮した外部アクセス、トレーサビリティ）を尊重してください。

---

以上が KabuSys の README です。必要であれば以下を追加で作成できます：
- .env.example のファイル
- CLI ラッパー（ETL / calendar / news をコマンドで起動するスクリプト）
- docker-compose / systemd サービス定義のサンプル

どれを優先して追加しますか？