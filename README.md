# KabuSys

日本株自動売買システムのコアライブラリ（軽量プロトタイプ）

このリポジトリは、J‑Quants API を用いたデータ取得、DuckDB によるデータ格納・スキーマ管理、
日次 ETL パイプライン、品質チェック、監査ログ（発注→約定のトレース）などを提供する
基盤コンポーネント群です。戦略（strategy/）、発注（execution/）、監視（monitoring/）のための
骨組みを備え、実装を拡張して自動売買システムを構築できます。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数／.env の自動読み込み（.env.local を優先して上書き）
  - プロジェクトルートは .git または pyproject.toml を探索して決定
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能
- J‑Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX 市場カレンダー取得
  - レート制限（120 req/min）を守る固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回、408/429/5xx を再試行）
  - 401 受信時はリフレッシュトークンで自動再取得して一度だけリトライ
  - 取得時刻（UTC の fetched_at）を付与して Look‑ahead Bias を防止
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義とインデックス
  - スキーマ初期化（init_schema）と接続取得ユーティリティ
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（DB の最終取得日を参照）、バックフィル（デフォルト 3 日）
  - カレンダーの先読み（デフォルト 90 日）を含む日次 ETL（run_daily_etl）
  - 品質チェック（欠損、重複、スパイク、日付不整合）を実行可能
  - ETL 結果を ETLResult オブジェクトで返却（品質問題／エラー情報含む）
- 監査ログ（kabusys.data.audit）
  - 戦略→シグナル→発注要求→約定まで UUID で辿れる監査テーブル群
  - 発注要求は冪等キー（order_request_id）で制御
  - すべての TIMESTAMP は UTC 保存を想定
- データ品質チェック（kabusys.data.quality）
  - check_missing_data, check_duplicates, check_spike, check_date_consistency
  - run_all_checks で一括実行し問題リストを取得

※ strategy、execution、monitoring パッケージは骨組みとして存在します（拡張して使用）。

---

## 動作要件

- Python 3.10 以上（コード内で PEP 604 の型記法（X | Y）を使用しているため）
- 主要依存パッケージ:
  - duckdb
- 標準ライブラリ: logging, urllib, json, datetime 等

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb
# パッケージとしてインストールする場合は packaging を整備の上 `pip install -e .` 等
```

---

## 環境変数（主要）

以下はコードで参照される主要な環境変数です。`.env` や `.env.local` に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

オプション（デフォルト値）:
- KABUSYS_ENV: 実行環境。許容値: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" にすると自動 .env 読み込みを無効化
- KABUS_API_BASE_URL: kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite（別用途）デフォルト: data/monitoring.db

.env の読み込み順序:
- OS 環境変数 > .env.local > .env
（.env.local は .env を上書き、既存の OS 環境は保護されます）

.env のパースはシェル形式を想定しています（export 句やクォート、コメント対応あり）。

---

## セットアップ手順（最短）

1. リポジトリをクローンし仮想環境を作成
2. 依存ライブラリをインストール（例: duckdb）
3. プロジェクトルートに `.env`（および必要なら `.env.local`）を作成して環境変数を設定
4. DuckDB スキーマを初期化

例:
```python
# scripts/init_db.py
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数/デフォルトから取得される
conn = schema.init_schema(settings.duckdb_path)
# 監査ログテーブルを追加する場合:
from kabusys.data import audit
audit.init_audit_schema(conn)

print("DB initialized:", settings.duckdb_path)
```

実行:
```bash
python scripts/init_db.py
```

---

## 使い方（代表的な例）

### 日次 ETL を実行してデータを取り込む

簡単なスクリプト例:
```python
from kabusys.data import schema, pipeline
from kabusys.config import settings
from datetime import date

# DB 初期化（まだなら）
conn = schema.init_schema(settings.duckdb_path)

# 今日分の ETL を実行（品質チェック有効、デフォルトバックフィル）
result = pipeline.run_daily_etl(conn, target_date=date.today())

print("ETL result:", result.to_dict())
if result.has_errors or result.has_quality_errors:
    print("問題あり:", result.errors, [q.check_name for q in result.quality_issues])
```

- run_daily_etl は market calendar → prices → financials → quality checks の順で処理
- ETLResult に取得件数、保存件数、品質問題（QualityIssue のリスト）、エラー一覧を格納

### 個別ジョブ (価格のみ) の実行
```python
from kabusys.data import schema, pipeline
from kabusys.config import settings
from datetime import date

conn = schema.get_connection(settings.duckdb_path)
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
print("prices fetched:", fetched, "saved:", saved)
```

### 監査ログ（発注監査）テーブルの初期化
```python
from kabusys.data import schema, audit
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
audit.init_audit_schema(conn)
```

---

## 開発者向けメモ

- jquants_client:
  - 内部に RateLimiter を持ち、モジュールレベルで id_token キャッシュを共有します。
  - get_id_token は refresh_token（環境変数）を使って ID トークンを取得します。
  - fetch_* 系はページネーション対応（pagination_key）で全件取得します。
  - save_* 系は DuckDB に対して ON CONFLICT DO UPDATE を使って冪等に保存します。

- pipeline:
  - 差分更新の判定には raw_* の最大日付を参照します（get_last_price_date 等）。
  - バックフィルをデフォルトで 3 日行い、API の後出し修正に対応します。
  - 品質チェックは fail-fast しない設計で、すべてのチェック結果を収集して返します。

- quality:
  - QualityIssue は check_name・table・severity（error/warning）・detail・rows を持つ
  - run_all_checks でまとめて呼び出し、logging レベルに応じて情報を出力します

---

## ディレクトリ構成

（主なファイル／ディレクトリ）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py     — J‑Quants API クライアント（取得・保存ロジック）
    - pipeline.py           — ETL パイプライン（run_daily_etl など）
    - schema.py             — DuckDB スキーマ定義・初期化
    - audit.py              — 監査ログ（発注→約定のトレース）定義/初期化
    - quality.py            — データ品質チェック
  - strategy/               — 戦略層（拡張用）
  - execution/              — 発注実行層（拡張用）
  - monitoring/             — 監視用（拡張用）

プロジェクトルートに .env/.env.local を置くことで自動読み込みされます（.git または pyproject.toml をルート判定に使用）。

---

## 注意事項 / ベストプラクティス

- 本ライブラリはデータ基盤と監査ログの基礎を提供します。実際の取引ロジック（ポジション管理・リスク管理・ブローカ接続など）は別途実装してください。
- 実運用（live）実行時は KABUSYS_ENV を `live` に設定して挙動を明確にすることを推奨します。
- 秘密情報（リフレッシュトークン等）は Git 管理下に置かないでください。`.env.local` を利用してローカルに安全に保持してください。
- J‑Quants API のレート制限を厳守する設計ですが、運用時は実際のレートに応じた調整や監視を行ってください。

---

必要があれば、README にサンプル CI/CD ワークフロー、より詳細な .env.example、または db 初期化／バックフィルの運用手順を追加できます。希望する内容があれば教えてください。