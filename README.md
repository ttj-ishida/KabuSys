# KabuSys

日本株向けの自動売買／データ基盤ライブラリ群です。J-Quants や kabuステーション 等からのデータ取得、DuckDB を用いたスキーマ定義・ETL、ニュース収集、データ品質チェック、監査ログ機能などを提供します。

主な利用対象は、データパイプライン（市場データ取得・前処理）、戦略レイヤー、実行／監視レイヤーのバックエンド実装です。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数 / 設定管理
  - プロジェクトルートの `.env` / `.env.local` を自動読み込み（無効化フラグあり）
  - 必須設定の取得とバリデーション

- J-Quants クライアント（data/jquants_client.py）
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限対応（120 req/min）、リトライ（指数バックオフ）、401 の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録
  - DuckDB への冪等保存（ON CONFLICT）

- ニュース収集（data/news_collector.py）
  - RSS フィード取得、XML の安全パース（defusedxml）
  - URL 正規化とトラッキングパラメータ除去、記事ID は正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証・プライベート IP ブロック）
  - 受信サイズ制限、DuckDB へチャンク挿入（INSERT ... RETURNING）

- DuckDB スキーマ管理（data/schema.py）
  - Raw / Processed / Feature / Execution / Audit にまたがる豊富なテーブル定義
  - インデックス定義・初期化関数（init_schema / get_connection）
  - 監査ログ用スキーマ（audit モジュール）を別途初期化可能

- ETL パイプライン（data/pipeline.py）
  - 差分取得（最後の取得日からの差分）とバックフィル（後出し修正吸収）
  - カレンダー先読み、品質チェックの実行（quality モジュール）
  - 日次 ETL 実行エントリ（run_daily_etl）

- カレンダー管理（data/calendar_management.py）
  - 市場カレンダーの差分更新ジョブ、営業日判定（is_trading_day など）
  - next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ

- データ品質チェック（data/quality.py）
  - 欠損、重複、スパイク、日付不整合チェック
  - QualityIssue オブジェクトで詳細を返す（severity: error/warning）

- 監査ログ（data/audit.py）
  - signal → order_request → execution の階層を UUID でトレース
  - 監査テーブル初期化（init_audit_schema / init_audit_db）

- プレースホルダとして strategy/ execution / monitoring パッケージを用意

---

## 必要条件

- Python 3.10 以上（型注釈に `X | None` を使用）
- 依存パッケージ（一例）
  - duckdb
  - defusedxml

pip を利用する場合の例:
```
pip install duckdb defusedxml
```

プロジェクトが配布される場合は requirements.txt / pyproject.toml に依存関係を追加してください。

---

## セットアップ手順

1. リポジトリを取得:
```
git clone <repo-url>
cd <repo>
```

2. 仮想環境（任意）を作成して有効化:
```
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール:
```
pip install duckdb defusedxml
# 開発用: pip install -e .
```

4. 環境変数の設定
- プロジェクトルートに `.env`（または `.env.local`）を配置します。
- 自動で `.env` を読み込む挙動は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで無効化可能です（テスト等で利用）。

例 `.env`（最低限必要なキー）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=securepassword
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
# 任意
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

5. DuckDB スキーマ初期化
- 初回はスキーマを作成しておきます。Python REPL またはスクリプトで:
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイルが無ければ作成されます
conn.close()
```

- 監査ログ用スキーマを別DBに作る場合:
```
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
audit_conn.close()
```

---

## 使い方（簡単な例）

- 日次 ETL を実行してデータを取得・保存・品質チェックまで行う:
```
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # 初回のみ、すでに初期化済みなら get_connection でも可
result = run_daily_etl(conn)  # target_date を渡すことも可能
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブを実行:
```
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(stats)
conn.close()
```

- JPX カレンダーの夜間バッチ（差分更新）:
```
from kabusys.data.schema import init_schema
from kabusys.data.calendar_management import calendar_update_job

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved:", saved)
conn.close()
```

- データ品質チェックの個別実行:
```
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.quality import run_all_checks

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
conn.close()
```

- J-Quants の直接利用（ID トークン取得や API 呼び出し）:
```
from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
token = get_id_token()  # settings.jquants_refresh_token を使用
records = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
```

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABU_API_BASE_URL (任意): kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須): Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須): Slack 通知先チャンネル ID
- DUCKDB_PATH (任意): DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意): 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意): environment。development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意): ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動読み込みを無効化

注意: Settings クラスは必須のキーが足りない場合に ValueError を投げます。

---

## ディレクトリ構成

以下は主要ファイル・ディレクトリ構成の抜粋です:

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得＋保存）
    - news_collector.py      -- RSS/news 収集・保存・銘柄抽出
    - schema.py              -- DuckDB スキーマ定義と初期化
    - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py -- マーケットカレンダー管理
    - audit.py               -- 監査ログスキーマ（signal/order/execution）
    - quality.py             -- データ品質チェック
  - strategy/
    - __init__.py            -- 戦略関連（拡張用）
  - execution/
    - __init__.py            -- 発注・ブローカ連携（拡張用）
  - monitoring/
    - __init__.py            -- 監視・アラート（拡張用）

ドキュメントや DataPlatform.md / DataSchema.md 参照を想定した設計が組み込まれています（実装は上記の Python モジュール内に反映）。

---

## 運用上の注意点

- API レート制限とリトライポリシーを実装していますが、実運用ではさらにスロットリングや監視を追加してください。
- DuckDB のファイル権限やバックアップ戦略を検討してください（単一ファイルにデータが集約されます）。
- ニュース収集では RSS の多様性やエンコーディング差異に注意してください。外部フィードの可用性に依存します。
- 監査ログ（audit）は削除しない前提で設計されています。スキーマ変更時は互換性に注意してください。
- 自動 .env 読み込みは便利ですが、本番では OS 環境変数や秘密管理サービスを推奨します。

---

何か追加で README に載せたい情報や、実際に使用するワークフロー（cron / Airflow / k8s Job 等）の例があれば教えてください。それに合わせた起動スクリプトや運用ガイドを追記します。