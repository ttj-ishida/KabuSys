# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
J-Quants からの市場データ取得、DuckDB によるデータ保管、ETL パイプライン、ニュース収集、品質チェック、監査ログ（発注〜約定トレーサビリティ）などの機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの取得（レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・メモリ保護）
- DuckDB による 3 層データレイヤ（Raw / Processed / Feature）と実行・監査用テーブルの定義
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）
- マーケットカレンダー管理（営業日判定・前後営業日検索）
- 監査ログ（signal → order_request → execution の追跡）
- 設定管理（.env 自動読み込み、必須環境変数の取得）

設計方針として冪等性（ON CONFLICT）、Look-ahead バイアス回避（fetched_at の記録）、堅牢なエラーハンドリングを重視しています。

---

## 主な機能一覧

- data/jquants_client.py
  - 株価日足（OHLCV）、四半期財務、マーケットカレンダーの取得
  - レートリミット（120 req/min）、指数バックオフリトライ、401 時の自動トークンリフレッシュ
  - DuckDB への冪等保存関数（save_*）

- data/news_collector.py
  - RSS フィードの安全な取得（SSRF 対策、gzip 上限、防爆対策）
  - URL 正規化（utm 等の除去）、SHA-256 ベースの記事 ID による冪等保存
  - raw_news / news_symbols への保存処理（チャンク挿入・INSERT RETURNING）

- data/schema.py / audit.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(), init_audit_db() による初期化

- data/pipeline.py
  - 日次 ETL のエントリポイント run_daily_etl()
  - 差分取得、バックフィル、品質チェックの統合

- data/quality.py
  - 欠損、重複、日付不整合、スパイク検出（QualityIssue オブジェクトを返す）

- data/calendar_management.py
  - 営業日判定、前後営業日取得、範囲内営業日取得、夜間カレンダー更新ジョブ

- config.py
  - 環境変数読み込み（.env / .env.local をプロジェクトルートから自動読み込み）
  - settings オブジェクト経由で必須設定を取得

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントの表記や挙動を使用）
- Git

1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - 追加で必要なパッケージがあれば適宜インストールしてください（例: requests 等）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（実行に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション等の API パスワード（本プロジェクトの一部モジュールが利用）
- SLACK_BOT_TOKEN: Slack 通知用トークン（監視機能を使う場合）
- SLACK_CHANNEL_ID: Slack チャネル ID

任意（デフォルトあり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用、デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 .env
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡易ガイド・コード例）

以下は主要な操作の例です。プロジェクトのモジュールを直接インポートして使用します。

- DuckDB スキーマ初期化（最初に一度だけ行う）
```python
from kabusys.data.schema import init_schema

# ファイル DB の初期化（親ディレクトリを自動作成）
conn = init_schema("data/kabusys.duckdb")
```

- 監査ログ用 DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- 日次 ETL の実行
```python
from kabusys.data.schema import get_connection
from kabusys.data.pipeline import run_daily_etl

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を省略すると今日を基準に実行
print(result.to_dict())
```

- 市場カレンダーの夜間更新ジョブ
```python
from kabusys.data.schema import get_connection
from kabusys.data.calendar_management import calendar_update_job

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.schema import get_connection
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出用に有効銘柄コードセットを渡すと news_symbols の紐付けを行う
known_codes = {"7203", "6758", "9984"}  # 例
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- J-Quants から生データを直接取得する（テスト用途など）
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
from kabusys.data.schema import get_connection

id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
records = jq.fetch_daily_quotes(id_token=id_token, date_from=None, date_to=None)
conn = get_connection("data/kabusys.duckdb")
jq.save_daily_quotes(conn, records)
```

- 設定の参照
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## API/モジュールのポイント

- jquants_client
  - _request() は内部でレートリミット・リトライ・401 リフレッシュを行う
  - fetch_* 系はページネーション対応
  - save_* は DuckDB へ冪等（ON CONFLICT）で保存

- news_collector
  - URL 正規化 → SHA-256（先頭32文字）で記事 ID を生成
  - defusedxml を使用して XML 攻撃を防ぐ
  - SSRF 対策としてリダイレクト先のスキーム/ホストを検査
  - 大きなレスポンスは MAX_RESPONSE_BYTES（デフォルト 10MB）で弾く

- pipeline
  - run_daily_etl はカレンダー取得 → 株価 ETL → 財務 ETL → 品質チェック の順で実行
  - 差分取得は DB の最終取得日を基準に自動算出（backfill 日数を指定可能）

- quality
  - 各種チェックは QualityIssue リストを返し、呼び出し元が継続/停止を判断する設計

- config
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）から .env/.env.local を自動読み込み
  - 自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定

---

## ディレクトリ構成

（抜粋）ソースは `src/kabusys` 以下に配置されています。

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ news_collector.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ calendar_management.py
   │  ├─ audit.py
   │  └─ quality.py
   ├─ strategy/
   │  └─ __init__.py
   ├─ execution/
   │  └─ __init__.py
   └─ monitoring/
      └─ __init__.py
```

主要ファイルの役割：
- config.py : 環境変数・設定管理
- data/schema.py : DuckDB のスキーマ定義・初期化
- data/jquants_client.py : J-Quants API クライアント
- data/pipeline.py : ETL パイプライン
- data/news_collector.py : RSS ニュース収集
- data/calendar_management.py : マーケットカレンダー管理
- data/audit.py : 監査ログ（発注〜約定のトレーサビリティ）
- data/quality.py : データ品質チェック

---

## 注意点 / 運用メモ

- J-Quants の API レート制限を超えないように設計されていますが、利用状況に応じて適切にパラメータ調整や実行間隔の管理を行ってください。
- DuckDB は単一ファイルで管理できますが、運用上はバックアップや権限管理に注意してください。
- .env に機密情報（トークン・パスワード）を置く場合は Git 管理から除外してください（.gitignore に追加）。
- run_daily_etl は品質チェックでエラーを返しても内部では可能な限り処理を継続します。致命的な問題時の挙動は呼び出し側（運用スクリプト）で判断してください。

---

必要に応じて README を拡張（例: CI / デプロイ手順、ユニットテストの実行、具体的な SQL やクエリ例）できます。追加したい項目があれば教えてください。