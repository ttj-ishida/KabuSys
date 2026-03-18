# KabuSys

日本株自動売買システムのライブラリ群（KabuSys）。  
J-Quants / kabuステーション 等から市場データを収集・整形し、DuckDB に保存、戦略・発注・監視の各レイヤーをサポートする基盤モジュール群です。

主な設計方針：
- データ取得は冪等（ON CONFLICT）かつトレース可能（fetched_at を UTC で記録）
- API レート制御・リトライ・トークンリフレッシュ対応
- ニュース収集で SSRF / XML Bomb 等の防御を実施
- データ品質チェック（欠損／スパイク／重複／日付不整合）を提供
- 監査ログ（シグナル→発注→約定のトレーサビリティ）をサポート

## 主要機能（機能一覧）
- J-Quants API クライアント
  - 株価日足（OHLCV）の取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）の取得
  - JPX マーケットカレンダーの取得
  - トークン自動リフレッシュ、レートリミット、再試行（指数バックオフ）
- DuckDB スキーマ定義・初期化
  - Raw / Processed / Feature / Execution / Audit 各レイヤー用テーブル定義
- ETL パイプライン
  - 差分取得（最終取得日からの差分、バックフィル）
  - 日次 ETL エントリポイント（run_daily_etl）
  - 市場カレンダーの先読み取得
- ニュース収集
  - RSS フィードから記事取得、前処理、冪等保存（raw_news）
  - 記事IDは正規化URLの SHA-256（先頭32文字）
  - 銘柄コード抽出と news_symbols への紐付け
- データ品質チェック（quality モジュール）
  - 欠損、スパイク、重複、日付不整合の検出
- 監査ログ（audit モジュール）
  - signal_events / order_requests / executions テーブル等でトレーサビリティを確保
- カレンダー管理（calendar_management）
  - 営業日判定・前後営業日検索・カレンダー更新ジョブ

## 要件
- Python 3.10 以上（型ヒントに | 演算子を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml
- （その他、slack 等の通知を行う場合は対応パッケージを追加）

例（最低限のインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

※ プロジェクト配布に requirements.txt / pyproject.toml があればそちらを使用してください。

## セットアップ手順

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境の作成と依存インストール（上記参照）

3. 環境変数の設定
- .env/.env.local をプロジェクトルートに置くと自動で読み込まれます（自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須の環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
  - SLACK_BOT_TOKEN       : Slack ボットトークン（通知機能を使う場合）
  - SLACK_CHANNEL_ID      : Slack チャンネルID（通知機能を使う場合）
- 任意（デフォルトあり）:
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DuckDB スキーマ初期化
- デフォルトのファイルは settings.duckdb_path（デフォルト: data/kabusys.duckdb）。
- メモリDB を使う場合は ":memory:" を指定可能。

例:
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # ファイル作成+テーブル作成
```

監査用 DB を別に初期化する場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

## 使い方（主要な API 例）

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 株価 ETL（個別日・差分制御）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

# conn は init_schema による接続
fetched, saved = run_prices_etl(conn, target_date=date.today())
```

- ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 事前に有効銘柄コードセットを用意
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数, ...}
```

- カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print("calendar saved:", saved)
```

- J-Quants トークン取得（直接）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用
```

- DuckDB をインメモリで使ってテストする
```python
conn = init_schema(":memory:")
# テスト用処理...
```

## 設計上の注意点 / 運用上の注意
- J-Quants API のレート制限（120 req/min）を尊重するため内部でスロットリングしています。大量の同時リクエストは行わないでください。
- get_id_token() は 401 時に自動リフレッシュを試みます。refresh_token は安全に保管してください。
- ニュース収集は外部 URL を扱うため、SSRF や XML インジェクション対策を組み込んでいます（defusedxml、リダイレクト検査、プライベートIPブロック等）。
- DuckDB テーブルは ON CONFLICT / RETURNING を多用して冪等性を確保します。
- ETL パイプラインは Fail-Fast にしない設計です。品質チェックで検出された問題に応じて呼び出し元が処理を決定してください。
- 本ライブラリは戦略・実際のブローカー接続を含めたフルなトレーディングシステムの一部です。実運用（特に live 環境）では十分なテストとリスク管理を行ってください。

## ディレクトリ構成（主要ファイル）
以下はソースの主要なファイル/モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     # 環境変数・設定管理（.env 自動読み込み）
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py           # RSS ニュース収集・保存・銘柄抽出
    - schema.py                   # DuckDB スキーマ定義・初期化
    - pipeline.py                 # ETL パイプライン（run_daily_etl 他）
    - calendar_management.py      # 市場カレンダー管理・判定ユーティリティ
    - audit.py                    # 監査ログ（signal/order/execution）
    - quality.py                  # データ品質チェック
  - strategy/
    - __init__.py                 # （戦略モジュール用プレースホルダ）
  - execution/
    - __init__.py                 # （発注実行モジュール用プレースホルダ）
  - monitoring/
    - __init__.py                 # （監視モジュール用プレースホルダ）

※ 実際のプロジェクトツリーに合わせて README を調整してください。

## よく使う環境変数（まとめ）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN (通知を使う場合)
  - SLACK_CHANNEL_ID (通知を使う場合)
- オプション / デフォルトあり:
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - KABUSYS_ENV (development | paper_trading | live) — default development
  - LOG_LEVEL — default INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env 自動読み込みを無効化

## 追加メモ
- テスト実行時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して環境依存の自動ロードを抑制できます。
- DuckDB の SQL 実行はパラメータバインド（?）を用いているので SQL インジェクションのリスクが低減されていますが、外部からの入力に対する適切な検証は必要です。

---

何か特定の利用例（例: バックフィルの設定、Slack 通知の実装、監査ログの参照クエリなど）について README に追記したい場合は、用途を教えてください。具体的なコード例・設定例を追加します。