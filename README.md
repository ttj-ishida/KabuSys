# KabuSys

日本株向け自動売買プラットフォームのライブラリ（コアモジュール群）。  
主にデータ取得・ETL、データ品質チェック、監査ログ、（将来的な）戦略・発注周りの基盤機能を提供します。

---

## プロジェクト概要

KabuSys は次の目的を持った内部ライブラリです。

- J-Quants API から株価・財務・マーケットカレンダー等を取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマと初期化
- 環境変数ベースの設定管理（.env 自動読み込み機能）
- 将来的に戦略（strategy）、発注実行（execution）、監視（monitoring）コンポーネントを統合

設計上の特徴：
- J-Quants API のレート制御（120 req/min）とリトライ（指数バックオフ、401 時の自動トークンリフレッシュ）
- データ取得時の fetched_at によるトレーサビリティ（Look-ahead Bias 防止）
- DuckDB への保存は冪等（ON CONFLICT DO UPDATE）
- 品質チェックは Fail-Fast ではなく問題を全て収集して呼び出し元で判断

---

## 主な機能一覧

- 設定管理
  - .env / .env.local をプロジェクトルートから自動読み込み（無効化可能）
  - 必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）
- J-Quants データクライアント（data.jquants_client）
  - get_id_token、fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar
  - API 呼び出しのレート制御、リトライ、トークン自動リフレッシュ
  - DuckDB への保存用関数（save_daily_quotes 等）
- DuckDB スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution 層にまたがるテーブル定義
  - init_schema(db_path) による初期化（冪等）
- ETL パイプライン（data.pipeline）
  - 差分更新（最終取得日を基にバックフィル）、calendar の先読み
  - run_daily_etl による一括処理（calendar → prices → financials → 品質チェック）
  - ETLResult による処理結果の集約
- 品質チェック（data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返却
- 監査ログ（data.audit）
  - signal_events、order_requests、executions 等の監査テーブルとインデックス
  - init_audit_schema / init_audit_db による初期化

---

## セットアップ手順

前提
- Python 3.9+（タイプヒントに union 型や typing を使用しているため 3.9 以上を想定）
- DuckDB を利用（pip でインストール可能）

例）仮想環境作成と依存インストール
```
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install duckdb
# pip install -e . などでローカルパッケージとしてインストールする場合は pyproject/setup に合わせて実行
```

環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack チャネル ID（必須）

オプション（デフォルトあり）
- KABU_API_BASE_URL : kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV : environment ("development", "paper_trading", "live")（default: development）
- LOG_LEVEL : ログレベル（"DEBUG","INFO",...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env 読み込みを無効化する場合に 1 を設定

サンプル .env（プロジェクトルートに .env を置くと自動読み込みされます）
```
# .env.example
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

※ 自動読み込みが不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（基本例）

1) DuckDB スキーマを初期化して ETL を実行する（日次 ETL）

Python での簡単な例：
```
from datetime import date
from kabusys.data import schema, pipeline

# DB 初期化（ファイルパス or ":memory:"）
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())

print(result.to_dict())
```

2) J-Quants からデータを直接取得して保存する（個別実行）
```
from kabusys.data import jquants_client as jq
from kabusys.data import schema
import duckdb

conn = schema.get_connection("data/kabusys.duckdb")  # スキーマ初期化済みを想定

# 指定銘柄の期間を取得して保存
records = jq.fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
jq.save_daily_quotes(conn, records)
```

3) 監査ログスキーマを追加する
```
from kabusys.data import audit, schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

4) 設定を参照する
```
from kabusys.config import settings

print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## API の挙動・注意点

- jquants_client._request は内部で固定間隔のスロットリング（120 req/min）を行います。大量データ取得時はページネーション経由で安全に取得されます。
- HTTP 401 を受け取った場合はリフレッシュトークンを使って ID トークンを自動更新し 1 回リトライします（無限ループ回避のため最大 1 回）。
- リトライ対象は 408 / 429 / 5xx などの一時的エラー。指数バックオフを採用。
- データ保存関数は冪等（ON CONFLICT DO UPDATE）なので、再実行しても重複を避けられます。
- ETL パイプラインのバックフィル（backfill_days）はデフォルト 3 日。API の「後出し修正」を吸収するために最終取得日から数日前を再取得します。
- 品質チェックはエラー・警告を収集します。呼び出し側で結果（ETLResult.quality_issues）を確認してアラートや停止判断を行ってください。

---

## ディレクトリ構成

代表的なファイル構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・設定管理（.env 自動ロード）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - schema.py                       — DuckDB スキーマ定義・初期化
    - pipeline.py                     — ETL パイプライン（差分更新・品質チェック）
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログスキーマ
    - pipeline.py
  - strategy/
    - __init__.py                      — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py                      — 発注実行モジュール（拡張ポイント）
  - monitoring/
    - __init__.py                      — 監視関連（拡張ポイント）

※ 実際のプロジェクトルートには pyproject.toml や .git/ があり、config._find_project_root がそれを基に .env を探索します。

---

## 開発・拡張ポイント

- strategy / execution / monitoring パッケージは現状プレースホルダです。ここに戦略ロジック、リスク管理、ブローカー接続、監視エンドポイントを実装できます。
- DuckDB スキーマは将来的に追加カラムやインデックスを足すことができますが、既存データとの互換性に注意してください。
- テストの際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、settings をモックするか環境変数を直接注入してください。
- 大量データ取得や長時間の ETL 実行時はログ（LOG_LEVEL）を DEBUG にして詳細を確認してください。

---

もし README にサンプル .env.example、実行スクリプト（CLI ラッパー）や CI 用の初期化手順を追加したい場合は、用途（開発用 / 本番デプロイ / テスト）を教えてください。必要に応じて例を追記します。