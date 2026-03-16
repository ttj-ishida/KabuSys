# KabuSys

日本株自動売買システム（ライブラリ・コンポーネント群）

このリポジトリは、J-Quants や kabuステーション 等から市場データを取得して DuckDB に蓄積し、品質チェック・戦略・発注までの基盤機能を提供するコンポーネント群です。ETL（抽出・変換・ロード）パイプライン、データスキーマ、監査ログ（トレーサビリティ）、データ品質チェックなどを備えています。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API からのデータ取得
  - 株価日足（OHLCV）
  - 財務データ（四半期 BS/PL）
  - JPX マーケットカレンダー（祝日・半日・SQ）
- API リクエスト管理
  - レート制限（120 req/min）に基づくスロットリング
  - リトライ（指数バックオフ、401 時はトークン自動リフレッシュ）
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
- DuckDB ベースのスキーマ（冪等性を意識した INSERT ... ON CONFLICT）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックスの定義
- ETL パイプライン（差分取得・バックフィル）
  - 市場カレンダー先読み、差分更新、品質チェック（欠損・重複・スパイク・日付不整合）
  - ETL 実行結果（ETLResult）で収集・監査可能
- 監査ログ（signal → order_request → execution のトレーサビリティ）
  - 発注要求（冪等キー）や約定ログを永続化
  - UTC タイムスタンプを保証
- データ品質チェックモジュール（複数チェックをまとめて実行）

---

## 前提（Prerequisites）

- Python 3.10 以上（型ヒントに `X | Y` を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - （標準ライブラリ: urllib, json, logging 等を使用）
- J-Quants / kabuステーション / Slack 等の API トークン（環境変数で設定）

実際に利用する際はプロジェクトの requirements.txt に沿って依存パッケージをインストールしてください。最低限の手順例:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install duckdb
# 他の依存があれば追加でインストール
```

---

## 環境変数（.env）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主要な環境変数（例）

- J-Quants
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- kabuステーション API
  - KABU_API_PASSWORD (必須) — kabu API パスワード
  - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- Slack
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- 実行モード / ログ
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

サンプル .env（プロジェクトルートに配置）:

```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

2. 依存パッケージをインストール（例: duckdb など）

```bash
python -m pip install duckdb
# その他、プロジェクトで必要なパッケージを追加
```

3. .env を作成して必要な環境変数を設定

4. DuckDB スキーマ初期化

プロジェクト内から Python を実行してスキーマを作成します（デフォルトパスを使用する場合）:

```bash
python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
```

または、アプリケーションコード内で:

```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

db_path = settings.duckdb_path  # settings から既定のパスを取得
conn = init_schema(db_path)
```

監査ログテーブルのみを追加したい場合:

```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema('data/kabusys.duckdb')
init_audit_schema(conn)
```

---

## 使い方（簡単な例）

- J-Quants の ID トークンを明示的に取得する

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # JQUANTS_REFRESH_TOKEN を settings から使って取得
```

- データのフェッチと保存（例: 株価日足を取得して保存）

```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')
records = jq.fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved={saved}")
```

- 日次 ETL を実行する（ログや品質チェックを含む）

```python
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema('data/kabusys.duckdb')
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- 品質チェックだけ実行する

```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

- 監査ログ（order_requests / executions）を初期化する

```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema('data/kabusys.duckdb')
init_audit_schema(conn)
```

---

## 推奨ワークフロー / 運用メモ

- 定期実行: run_daily_etl を cron / systemd timer / Airflow 等で日次実行してデータを差分更新する。
- 監査とモニタリング: ETLResult や quality モジュールの検出結果を Slack 等に通知して異常を監視する。
- テスト: 自動テスト実行時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して .env 自動読み込みを無効化できます。
- 本番 / ペーパー切り替え: KABUSYS_ENV に `development` / `paper_trading` / `live` を設定して動作モードを切替える。is_live / is_paper / is_dev が利用可能です。

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 以下）

- src/
  - kabusys/
    - __init__.py
    - config.py
      - 環境変数管理・自動 .env ロード・Settings クラス
    - data/
      - __init__.py
      - jquants_client.py
        - J-Quants API クライアント（フェッチ、保存、認証、レート制御、リトライ）
      - schema.py
        - DuckDB スキーマ定義、init_schema / get_connection
      - pipeline.py
        - ETL パイプライン（差分取得、バックフィル、品質チェック）
      - audit.py
        - 監査ログ（signal_events, order_requests, executions）初期化
      - quality.py
        - データ品質チェック（欠損、重複、スパイク、日付不整合）
    - strategy/
      - __init__.py
      - （戦略ロジックを配置する想定）
    - execution/
      - __init__.py
      - （証券会社発注・注文管理を配置する想定）
    - monitoring/
      - __init__.py
      - （監視関連を配置する想定）

---

## 開発者向け補足

- 型アノテーションや設計メモはコード内の docstring に詳述されています。特に jquants_client は取得時刻のトレーサビリティ（fetched_at）やページネーション・トークンキャッシュ等の実装に注意してください。
- DuckDB スキーマは外部キーやインデックスを含みます。既存データがある場合も冪等にテーブル作成を行うため安全に初期化できます。
- quality モジュールは Fail-Fast ではなく全件検出を行い、呼び出し元が重大度に応じて処理を決定できます。

---

もし README に追加したいサンプルスクリプトやデプロイ手順（Dockerfile / systemd / Airflow など）があれば、要望を教えてください。README を運用方針や CI/CD 用に拡張できます。