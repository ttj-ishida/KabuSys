# KabuSys

日本株向けの自動売買／データプラットフォーム共通ライブラリです。  
J-Quants などの外部データ取得、DuckDB ベースのスキーマ管理、ETL パイプライン、ニュース収集、データ品質チェック、監査ログ（発注→約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に蓄積する ETL パイプライン
- RSS フィード等からニュースを収集して記事と銘柄紐付けを行うニュース収集モジュール
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ
- 市場カレンダー管理（営業日判定、翌営業日/前営業日の計算）
- 設定管理（環境変数・.env の自動読み込み）

設計上のポイント:
- API レート制御・リトライ・トークン自動リフレッシュ（J-Quants）
- DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE / DO NOTHING）
- SSRF / XML BOM 等に配慮した安全な RSS 取り込み
- 品質チェックは fail-fast とせず、問題一覧を返す

---

## 機能一覧

- 設定管理
  - 環境変数およびプロジェクトルートの `.env` / `.env.local` の自動ロード
  - 必須環境変数のラッパー（`kabusys.config.settings`）

- データ取得（kabusys.data.jquants_client）
  - 日足価格（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー
  - ページネーション対応、レートリミット、リトライ、トークン自動リフレッシュ
  - DuckDB へ保存する save_* 関数（冪等）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得、前処理、id 生成（正規化 URL の SHA-256 部分）
  - SSRF・Gzip・XML 攻撃対策、受信サイズ上限、DuckDB へのバルク保存
  - 記事と銘柄コードの紐付け（news_symbols）

- スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層の DuckDB DDL を定義
  - 初期化関数 `init_schema(db_path)`、接続取得 `get_connection(db_path)`

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（market calendar → prices → financials → 品質チェック）
  - 差分取得、バックフィル、品質チェックの集約（`run_daily_etl`）

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、期間内営業日取得、夜間更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions などの監査スキーマ
  - 監査スキーマの初期化（トランザクション対応）`init_audit_schema` / `init_audit_db`

- 品質チェック（kabusys.data.quality）
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - 各チェックは QualityIssue のリストを返す。`run_all_checks` で一括実行

---

## 必要条件（例）

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - defusedxml

（実環境では pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン／展開
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e . など）
4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか、OS 環境変数で設定します。
   - 自動読み込みはデフォルトで有効。無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

.env の例（.env.example を参考にしてください）:
    JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
    KABU_API_PASSWORD=<kabu_api_password>
    SLACK_BOT_TOKEN=<slack_bot_token>
    SLACK_CHANNEL_ID=<slack_channel_id>
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

注意:
- パッケージは起点ファイルの位置から親ディレクトリを上に辿り `.git` または `pyproject.toml` を見つけてプロジェクトルートを判定し、そこから `.env` / `.env.local` を読み込みます。

---

## 使い方（主要な例）

以下は最小限の使い方例です。実運用ではログ設定やエラーハンドリングを適切に行ってください。

- DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB に接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "6501"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
```

- 監査 DB 初期化（監査専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

- 品質チェックを単体実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = run_all_checks(conn, reference_date=date.today())
for i in issues:
    print(i)
```

- J-Quants トークン取得（内部キャッシュ利用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使って取得
```

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（1 を設定）

注意: `kabusys.config` モジュールはプロジェクトルートを `.git` または `pyproject.toml` で判定し、`.env` / `.env.local` を自動で読み込みます。テスト等で自動読み込みを抑制したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - execution/                （発注・約定・ブローカー連携用モジュール群（未実装箇所））
  - strategy/                 （戦略モジュール置き場（未実装箇所））
  - monitoring/               （監視用モジュール置き場）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS 収集 / 前処理 / 保存ロジック
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py  — 市場カレンダーの管理・営業日ロジック
    - audit.py                — 監査ログ用スキーマ初期化
    - quality.py              — データ品質チェック

ファイル毎にドキュメンテーションと関数名が整備されており、上記 API を呼ぶことで主要処理を行えます。

---

## 開発者向けメモ

- DuckDB への大量挿入はチャンク化されています（news_collector など）。
- J-Quants API 呼び出しはレート制御・再試行を備えています。429 の場合は Retry-After ヘッダを優先します。
- ニュース記事 ID は URL 正規化（トラッキングパラメータ除去）後の SHA-256 の先頭 32 文字を使用して冪等性を保ちます。
- news_collector は SSRF 対策としてリダイレクト先のスキームやプライベート IP をチェックします。
- audit.init_audit_schema は必要に応じて transactional=True により DDL をトランザクション内で作成できます（DuckDB のトランザクション挙動に注意）。

---

不明点や README に追加したい内容（例: CLI、cron や systemd による定期実行例、さらに具体的な .env.example の内容など）があれば教えてください。README を用途に合わせて拡張します。