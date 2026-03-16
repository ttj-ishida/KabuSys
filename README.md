# KabuSys

日本株の自動売買プラットフォーム向けに設計された軽量ライブラリ群です。主にデータ取得（J-Quants）、ETL パイプライン、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）、および設定管理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の用途を想定したライブラリセットです。

- J-Quants API から株価・財務・マーケットカレンダーを取得して DuckDB に保存する。
- 日次 ETL パイプライン（差分更新・バックフィル・品質チェック）を実行する。
- データ品質チェック（欠損・スパイク・重複・日付不整合）を行う。
- 監査ログ（シグナル、発注要求、約定）用スキーマを提供してトレーサビリティを確保する。
- 環境変数・設定の一元管理を行う（.env 自動読み込み対応）。

設計上のポイント:
- API レート制限とリトライ（指数バックオフ）に対応。
- データ保存は冪等に行う（ON CONFLICT DO UPDATE）。
- すべての日時は UTC を基本に扱う（監査ログ等）。

---

## 主な機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（OS 環境変数 > .env.local > .env）
  - 必須 env チェック helper（settings）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得
  - RateLimiter（120 req/min）、リトライ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ保存する save_* 関数（冪等）
- DuckDB スキーマ定義／初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution レイヤーのテーブル定義
  - init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日ベースの差分）、バックフィル、カレンダー先読み
  - run_daily_etl() により市場カレンダー→株価→財務→品質チェックを一括実行
  - ETL 実行結果を ETLResult で返却（品質問題やエラーを集約）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク（前日比閾値）、日付不整合チェック
  - run_all_checks() でまとめて実行
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブルとインデックス
  - init_audit_schema(), init_audit_db()

未実装だが想定される領域（プレースホルダ）:
- strategy/
- execution/
- monitoring/

---

## セットアップ手順

前提
- Python 3.10 以降を推奨（型ヒントに | 演算子などを使用）
- duckdb を利用します

1. リポジトリをチェックアウト
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb
   - （開発時は pip install -e . など）

4. 環境変数の準備
   - プロジェクトルート（pyproject.toml または .git のある場所）に .env / .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu API（証券会社連携）用パスワード
- SLACK_BOT_TOKEN — 通知用 Slack bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

オプション（デフォルトあり）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — データベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 で自動 .env 読み込みを無効化

例 .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## 使い方（サンプル）

以下は基本的なワークフローの例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = schema.init_schema(":memory:")
```

2) 監査ログスキーマ追加（必要な場合）
```python
from kabusys.data import audit

audit.init_audit_schema(conn)
# または監査専用 DB を別に作る:
# audit_conn = audit.init_audit_db("data/audit.duckdb")
```

3) 日次 ETL を実行（市場カレンダー・株価・財務を取得して保存し、品質チェックを実行）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ今日を基準に実行
print(result.to_dict())
```

run_daily_etl は ETLResult を返します。result.has_errors / result.has_quality_errors などで判定できます。

4) J-Quants の個別 API 呼び出し（テスト・デバッグ用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

token = get_id_token()  # settings.jquants_refresh_token を使って id_token を取得
records = fetch_daily_quotes(code="7203", date_from=date(2023,1,1), date_to=date(2023,12,31))
```

5) 品質チェックを個別に実行
```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=None)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- jquants_client はレート制限（120 req/min）とリトライ機構を内蔵しています。大量取得時は実行時間に影響します。
- get_id_token() は内部で自動的にトークンをキャッシュ・リフレッシュします（401 の際に1回リフレッシュして再試行）。

---

## ディレクトリ構成

以下は主要ファイル・モジュールの簡易ツリー（src ベース）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      — J-Quants API クライアント (fetch_*, save_*)
      - schema.py              — DuckDB スキーマ定義 & init_schema
      - pipeline.py            — ETL パイプライン（run_daily_etl 等）
      - audit.py               — 監査ログ（signal/order/execution）スキーマ
      - quality.py             — データ品質チェック
    - strategy/
      - __init__.py            — 戦略コード用プレースホルダ
    - execution/
      - __init__.py            — 発注・ブローカー連携用プレースホルダ
    - monitoring/
      - __init__.py            — 監視用プレースホルダ

各ファイルの役割は上記の「主な機能一覧」参照。

---

## 開発・運用上の注意

- スキーマ変更は互換性に注意してください。init_schema と init_audit_schema は冪等にテーブルを作成しますが、既存カラム変更や削除は手動での移行が必要です。
- ETL の差分ロジックは raw テーブルの最終日付を基準にします。外部からデータを直接挿入すると想定と異なる動作をする可能性があります。
- audit テーブルは削除しない前提で設計されています（ON DELETE RESTRICT／監査ログは基本 never delete）。
- すべてのタイムスタンプは UTC を前提とします（監査テーブル初期化で SET TimeZone='UTC' を実行）。

---

## ライセンス・貢献

本リポジトリ固有のライセンスや貢献ルールはこの README に含まれていません。実運用に入れる前にライセンス設定、CI、テストの追加、そして運用ドキュメント（運用時のリトライ方針、障害時の手順、監査ログ保存ポリシーなど）を整備してください。

---

README に含めてほしい追加情報（例: 実際の .env.example、サンプルデータ、CI 設定、Dockerfile）や、特定のユースケース向けの使い方があれば教えてください。必要に応じて追記・拡張します。