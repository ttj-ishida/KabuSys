# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買およびデータプラットフォーム向けのライブラリ群です。J-Quants や kabuステーション など外部サービスからデータを取得・永続化し、戦略・発注・監視のためのスキーマ／ユーティリティを提供します。

主な目的:
- 市場データ（株価、財務、マーケットカレンダー等）の収集と DuckDB への永続化
- データ品質チェック、監査ログ（シグナル→発注→約定のトレース）
- 戦略・実行・モニタリングのための共通基盤

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（必要に応じて無効化可能）
  - 必須設定のラッパー（settings オブジェクト）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）・財務（四半期 BS/PL）・JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応（固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回。HTTP 408/429/5xx の再試行）
  - 401 発生時の自動トークンリフレッシュ（1 回だけ再試行）
  - ページネーション対応
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar）

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化 API: init_schema(), get_connection()
  - インデックスやテーブル作成順を考慮した安全な初期化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions の監査テーブル
  - 冪等キー（order_request_id）を用いた重複防止
  - init_audit_schema() / init_audit_db()

- データ品質チェック（kabusys.data.quality）
  - 欠損（OHLC 欠損）検出
  - スパイク（前日比 ±X%）検出
  - 主キー重複検出
  - 日付不整合（未来日付・非営業日データ）検出
  - run_all_checks() による一括実行、QualityIssue オブジェクトで問題を返す

---

## 要件

最低限必要なライブラリ（例）
- Python 3.10+
- duckdb
- （標準ライブラリのみで動く部分が多いですが、実運用では HTTP 周りの設定や追加ライブラリが必要になる場合があります）

インストール例（プロジェクトルートで）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb
pip install -e .
```
（setup 配置がない場合は `pip install duckdb` としてライブラリを利用してください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。

2. 仮想環境を作成して有効化し、必要パッケージをインストールします（上記参照）。

3. 環境変数を設定します。プロジェクトルートに `.env` または `.env.local` を用意すると自動的に読み込まれます（自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須環境変数（例）:
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

任意（既定値あり）:
- KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
- LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL （デフォルト: INFO）
- DUCKDB_PATH=data/kabusys.duckdb （デフォルト）
- SQLITE_PATH=data/monitoring.db （デフォルト）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（クイックスタート）

以下はライブラリの主要なユースケースの例です。

- DuckDB スキーマ初期化:
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# ファイル指定で初期化
conn = init_schema(settings.duckdb_path)
# 既存 DB に接続するだけ
# conn = get_connection(settings.duckdb_path)
```

- J-Quants から日足を取得して DuckDB に保存:
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
# 必要なら明示的にトークン取得
id_token = get_id_token()

records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"saved {n} rows")
```

- 財務データ / マーケットカレンダーの取得・保存は同様:
  - fetch_financial_statements(), save_financial_statements()
  - fetch_market_calendar(), save_market_calendar()

- 監査ログ（監査用 DB を別に用意する場合）:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```
既存接続に追加する場合は init_audit_schema(conn) を使います。

- データ品質チェックの実行:
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import get_connection
from kabusys.config import settings

conn = get_connection(settings.duckdb_path)
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.severity, issue.detail)
    for row in issue.rows:
        print(row)
```

---

## 設計上の注意点 / 実装上のポイント

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml の存在）から行います。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- J-Quants クライアントはレート制限（120 req/min）とリトライを組み込んでいます。429 の場合は Retry-After ヘッダを優先します。
- トークンはモジュールレベルでキャッシュされ、401 発生時は一度だけリフレッシュして再試行します（無限再帰にならないよう制御）。
- DuckDB への挿入は ON CONFLICT DO UPDATE（冪等）を利用しています。
- 監査ログは削除しない前提で設計されています（FOREIGN KEY は ON DELETE RESTRICT など）。
- すべてのタイムスタンプは UTC 保存を前提にしています（監査モジュールは接続時に SET TimeZone='UTC' を実行します）。

---

## ディレクトリ構成

（プロジェクトルート: src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py                      （パッケージ初期化、version）
  - config.py                        （環境変数・設定管理、settings オブジェクト）
  - data/
    - __init__.py
    - jquants_client.py              （J-Quants API クライアント、fetch/save 系）
    - schema.py                      （DuckDB スキーマ定義・初期化）
    - audit.py                       （監査ログ用スキーマ・初期化）
    - quality.py                     （データ品質チェック）
  - strategy/
    - __init__.py                    （戦略関連モジュール置き場）
  - execution/
    - __init__.py                    （発注・執行関連モジュール置き場）
  - monitoring/
    - __init__.py                    （モニタリング関連モジュール置き場）

主なファイルの役割:
- config.py: 環境変数のパース（.env 自動読み込み含む）、Settings ラッパー
- data/jquants_client.py: 外部 API とのやり取り、変換ユーティリティ、DuckDB 保存関数
- data/schema.py: DuckDB の全テーブル DDL と init_schema API
- data/audit.py: 監査ログテーブルと init_audit_schema / init_audit_db
- data/quality.py: データ品質チェックロジック

---

## 主要 API サマリ

- kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.kabu_api_password
  - settings.kabu_api_base_url
  - settings.slack_bot_token
  - settings.slack_channel_id
  - settings.duckdb_path, settings.sqlite_path
  - settings.env / settings.is_live / settings.is_paper / settings.is_dev

- kabusys.data.jquants_client
  - get_id_token(refresh_token: Optional[str]) -> str
  - fetch_daily_quotes(id_token, code, date_from, date_to) -> list[dict]
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records) -> int
  - save_financial_statements(conn, records) -> int
  - save_market_calendar(conn, records) -> int

- kabusys.data.schema
  - init_schema(db_path) -> DuckDB connection
  - get_connection(db_path) -> DuckDB connection

- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(db_path) -> DuckDB connection

- kabusys.data.quality
  - check_missing_data(conn, target_date) -> list[QualityIssue]
  - check_spike(conn, target_date, threshold) -> list[QualityIssue]
  - check_duplicates(conn, target_date) -> list[QualityIssue]
  - check_date_consistency(conn, reference_date) -> list[QualityIssue]
  - run_all_checks(conn, target_date, reference_date, spike_threshold) -> list[QualityIssue]

---

## 補足 / よくある質問

- Q: .env のパース仕様は?
  - A: export を許容し、シングル/ダブルクォート内のエスケープに対応。行末コメントはクォート外かつ直前が空白／タブのときに認識します。

- Q: API のレート制限はどう担保されている?
  - A: モジュール内の _RateLimiter が固定間隔（60/120 秒）でスロットリングします。複数プロセスで同時に動かす場合は別途調整が必要です。

- Q: DuckDB の初期化は安全か?
  - A: init_schema は IF NOT EXISTS を用いて冪等にテーブルを作成します。初回だけ実行してください。

---

この README はコードベースの現状（v0.1.0）に基づいて作成しています。実際の運用や追加機能（戦略実装、実ブローカー連携、監視・アラート）に応じて README を拡張してください。質問やサンプルが必要であれば教えてください。