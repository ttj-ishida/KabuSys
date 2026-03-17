# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群。  
J-Quants や kabuステーション 等の外部 API からのデータ取得、DuckDB によるデータ永続化、ETL パイプライン、ニュース収集、データ品質チェック、監査ログなどを提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT）で保存
- API レート制限・リトライ・トークン自動リフレッシュを考慮
- Look‑ahead bias を避けるためフェッチ時刻（fetched_at）やタイムゾーンを明示
- SSRF / XML Bomb 等のセキュリティ対策を考慮した実装

バージョン: 0.1.0

---

## 機能一覧

- 設定管理
  - .env（.env.local）または環境変数から設定を自動読込（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）
  - 必須環境変数のラップ（settings オブジェクト）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務指標、JPX カレンダーの取得
  - レートリミット、リトライ、401 の自動トークンリフレッシュ、ページネーション対応
  - DuckDB への冪等的保存（save_* 関数群）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理（URL 除去・空白正規化）、記事 ID の正規化（SHA-256）
  - SSRF 対策、受信サイズ上限、XML パースの安全化（defusedxml）
  - DuckDB へ冪等保存（raw_news, news_symbols）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス作成や init_schema / get_connection API
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終日を検出して未取得分のみ取得）
  - カレンダー先読み、backfill による後出し修正吸収、品質チェック統合
  - run_daily_etl により一括処理
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の探索、JPX カレンダー夜間更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレーサビリティ用スキーマの初期化
  - UTC 固定、冪等キー（order_request_id / broker_execution_id）
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで問題を集約
- その他
  - strategy / execution / monitoring パッケージのプレースホルダ（拡張ポイント）

---

## 動作環境・依存

- Python 3.10+
  - （型ヒントに | 演算子等を使用しているため 3.10 以上を想定）
- 必要パッケージ（代表的なもの）
  - duckdb
  - defusedxml
（プロジェクトの requirements.txt／pyproject.toml があればそれに従ってください）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# またはプロジェクト配布後: pip install -e .
```

---

## 環境変数（主なもの）

自動ロード順: OS 環境変数 > .env.local > .env  
プロジェクトルートは .git または pyproject.toml を基準に自動検出します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視系 SQLite（デフォルト: data/monitoring.db）

開発・テスト向け:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化

.env の例:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（基本）

1. リポジトリをクローンし、仮想環境を作成・有効化
2. 必要な依存をインストール（duckdb, defusedxml 等）
3. 環境変数を設定（上記 .env をプロジェクトルートに置く）
4. DuckDB スキーマ初期化
   - Python REPL / スクリプトで:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # :memory: も可
```
5. 監査ログ用スキーマを別 DB で初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要な例）

- settings の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
```

- J-Quants の ID トークンを取得
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

- 株価・財務・カレンダーの ETL（1日分・差分実行）
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- RSS ニュース収集（既知銘柄セットを渡してニュース→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"6758", "7203", "9984"}  # 例: 有効な銘柄コード集合
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- 生データを直接フェッチして保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = save_daily_quotes(conn, records)
```

- 品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

---

## 推奨運用フロー（例）

- 毎日夜間バッチ（Cron／Airflow 等）
  - calendar_update_job（カレンダー先読み）
  - run_daily_etl（データ差分取得 + 品質チェック）
  - ニュース収集ジョブ
  - 監査ログ用 DB の初期化は一度のみ（必要に応じてスキーマ追加）

- ライブ発注系は別プロセスで strategy → execution 層を実装し、audit テーブルでトレース

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ初期化（__version__）
- config.py — 環境変数・設定の読み込みと検証（settings）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save）
  - news_collector.py — RSS ニュース収集・保存・銘柄抽出
  - schema.py — DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py — ETL パイプライン（差分更新・run_daily_etl 等）
  - calendar_management.py — 市場カレンダー操作・更新ジョブ
  - audit.py — 監査ログスキーマ（signal/order_request/execution）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
- strategy/
  - __init__.py — 戦略レイヤー（拡張ポイント）
- execution/
  - __init__.py — 発注／約定管理（拡張ポイント）
- monitoring/
  - __init__.py — 監視機能（拡張ポイント）

---

## 注意事項 / 実運用時のポイント

- API トークン等の秘密情報は Git 管理しないこと（.env は .gitignore 推奨）。
- DuckDB ファイルのバックアップ・ローテーションを運用方針に合わせて行ってください。
- real money（live）環境では KABUSYS_ENV を `live` に設定し、ログ・モニタリングを強化してください。
- 実運用でのエラーや例外対応は呼び出し側（ジョブランナー）で堅牢に扱うこと（リトライ、アラート、ロールバック等）。
- strategy / execution / monitoring は本リポジトリの拡張ポイント。発注ロジックやリスク管理は運用者が実装してください。

---

もし README に追加したい内容（例: 実際の requirements.txt、CI 設定、より詳細なサンプルコード、運用 runbook 等）があれば教えてください。必要に応じて追記・整備します。